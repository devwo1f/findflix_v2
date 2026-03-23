import json
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession, RedisClient
from app.db.models import RecommendationLog, Title
from app.schemas.recommendations import (
    RecommendationFeedback,
    RecommendationListResponse,
    RecommendationRequest,
    TrendingResponse,
    VibeCheckRequest,
    VibeCheckResponse,
)
from app.schemas.titles import TitleResponse
from app.services.recommendation import RecommendationService
from app.services.tmdb import tmdb_client, upsert_tmdb_items

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

TRENDING_CACHE_TTL = 3600  # 1 hour


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


@router.post("/vibe-check", response_model=VibeCheckResponse)
async def vibe_check(
    body: VibeCheckRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    logger.info(
        "vibe_check",
        user_id=str(current_user.id),
        mood=body.mood,
        vibe=body.vibe,
        time=body.time_available,
        type=body.content_type,
    )
    service = RecommendationService(db)
    picks, summary = await service.vibe_check(
        user_id=current_user.id,
        mood=body.mood,
        time_available=body.time_available,
        content_type=body.content_type,
        vibe=body.vibe,
    )
    return VibeCheckResponse(picks=picks, vibe_summary=summary)


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    db: DbSession,
    redis: RedisClient,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    logger.info("get_trending", page=page)

    cache_key = f"trending:page:{page}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return TrendingResponse(**data)
    except Exception:
        pass

    try:
        tmdb_data = await tmdb_client.get_trending(time_window="week", page=page)
        raw_results = tmdb_data.get("results", [])
        tmdb_total = tmdb_data.get("total_results", 0)
        titles = await upsert_tmdb_items(db, raw_results)
        await db.commit()

        items = [TitleResponse.model_validate(t) for t in titles]
        response = TrendingResponse(items=items, total=tmdb_total, page=page)

        try:
            await redis.set(cache_key, response.model_dump_json(), ex=TRENDING_CACHE_TTL)
        except Exception:
            pass

        return response
    except Exception as exc:
        logger.warning("tmdb_trending_fallback", error=str(exc))

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
