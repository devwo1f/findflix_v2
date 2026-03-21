from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    FeedbackEvent,
    QuestionnaireResponse,
    TasteEmbedding,
    WatchHistory,
)

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Manages user taste embeddings by calling the ML service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ml_base_url = settings.ML_SERVICE_URL

    async def generate_user_embedding(self, user_id: UUID) -> list[float] | None:
        """Build a full embedding from questionnaire answers and watch history."""
        logger.info("generate_embedding_start", user_id=str(user_id))

        # Gather questionnaire data
        q_result = await self.db.execute(
            select(QuestionnaireResponse)
            .where(QuestionnaireResponse.user_id == user_id)
            .order_by(QuestionnaireResponse.completed_at.desc())
            .limit(1)
        )
        questionnaire = q_result.scalar_one_or_none()

        # Gather watch history
        wh_result = await self.db.execute(
            select(WatchHistory).where(WatchHistory.user_id == user_id).order_by(WatchHistory.watched_at.desc()).limit(100)
        )
        watch_entries = wh_result.scalars().all()

        # Build feature payload
        payload = {
            "user_id": str(user_id),
            "questionnaire": {
                "genre_preferences": questionnaire.genre_preferences if questionnaire else {},
                "mood_preferences": questionnaire.mood_preferences if questionnaire else {},
                "pacing_preference": questionnaire.pacing_preference if questionnaire else None,
                "tone_preference": questionnaire.tone_preference if questionnaire else None,
                "intensity_preference": questionnaire.intensity_preference if questionnaire else None,
                "runtime_preference": questionnaire.runtime_preference if questionnaire else None,
                "rewatch_tolerance": questionnaire.rewatch_tolerance if questionnaire else None,
            },
            "watch_history": [
                {
                    "title_id": str(wh.title_id),
                    "rating": wh.rating,
                    "would_rewatch": wh.would_rewatch,
                    "mood_feedback": wh.mood_feedback,
                    "completion_percentage": wh.completion_percentage,
                }
                for wh in watch_entries
            ],
        }

        # Call ML service
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.ml_base_url}/embed/user", json=payload)
                response.raise_for_status()
                data = response.json()
                embedding_vector = data.get("embedding")
                model_version = data.get("model_version", "v1")
        except httpx.HTTPError as exc:
            logger.error("embedding_generation_failed", error=str(exc), user_id=str(user_id))
            return None

        if embedding_vector is None:
            logger.warning("embedding_empty_response", user_id=str(user_id))
            return None

        # Upsert embedding
        existing_result = await self.db.execute(
            select(TasteEmbedding)
            .where(TasteEmbedding.user_id == user_id)
            .order_by(TasteEmbedding.updated_at.desc())
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.embedding_vector = embedding_vector
            existing.model_version = model_version
        else:
            te = TasteEmbedding(
                user_id=user_id,
                embedding_vector=embedding_vector,
                model_version=model_version,
            )
            self.db.add(te)

        await self.db.flush()
        logger.info("embedding_generated", user_id=str(user_id), dim=len(embedding_vector))
        return embedding_vector

    async def update_embedding_on_feedback(self, user_id: UUID, feedback: dict) -> list[float] | None:
        """Incrementally update embedding based on user feedback."""
        logger.info("incremental_embedding_update", user_id=str(user_id))

        # Fetch current embedding
        result = await self.db.execute(
            select(TasteEmbedding)
            .where(TasteEmbedding.user_id == user_id)
            .order_by(TasteEmbedding.updated_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing is None or existing.embedding_vector is None:
            logger.info("no_existing_embedding_full_regen", user_id=str(user_id))
            return await self.generate_user_embedding(user_id)

        payload = {
            "user_id": str(user_id),
            "current_embedding": existing.embedding_vector,
            "feedback": feedback,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"{self.ml_base_url}/embed/update", json=payload)
                response.raise_for_status()
                data = response.json()
                new_embedding = data.get("embedding")
        except httpx.HTTPError as exc:
            logger.error("incremental_update_failed", error=str(exc))
            return None

        if new_embedding:
            existing.embedding_vector = new_embedding
            await self.db.flush()
            logger.info("embedding_updated_incrementally", user_id=str(user_id))

        return new_embedding
