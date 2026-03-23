import asyncio
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Title, TitleType, RegionalAvailability, ProviderType, User
from app.db.session import async_session_factory
from app.services.tmdb import TMDbClient, upsert_tmdb_items
from app.services.embedding import EmbeddingService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _sync_trending_async(pages: int = 10) -> int:
    """Fetch trending titles from TMDb and upsert them into the database."""
    client = TMDbClient()
    synced = 0

    try:
        async with async_session_factory() as db:
            for page in range(1, pages + 1):
                data = await client.get_trending(time_window="week", page=page)
                results = data.get("results", [])
                upserted = await upsert_tmdb_items(db, results)
                synced += len(upserted)

            await db.commit()
    finally:
        await client.close()

    logger.info("sync_trending_complete", synced=synced)
    return synced


async def _sync_popular_async(pages: int = 5) -> int:
    """Fetch popular movies and TV shows and upsert them."""
    client = TMDbClient()
    synced = 0

    try:
        async with async_session_factory() as db:
            for page in range(1, pages + 1):
                movie_data = await client.discover(
                    {"media_type": "movie", "sort_by": "popularity.desc"}, page=page
                )
                upserted = await upsert_tmdb_items(
                    db, movie_data.get("results", []), default_media_type="movie"
                )
                synced += len(upserted)

            for page in range(1, pages + 1):
                tv_data = await client.discover(
                    {"media_type": "tv", "sort_by": "popularity.desc"}, page=page
                )
                upserted = await upsert_tmdb_items(
                    db, tv_data.get("results", []), default_media_type="tv"
                )
                synced += len(upserted)

            await db.commit()
    finally:
        await client.close()

    logger.info("sync_popular_complete", synced=synced)
    return synced


async def _sync_availability_async() -> int:
    """Update regional availability for all titles."""
    client = TMDbClient()
    updated = 0
    regions = ["US", "GB", "CA", "AU", "DE", "FR"]

    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Title).limit(500))
            titles = result.scalars().all()

            for title in titles:
                for region in regions:
                    try:
                        providers = await client.get_watch_providers(
                            title.tmdb_id, title.title_type.value, region
                        )
                    except Exception:
                        continue

                    for provider_type_key in ["flatrate", "rent", "buy", "free"]:
                        provider_list = providers.get(provider_type_key, [])
                        ptype = ProviderType(provider_type_key.upper())

                        for p in provider_list:
                            # Check if this availability already exists
                            existing = await db.execute(
                                select(RegionalAvailability).where(
                                    RegionalAvailability.title_id == title.id,
                                    RegionalAvailability.region == region,
                                    RegionalAvailability.provider_name == p.get("provider_name", ""),
                                    RegionalAvailability.provider_type == ptype,
                                )
                            )
                            if existing.scalar_one_or_none():
                                continue

                            ra = RegionalAvailability(
                                title_id=title.id,
                                region=region,
                                provider_name=p.get("provider_name", "Unknown"),
                                provider_type=ptype,
                                provider_logo_path=p.get("logo_path"),
                                link=providers.get("link"),
                            )
                            db.add(ra)
                            updated += 1

            await db.commit()
    finally:
        await client.close()

    logger.info("sync_availability_complete", updated=updated)
    return updated


async def _update_embeddings_async() -> int:
    """Batch-update user embeddings."""
    updated = 0

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        users = result.scalars().all()

        service = EmbeddingService(db)
        for user in users:
            try:
                embedding = await service.generate_user_embedding(user.id)
                if embedding:
                    updated += 1
            except Exception as exc:
                logger.error("embedding_update_failed", user_id=str(user.id), error=str(exc))

        await db.commit()

    logger.info("update_embeddings_complete", updated=updated)
    return updated


@celery_app.task(name="app.tasks.sync_tasks.sync_trending_titles", bind=True, max_retries=3)
def sync_trending_titles(self, pages: int = 10):
    """Celery task: fetch and store trending titles from TMDb."""
    try:
        count = _run_async(_sync_trending_async(pages=pages))
        return {"status": "success", "synced": count}
    except Exception as exc:
        logger.error("sync_trending_failed", error=str(exc))
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.sync_tasks.sync_popular_titles", bind=True, max_retries=3)
def sync_popular_titles(self, pages: int = 5):
    """Celery task: fetch and store popular movies and TV shows."""
    try:
        count = _run_async(_sync_popular_async(pages=pages))
        return {"status": "success", "synced": count}
    except Exception as exc:
        logger.error("sync_popular_failed", error=str(exc))
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.sync_tasks.sync_availability", bind=True, max_retries=3)
def sync_availability(self):
    """Celery task: update regional availability for titles."""
    try:
        count = _run_async(_sync_availability_async())
        return {"status": "success", "updated": count}
    except Exception as exc:
        logger.error("sync_availability_failed", error=str(exc))
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.sync_tasks.update_user_embeddings", bind=True, max_retries=2)
def update_user_embeddings(self):
    """Celery task: batch-update all user embeddings."""
    try:
        count = _run_async(_update_embeddings_async())
        return {"status": "success", "updated": count}
    except Exception as exc:
        logger.error("update_embeddings_failed", error=str(exc))
        self.retry(exc=exc, countdown=120)
