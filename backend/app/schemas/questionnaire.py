from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class QuestionnaireSubmit(BaseModel):
    """Accepts both Flutter format (lists/floats) and dict/string formats."""
    genre_preferences: Any = Field(default_factory=dict)
    mood_preferences: Any = Field(default_factory=dict)
    pacing_preference: Any = None
    tone_preference: Any = None
    intensity_preference: Any = None
    runtime_preference: str | None = None
    rewatch_tolerance: str | None = None
    preferred_providers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_preferences(self) -> "QuestionnaireSubmit":
        if isinstance(self.genre_preferences, list):
            self.genre_preferences = {str(g): 1.0 for g in self.genre_preferences}
        if isinstance(self.mood_preferences, list):
            self.mood_preferences = {str(m): 1.0 for m in self.mood_preferences}

        if isinstance(self.pacing_preference, (int, float)):
            v = float(self.pacing_preference)
            self.pacing_preference = "slow" if v < 0.33 else ("fast" if v > 0.66 else "moderate")
        if isinstance(self.tone_preference, (int, float)):
            v = float(self.tone_preference)
            self.tone_preference = "light" if v < 0.33 else ("dark" if v > 0.66 else "balanced")
        if isinstance(self.intensity_preference, (int, float)):
            v = float(self.intensity_preference)
            self.intensity_preference = "low" if v < 0.33 else ("high" if v > 0.66 else "medium")

        return self


class QuestionnaireUpdate(QuestionnaireSubmit):
    pass


class QuestionnaireResponse(BaseModel):
    id: UUID
    user_id: UUID
    genre_preferences: Any = {}
    mood_preferences: Any = {}
    pacing_preference: str | None = None
    tone_preference: str | None = None
    intensity_preference: str | None = None
    runtime_preference: str | None = None
    rewatch_tolerance: str | None = None
    preferred_providers: list[str] = []
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
