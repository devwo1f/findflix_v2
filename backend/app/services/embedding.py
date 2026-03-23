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

_PACING_MAP = {"slow": 0.2, "moderate": 0.5, "fast": 0.8}
_TONE_MAP = {"light": 0.2, "balanced": 0.5, "dark": 0.8}
_INTENSITY_MAP = {"low": 0.2, "medium": 0.5, "high": 0.8}
_RUNTIME_MAP = {"<90": 0.2, "short": 0.2, "90-120": 0.4, "medium": 0.5, "120-150": 0.6, "long": 0.7, "150+": 0.8, "any": 0.5}
_REWATCH_MAP = {"never": 0.0, "no": 0.0, "sometimes": 0.5, "often": 1.0, "yes": 1.0}


def _to_ml_questionnaire(q: QuestionnaireResponse | None) -> dict:
    """Translate stored questionnaire into the format the ML service expects."""
    if q is None:
        return {}

    genre_ids: list[int] = []
    gp = q.genre_preferences
    if isinstance(gp, dict):
        for k in gp:
            try:
                genre_ids.append(int(k))
            except (ValueError, TypeError):
                pass
    elif isinstance(gp, list):
        for g in gp:
            try:
                genre_ids.append(int(g))
            except (ValueError, TypeError):
                pass

    mood_list: list[str] = []
    mp = q.mood_preferences
    if isinstance(mp, dict):
        mood_list = list(mp.keys())
    elif isinstance(mp, list):
        mood_list = [str(m) for m in mp]

    return {
        "preferred_genre_ids": genre_ids,
        "mood_preferences": mood_list,
        "pacing": _PACING_MAP.get(q.pacing_preference or "", 0.5),
        "tone": _TONE_MAP.get(q.tone_preference or "", 0.5),
        "intensity": _INTENSITY_MAP.get(q.intensity_preference or "", 0.5),
        "runtime_preference": _RUNTIME_MAP.get(q.runtime_preference or "", 0.5),
        "rewatch_tolerance": _REWATCH_MAP.get(q.rewatch_tolerance or "", 0.5),
    }


class EmbeddingService:
    """Manages user taste embeddings by calling the ML service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ml_base_url = settings.ML_SERVICE_URL

    async def generate_user_embedding(self, user_id: UUID) -> list[float] | None:
        """Build a full embedding from questionnaire answers and watch history."""
        logger.info("generate_embedding_start", user_id=str(user_id))

        q_result = await self.db.execute(
            select(QuestionnaireResponse)
            .where(QuestionnaireResponse.user_id == user_id)
            .order_by(QuestionnaireResponse.completed_at.desc())
            .limit(1)
        )
        questionnaire = q_result.scalar_one_or_none()

        wh_result = await self.db.execute(
            select(WatchHistory).where(WatchHistory.user_id == user_id).order_by(WatchHistory.watched_at.desc()).limit(100)
        )
        watch_entries = wh_result.scalars().all()

        payload = {
            "questionnaire": _to_ml_questionnaire(questionnaire),
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
        """Re-generate the full embedding on feedback (incremental update
        endpoint doesn't exist, so we just regenerate)."""
        logger.info("embedding_feedback_regen", user_id=str(user_id))
        return await self.generate_user_embedding(user_id)
