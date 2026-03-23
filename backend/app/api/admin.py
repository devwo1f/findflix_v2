import httpx
import structlog
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import AdminUser, DbSession
from app.db.models import (
    FeedbackEvent,
    QuestionnaireResponse,
    RecommendationLog,
    TasteEmbedding,
    Title,
    User,
    WatchHistory,
)
from app.schemas.auth import UserResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def system_stats(db: DbSession, admin_user: AdminUser):
    logger.info("admin_stats_request", admin_id=str(admin_user.id))

    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    title_count = (await db.execute(select(func.count()).select_from(Title))).scalar() or 0
    watch_count = (await db.execute(select(func.count()).select_from(WatchHistory))).scalar() or 0
    rec_count = (await db.execute(select(func.count()).select_from(RecommendationLog))).scalar() or 0
    feedback_count = (await db.execute(select(func.count()).select_from(FeedbackEvent))).scalar() or 0

    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar() or 0

    return {
        "total_users": user_count,
        "active_users": active_users,
        "total_titles": title_count,
        "total_watches": watch_count,
        "total_recommendations": rec_count,
        "total_feedback_events": feedback_count,
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: DbSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    logger.info("admin_list_users", admin_id=str(admin_user.id), page=page)

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/recommendations/logs")
async def recommendation_logs(
    db: DbSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    logger.info("admin_rec_logs", admin_id=str(admin_user.id))

    result = await db.execute(
        select(RecommendationLog)
        .order_by(RecommendationLog.shown_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id),
            "title_id": str(log.title_id),
            "score": log.score,
            "reason": log.reason,
            "model_version": log.model_version,
            "shown_at": log.shown_at.isoformat() if log.shown_at else None,
            "clicked": log.clicked,
            "feedback": log.feedback,
        }
        for log in logs
    ]


@router.get("/model/info")
async def model_info(admin_user: AdminUser, db: DbSession):
    logger.info("admin_model_info", admin_id=str(admin_user.id))

    questionnaire_count = (
        await db.execute(select(func.count()).select_from(QuestionnaireResponse))
    ).scalar() or 0
    embedding_count = (
        await db.execute(select(func.count()).select_from(TasteEmbedding))
    ).scalar() or 0
    watch_count = (
        await db.execute(select(func.count()).select_from(WatchHistory))
    ).scalar() or 0

    ml_status = {"retrieval_ready": False, "ranking_ready": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ML_SERVICE_URL}/model/info")
            if resp.status_code == 200:
                ml_status = resp.json()
    except Exception:
        pass

    return {
        "ml_service": ml_status,
        "questionnaire_responses": questionnaire_count,
        "taste_embeddings": embedding_count,
        "watch_history_entries": watch_count,
        "can_train": watch_count >= 10 or questionnaire_count >= 1,
        "training_hint": (
            "Run: docker compose exec ml_service python -m ml_service.training.train_all"
            if watch_count >= 10
            else "Need more user interactions before training is effective. "
                 "Content-based recommendations are active in the meantime."
        ),
    }


@router.post("/sync/tmdb", status_code=202)
async def trigger_tmdb_sync(admin_user: AdminUser):
    logger.info("admin_tmdb_sync", admin_id=str(admin_user.id))
    from app.tasks.sync_tasks import sync_trending_titles, sync_popular_titles

    trending_task = sync_trending_titles.delay(pages=10)
    popular_task = sync_popular_titles.delay(pages=5)

    return {
        "message": "TMDb sync tasks dispatched",
        "status": "accepted",
        "tasks": {
            "trending": trending_task.id,
            "popular": popular_task.id,
        },
    }
