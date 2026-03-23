import random
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import (
    QuestionnaireResponse,
    RecommendationLog,
    RegionalAvailability,
    TasteEmbedding,
    Title,
    TitleType,
    WatchHistory,
)
from app.schemas.recommendations import RecommendationItem, RecommendationRequest
from app.schemas.titles import AvailabilityInfo, TitleResponse

logger = structlog.get_logger(__name__)

TMDB_GENRE_NAMES: dict[int, str] = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 53: "Thriller",
    10752: "War", 37: "Western", 10770: "TV Movie",
}

MOOD_GENRE_MAP: dict[str, list[int]] = {
    "happy": [35, 16, 10751, 10402],       # Comedy, Animation, Family, Music
    "sad": [18, 10749],                      # Drama, Romance
    "excited": [28, 12, 878],                # Action, Adventure, Sci-Fi
    "relaxed": [35, 99, 10751, 16],          # Comedy, Documentary, Family, Animation
    "tense": [53, 27, 80, 9648],             # Thriller, Horror, Crime, Mystery
    "romantic": [10749, 18, 35],             # Romance, Drama, Comedy
    "nostalgic": [18, 12, 14, 10751],        # Drama, Adventure, Fantasy, Family
    "curious": [99, 878, 9648, 36],          # Documentary, Sci-Fi, Mystery, History
    "scared": [27, 53, 9648],                # Horror, Thriller, Mystery
    "inspired": [18, 99, 36, 12],            # Drama, Documentary, History, Adventure
}

PACING_GENRE_BOOST: dict[str, list[int]] = {
    "fast": [28, 12, 878, 53],
    "moderate": [18, 80, 9648, 14],
    "slow": [18, 99, 36, 10749],
}

TONE_GENRE_BOOST: dict[str, list[int]] = {
    "light": [35, 16, 10751, 10402],
    "dark": [27, 53, 80, 9648],
    "balanced": [18, 12, 878, 14],
}

RUNTIME_FILTER: dict[str, tuple[int, int]] = {
    "<90": (0, 90),
    "short": (0, 90),
    "90-120": (90, 120),
    "medium": (90, 120),
    "120-150": (120, 150),
    "long": (120, 300),
    "150+": (150, 500),
    "any": (0, 500),
}

VIBE_GENRE_MAP: dict[str, list[int]] = {
    "mind-bending": [878, 9648, 53, 14],
    "feel-good": [35, 10751, 16, 10402],
    "edge-of-seat": [28, 53, 80, 878],
    "tear-jerker": [18, 10749, 36],
    "laugh-out-loud": [35, 16, 10402],
    "epic-adventure": [12, 28, 14, 878],
    "cozy": [10751, 35, 16, 10749],
    "dark-gritty": [80, 27, 53, 18],
}

VIBE_SUMMARIES: dict[str, str] = {
    "mind-bending": "reality-twisting stories to blow your mind",
    "feel-good": "warm picks guaranteed to put a smile on your face",
    "edge-of-seat": "pulse-pounding thrills you won't be able to pause",
    "tear-jerker": "emotionally powerful stories that hit deep",
    "laugh-out-loud": "hilarious picks to keep you laughing",
    "epic-adventure": "grand journeys and breathtaking worlds",
    "cozy": "comforting watches for a chill night in",
    "dark-gritty": "intense, no-holds-barred storytelling",
}

TIME_RUNTIME: dict[str, tuple[int, int]] = {
    "quick": (0, 95),
    "standard": (80, 150),
    "long": (120, 300),
    "marathon": (0, 500),
}


def _extract_genre_ids(title: Title) -> set[int]:
    """Extract genre IDs from the JSONB genres field."""
    ids: set[int] = set()
    if not title.genres:
        return ids
    for g in title.genres:
        if isinstance(g, dict):
            gid = g.get("id")
            if gid is not None:
                ids.add(int(gid))
    return ids


class RecommendationService:
    """Orchestrates the full recommendation pipeline using content-based
    filtering from questionnaire preferences, with ML service as enhancement."""

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

        questionnaire = await self._get_questionnaire(user_id)
        watched_ids = await self._get_watched_ids(user_id)

        embedding = await self._get_user_embedding(user_id)
        if embedding:
            ml_results = await self._try_ml_pipeline(embedding, user_id, request, region)
            if ml_results:
                logger.info("recommendation_pipeline_complete", user_id=str(user_id), count=len(ml_results), source="ml")
                return ml_results

        if questionnaire:
            results = await self._content_based_recommendations(
                questionnaire, watched_ids, request, region
            )
        else:
            results = await self._popularity_recommendations(watched_ids, request.limit, region)

        await self._log_recommendations(user_id, results)
        logger.info("recommendation_pipeline_complete", user_id=str(user_id), count=len(results), source="content" if questionnaire else "popularity")
        return results

    # ------------------------------------------------------------------
    # Content-based recommendation engine (uses questionnaire directly)
    # ------------------------------------------------------------------

    async def _content_based_recommendations(
        self,
        questionnaire: QuestionnaireResponse,
        watched_ids: set,
        request: RecommendationRequest,
        region: str,
    ) -> list[RecommendationItem]:
        genre_prefs = questionnaire.genre_preferences or {}
        mood_prefs = questionnaire.mood_preferences or {}
        pacing_val = questionnaire.pacing_preference  # float 0-1
        tone_val = questionnaire.tone_preference       # float 0-1
        runtime_pref = questionnaire.runtime_preference

        preferred_genre_ids: set[int] = set()
        if isinstance(genre_prefs, dict):
            for gid_str, weight in genre_prefs.items():
                try:
                    preferred_genre_ids.add(int(gid_str))
                except (ValueError, TypeError):
                    pass
        elif isinstance(genre_prefs, list):
            for gid in genre_prefs:
                try:
                    preferred_genre_ids.add(int(gid))
                except (ValueError, TypeError):
                    pass

        mood_genre_boost: set[int] = set()
        active_mood = request.mood
        mood_keys = []
        if active_mood:
            mood_keys.append(active_mood.lower())
        if isinstance(mood_prefs, dict):
            mood_keys.extend(mood_prefs.keys())
        elif isinstance(mood_prefs, list):
            mood_keys.extend(mood_prefs)
        for mk in mood_keys:
            mood_genre_boost.update(MOOD_GENRE_MAP.get(mk.lower(), []))

        pacing_boost: set[int] = set()
        pacing_f = float(pacing_val) if pacing_val is not None else 0.5
        pacing_key = "slow" if pacing_f < 0.33 else ("fast" if pacing_f > 0.66 else "moderate")
        pacing_boost.update(PACING_GENRE_BOOST.get(pacing_key, []))

        tone_boost: set[int] = set()
        tone_f = float(tone_val) if tone_val is not None else 0.5
        tone_key = "light" if tone_f < 0.33 else ("dark" if tone_f > 0.66 else "balanced")
        tone_boost.update(TONE_GENRE_BOOST.get(tone_key, []))

        pool_size = max(request.limit * 5, 200)
        query = (
            select(Title)
            .options(selectinload(Title.regional_availability))
            .order_by(Title.popularity.desc())
            .limit(pool_size)
        )
        result = await self.db.execute(query)
        candidate_titles = result.scalars().all()

        rt_min, rt_max = RUNTIME_FILTER.get(runtime_pref or "any", (0, 500))

        scored: list[tuple[Title, float, str]] = []
        for title in candidate_titles:
            if title.id in watched_ids:
                continue

            if title.runtime and not (rt_min <= title.runtime <= rt_max):
                continue

            title_genres = _extract_genre_ids(title)
            score = 0.0
            reasons: list[str] = []

            genre_overlap = title_genres & preferred_genre_ids
            if genre_overlap:
                score += len(genre_overlap) * 25.0
                genre_names = [TMDB_GENRE_NAMES.get(gid, "") for gid in list(genre_overlap)[:2]]
                genre_names = [n for n in genre_names if n]
                if genre_names:
                    reasons.append(f"Matches your taste in {', '.join(genre_names)}")

            mood_overlap = title_genres & mood_genre_boost
            if mood_overlap:
                score += len(mood_overlap) * 15.0
                if active_mood:
                    reasons.append(f"Perfect for a {active_mood} mood")

            pacing_overlap = title_genres & pacing_boost
            if pacing_overlap:
                score += len(pacing_overlap) * 5.0

            tone_overlap = title_genres & tone_boost
            if tone_overlap:
                score += len(tone_overlap) * 5.0

            if title.vote_average:
                score += title.vote_average * 3.0
            if title.popularity:
                score += min(title.popularity / 10.0, 20.0)

            score += random.uniform(0, 5.0)

            if not reasons:
                if title.vote_average and title.vote_average > 7.5:
                    reasons.append("Highly rated")
                reasons.append("Trending now")

            scored.append((title, score, ". ".join(reasons)))

        scored.sort(key=lambda x: x[1], reverse=True)

        items: list[RecommendationItem] = []
        for title, score, reason in scored[:request.limit]:
            availability = self._build_availability(title)
            norm_score = min(score / 100.0, 1.0)
            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=norm_score,
                    reason=reason,
                    availability=availability,
                )
            )
        return items

    # ------------------------------------------------------------------
    # ML pipeline (enhancement when model is trained)
    # ------------------------------------------------------------------

    async def _try_ml_pipeline(
        self,
        embedding: list[float],
        user_id: UUID,
        request: RecommendationRequest,
        region: str,
    ) -> list[RecommendationItem] | None:
        candidates = await self._get_candidates(embedding, request.limit * 3)
        if not candidates:
            return None

        user_context = {
            "mood": request.mood,
            "include_rewatches": request.include_rewatches,
            "region": region,
        }
        ranked = await self._rerank(candidates, user_context)

        if not request.include_rewatches:
            watched_ids = await self._get_watched_ids(user_id)
            watched_str = {str(wid) for wid in watched_ids}
            ranked = [c for c in ranked if str(c.get("title_id", "")) not in watched_str]

        results = await self._generate_explanations(ranked[:request.limit], request.mood)
        if results:
            await self._log_recommendations(user_id, results)
        return results if results else None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_questionnaire(self, user_id: UUID) -> QuestionnaireResponse | None:
        result = await self.db.execute(
            select(QuestionnaireResponse)
            .where(QuestionnaireResponse.user_id == user_id)
            .order_by(QuestionnaireResponse.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_watched_ids(self, user_id: UUID) -> set:
        result = await self.db.execute(
            select(WatchHistory.title_id).where(WatchHistory.user_id == user_id)
        )
        return {row[0] for row in result.all()}

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
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ml_base_url}/retrieve",
                    json={"user_embedding": embedding, "top_k": count},
                )
                response.raise_for_status()
                return response.json().get("candidates", [])
        except httpx.HTTPError as exc:
            logger.warning("ml_retrieval_failed", error=str(exc))
            return []

    async def _rerank(self, candidates: list[dict[str, Any]], user_context: dict[str, Any]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ml_base_url}/rank",
                    json={"candidates": candidates, "context": user_context},
                )
                response.raise_for_status()
                return response.json().get("ranked", candidates)
        except httpx.HTTPError as exc:
            logger.warning("ml_rerank_failed", error=str(exc))
            return candidates

    async def _generate_explanations(
        self,
        results: list[dict[str, Any]],
        mood: str | None,
    ) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for candidate in results:
            title_id = candidate.get("title_id")
            score = candidate.get("score", 0.0)

            result = await self.db.execute(
                select(Title)
                .options(selectinload(Title.regional_availability))
                .where(Title.id == title_id)
            )
            title = result.scalar_one_or_none()
            if title is None:
                continue

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

            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=score,
                    reason=reason,
                    availability=self._build_availability(title),
                )
            )
        return items

    def _build_availability(self, title: Title) -> list[AvailabilityInfo]:
        return [
            AvailabilityInfo(
                region=ra.region,
                provider_name=ra.provider_name,
                provider_type=ra.provider_type.value,
                provider_logo_path=ra.provider_logo_path,
                link=ra.link,
            )
            for ra in (title.regional_availability or [])
        ]

    async def _log_recommendations(self, user_id: UUID, items: list[RecommendationItem]) -> None:
        for item in items:
            log = RecommendationLog(
                user_id=user_id,
                title_id=item.title.id,
                score=item.score,
                reason=item.reason,
                model_version="content_v1",
            )
            self.db.add(log)
        await self.db.flush()

    async def _popularity_recommendations(
        self,
        watched_ids: set,
        limit: int,
        region: str,
    ) -> list[RecommendationItem]:
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
            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=min((title.popularity or 0) / 100.0, 1.0),
                    reason="Popular right now",
                    availability=self._build_availability(title),
                )
            )
        return items

    # ------------------------------------------------------------------
    # Vibe Check -- instant decision helper
    # ------------------------------------------------------------------

    async def vibe_check(
        self,
        user_id: UUID,
        mood: str,
        time_available: str,
        content_type: str,
        vibe: str,
    ) -> tuple[list[RecommendationItem], str]:
        watched_ids = await self._get_watched_ids(user_id)
        questionnaire = await self._get_questionnaire(user_id)

        vibe_genres = set(VIBE_GENRE_MAP.get(vibe, []))
        mood_genres = set(MOOD_GENRE_MAP.get(mood.lower(), []))
        target_genres = vibe_genres | mood_genres

        user_genre_prefs: set[int] = set()
        if questionnaire:
            gp = questionnaire.genre_preferences
            if isinstance(gp, dict):
                for k in gp:
                    try:
                        user_genre_prefs.add(int(k))
                    except (ValueError, TypeError):
                        pass

        rt_min, rt_max = TIME_RUNTIME.get(time_available, (0, 500))

        pool_size = 500
        query = (
            select(Title)
            .options(selectinload(Title.regional_availability))
            .order_by(Title.popularity.desc())
            .limit(pool_size)
        )
        if content_type == "movie":
            query = query.where(Title.title_type == TitleType.MOVIE)
        elif content_type == "tv":
            query = query.where(Title.title_type == TitleType.TV)

        result = await self.db.execute(query)
        candidates = result.scalars().all()

        scored: list[tuple[Title, float, str]] = []
        for title in candidates:
            if title.id in watched_ids:
                continue

            if content_type != "tv" and title.runtime:
                if not (rt_min <= title.runtime <= rt_max):
                    continue

            title_genres = _extract_genre_ids(title)
            score = 0.0
            reasons: list[str] = []

            vibe_match = title_genres & vibe_genres
            if vibe_match:
                score += len(vibe_match) * 30.0
                names = [TMDB_GENRE_NAMES.get(g, "") for g in list(vibe_match)[:2]]
                names = [n for n in names if n]
                if names:
                    reasons.append(f"Perfect {vibe.replace('-', ' ')} pick")

            mood_match = title_genres & mood_genres
            if mood_match:
                score += len(mood_match) * 20.0
                if not reasons:
                    reasons.append(f"Great for your {mood} mood")

            user_pref_match = title_genres & user_genre_prefs
            if user_pref_match:
                score += len(user_pref_match) * 10.0
                if not reasons:
                    names = [TMDB_GENRE_NAMES.get(g, "") for g in list(user_pref_match)[:2]]
                    names = [n for n in names if n]
                    if names:
                        reasons.append(f"Matches your love of {', '.join(names)}")

            if title.vote_average and title.vote_average > 7.0:
                score += (title.vote_average - 7.0) * 8.0
                if title.vote_average > 8.0:
                    reasons.append(f"Rated {title.vote_average:.1f}/10")

            if title.popularity:
                score += min(title.popularity / 20.0, 10.0)

            score += random.uniform(0, 8.0)

            if score > 10:
                if not reasons:
                    reasons.append("A hidden gem worth discovering")
                scored.append((title, score, reasons[0]))

        scored.sort(key=lambda x: x[1], reverse=True)

        seen_genres: list[set[int]] = []
        diverse_picks: list[tuple[Title, float, str]] = []
        for title, score, reason in scored:
            tg = _extract_genre_ids(title)
            too_similar = any(len(tg & sg) >= 3 for sg in seen_genres)
            if not too_similar or len(diverse_picks) < 2:
                diverse_picks.append((title, score, reason))
                seen_genres.append(tg)
            if len(diverse_picks) >= 5:
                break

        items: list[RecommendationItem] = []
        max_score = diverse_picks[0][1] if diverse_picks else 1.0
        for title, score, reason in diverse_picks:
            items.append(
                RecommendationItem(
                    title=TitleResponse.model_validate(title),
                    score=min(score / max_score, 1.0),
                    reason=reason,
                    availability=self._build_availability(title),
                )
            )

        await self._log_recommendations(user_id, items)

        mood_emoji = {"happy": "\U0001F60A", "sad": "\U0001F622", "excited": "\U0001F929", "relaxed": "\U0001F60C", "tense": "\U0001F630", "romantic": "\U0001F495", "curious": "\U0001F9D0", "scared": "\U0001F631"}.get(mood.lower(), "\u2728")
        vibe_desc = VIBE_SUMMARIES.get(vibe, "something special")
        summary = f"Here are {len(items)} {vibe_desc} {mood_emoji}"

        return items, summary
