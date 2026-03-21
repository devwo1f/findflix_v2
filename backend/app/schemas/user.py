from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.titles import TitleResponse


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    region: str | None = Field(None, max_length=10)
    language: str | None = Field(None, max_length=10)


class WatchHistoryEntry(BaseModel):
    title_id: UUID
    rating: float | None = Field(None, ge=0, le=10)
    would_rewatch: bool | None = None
    mood_feedback: str | None = Field(None, max_length=100)
    completion_percentage: float = Field(100.0, ge=0, le=100)


class WatchHistoryResponse(BaseModel):
    id: UUID
    title: TitleResponse
    watched_at: datetime
    rating: float | None = None
    would_rewatch: bool | None = None
    mood_feedback: str | None = None
    completion_percentage: float = 100.0


class WatchlistAdd(BaseModel):
    title_id: UUID
    priority: int = Field(0, ge=0, le=10)
    notes: str | None = Field(None, max_length=1000)


class WatchlistResponse(BaseModel):
    id: UUID
    title: TitleResponse
    added_at: datetime
    priority: int = 0
    notes: str | None = None


class FeedbackSubmit(BaseModel):
    title_id: UUID
    event_type: str = Field(..., description="skip / hide / not_interested / rate")
    value: dict[str, Any] | None = None


class DashboardStats(BaseModel):
    total_watched: int
    total_watchlist: int
    average_rating: float | None
    top_genres: list[dict[str, Any]]
    recent_activity: list[dict[str, Any]]
    recommendations_pending: int


class SearchHistoryResponse(BaseModel):
    id: UUID
    query: str
    filters: dict[str, Any] | None = None
    searched_at: datetime

    model_config = {"from_attributes": True}
