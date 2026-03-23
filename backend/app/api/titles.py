import math
from datetime import date
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
from app.services.tmdb import tmdb_client, upsert_tmdb_items

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/titles", tags=["titles"])


def _build_filter_query(
    base: Select,
    genre: str | None,
    title_type: str | None,
    year_from: int | None,
    year_to: int | None,
) -> Select:
    if genre:
        base = base.where(Title.genres.op("@>")([{"name": genre}]))
    if title_type:
        try:
            tt = TitleType(title_type.upper())
            base = base.where(Title.title_type == tt)
        except ValueError:
            pass
    if year_from:
        base = base.where(Title.release_date >= date(year_from, 1, 1))
    if year_to:
        base = base.where(Title.release_date <= date(year_to, 12, 31))
    return base


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

    if q and q.strip():
        try:
            tmdb_data = await tmdb_client.search_titles(query=q, page=page)
            raw_results = tmdb_data.get("results", [])
            tmdb_total = tmdb_data.get("total_results", 0)
            tmdb_pages = tmdb_data.get("total_pages", 1)
            upserted = await upsert_tmdb_items(db, raw_results)
            await db.commit()

            items = [TitleResponse.model_validate(t) for t in upserted]
            return TitleListResponse(
                items=items,
                total=tmdb_total,
                page=page,
                per_page=per_page,
                pages=tmdb_pages,
            )
        except Exception as exc:
            logger.warning("tmdb_search_fallback", error=str(exc))

    base_query = select(Title)
    if q:
        base_query = base_query.where(Title.name.ilike(f"%{q}%"))
    base_query = _build_filter_query(base_query, genre, type, year_from, year_to)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = base_query.order_by(Title.popularity.desc()).offset((page - 1) * per_page).limit(per_page)
    titles = (await db.execute(query)).scalars().all()

    return TitleListResponse(
        items=[TitleResponse.model_validate(t) for t in titles],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/tmdb/{tmdb_id}", response_model=TitleDetail)
async def get_title_by_tmdb_id(tmdb_id: int, db: DbSession):
    """Fetch a title by its TMDb ID. Creates it locally if not already in the DB."""
    result = await db.execute(
        select(Title).options(selectinload(Title.regional_availability))
        .where(Title.tmdb_id == tmdb_id)
    )
    title = result.scalar_one_or_none()

    if title is None:
        for media in ("movie", "tv"):
            try:
                detail_data = await tmdb_client.get_title_detail(tmdb_id, media)
                if detail_data.get("id"):
                    detail_data["media_type"] = media
                    upserted = await upsert_tmdb_items(db, [detail_data])
                    await db.commit()
                    if upserted:
                        title = upserted[0]
                    break
            except Exception:
                continue

    if title is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found on TMDb")

    availability = [
        AvailabilityInfo(
            region=ra.region,
            provider_name=ra.provider_name,
            provider_type=ra.provider_type.value,
            provider_logo_path=ra.provider_logo_path,
            link=ra.link,
        )
        for ra in (title.regional_availability or [])
    ]

    detail = TitleDetail.model_validate(title)
    detail.availability = availability
    return detail


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
        raw_results = tmdb_data.get("results", [])[:20]
        media = "movie" if title.title_type == TitleType.MOVIE else "tv"
        similar = await upsert_tmdb_items(db, raw_results, default_media_type=media)
        await db.commit()
        return [TitleResponse.model_validate(t) for t in similar]
    except Exception as exc:
        logger.error("tmdb_similar_failed", error=str(exc))
        return []


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(admin_user: AdminUser):
    logger.info("tmdb_sync_triggered", admin_id=str(admin_user.id))
    return {"message": "TMDb sync task has been queued"}
