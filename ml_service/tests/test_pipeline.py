"""Tests for the retrieval and ranking pipelines."""

from __future__ import annotations

from typing import Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ml_service.core.config import settings


# ---------------------------------------------------------------------------
# Retrieval pipeline tests
# ---------------------------------------------------------------------------

class TestRetrievalPipeline:
    """Test the RetrievalPipeline with a mocked model."""

    @pytest.fixture
    def pipeline(self):
        """Create a pipeline with no real model loaded."""
        with patch(
            "ml_service.pipeline.retrieval.RetrievalPipeline._load_model"
        ):
            from ml_service.pipeline.retrieval import RetrievalPipeline
            p = RetrievalPipeline.__new__(RetrievalPipeline)
            p.embedding_dim = settings.EMBEDDING_DIM
            p._user_tower = None
            p._item_tower = None
            p._item_ids = []
            p._item_embeddings = None
            p._index_ready = False
            return p

    def test_not_ready_initially(self, pipeline) -> None:
        assert not pipeline.is_ready

    def test_retrieve_returns_empty_when_not_ready(self, pipeline) -> None:
        emb = np.random.randn(settings.EMBEDDING_DIM).astype(np.float32)
        results = pipeline.retrieve(emb, top_k=10)
        assert results == []

    def test_retrieve_with_manual_index(self, pipeline) -> None:
        """Build a brute-force index manually and verify retrieval."""
        n_items = 50
        dim = settings.EMBEDDING_DIM
        rng = np.random.RandomState(42)

        # Create random item embeddings and normalise
        embs = rng.randn(n_items, dim).astype(np.float32)
        embs /= np.linalg.norm(embs, axis=-1, keepdims=True)

        pipeline._item_embeddings = embs
        pipeline._item_ids = [f"title_{i}" for i in range(n_items)]
        pipeline._index_ready = True

        # Query with the first item's embedding -> should return itself as top-1
        query = embs[0]
        results = pipeline.retrieve(query, top_k=5)

        assert len(results) == 5
        assert results[0][0] == "title_0"
        assert results[0][1] == pytest.approx(1.0, abs=1e-5)

        # Scores should be descending
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_top_k_larger_than_catalog(self, pipeline) -> None:
        dim = settings.EMBEDDING_DIM
        embs = np.eye(3, dim, dtype=np.float32)
        embs /= np.linalg.norm(embs, axis=-1, keepdims=True)

        pipeline._item_embeddings = embs
        pipeline._item_ids = ["a", "b", "c"]
        pipeline._index_ready = True

        results = pipeline.retrieve(embs[0], top_k=100)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Ranking pipeline tests
# ---------------------------------------------------------------------------

class TestRankingPipeline:
    """Test ranking pipeline with the untrained reranker."""

    @pytest.fixture
    def pipeline(self):
        with patch(
            "ml_service.pipeline.ranking.RankingPipeline._load_model"
        ):
            from ml_service.models.reranker import TransformerReranker
            from ml_service.pipeline.ranking import RankingPipeline

            p = RankingPipeline.__new__(RankingPipeline)
            p._reranker = TransformerReranker(d_model=settings.EMBEDDING_DIM)
            return p

    def test_rank_returns_all_candidates(self, pipeline) -> None:
        dim = settings.EMBEDDING_DIM
        user_seq = np.random.randn(10, dim).astype(np.float32)
        candidates = [
            {"title_id": f"t{i}", "features": np.random.randn(dim).astype(np.float32)}
            for i in range(5)
        ]
        ranked = pipeline.rank({"user_sequence": user_seq}, candidates)
        assert len(ranked) == 5
        # Each result should have title_id and score
        for r in ranked:
            assert "title_id" in r
            assert "score" in r
            assert 0.0 <= r["score"] <= 1.0

    def test_rank_empty_candidates(self, pipeline) -> None:
        user_seq = np.random.randn(10, settings.EMBEDDING_DIM).astype(np.float32)
        ranked = pipeline.rank({"user_sequence": user_seq}, [])
        assert ranked == []

    def test_rank_sorted_descending(self, pipeline) -> None:
        dim = settings.EMBEDDING_DIM
        user_seq = np.random.randn(10, dim).astype(np.float32)
        candidates = [
            {"title_id": f"t{i}", "features": np.random.randn(dim).astype(np.float32)}
            for i in range(8)
        ]
        ranked = pipeline.rank({"user_sequence": user_seq}, candidates)
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Diversity (MMR) tests
# ---------------------------------------------------------------------------

class TestDiversity:
    def test_mmr_preserves_count(self) -> None:
        from ml_service.pipeline.ranking import RankingPipeline

        ranked = [
            {"title_id": "a", "score": 0.9},
            {"title_id": "b", "score": 0.8},
            {"title_id": "c", "score": 0.7},
        ]
        features = {
            "a": np.array([1, 0, 0], dtype=np.float32),
            "b": np.array([0, 1, 0], dtype=np.float32),
            "c": np.array([0, 0, 1], dtype=np.float32),
        }
        result = RankingPipeline.apply_diversity(ranked, features, lambda_diversity=0.7)
        assert len(result) == 3

    def test_mmr_top_n(self) -> None:
        from ml_service.pipeline.ranking import RankingPipeline

        ranked = [{"title_id": str(i), "score": 1.0 - i * 0.1} for i in range(10)]
        features = {str(i): np.random.randn(5).astype(np.float32) for i in range(10)}
        result = RankingPipeline.apply_diversity(ranked, features, top_n=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Rewatch filter tests
# ---------------------------------------------------------------------------

class TestRewatchFilter:
    def test_filter_removes_watched(self) -> None:
        from ml_service.pipeline.ranking import RankingPipeline

        ranked = [
            {"title_id": "a", "score": 0.9},
            {"title_id": "b", "score": 0.8},
            {"title_id": "c", "score": 0.7},
        ]
        result = RankingPipeline.apply_rewatch_filter(ranked, {"a", "c"}, include_rewatches=False)
        assert len(result) == 1
        assert result[0]["title_id"] == "b"

    def test_filter_flags_rewatches(self) -> None:
        from ml_service.pipeline.ranking import RankingPipeline

        ranked = [
            {"title_id": "a", "score": 0.9},
            {"title_id": "b", "score": 0.8},
        ]
        result = RankingPipeline.apply_rewatch_filter(ranked, {"a"}, include_rewatches=True)
        assert len(result) == 2
        assert result[0]["is_rewatch"] is True
        assert result[1]["is_rewatch"] is False


# ---------------------------------------------------------------------------
# Feature engineering round-trip tests
# ---------------------------------------------------------------------------

class TestFeatureEngineering:
    def test_user_features_shape(self) -> None:
        from ml_service.features.user_features import extract_user_features

        questionnaire = {
            "preferred_genre_ids": [28, 35],
            "mood_preferences": ["happy", "excited"],
            "pacing": 0.7,
            "tone": 0.3,
            "intensity": 0.5,
            "runtime_preference": 0.6,
            "rewatch_tolerance": 0.4,
            "region": "US",
            "language": "en",
        }
        features = extract_user_features(questionnaire, [], [])
        assert features["genre_preferences"].shape == (settings.NUM_GENRES,)
        assert features["mood_preferences"].shape == (settings.NUM_MOODS,)
        assert features["watch_history_embeddings"].shape == (
            settings.MAX_WATCH_HISTORY,
            settings.EMBEDDING_DIM,
        )

    def test_item_features_shape(self) -> None:
        from ml_service.features.item_features import extract_item_features

        metadata = {
            "genre_ids": [28, 878],
            "cast": [{"id": 1, "name": "Actor A"}, {"id": 2, "name": "Actor B"}],
            "overview": "A thrilling adventure in space",
            "runtime": 120,
            "popularity": 45.6,
            "vote_average": 7.8,
            "vote_count": 1200,
            "release_date": "2024-01-15",
            "providers": ["Netflix", "Amazon"],
            "original_language": "en",
        }
        features = extract_item_features(metadata)
        assert features["genres"].shape == (settings.NUM_GENRES,)
        assert features["cast_embedding"].shape == (settings.CAST_EMBEDDING_DIM,)
        assert features["plot_embedding"].shape == (settings.PLOT_EMBEDDING_DIM,)
