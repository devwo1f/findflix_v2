from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.db.models import QuestionnaireResponse as QuestionnaireModel
from app.schemas.questionnaire import (
    QuestionnaireResponse,
    QuestionnaireSubmit,
    QuestionnaireUpdate,
)
from app.services.embedding import EmbeddingService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


@router.post("", response_model=QuestionnaireResponse, status_code=status.HTTP_201_CREATED)
async def submit_questionnaire(body: QuestionnaireSubmit, db: DbSession, current_user: CurrentUser):
    logger.info("questionnaire_submit", user_id=str(current_user.id))

    # Check if user already has one
    existing = await db.execute(
        select(QuestionnaireModel).where(QuestionnaireModel.user_id == current_user.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Questionnaire already submitted. Use PUT to update.",
        )

    qr = QuestionnaireModel(
        user_id=current_user.id,
        genre_preferences=body.genre_preferences,
        mood_preferences=body.mood_preferences,
        pacing_preference=body.pacing_preference,
        tone_preference=body.tone_preference,
        intensity_preference=body.intensity_preference,
        runtime_preference=body.runtime_preference,
        rewatch_tolerance=body.rewatch_tolerance,
        preferred_providers=body.preferred_providers,  # type: ignore[arg-type]
        completed_at=datetime.now(timezone.utc),
    )
    db.add(qr)
    await db.flush()
    await db.refresh(qr)

    # Trigger embedding generation asynchronously
    embedding_service = EmbeddingService(db)
    await embedding_service.generate_user_embedding(current_user.id)

    logger.info("questionnaire_submitted", user_id=str(current_user.id), qr_id=str(qr.id))
    return QuestionnaireResponse.model_validate(qr)


@router.get("", response_model=QuestionnaireResponse)
async def get_questionnaire(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(QuestionnaireModel)
        .where(QuestionnaireModel.user_id == current_user.id)
        .order_by(QuestionnaireModel.completed_at.desc())
        .limit(1)
    )
    qr = result.scalar_one_or_none()
    if qr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questionnaire found")
    return QuestionnaireResponse.model_validate(qr)


@router.put("", response_model=QuestionnaireResponse)
async def update_questionnaire(body: QuestionnaireUpdate, db: DbSession, current_user: CurrentUser):
    logger.info("questionnaire_update", user_id=str(current_user.id))

    result = await db.execute(
        select(QuestionnaireModel)
        .where(QuestionnaireModel.user_id == current_user.id)
        .order_by(QuestionnaireModel.completed_at.desc())
        .limit(1)
    )
    qr = result.scalar_one_or_none()
    if qr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questionnaire found to update")

    qr.genre_preferences = body.genre_preferences
    qr.mood_preferences = body.mood_preferences
    qr.pacing_preference = body.pacing_preference
    qr.tone_preference = body.tone_preference
    qr.intensity_preference = body.intensity_preference
    qr.runtime_preference = body.runtime_preference
    qr.rewatch_tolerance = body.rewatch_tolerance
    qr.preferred_providers = body.preferred_providers  # type: ignore[assignment]
    qr.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(qr)

    # Re-generate embedding
    embedding_service = EmbeddingService(db)
    await embedding_service.generate_user_embedding(current_user.id)

    logger.info("questionnaire_updated", user_id=str(current_user.id))
    return QuestionnaireResponse.model_validate(qr)
