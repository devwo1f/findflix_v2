"""Feature engineering utilities for title (item) data.

Transforms raw TMDb-style title metadata into numeric feature vectors
suitable for the item tower of the two-tower model.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from ml_service.core.config import settings
from ml_service.features.user_features import GENRE_ID_TO_INDEX, TMDB_GENRE_IDS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_item_features(title_metadata: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Build the full item feature dict expected by ``ItemTower``.

    Parameters
    ----------
    title_metadata : dict
        Keys: genre_ids, cast (list[dict] with ``id``, ``name``),
        overview (str), runtime (int minutes), popularity (float),
        vote_average (float), vote_count (int), release_date (str ISO),
        providers (list), original_language (str)

    Returns
    -------
    dict[str, np.ndarray]
        Ready-to-feed feature arrays (without batch dimension).
    """
    genre_vec = encode_title_genres(title_metadata.get("genre_ids", []))
    cast_emb = encode_cast(
        title_metadata.get("cast", []),
        embeddings_cache=None,
    )
    plot_emb = encode_plot(title_metadata.get("overview", ""), tokenizer=None)

    pop, vote_avg, vote_cnt = normalize_popularity(
        title_metadata.get("popularity", 0.0),
        title_metadata.get("vote_average", 0.0),
        title_metadata.get("vote_count", 0),
    )

    runtime = _normalize_runtime(title_metadata.get("runtime", 90))
    release_year = _normalize_year(title_metadata.get("release_date", ""))
    provider_count = _normalize_provider_count(
        len(title_metadata.get("providers", []))
    )
    language_id = _encode_language(
        title_metadata.get("original_language", "en")
    )

    return {
        "genres": genre_vec,
        "cast_embedding": cast_emb,
        "plot_embedding": plot_emb,
        "runtime": np.array([runtime], dtype=np.float32),
        "popularity": np.array([pop], dtype=np.float32),
        "vote_average": np.array([vote_avg], dtype=np.float32),
        "release_year": np.array([release_year], dtype=np.float32),
        "provider_count": np.array([provider_count], dtype=np.float32),
        "language_id": np.array(language_id, dtype=np.int32),
    }


def encode_title_genres(genres: List[int]) -> np.ndarray:
    """Multi-hot encoding from TMDb genre IDs."""
    vec = np.zeros(settings.NUM_GENRES, dtype=np.float32)
    for gid in genres:
        idx = GENRE_ID_TO_INDEX.get(gid)
        if idx is not None:
            vec[idx] = 1.0
    return vec


def encode_cast(
    cast_list: List[Dict[str, Any]],
    embeddings_cache: Optional[Dict[int, np.ndarray]] = None,
    max_cast: int = 10,
) -> np.ndarray:
    """Produce an averaged cast embedding.

    If *embeddings_cache* is provided, look up each cast member's pre-trained
    embedding by their ``id`` and average.  Otherwise fall back to a
    deterministic hash-based embedding.
    """
    dim = settings.CAST_EMBEDDING_DIM
    embeddings: List[np.ndarray] = []

    for member in cast_list[:max_cast]:
        cast_id = member.get("id", 0)
        if embeddings_cache and cast_id in embeddings_cache:
            embeddings.append(embeddings_cache[cast_id])
        else:
            # Deterministic pseudo-embedding from cast id
            embeddings.append(_hash_embedding(str(cast_id), dim))

    if not embeddings:
        return np.zeros(dim, dtype=np.float32)

    return np.mean(np.stack(embeddings), axis=0).astype(np.float32)


def encode_plot(
    overview: str,
    tokenizer: Optional[Any] = None,
    dim: int = settings.PLOT_EMBEDDING_DIM,
) -> np.ndarray:
    """Produce a plot embedding.

    Uses *tokenizer* if provided (e.g. a sentence-transformers model).
    Otherwise falls back to a simple hash-based bag-of-words embedding that
    is deterministic and requires no external model.
    """
    if tokenizer is not None:
        # tokenizer is expected to implement encode(text) -> np.ndarray
        return np.array(tokenizer.encode(overview), dtype=np.float32)[:dim]

    if not overview:
        return np.zeros(dim, dtype=np.float32)

    # Simple TF-IDF-like hashing trick
    tokens = overview.lower().split()
    vec = np.zeros(dim, dtype=np.float32)
    for token in tokens:
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % dim
        # TF component: count-based
        vec[idx] += 1.0

    # Normalise to unit vector
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def normalize_popularity(
    popularity: float,
    vote_avg: float,
    vote_count: int,
) -> tuple[float, float, float]:
    """Normalise popularity metrics to roughly [0, 1].

    - popularity:  log-scaled then clipped
    - vote_avg:    divided by 10
    - vote_count:  log-scaled then clipped
    """
    pop_norm = min(math.log1p(popularity) / 10.0, 1.0)
    avg_norm = min(vote_avg / 10.0, 1.0)
    cnt_norm = min(math.log1p(vote_count) / 12.0, 1.0)
    return pop_norm, avg_norm, cnt_norm


def compute_freshness(release_date: str, half_life_days: float = 365.0) -> float:
    """Exponential decay score based on how recent the title is.

    Returns a value in (0, 1] where 1 means brand-new.
    """
    if not release_date:
        return 0.0
    try:
        rd = datetime.fromisoformat(release_date).replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    now = datetime.now(timezone.utc)
    days_old = max((now - rd).days, 0)
    return math.exp(-0.693 * days_old / half_life_days)  # 0.693 = ln(2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_runtime(runtime_minutes: int) -> float:
    """Normalise runtime (in minutes) to [0, 1]. 240 min = 1.0."""
    return min(float(runtime_minutes) / 240.0, 1.0)


def _normalize_year(release_date: str) -> float:
    """Extract year from ISO date string and normalise to [0, 1].

    Maps 1900..2030 -> 0..1.
    """
    if not release_date:
        return 0.5
    try:
        year = int(release_date[:4])
    except (ValueError, IndexError):
        return 0.5
    return min(max((year - 1900) / 130.0, 0.0), 1.0)


def _normalize_provider_count(count: int) -> float:
    """Normalise streaming-provider count to [0, 1]. 20 providers = 1.0."""
    return min(count / 20.0, 1.0)


def _encode_language(lang_code: str) -> int:
    """Hash-based language encoding."""
    return hash(lang_code.lower()) % settings.NUM_LANGUAGES


def _hash_embedding(key: str, dim: int) -> np.ndarray:
    """Deterministic pseudo-random embedding from a string key."""
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9
    return vec
