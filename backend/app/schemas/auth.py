from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=100)
    region: str | None = Field("US", max_length=10)
    language: str | None = Field("en", max_length=10)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class FirebaseAuthRequest(BaseModel):
    firebase_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    region: str | None = None
    language: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
