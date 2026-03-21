"""Configuration settings for the ML recommendation service."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML service configuration loaded from environment variables."""

    MODEL_PATH: str = "/app/models"
    REDIS_URL: str = "redis://localhost:6379/0"
    EMBEDDING_DIM: int = 128
    TOP_K: int = 100
    BATCH_SIZE: int = 256

    # Model file names
    RETRIEVAL_MODEL_DIR: str = "two_tower"
    RERANKER_MODEL_DIR: str = "reranker"

    # Feature dimensions
    NUM_GENRES: int = 19  # TMDb genre count
    NUM_MOODS: int = 10
    CAST_EMBEDDING_DIM: int = 64
    PLOT_EMBEDDING_DIM: int = 128
    MAX_WATCH_HISTORY: int = 50
    NUM_REGIONS: int = 50
    NUM_LANGUAGES: int = 50

    # Serving
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    LOG_LEVEL: str = "info"

    # Training
    LEARNING_RATE: float = 1e-3
    EPOCHS: int = 20
    EARLY_STOPPING_PATIENCE: int = 3
    DATABASE_URL: str = "postgresql://findflix:findflix@localhost:5432/findflix"

    # Ranking
    DIVERSITY_LAMBDA: float = 0.3
    NOVELTY_WEIGHT: float = 0.1

    model_config = {"env_prefix": "ML_"}


settings = Settings()
