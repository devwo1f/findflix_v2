from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AvailabilityInfo(BaseModel):
    region: str
    provider_name: str
    provider_type: str
    provider_logo_path: str | None = None
    link: str | None = None

    model_config = {"from_attributes": True}


class TitleResponse(BaseModel):
    id: UUID
    tmdb_id: int
    title_type: str
    name: str
    original_name: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: date | str | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    popularity: float | None = None
    runtime: int | None = None
    genres: list[Any] = []
    original_language: str | None = None

    model_config = {"from_attributes": True}


class TitleDetail(TitleResponse):
    cast_members: list[Any] = []
    keywords: list[Any] = []
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    availability: list[AvailabilityInfo] = []


class TitleSearch(BaseModel):
    q: str | None = None
    genre: str | None = None
    title_type: str | None = Field(None, alias="type")
    year_from: int | None = None
    year_to: int | None = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class TitleListResponse(BaseModel):
    items: list[TitleResponse]
    total: int
    page: int
    per_page: int
    pages: int
