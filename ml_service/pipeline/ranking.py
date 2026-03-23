"""Ranking pipeline: reranks retrieval candidates using the transformer reranker.

Applies the reranker model, then post-processes with diversity (MMR) and
rewatch filtering.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import structlog
import tensorflow as tf

from ml_service.core.config import settings
from ml_service.models.reranker import TransformerReranker  # noqa: F401 (needed for keras deserialization)
from ml_service.training.train_reranker import WarmupCosineSchedule  # noqa: F401

logger = structlog.get_logger(__name__)


class RankingPipeline:
    """Reranks candidate titles and applies diversity / rewatch filters."""

    def __init__(
        self,
        model_path: Optional[str] = None,
    ) -> None:
        self._reranker: Optional[TransformerReranker] = None
        base = model_path or os.path.join(
            settings.MODEL_PATH, settings.RERANKER_MODEL_DIR
        )
        self._load_model(base)

    def _load_model(self, path: str) -> None:
        try:
            keras_path = os.path.join(path, "model.keras")
            if os.path.isfile(keras_path):
                self._reranker = tf.keras.models.load_model(keras_path)
                logger.info("reranker_model_loaded", path=keras_path)
            elif os.path.isdir(path) and os.path.exists(os.path.join(path, "saved_model.pb")):
                self._reranker = tf.keras.models.load_model(path)
                logger.info("reranker_model_loaded", path=path)
            else:
                logger.warning(
                    "reranker_model_not_found_using_untrained",
                    path=path,
                )
                self._reranker = TransformerReranker()
        except Exception:
            logger.exception("reranker_model_load_error", path=path)
            self._reranker = TransformerReranker()

    @property
    def is_ready(self) -> bool:
        return self._reranker is not None

    # ------------------------------------------------------------------
    # Core ranking
    # ------------------------------------------------------------------

    def rank(
        self,
        user_context: Dict[str, np.ndarray],
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Score and rerank candidates.

        Parameters
        ----------
        user_context : dict
            Must contain ``user_sequence`` (seq_len, feat_dim).
        candidates : list[dict]
            Each dict has ``title_id``, ``features`` (np.ndarray), and
            optionally ``retrieval_score``.

        Returns
        -------
        list[dict]
            Candidates sorted descending by reranker score.  Each dict has
            ``title_id``, ``score``, ``retrieval_score``.
        """
        if not candidates:
            return []

        if self._reranker is None:
            logger.warning("reranker_not_loaded_returning_unsorted")
            return candidates

        # Build batched input (batch=1)
        user_seq = user_context["user_sequence"]  # (S, D)
        cand_features = np.stack(
            [c["features"] for c in candidates], axis=0
        )  # (C, F)

        inputs = {
            "user_sequence": np.expand_dims(user_seq, 0),       # (1, S, D)
            "candidates": np.expand_dims(cand_features, 0),     # (1, C, F)
        }

        scores = self._reranker(inputs, training=False).numpy().squeeze(0)  # (C,)

        ranked: List[Dict[str, Any]] = []
        for i, cand in enumerate(candidates):
            ranked.append(
                {
                    "title_id": cand["title_id"],
                    "score": float(scores[i]),
                    "retrieval_score": cand.get("retrieval_score", 0.0),
                }
            )

        ranked.sort(key=lambda r: r["score"], reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Diversity via Maximal Marginal Relevance (MMR)
    # ------------------------------------------------------------------

    @staticmethod
    def apply_diversity(
        ranked_list: List[Dict[str, Any]],
        candidate_features: Dict[str, np.ndarray],
        lambda_diversity: float = settings.DIVERSITY_LAMBDA,
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Re-order *ranked_list* using MMR to promote diversity.

        MMR(d) = lambda * score(d) - (1 - lambda) * max_sim(d, selected)

        Parameters
        ----------
        ranked_list : list[dict]
            Must have ``title_id`` and ``score``.
        candidate_features : dict[str, np.ndarray]
            Mapping title_id -> feature vector for similarity computation.
        lambda_diversity : float
            Trade-off between relevance and diversity.  1.0 = pure relevance.
        top_n : int or None
            Number of results to return.  Defaults to len(ranked_list).
        """
        if not ranked_list:
            return []
        n = top_n or len(ranked_list)

        selected: List[Dict[str, Any]] = []
        selected_feats: List[np.ndarray] = []
        remaining = list(ranked_list)

        for _ in range(min(n, len(ranked_list))):
            best_idx = -1
            best_mmr = -float("inf")

            for idx, cand in enumerate(remaining):
                tid = cand["title_id"]
                feat = candidate_features.get(tid)
                if feat is None:
                    # No features -> skip diversity penalty
                    sim = 0.0
                else:
                    sim = TransformerReranker.compute_diversity_penalty(
                        feat, selected_feats
                    )
                mmr = lambda_diversity * cand["score"] - (1 - lambda_diversity) * sim
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = idx

            chosen = remaining.pop(best_idx)
            chosen["mmr_score"] = best_mmr
            selected.append(chosen)

            feat = candidate_features.get(chosen["title_id"])
            if feat is not None:
                selected_feats.append(feat)

        return selected

    # ------------------------------------------------------------------
    # Rewatch filter
    # ------------------------------------------------------------------

    @staticmethod
    def apply_rewatch_filter(
        ranked_list: List[Dict[str, Any]],
        watch_history: Set[str],
        include_rewatches: bool = False,
    ) -> List[Dict[str, Any]]:
        """Remove or down-rank titles the user has already watched.

        Parameters
        ----------
        ranked_list : list[dict]
            Each entry has ``title_id``.
        watch_history : set[str]
            Title IDs the user has watched.
        include_rewatches : bool
            If True, keep watched titles but flag them.
        """
        if include_rewatches:
            for item in ranked_list:
                item["is_rewatch"] = item["title_id"] in watch_history
            return ranked_list

        return [
            item for item in ranked_list
            if item["title_id"] not in watch_history
        ]
