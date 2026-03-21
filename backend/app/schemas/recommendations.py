from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.titles import AvailabilityInfo, TitleResponse


class RecommendationRequest(BaseModel):
    include_rewatches: bool = False
    mood: str | None = None
    limit: int = Field(20, ge=1, le=100)


class RecommendationItem(BaseModel):
    title: TitleResponse
    score: float
    reason: str
    availability: list[AvailabilityInfo] = []


class RecommendationListResponse(BaseModel):
    items: list[RecommendationItem]
    model_version: str | None = None
    total: int


class RecommendationFeedback(BaseModel):
    feedback: str = Field(..., description="liked / disliked / not_interested / clicked")


class TrendingResponse(BaseModel):
    items: list[TitleResponse]
    total: int
    page: int
