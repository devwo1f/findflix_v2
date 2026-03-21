from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import (
    RecommendationLog,
    RegionalAvailability,
    TasteEmbedding,
    Title,
    WatchHistory,
)
from app.schemas.recommendations import RecommendationItem, RecommendationRequest
from app.schemas.titles import AvailabilityInfo, TitleResponse

logger = structlog.get_logger(__name__)


class RecommendationService:
    """Orchestrates the full recommendation pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ml_base_url = settings.ML_SERVICE_URL

    async def get_recommendations(
        self,
        user_id: UUID,
        request: RecommendationRequest,
        region: str = "US",
    ) -> list[RecommendationItem]:
        logger.info("recommendation_pipeline_start", user_id=str(user_id), mood=request.mood, limit=request.limit)

        # 1. Retrieve user embedding
        embedding = await self._get_user_embedding(user_id)
        if embedding is None:
            logger.warning("no_embedding_found_fallback", user_id=str(user_id))
            return await self._fallback_recommendations(user_id, request.limit, region)

        # 2. Get candidates from ML service
        candidates = await self._get_candidates(embedding, request.limit * 3)

        # 3. Re-rank with user context
        user_context = {
            "mood": request.mood,
            "include_rewatches": request.include_rewatches,
            "region": region,
        }
        ranked = await self._rerank(candidates, user_context)

        # 4. Apply filters (rewatches, region, diversity)
        filtered = await self._apply_filters(ranked, user_id, request, region)

        # 5. Generate explanations
        results = await self._generate_explanations(filtered[: request.limit], request.mood)

        # 6. Log recommendations
        await self._log_recommendations(user_id, results)

        logger.info("recommendation_pipeline_complete", user_id=str(user_id), count=len(results))
        return results

    async def _get_user_embedding(self, user_id: UUID) -> list[float] | None:
        result = await self.db.execute(
            select(TasteEmbedding)
            .where(TasteEmbedding.user_id == user_id)
            .order_by(TasteEmbedding.updated_at.desc())
            .limit(1)
        )
        te = result.scalar_one_or_none()
        return te.embedding_vector if te else None

    async def _get_candidates(self, embedding: list[float], count: int) -> list[dict[str, Any]]:
        """Call ML service for candidate retrieval."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ml_base_url}/retrieve",
                    json={"embedding": embedding, "count": count},
                )
                response.raise_for_status()
                return response.json().get("candidates", [])
        except httpx.HTTPError as exc:
            logger.error("ml_retrieval_failed", error=str(exc))
            return []

    async def _rerank(self, candidates: list[dict[str, Any]], user_context: dict[str, Any]) -> list[dict[str, Any]]:
        """Call ML service to rerank candidates."""
        if not candidates:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ml_base_url}/rerank",
                    json={"candidates": candidates, "context": user_context},
                )
                response.raise_for_status()
                return response.json().get("ranked", candidates)
        except httpx.HTTPError as exc:
            logger.warning("ml_rerank_failed_using_original_order", error=str(exc))
            return candidates

    async def _apply_filters(
        self,
        ranked: list[dict[str, Any]],
        user_id: UUID,
        request: RecommendationRequest,
        region: str,
    ) -> list[dict[str, Any]]:
        if not ranked:
            return ranked

        # Get watched title IDs for filtering rewatches
        if not request.include_rewatches:
            watched_result = await self.db.execute(
                select(WatchHistory.title_id).where(WatchHistory.user_id == user_id)
            )
            watched_ids = {str(row[0]) for row in watched_result.all()}
            ranked = [c for c in ranked if str(c.get("title_id", "")) not in watched_ids]

        return ranked

    async def _generate_explanations(
        self,
        results: list[dict[str, Any]],
        mood: str | None,
    ) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for candidate in results:
            tmdb_id = candidate.get("tmdb_id")
            score = candidate.get("score", 0.0)

            # Fetch title from DB
            result = await self.db.execute(
                select(Title)
                .options(selectinload(Title.regional_availability))
                .where(Title.tmdb_id == tmdb_id)
            )
            title = result.scalar_one_or_none()
            if title is None:
                continue

            # Build reason
            reasons = []
            genres = title.genres or []
            if genres:
                genre_names = [g.get("name", "") for g in genres[:2]] if isinstance(genres, list) else []
                if genre_names:
                    reasons.append(f"Matches your taste in {', '.join(genre_names)}")
            if mood:
                reasons.append(f"Great for a {mood} mood")
            if score > 0.8:
                reasons.append("Highly rated by similar users")
            reason = ". ".join(reasons) if reasons else "Recommended based on your profile"

            availability = [
                AvailabilityInfo(
                    region=ra.region,
                    provider_name=ra.provider_name,
                    provider_type=ra.provider_type.value,
                    provider_logo_path=ra.provider_logo_path,
                    link=ra.link,
                )
                for ra in title.regional_availability
            ]

            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=score,
                    reason=reason,
                    availability=availability,
                )
            )
        return items

    async def _log_recommendations(self, user_id: UUID, items: list[RecommendationItem]) -> None:
        for item in items:
            log = RecommendationLog(
                user_id=user_id,
                title_id=item.title.id,
                score=item.score,
                reason=item.reason,
                model_version="v1",
            )
            self.db.add(log)
        await self.db.flush()

    async def _fallback_recommendations(
        self,
        user_id: UUID,
        limit: int,
        region: str,
    ) -> list[RecommendationItem]:
        """Popularity-based fallback when no user embedding exists."""
        logger.info("fallback_recommendations", user_id=str(user_id))

        # Get watched titles to exclude
        watched_result = await self.db.execute(
            select(WatchHistory.title_id).where(WatchHistory.user_id == user_id)
        )
        watched_ids = {row[0] for row in watched_result.all()}

        query = (
            select(Title)
            .options(selectinload(Title.regional_availability))
            .order_by(Title.popularity.desc())
            .limit(limit + len(watched_ids))
        )
        result = await self.db.execute(query)
        titles = result.scalars().all()

        items: list[RecommendationItem] = []
        for title in titles:
            if title.id in watched_ids:
                continue
            if len(items) >= limit:
                break

            availability = [
                AvailabilityInfo(
                    region=ra.region,
                    provider_name=ra.provider_name,
                    provider_type=ra.provider_type.value,
                    provider_logo_path=ra.provider_logo_path,
                    link=ra.link,
                )
                for ra in title.regional_availability
            ]

            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=title.popularity / 100.0 if title.popularity else 0.0,
                    reason="Popular right now",
                    availability=availability,
                )
            )

        await self._log_recommendations(user_id, items)
        return items
