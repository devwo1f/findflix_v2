"""Feature engineering utilities for user data.

Transforms raw questionnaire responses, watch history, and feedback events
into numeric feature vectors suitable for the two-tower model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from ml_service.core.config import settings


# ---------------------------------------------------------------------------
# TMDb genre mapping  (sorted by genre ID for deterministic multi-hot order)
# ---------------------------------------------------------------------------

TMDB_GENRE_IDS: List[int] = sorted([
    28, 12, 16, 35, 80, 99, 18, 10751, 14, 36,
    27, 10402, 9648, 10749, 878, 10770, 53, 10752, 37,
])

GENRE_ID_TO_INDEX: Dict[int, int] = {gid: idx for idx, gid in enumerate(TMDB_GENRE_IDS)}

# Standard mood vocabulary
MOOD_VOCAB: List[str] = [
    "happy", "sad", "excited", "relaxed", "tense",
    "romantic", "nostalgic", "curious", "scared", "inspired",
]
MOOD_TO_INDEX: Dict[str, int] = {m: i for i, m in enumerate(MOOD_VOCAB)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_user_features(
    questionnaire: Dict[str, Any],
    watch_history: List[Dict[str, Any]],
    feedback_events: List[Dict[str, Any]],
) -> Dict[str, np.ndarray]:
    """Build the full user feature dict expected by ``UserTower``.

    Parameters
    ----------
    questionnaire : dict
        Keys: preferred_genre_ids, mood_preferences, pacing, tone, intensity,
        runtime_preference, rewatch_tolerance, region, language
    watch_history : list[dict]
        Each entry: {title_id, embedding (list[float]), timestamp}
    feedback_events : list[dict]
        Each entry: {title_id, event_type, value, timestamp}

    Returns
    -------
    dict[str, np.ndarray]
        Ready-to-feed feature arrays (without batch dimension).
    """
    genre_vec = encode_genres(questionnaire.get("preferred_genre_ids", []))
    mood_vec = encode_mood(questionnaire.get("mood_preferences", []))

    pacing, tone, intensity = normalize_preferences(
        questionnaire.get("pacing", 0.5),
        questionnaire.get("tone", 0.5),
        questionnaire.get("intensity", 0.5),
    )

    runtime_pref = float(questionnaire.get("runtime_preference", 0.5))
    rewatch_tol = float(questionnaire.get("rewatch_tolerance", 0.5))

    # Encode region / language as integer ids (simple hash mod)
    region_id = _encode_categorical(questionnaire.get("region", "US"), settings.NUM_REGIONS)
    language_id = _encode_categorical(questionnaire.get("language", "en"), settings.NUM_LANGUAGES)

    watch_seq = build_watch_sequence(watch_history, max_len=settings.MAX_WATCH_HISTORY)

    # Optionally weight genre vector by positive feedback
    genre_vec = _adjust_genres_by_feedback(genre_vec, feedback_events)

    return {
        "genre_preferences": genre_vec,
        "mood_preferences": mood_vec,
        "pacing": np.array([pacing], dtype=np.float32),
        "tone": np.array([tone], dtype=np.float32),
        "intensity": np.array([intensity], dtype=np.float32),
        "runtime_preference": np.array([runtime_pref], dtype=np.float32),
        "rewatch_tolerance": np.array([rewatch_tol], dtype=np.float32),
        "watch_history_embeddings": watch_seq,
        "region_id": np.array(region_id, dtype=np.int32),
        "language_id": np.array(language_id, dtype=np.int32),
    }


def encode_genres(genre_list: List[int]) -> np.ndarray:
    """Convert a list of TMDb genre IDs into a multi-hot float vector."""
    vec = np.zeros(settings.NUM_GENRES, dtype=np.float32)
    for gid in genre_list:
        idx = GENRE_ID_TO_INDEX.get(gid)
        if idx is not None:
            vec[idx] = 1.0
    return vec


def encode_mood(mood_preferences: List[str]) -> np.ndarray:
    """Convert mood name list to multi-hot vector."""
    vec = np.zeros(settings.NUM_MOODS, dtype=np.float32)
    for mood in mood_preferences:
        idx = MOOD_TO_INDEX.get(mood.lower())
        if idx is not None:
            vec[idx] = 1.0
    return vec


def build_watch_sequence(
    history: List[Dict[str, Any]],
    max_len: int = 50,
    embedding_dim: int = settings.EMBEDDING_DIM,
) -> np.ndarray:
    """Build a padded sequence of watch-history embeddings.

    Parameters
    ----------
    history : list[dict]
        Each entry must have an ``embedding`` key (list of floats).
    max_len : int
        Maximum sequence length (truncates oldest).

    Returns
    -------
    np.ndarray  shape (max_len, embedding_dim)
        Zero-padded from the left.
    """
    # Sort by timestamp ascending (oldest first)
    sorted_hist = sorted(history, key=lambda h: h.get("timestamp", ""))

    embeddings = []
    for entry in sorted_hist:
        emb = entry.get("embedding")
        if emb is not None:
            arr = np.array(emb, dtype=np.float32)
            if arr.shape == (embedding_dim,):
                embeddings.append(arr)

    # Truncate to most recent max_len
    embeddings = embeddings[-max_len:]

    # Zero-pad on the left
    seq = np.zeros((max_len, embedding_dim), dtype=np.float32)
    if embeddings:
        stacked = np.stack(embeddings, axis=0)
        seq[-len(embeddings):] = stacked

    return seq


def normalize_preferences(
    pacing: float,
    tone: float,
    intensity: float,
) -> tuple[float, float, float]:
    """Clamp and normalise preference scalars to [0, 1]."""
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    return _clamp(pacing), _clamp(tone), _clamp(intensity)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _encode_categorical(value: str, vocab_size: int) -> int:
    """Deterministic hash-based encoding for a categorical string."""
    return hash(value.lower()) % vocab_size


def _adjust_genres_by_feedback(
    genre_vec: np.ndarray,
    feedback_events: List[Dict[str, Any]],
) -> np.ndarray:
    """Boost / suppress genre weights based on explicit feedback.

    Positive events (``like``, ``save``) add a small boost to genres of the
    liked title.  Negative events (``dislike``, ``hide``) suppress.
    """
    adjustments = np.zeros_like(genre_vec)
    for event in feedback_events:
        event_type = event.get("event_type", "")
        title_genres: List[int] = event.get("genre_ids", [])
        if event_type in ("like", "save", "watch_complete"):
            for gid in title_genres:
                idx = GENRE_ID_TO_INDEX.get(gid)
                if idx is not None:
                    adjustments[idx] += 0.1
        elif event_type in ("dislike", "hide"):
            for gid in title_genres:
                idx = GENRE_ID_TO_INDEX.get(gid)
                if idx is not None:
                    adjustments[idx] -= 0.1

    adjusted = genre_vec + adjustments
    return np.clip(adjusted, 0.0, 2.0)
