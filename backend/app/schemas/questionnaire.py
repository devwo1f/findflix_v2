from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionnaireSubmit(BaseModel):
    genre_preferences: dict[str, Any] = Field(default_factory=dict, description="Genre name -> weight mapping")
    mood_preferences: dict[str, Any] = Field(default_factory=dict, description="Mood name -> weight mapping")
    pacing_preference: str | None = Field(None, description="slow / moderate / fast")
    tone_preference: str | None = Field(None, description="light / balanced / dark")
    intensity_preference: str | None = Field(None, description="low / medium / high")
    runtime_preference: str | None = Field(None, description="short / medium / long / any")
    rewatch_tolerance: str | None = Field(None, description="never / sometimes / often")
    preferred_providers: list[str] = Field(default_factory=list, description="List of streaming providers")


class QuestionnaireUpdate(QuestionnaireSubmit):
    pass


class QuestionnaireResponse(BaseModel):
    id: UUID
    user_id: UUID
    genre_preferences: dict[str, Any] = {}
    mood_preferences: dict[str, Any] = {}
    pacing_preference: str | None = None
    tone_preference: str | None = None
    intensity_preference: str | None = None
    runtime_preference: str | None = None
    rewatch_tolerance: str | None = None
    preferred_providers: list[str] = []
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
