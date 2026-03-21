from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession
from app.db.models import RecommendationLog, Title
from app.schemas.recommendations import (
    RecommendationFeedback,
    RecommendationListResponse,
    RecommendationRequest,
    TrendingResponse,
)
from app.schemas.titles import TitleResponse
from app.services.recommendation import RecommendationService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationListResponse)
async def get_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    include_rewatches: bool = Query(False),
    mood: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    logger.info("get_recommendations", user_id=str(current_user.id), mood=mood, limit=limit)

    request = RecommendationRequest(include_rewatches=include_rewatches, mood=mood, limit=limit)
    service = RecommendationService(db)
    items = await service.get_recommendations(
        user_id=current_user.id,
        request=request,
        region=current_user.region or "US",
    )

    return RecommendationListResponse(
        items=items,
        model_version="v1",
        total=len(items),
    )


@router.post("/{rec_id}/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(
    rec_id: UUID,
    body: RecommendationFeedback,
    db: DbSession,
    current_user: CurrentUser,
):
    logger.info("recommendation_feedback", rec_id=str(rec_id), feedback=body.feedback, user_id=str(current_user.id))

    result = await db.execute(
        select(RecommendationLog).where(
            RecommendationLog.id == rec_id,
            RecommendationLog.user_id == current_user.id,
        )
    )
    rec_log = result.scalar_one_or_none()
    if rec_log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    rec_log.feedback = body.feedback
    if body.feedback == "clicked":
        rec_log.clicked = True

    await db.flush()

    return {"message": "Feedback recorded", "rec_id": str(rec_id), "feedback": body.feedback}


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    logger.info("get_trending", page=page)

    count_result = await db.execute(select(func.count()).select_from(Title))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Title)
        .order_by(Title.popularity.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    titles = result.scalars().all()

    return TrendingResponse(
        items=[TitleResponse.model_validate(t) for t in titles],
        total=total,
        page=page,
    )
