import abc
from datetime import date, datetime, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class ContentProviderBase(abc.ABC):
    """Abstract base class for content metadata providers."""

    @abc.abstractmethod
    async def search_titles(self, query: str, page: int = 1) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    async def get_title_detail(self, external_id: int, title_type: str) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    async def get_watch_providers(self, external_id: int, title_type: str, region: str = "US") -> dict[str, Any]:
        ...

    @abc.abstractmethod
    async def get_similar(self, external_id: int, title_type: str, page: int = 1) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    async def get_trending(self, time_window: str = "week", page: int = 1) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    async def discover(self, filters: dict[str, Any], page: int = 1) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# TMDb implementation
# ---------------------------------------------------------------------------

class TMDbClient(ContentProviderBase):
    """TMDb API client with retry logic and structured logging."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.TMDB_API_KEY
        self.base_url = base_url or settings.TMDB_BASE_URL
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        params = params or {}
        params["api_key"] = self.api_key

        logger.debug("tmdb_request", method=method, path=path, params={k: v for k, v in params.items() if k != "api_key"})

        response = await client.request(method, path, params=params)
        response.raise_for_status()
        data = response.json()

        logger.info("tmdb_response", path=path, status=response.status_code)
        return data

    # ----- Public API -----

    async def search_titles(self, query: str, page: int = 1) -> dict[str, Any]:
        results = await self._request("GET", "/search/multi", params={"query": query, "page": page})
        return results

    async def get_title_detail(self, external_id: int, title_type: str) -> dict[str, Any]:
        media = "movie" if title_type.upper() == "MOVIE" else "tv"
        detail = await self._request("GET", f"/{media}/{external_id}", params={"append_to_response": "credits,keywords"})
        return detail

    async def get_watch_providers(self, external_id: int, title_type: str, region: str = "US") -> dict[str, Any]:
        media = "movie" if title_type.upper() == "MOVIE" else "tv"
        data = await self._request("GET", f"/{media}/{external_id}/watch/providers")
        results = data.get("results", {})
        region_data = results.get(region, {})
        return region_data

    async def get_similar(self, external_id: int, title_type: str, page: int = 1) -> dict[str, Any]:
        media = "movie" if title_type.upper() == "MOVIE" else "tv"
        return await self._request("GET", f"/{media}/{external_id}/similar", params={"page": page})

    async def get_trending(self, time_window: str = "week", page: int = 1) -> dict[str, Any]:
        return await self._request("GET", f"/trending/all/{time_window}", params={"page": page})

    async def discover(self, filters: dict[str, Any], page: int = 1) -> dict[str, Any]:
        media = filters.pop("media_type", "movie")
        params = {"page": page, **filters}
        return await self._request("GET", f"/discover/{media}", params=params)


# Module-level singleton
tmdb_client = TMDbClient()


# ---------------------------------------------------------------------------
# Shared upsert helper
# ---------------------------------------------------------------------------

def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


async def upsert_tmdb_items(
    db: AsyncSession,
    items: list[dict[str, Any]],
    *,
    default_media_type: str | None = None,
) -> list["Title"]:
    """Parse raw TMDb result items and upsert them into the database.

    Returns the list of Title ORM objects (both newly created and updated).
    Caller is responsible for committing the session.
    """
    from app.db.models import Title, TitleType

    if not items:
        return []

    tmdb_ids = [it["id"] for it in items if it.get("id")]
    existing_result = await db.execute(
        select(Title).where(Title.tmdb_id.in_(tmdb_ids))
    )
    existing_map: dict[int, Title] = {
        t.tmdb_id: t for t in existing_result.scalars().all()
    }

    upserted: list[Title] = []

    for item in items:
        tmdb_id = item.get("id")
        if not tmdb_id:
            continue

        media_type = item.get("media_type") or default_media_type or "movie"
        if media_type not in ("movie", "tv"):
            continue

        title_type = TitleType.TV if media_type == "tv" else TitleType.MOVIE
        parsed_date = _parse_date(
            item.get("release_date") or item.get("first_air_date")
        )

        title = existing_map.get(tmdb_id)
        if title:
            title.popularity = item.get("popularity", title.popularity)
            title.vote_average = item.get("vote_average", title.vote_average)
            title.vote_count = item.get("vote_count", title.vote_count)
            if item.get("poster_path"):
                title.poster_path = item["poster_path"]
            if item.get("backdrop_path"):
                title.backdrop_path = item["backdrop_path"]
            if item.get("overview"):
                title.overview = item["overview"]
            title.updated_at = datetime.now(timezone.utc)
        else:
            genres = item.get("genres") or [
                {"id": gid} for gid in item.get("genre_ids", [])
            ]
            cast_members = []
            credits = item.get("credits")
            if credits and credits.get("cast"):
                cast_members = [
                    {"name": c.get("name"), "character": c.get("character")}
                    for c in credits["cast"][:10]
                ]
            keywords_data = []
            kw_block = item.get("keywords")
            if kw_block:
                keywords_data = kw_block.get("keywords") or kw_block.get("results") or []

            title = Title(
                tmdb_id=tmdb_id,
                title_type=title_type,
                name=item.get("title") or item.get("name", "Unknown"),
                original_name=item.get("original_title") or item.get("original_name"),
                overview=item.get("overview"),
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                release_date=parsed_date,
                vote_average=item.get("vote_average", 0),
                vote_count=item.get("vote_count", 0),
                popularity=item.get("popularity", 0),
                runtime=item.get("runtime") or (item.get("episode_run_time", [None]) or [None])[0],
                genres=genres,
                cast_members=cast_members,
                keywords=keywords_data,
                original_language=item.get("original_language"),
                status=item.get("status"),
            )
            db.add(title)
            existing_map[tmdb_id] = title

        upserted.append(title)

    await db.flush()
    return upserted
