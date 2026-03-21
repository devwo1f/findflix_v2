import math
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from app.core.dependencies import AdminUser, CurrentUser, DbSession
from app.db.models import RegionalAvailability, Title, TitleType
from app.schemas.titles import (
    AvailabilityInfo,
    TitleDetail,
    TitleListResponse,
    TitleResponse,
)
from app.services.tmdb import tmdb_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/titles", tags=["titles"])


def _build_search_query(
    q: str | None,
    genre: str | None,
    title_type: str | None,
    year_from: int | None,
    year_to: int | None,
) -> Select:
    query = select(Title)

    if q:
        query = query.where(Title.name.ilike(f"%{q}%"))
    if genre:
        # genres is a JSONB array of objects with 'name' key
        query = query.where(Title.genres.op("@>")([{"name": genre}]))
    if title_type:
        try:
            tt = TitleType(title_type.upper())
            query = query.where(Title.title_type == tt)
        except ValueError:
            pass
    if year_from:
        query = query.where(Title.release_date >= str(year_from))
    if year_to:
        query = query.where(Title.release_date <= f"{year_to}-12-31")

    return query


@router.get("/search", response_model=TitleListResponse)
async def search_titles(
    db: DbSession,
    q: str | None = Query(None),
    genre: str | None = Query(None),
    type: str | None = Query(None),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    logger.info("title_search", q=q, genre=genre, type=type, page=page)

    base_query = _build_search_query(q, genre, type, year_from, year_to)

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = base_query.order_by(Title.popularity.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    titles = result.scalars().all()

    return TitleListResponse(
        items=[TitleResponse.model_validate(t) for t in titles],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/{title_id}", response_model=TitleDetail)
async def get_title(title_id: UUID, db: DbSession):
    result = await db.execute(
        select(Title).options(selectinload(Title.regional_availability)).where(Title.id == title_id)
    )
    title = result.scalar_one_or_none()
    if title is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

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

    detail = TitleDetail.model_validate(title)
    detail.availability = availability
    return detail


@router.get("/{title_id}/availability")
async def get_availability(
    title_id: UUID,
    db: DbSession,
    region: str = Query("US"),
):
    result = await db.execute(
        select(RegionalAvailability).where(
            RegionalAvailability.title_id == title_id,
            RegionalAvailability.region == region,
        )
    )
    rows = result.scalars().all()
    return [
        AvailabilityInfo(
            region=ra.region,
            provider_name=ra.provider_name,
            provider_type=ra.provider_type.value,
            provider_logo_path=ra.provider_logo_path,
            link=ra.link,
        )
        for ra in rows
    ]


@router.get("/{title_id}/similar", response_model=list[TitleResponse])
async def get_similar(title_id: UUID, db: DbSession):
    result = await db.execute(select(Title).where(Title.id == title_id))
    title = result.scalar_one_or_none()
    if title is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

    try:
        tmdb_data = await tmdb_client.get_similar(title.tmdb_id, title.title_type.value)
        tmdb_ids = [r["id"] for r in tmdb_data.get("results", [])[:10]]
    except Exception as exc:
        logger.error("tmdb_similar_failed", error=str(exc))
        tmdb_ids = []

    if not tmdb_ids:
        return []

    result = await db.execute(select(Title).where(Title.tmdb_id.in_(tmdb_ids)))
    similar_titles = result.scalars().all()
    return [TitleResponse.model_validate(t) for t in similar_titles]


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(admin_user: AdminUser):
    logger.info("tmdb_sync_triggered", admin_id=str(admin_user.id))
    # In production, dispatch a Celery task
    return {"message": "TMDb sync task has been queued"}
