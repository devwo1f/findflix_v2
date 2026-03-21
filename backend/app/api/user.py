from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession
from app.db.models import (
    FeedbackEvent,
    RecommendationLog,
    SearchHistory,
    Title,
    WatchHistory,
    WatchlistEntry,
)
from app.schemas.auth import UserResponse
from app.schemas.titles import TitleResponse
from app.schemas.user import (
    DashboardStats,
    FeedbackSubmit,
    ProfileUpdate,
    SearchHistoryResponse,
    WatchHistoryEntry,
    WatchHistoryResponse,
    WatchlistAdd,
    WatchlistResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(body: ProfileUpdate, db: DbSession, current_user: CurrentUser):
    logger.info("profile_update", user_id=str(current_user.id))

    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    if body.region is not None:
        current_user.region = body.region
    if body.language is not None:
        current_user.language = body.language

    await db.flush()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: DbSession, current_user: CurrentUser):
    uid = current_user.id

    # Total watched
    watched_count_result = await db.execute(
        select(func.count()).select_from(WatchHistory).where(WatchHistory.user_id == uid)
    )
    total_watched = watched_count_result.scalar() or 0

    # Total watchlist
    watchlist_count_result = await db.execute(
        select(func.count()).select_from(WatchlistEntry).where(WatchlistEntry.user_id == uid)
    )
    total_watchlist = watchlist_count_result.scalar() or 0

    # Average rating
    avg_result = await db.execute(
        select(func.avg(WatchHistory.rating)).where(WatchHistory.user_id == uid, WatchHistory.rating.isnot(None))
    )
    average_rating = avg_result.scalar()
    average_rating = round(float(average_rating), 2) if average_rating else None

    # Top genres from watch history
    wh_result = await db.execute(
        select(WatchHistory)
        .options(selectinload(WatchHistory.title))
        .where(WatchHistory.user_id == uid)
        .order_by(WatchHistory.watched_at.desc())
        .limit(50)
    )
    watch_entries = wh_result.scalars().all()

    genre_counts: dict[str, int] = {}
    for wh in watch_entries:
        if wh.title and wh.title.genres:
            for g in wh.title.genres:
                name = g.get("name", "Unknown") if isinstance(g, dict) else str(g)
                genre_counts[name] = genre_counts.get(name, 0) + 1
    top_genres = sorted(
        [{"name": k, "count": v} for k, v in genre_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # Recent activity
    recent_activity = [
        {
            "title": wh.title.name if wh.title else "Unknown",
            "watched_at": wh.watched_at.isoformat(),
            "rating": wh.rating,
        }
        for wh in watch_entries[:5]
    ]

    # Pending recommendations
    rec_count_result = await db.execute(
        select(func.count())
        .select_from(RecommendationLog)
        .where(RecommendationLog.user_id == uid, RecommendationLog.clicked.is_(False))
    )
    recommendations_pending = rec_count_result.scalar() or 0

    return DashboardStats(
        total_watched=total_watched,
        total_watchlist=total_watchlist,
        average_rating=average_rating,
        top_genres=top_genres,
        recent_activity=recent_activity,
        recommendations_pending=recommendations_pending,
    )


# ---------------------------------------------------------------------------
# Watch History
# ---------------------------------------------------------------------------

@router.post("/watch-history", status_code=status.HTTP_201_CREATED)
async def add_watch_history(body: WatchHistoryEntry, db: DbSession, current_user: CurrentUser):
    logger.info("add_watch_history", user_id=str(current_user.id), title_id=str(body.title_id))

    # Verify title exists
    title_result = await db.execute(select(Title).where(Title.id == body.title_id))
    title = title_result.scalar_one_or_none()
    if title is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

    entry = WatchHistory(
        user_id=current_user.id,
        title_id=body.title_id,
        rating=body.rating,
        would_rewatch=body.would_rewatch,
        mood_feedback=body.mood_feedback,
        completion_percentage=body.completion_percentage,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    return {"id": str(entry.id), "message": "Watch history entry added"}


@router.get("/watch-history", response_model=list[WatchHistoryResponse])
async def get_watch_history(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(WatchHistory)
        .options(selectinload(WatchHistory.title))
        .where(WatchHistory.user_id == current_user.id)
        .order_by(WatchHistory.watched_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    return [
        WatchHistoryResponse(
            id=e.id,
            title=TitleResponse.model_validate(e.title),
            watched_at=e.watched_at,
            rating=e.rating,
            would_rewatch=e.would_rewatch,
            mood_feedback=e.mood_feedback,
            completion_percentage=e.completion_percentage,
        )
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

@router.post("/watchlist", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(body: WatchlistAdd, db: DbSession, current_user: CurrentUser):
    logger.info("add_to_watchlist", user_id=str(current_user.id), title_id=str(body.title_id))

    # Verify title exists
    title_result = await db.execute(select(Title).where(Title.id == body.title_id))
    if title_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

    # Check duplicate
    existing = await db.execute(
        select(WatchlistEntry).where(
            WatchlistEntry.user_id == current_user.id,
            WatchlistEntry.title_id == body.title_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in watchlist")

    entry = WatchlistEntry(
        user_id=current_user.id,
        title_id=body.title_id,
        priority=body.priority,
        notes=body.notes,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    return {"id": str(entry.id), "message": "Added to watchlist"}


@router.get("/watchlist", response_model=list[WatchlistResponse])
async def get_watchlist(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(WatchlistEntry)
        .options(selectinload(WatchlistEntry.title))
        .where(WatchlistEntry.user_id == current_user.id)
        .order_by(WatchlistEntry.priority.desc(), WatchlistEntry.added_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    return [
        WatchlistResponse(
            id=e.id,
            title=TitleResponse.model_validate(e.title),
            added_at=e.added_at,
            priority=e.priority,
            notes=e.notes,
        )
        for e in entries
    ]


@router.delete("/watchlist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(entry_id: UUID, db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(WatchlistEntry).where(
            WatchlistEntry.id == entry_id,
            WatchlistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist entry not found")

    await db.delete(entry)
    await db.flush()


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(body: FeedbackSubmit, db: DbSession, current_user: CurrentUser):
    logger.info("feedback_submit", user_id=str(current_user.id), event_type=body.event_type)

    event = FeedbackEvent(
        user_id=current_user.id,
        title_id=body.title_id,
        event_type=body.event_type,
        value=body.value,
    )
    db.add(event)
    await db.flush()

    return {"id": str(event.id), "message": "Feedback recorded"}


# ---------------------------------------------------------------------------
# Search History
# ---------------------------------------------------------------------------

@router.get("/search-history", response_model=list[SearchHistoryResponse])
async def get_search_history(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
):
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.searched_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()
    return [SearchHistoryResponse.model_validate(e) for e in entries]
