from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class QuestionnaireSubmit(BaseModel):
    """Accepts both Flutter format (lists/floats) and dict/string formats."""
    genre_preferences: Any = Field(default_factory=dict)
    mood_preferences: Any = Field(default_factory=dict)
    pacing_preference: float | None = 0.5
    tone_preference: float | None = 0.5
    intensity_preference: float | None = 0.5
    runtime_preference: str | None = None
    rewatch_tolerance: str | None = None
    preferred_providers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_preferences(self) -> "QuestionnaireSubmit":
        if isinstance(self.genre_preferences, list):
            self.genre_preferences = {str(g): 1.0 for g in self.genre_preferences}
        if isinstance(self.mood_preferences, list):
            self.mood_preferences = {str(m): 1.0 for m in self.mood_preferences}

        pacing_map = {"slow": 0.2, "moderate": 0.5, "fast": 0.8}
        tone_map = {"light": 0.2, "balanced": 0.5, "dark": 0.8}
        intensity_map = {"low": 0.2, "medium": 0.5, "high": 0.8}

        if isinstance(self.pacing_preference, str):
            self.pacing_preference = pacing_map.get(self.pacing_preference, 0.5)
        if isinstance(self.tone_preference, str):
            self.tone_preference = tone_map.get(self.tone_preference, 0.5)
        if isinstance(self.intensity_preference, str):
            self.intensity_preference = intensity_map.get(self.intensity_preference, 0.5)

        return self


class QuestionnaireUpdate(QuestionnaireSubmit):
    pass


class QuestionnaireResponse(BaseModel):
    id: UUID
    user_id: UUID
    genre_preferences: Any = {}
    mood_preferences: Any = {}
    pacing_preference: float | None = None
    tone_preference: float | None = None
    intensity_preference: float | None = None
    runtime_preference: str | None = None
    rewatch_tolerance: str | None = None
    preferred_providers: list[str] = []
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
