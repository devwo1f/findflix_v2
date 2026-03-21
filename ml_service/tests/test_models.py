"""Tests for model creation, forward pass shapes, and embedding dimensions."""

from __future__ import annotations

import numpy as np
import pytest
import tensorflow as tf

from ml_service.core.config import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_tower():
    from ml_service.models.two_tower import UserTower
    return UserTower(embedding_dim=settings.EMBEDDING_DIM)


@pytest.fixture
def item_tower():
    from ml_service.models.two_tower import ItemTower
    return ItemTower(embedding_dim=settings.EMBEDDING_DIM)


@pytest.fixture
def reranker():
    from ml_service.models.reranker import TransformerReranker
    return TransformerReranker(d_model=settings.EMBEDDING_DIM)


def _random_user_inputs(batch_size: int = 2) -> dict[str, np.ndarray]:
    rng = np.random.RandomState(0)
    return {
        "genre_preferences": rng.rand(batch_size, settings.NUM_GENRES).astype(np.float32),
        "mood_preferences": rng.rand(batch_size, settings.NUM_MOODS).astype(np.float32),
        "pacing": rng.rand(batch_size, 1).astype(np.float32),
        "tone": rng.rand(batch_size, 1).astype(np.float32),
        "intensity": rng.rand(batch_size, 1).astype(np.float32),
        "runtime_preference": rng.rand(batch_size, 1).astype(np.float32),
        "rewatch_tolerance": rng.rand(batch_size, 1).astype(np.float32),
        "watch_history_embeddings": rng.randn(
            batch_size, settings.MAX_WATCH_HISTORY, settings.EMBEDDING_DIM
        ).astype(np.float32),
        "region_id": rng.randint(0, settings.NUM_REGIONS, size=(batch_size,)).astype(np.int32),
        "language_id": rng.randint(0, settings.NUM_LANGUAGES, size=(batch_size,)).astype(np.int32),
    }


def _random_item_inputs(batch_size: int = 2) -> dict[str, np.ndarray]:
    rng = np.random.RandomState(1)
    return {
        "genres": rng.rand(batch_size, settings.NUM_GENRES).astype(np.float32),
        "cast_embedding": rng.randn(batch_size, settings.CAST_EMBEDDING_DIM).astype(np.float32),
        "plot_embedding": rng.randn(batch_size, settings.PLOT_EMBEDDING_DIM).astype(np.float32),
        "runtime": rng.rand(batch_size, 1).astype(np.float32),
        "popularity": rng.rand(batch_size, 1).astype(np.float32),
        "vote_average": rng.rand(batch_size, 1).astype(np.float32),
        "release_year": rng.rand(batch_size, 1).astype(np.float32),
        "provider_count": rng.rand(batch_size, 1).astype(np.float32),
        "language_id": rng.randint(0, settings.NUM_LANGUAGES, size=(batch_size,)).astype(np.int32),
    }


# ---------------------------------------------------------------------------
# UserTower tests
# ---------------------------------------------------------------------------

class TestUserTower:
    def test_output_shape(self, user_tower: tf.keras.Model) -> None:
        inputs = _random_user_inputs(batch_size=4)
        output = user_tower(inputs, training=False)
        assert output.shape == (4, settings.EMBEDDING_DIM)

    def test_output_normalized(self, user_tower: tf.keras.Model) -> None:
        inputs = _random_user_inputs(batch_size=3)
        output = user_tower(inputs, training=False).numpy()
        norms = np.linalg.norm(output, axis=-1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_training_mode_runs(self, user_tower: tf.keras.Model) -> None:
        inputs = _random_user_inputs(batch_size=2)
        output = user_tower(inputs, training=True)
        assert output.shape == (2, settings.EMBEDDING_DIM)


# ---------------------------------------------------------------------------
# ItemTower tests
# ---------------------------------------------------------------------------

class TestItemTower:
    def test_output_shape(self, item_tower: tf.keras.Model) -> None:
        inputs = _random_item_inputs(batch_size=4)
        output = item_tower(inputs, training=False)
        assert output.shape == (4, settings.EMBEDDING_DIM)

    def test_output_normalized(self, item_tower: tf.keras.Model) -> None:
        inputs = _random_item_inputs(batch_size=3)
        output = item_tower(inputs, training=False).numpy()
        norms = np.linalg.norm(output, axis=-1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_training_mode_runs(self, item_tower: tf.keras.Model) -> None:
        inputs = _random_item_inputs(batch_size=2)
        output = item_tower(inputs, training=True)
        assert output.shape == (2, settings.EMBEDDING_DIM)


# ---------------------------------------------------------------------------
# TransformerReranker tests
# ---------------------------------------------------------------------------

class TestTransformerReranker:
    def test_output_shape(self, reranker: tf.keras.Model) -> None:
        batch, seq_len, num_candidates, feat_dim = 2, 10, 5, settings.EMBEDDING_DIM
        inputs = {
            "user_sequence": np.random.randn(batch, seq_len, feat_dim).astype(np.float32),
            "candidates": np.random.randn(batch, num_candidates, feat_dim).astype(np.float32),
        }
        scores = reranker(inputs, training=False)
        assert scores.shape == (batch, num_candidates)

    def test_scores_in_range(self, reranker: tf.keras.Model) -> None:
        inputs = {
            "user_sequence": np.random.randn(2, 8, settings.EMBEDDING_DIM).astype(np.float32),
            "candidates": np.random.randn(2, 3, settings.EMBEDDING_DIM).astype(np.float32),
        }
        scores = reranker(inputs, training=False).numpy()
        assert np.all(scores >= 0.0) and np.all(scores <= 1.0)

    def test_diversity_penalty(self) -> None:
        from ml_service.models.reranker import TransformerReranker

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        penalty = TransformerReranker.compute_diversity_penalty(a, [b])
        assert penalty == pytest.approx(1.0, abs=1e-5)

    def test_diversity_penalty_empty_selected(self) -> None:
        from ml_service.models.reranker import TransformerReranker

        a = np.array([1.0, 0.0, 0.0])
        assert TransformerReranker.compute_diversity_penalty(a, []) == 0.0

    def test_novelty_bonus(self) -> None:
        from ml_service.models.reranker import TransformerReranker

        cand_genres = np.array([1, 0, 1, 0], dtype=np.float32)
        user_genres = np.array([1, 0, 0, 0], dtype=np.float32)
        bonus = TransformerReranker.compute_novelty_bonus(
            cand_genres, [1, 2, 3], user_genres, {1}
        )
        # 1 unseen genre out of 2 -> genre_novelty = 0.5
        # 2 new cast out of 3 -> cast_novelty = 0.667
        assert bonus > 0


# ---------------------------------------------------------------------------
# Fallback recommender tests
# ---------------------------------------------------------------------------

class TestFallbackRecommender:
    def test_popularity_based(self) -> None:
        from ml_service.models.fallback import FallbackRecommender

        catalog = [
            {"id": "1", "popularity": 100, "vote_average": 8.0},
            {"id": "2", "popularity": 50, "vote_average": 7.0},
            {"id": "3", "popularity": 200, "vote_average": 9.0},
        ]
        fb = FallbackRecommender(catalog)
        results = fb.popularity_based(limit=2)
        assert len(results) == 2
        assert results[0]["title_id"] == "3"

    def test_cold_start(self) -> None:
        from ml_service.models.fallback import FallbackRecommender

        catalog = [
            {"id": "1", "genre_ids": [28, 12], "vote_average": 8.0, "vote_count": 100},
            {"id": "2", "genre_ids": [35], "vote_average": 7.0, "vote_count": 100},
            {"id": "3", "genre_ids": [28], "vote_average": 9.0, "vote_count": 100},
        ]
        fb = FallbackRecommender(catalog)
        results = fb.cold_start({"preferred_genre_ids": [28]}, limit=3)
        assert len(results) > 0
        # Action-containing titles should rank higher
        action_ids = {r["title_id"] for r in results[:2]}
        assert "1" in action_ids or "3" in action_ids
