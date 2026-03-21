import abc
from typing import Any

import httpx
import structlog
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
