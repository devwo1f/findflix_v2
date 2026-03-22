import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TitleType(str, enum.Enum):
    MOVIE = "movie"
    TV = "tv"


class ProviderType(str, enum.Enum):
    FLATRATE = "flatrate"
    RENT = "rent"
    BUY = "buy"
    FREE = "free"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    region: Mapped[str | None] = mapped_column(String(10), default="US")
    language: Mapped[str | None] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    questionnaire_responses: Mapped[list["QuestionnaireResponse"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    taste_embeddings: Mapped[list["TasteEmbedding"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watch_history: Mapped[list["WatchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlist_entries: Mapped[list["WatchlistEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    recommendation_logs: Mapped[list["RecommendationLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    device_sessions: Mapped[list["DeviceSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_preference: Mapped["NotificationPreference | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# QuestionnaireResponse
# ---------------------------------------------------------------------------

class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    genre_preferences: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    mood_preferences: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    pacing_preference: Mapped[str | None] = mapped_column(String(50))
    tone_preference: Mapped[str | None] = mapped_column(String(50))
    intensity_preference: Mapped[str | None] = mapped_column(String(50))
    runtime_preference: Mapped[str | None] = mapped_column(String(50))
    rewatch_tolerance: Mapped[str | None] = mapped_column(String(50))
    preferred_providers: Mapped[dict | None] = mapped_column(JSONB, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="questionnaire_responses")


# ---------------------------------------------------------------------------
# TasteEmbedding
# ---------------------------------------------------------------------------

class TasteEmbedding(Base):
    __tablename__ = "taste_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="taste_embeddings")


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

class Title(Base):
    __tablename__ = "titles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title_type: Mapped[TitleType] = mapped_column(Enum(TitleType, name="title_type", create_type=False), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(500))
    backdrop_path: Mapped[str | None] = mapped_column(String(500))
    release_date: Mapped[str | None] = mapped_column(String(20))
    vote_average: Mapped[float | None] = mapped_column(Float, default=0.0)
    vote_count: Mapped[int | None] = mapped_column(Integer, default=0)
    popularity: Mapped[float | None] = mapped_column(Float, default=0.0)
    runtime: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[dict | None] = mapped_column(JSONB, default=list)
    cast_members: Mapped[dict | None] = mapped_column(JSONB, default=list)
    keywords: Mapped[dict | None] = mapped_column(JSONB, default=list)
    original_language: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    regional_availability: Mapped[list["RegionalAvailability"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    watch_history_entries: Mapped[list["WatchHistory"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    watchlist_entries: Mapped[list["WatchlistEntry"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    recommendation_logs: Mapped[list["RecommendationLog"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(back_populates="title", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_titles_popularity", "popularity"),
        Index("ix_titles_vote_average", "vote_average"),
        Index("ix_titles_release_date", "release_date"),
    )


# ---------------------------------------------------------------------------
# RegionalAvailability
# ---------------------------------------------------------------------------

class RegionalAvailability(Base):
    __tablename__ = "regional_availability"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, name="provider_type", create_type=False), nullable=False)
    provider_logo_path: Mapped[str | None] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    title: Mapped["Title"] = relationship(back_populates="regional_availability")

    __table_args__ = (
        Index("ix_regional_availability_title_region", "title_id", "region"),
    )


# ---------------------------------------------------------------------------
# WatchHistory
# ---------------------------------------------------------------------------

class WatchHistory(Base):
    __tablename__ = "watch_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    would_rewatch: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mood_feedback: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completion_percentage: Mapped[float] = mapped_column(Float, default=100.0)

    user: Mapped["User"] = relationship(back_populates="watch_history")
    title: Mapped["Title"] = relationship(back_populates="watch_history_entries")

    __table_args__ = (
        Index("ix_watch_history_user_watched", "user_id", "watched_at"),
    )


# ---------------------------------------------------------------------------
# WatchlistEntry
# ---------------------------------------------------------------------------

class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="watchlist_entries")
    title: Mapped["Title"] = relationship(back_populates="watchlist_entries")

    __table_args__ = (
        UniqueConstraint("user_id", "title_id", name="uq_watchlist_user_title"),
        Index("ix_watchlist_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# RecommendationLog
# ---------------------------------------------------------------------------

class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(50))
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship(back_populates="recommendation_logs")
    title: Mapped["Title"] = relationship(back_populates="recommendation_logs")

    __table_args__ = (
        Index("ix_recommendation_logs_user", "user_id"),
        Index("ix_recommendation_logs_shown_at", "shown_at"),
    )


# ---------------------------------------------------------------------------
# SearchHistory
# ---------------------------------------------------------------------------

class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="search_history")

    __table_args__ = (
        Index("ix_search_history_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# FeedbackEvent
# ---------------------------------------------------------------------------

class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # skip, hide, not_interested, rate
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="feedback_events")
    title: Mapped["Title"] = relationship(back_populates="feedback_events")

    __table_args__ = (
        Index("ix_feedback_events_user", "user_id"),
        Index("ix_feedback_events_type", "event_type"),
    )


# ---------------------------------------------------------------------------
# DeviceSession
# ---------------------------------------------------------------------------

class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(200))
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship(back_populates="device_sessions")

    __table_args__ = (
        Index("ix_device_sessions_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# NotificationPreference
# ---------------------------------------------------------------------------

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    new_recommendations: Mapped[bool] = mapped_column(Boolean, default=True)
    watchlist_available: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="notification_preference")
