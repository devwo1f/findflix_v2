"""Recommendation orchestrator: ties retrieval, ranking, and post-processing.

This is the main entry-point called by the API layer.  It coordinates the
full pipeline:  embed user -> retrieve candidates -> rerank -> diversify ->
filter -> generate explanations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import numpy as np
import structlog

from ml_service.core.config import settings
from ml_service.features.user_features import (
    GENRE_ID_TO_INDEX,
    TMDB_GENRE_IDS,
    extract_user_features,
)
from ml_service.models.fallback import FallbackRecommender
from ml_service.pipeline.ranking import RankingPipeline
from ml_service.pipeline.retrieval import RetrievalPipeline

logger = structlog.get_logger(__name__)

# Reverse mapping for explanation generation
INDEX_TO_GENRE_NAME: Dict[int, str] = {}
_GENRE_NAMES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Family", "Fantasy", "History",
    "Horror", "Music", "Mystery", "Romance", "Science Fiction",
    "TV Movie", "Thriller", "War", "Western",
]
for _idx, _name in enumerate(_GENRE_NAMES):
    INDEX_TO_GENRE_NAME[_idx] = _name


class RecommendationOrchestrator:
    """End-to-end recommendation pipeline."""

    def __init__(
        self,
        retrieval: Optional[RetrievalPipeline] = None,
        ranking: Optional[RankingPipeline] = None,
        fallback: Optional[FallbackRecommender] = None,
    ) -> None:
        self.retrieval = retrieval or RetrievalPipeline()
        self.ranking = ranking or RankingPipeline()
        self.fallback = fallback or FallbackRecommender()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def recommend(
        self,
        user_id: str,
        request: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Produce a final recommendation list for *user_id*.

        Parameters
        ----------
        user_id : str
        request : dict
            Expected keys:
                questionnaire       : dict
                watch_history       : list[dict]
                feedback_events     : list[dict]
                top_k               : int (optional)
                include_rewatches   : bool (optional)
                diversity_lambda    : float (optional)

        Returns
        -------
        list[dict]
            Each entry has ``title_id``, ``score``, ``reason``.
        """
        top_k = request.get("top_k", settings.TOP_K)
        include_rewatches = request.get("include_rewatches", False)
        diversity_lambda = request.get("diversity_lambda", settings.DIVERSITY_LAMBDA)

        questionnaire = request.get("questionnaire", {})
        watch_history = request.get("watch_history", [])
        feedback_events = request.get("feedback_events", [])

        # --- Fallback when models are not ready ---
        if not self.retrieval.is_ready:
            logger.warning(
                "models_not_ready_using_fallback",
                user_id=user_id,
            )
            return self._fallback_recommend(questionnaire, top_k)

        # --- 1. Feature extraction & user embedding ---
        try:
            user_features = extract_user_features(
                questionnaire, watch_history, feedback_events
            )
            user_embedding = self.retrieval.embed_user(user_features)
        except Exception:
            logger.exception("user_embedding_failed", user_id=user_id)
            return self._fallback_recommend(questionnaire, top_k)

        # --- 2. Retrieval ---
        try:
            retrieval_results = self.retrieval.retrieve(
                user_embedding, top_k=top_k * 3  # over-retrieve for diversity
            )
        except Exception:
            logger.exception("retrieval_failed", user_id=user_id)
            return self._fallback_recommend(questionnaire, top_k)

        logger.info(
            "retrieval_complete",
            user_id=user_id,
            num_candidates=len(retrieval_results),
        )

        if not retrieval_results:
            return self._fallback_recommend(questionnaire, top_k)

        # --- 3. Ranking ---
        candidates_for_ranking = [
            {
                "title_id": tid,
                "features": np.zeros(settings.EMBEDDING_DIM, dtype=np.float32),
                "retrieval_score": score,
            }
            for tid, score in retrieval_results
        ]

        user_seq = user_features.get(
            "watch_history_embeddings",
            np.zeros(
                (settings.MAX_WATCH_HISTORY, settings.EMBEDDING_DIM),
                dtype=np.float32,
            ),
        )

        try:
            ranked = self.ranking.rank(
                user_context={"user_sequence": user_seq},
                candidates=candidates_for_ranking,
            )
        except Exception:
            logger.exception("ranking_failed_using_retrieval_order", user_id=user_id)
            ranked = [
                {"title_id": tid, "score": score, "retrieval_score": score}
                for tid, score in retrieval_results
            ]

        # --- 4. Rewatch filter ---
        watched_ids: Set[str] = {
            str(h.get("title_id", "")) for h in watch_history
        }
        ranked = RankingPipeline.apply_rewatch_filter(
            ranked, watched_ids, include_rewatches
        )

        # --- 5. Diversity ---
        candidate_features: Dict[str, np.ndarray] = {
            c["title_id"]: c.get("features", np.zeros(settings.EMBEDDING_DIM))
            for c in candidates_for_ranking
        }
        ranked = RankingPipeline.apply_diversity(
            ranked, candidate_features, lambda_diversity=diversity_lambda, top_n=top_k
        )

        # --- 6. Explanations ---
        user_profile = questionnaire
        for item in ranked:
            item["reason"] = self.generate_explanation(
                item, user_profile, item.get("score", 0.0)
            )

        logger.info(
            "recommendation_complete",
            user_id=user_id,
            num_results=len(ranked),
        )

        return ranked

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_explanation(
        title: Dict[str, Any],
        user_profile: Dict[str, Any],
        score: float,
    ) -> str:
        """Produce a human-readable reason for why this title was recommended.

        Heuristic-based: matches on genres, score bucket, and preferences.
        """
        reasons: List[str] = []

        # Genre overlap
        user_genres = set(user_profile.get("preferred_genre_ids", []))
        title_genres = set(title.get("genre_ids", []))
        overlap = user_genres & title_genres
        if overlap:
            genre_names = []
            for gid in overlap:
                idx = GENRE_ID_TO_INDEX.get(gid)
                if idx is not None and idx in INDEX_TO_GENRE_NAME:
                    genre_names.append(INDEX_TO_GENRE_NAME[idx])
            if genre_names:
                reasons.append(f"Matches your interest in {', '.join(genre_names)}")

        # Score-based bucket
        if score >= 0.9:
            reasons.append("Highly recommended for you")
        elif score >= 0.7:
            reasons.append("Great match based on your preferences")
        elif score >= 0.5:
            reasons.append("You might enjoy this")

        # Rewatch
        if title.get("is_rewatch"):
            reasons.append("Worth watching again")

        if not reasons:
            reasons.append("Recommended based on your profile")

        return ". ".join(reasons) + "."

    # ------------------------------------------------------------------
    # Fallback path
    # ------------------------------------------------------------------

    def _fallback_recommend(
        self,
        questionnaire: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Use the non-ML fallback recommender."""
        preferred = questionnaire.get("preferred_genre_ids", [])
        if preferred:
            return self.fallback.cold_start(questionnaire, limit=limit)
        return self.fallback.popularity_based(limit=limit)
