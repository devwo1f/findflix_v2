"""Retrieval pipeline: generates top-K candidates using the two-tower model.

At startup the pipeline loads the trained item tower, computes embeddings for
all items in the catalog, builds an approximate-nearest-neighbour index, and
serves retrieval requests by embedding the query user then searching the
index.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
import tensorflow as tf

from ml_service.core.config import settings

logger = structlog.get_logger(__name__)


class RetrievalPipeline:
    """Two-tower retrieval with brute-force or ScaNN index."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        embedding_dim: int = settings.EMBEDDING_DIM,
    ) -> None:
        self.embedding_dim = embedding_dim
        self._user_tower: Optional[tf.keras.Model] = None
        self._item_tower: Optional[tf.keras.Model] = None
        self._item_ids: List[str] = []
        self._item_embeddings: Optional[np.ndarray] = None  # (N, D)
        self._index_ready = False

        base = model_path or os.path.join(settings.MODEL_PATH, settings.RETRIEVAL_MODEL_DIR)
        self._load_model(base)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self, base_path: str) -> None:
        user_path = os.path.join(base_path, "user_tower")
        item_path = os.path.join(base_path, "item_tower")
        try:
            if os.path.isdir(user_path) and os.path.isdir(item_path):
                self._user_tower = tf.keras.models.load_model(user_path)
                self._item_tower = tf.keras.models.load_model(item_path)
                logger.info("retrieval_model_loaded", path=base_path)
            else:
                logger.warning("retrieval_model_not_found", path=base_path)
        except Exception:
            logger.exception("retrieval_model_load_error", path=base_path)

    @property
    def is_ready(self) -> bool:
        return self._user_tower is not None and self._index_ready

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def build_index(
        self,
        item_ids: List[str],
        item_features: List[Dict[str, np.ndarray]],
    ) -> None:
        """Compute item embeddings and build a brute-force index.

        Parameters
        ----------
        item_ids : list[str]
            Title identifiers matching 1-to-1 with *item_features*.
        item_features : list[dict]
            Each dict contains the feature arrays expected by ``ItemTower``.
        """
        if self._item_tower is None:
            logger.warning("cannot_build_index_no_item_tower")
            return

        logger.info("building_ann_index", num_items=len(item_ids))

        # Batch-compute embeddings
        embeddings: List[np.ndarray] = []
        batch_size = settings.BATCH_SIZE

        for start in range(0, len(item_features), batch_size):
            batch_feats = item_features[start : start + batch_size]
            batch_dict = _stack_feature_dicts(batch_feats)
            batch_emb = self._item_tower(batch_dict, training=False).numpy()
            embeddings.append(batch_emb)

        self._item_embeddings = np.concatenate(embeddings, axis=0)  # (N, D)
        self._item_ids = list(item_ids)
        self._index_ready = True
        logger.info("ann_index_built", num_items=len(self._item_ids))

    def refresh_index(
        self,
        item_ids: List[str],
        item_features: List[Dict[str, np.ndarray]],
    ) -> None:
        """Rebuild the ANN index (alias for ``build_index``)."""
        self.build_index(item_ids, item_features)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        user_embedding: np.ndarray,
        top_k: int = settings.TOP_K,
    ) -> List[Tuple[str, float]]:
        """Find the *top_k* closest items to the given user embedding.

        Uses brute-force cosine similarity (exact search).  For production
        datasets exceeding ~100 k items, replace with ScaNN or FAISS.

        Parameters
        ----------
        user_embedding : np.ndarray  shape (D,) or (1, D)
            L2-normalised user embedding.
        top_k : int

        Returns
        -------
        list[tuple[str, float]]
            ``(title_id, score)`` pairs sorted descending by score.
        """
        if not self._index_ready or self._item_embeddings is None:
            logger.warning("retrieval_index_not_ready")
            return []

        query = user_embedding.reshape(1, -1).astype(np.float32)
        # Cosine similarity (embeddings are already L2-normalised)
        scores = (query @ self._item_embeddings.T).flatten()  # (N,)

        # Partial argsort for top-k
        if top_k < len(scores):
            top_indices = np.argpartition(scores, -top_k)[-top_k:]
        else:
            top_indices = np.arange(len(scores))

        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [
            (self._item_ids[i], float(scores[i]))
            for i in top_indices
        ]

    def embed_user(self, user_features: Dict[str, np.ndarray]) -> np.ndarray:
        """Run the user tower to produce an embedding.

        Adds a batch dimension, runs inference, removes it.
        """
        if self._user_tower is None:
            raise RuntimeError("User tower not loaded")

        batched = {k: np.expand_dims(v, 0) for k, v in user_features.items()}
        emb = self._user_tower(batched, training=False).numpy()
        return emb.squeeze(0)

    def embed_item(self, item_features: Dict[str, np.ndarray]) -> np.ndarray:
        """Run the item tower to produce an embedding."""
        if self._item_tower is None:
            raise RuntimeError("Item tower not loaded")

        batched = {k: np.expand_dims(v, 0) for k, v in item_features.items()}
        emb = self._item_tower(batched, training=False).numpy()
        return emb.squeeze(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stack_feature_dicts(
    feature_dicts: List[Dict[str, np.ndarray]],
) -> Dict[str, np.ndarray]:
    """Stack a list of per-item feature dicts into a batched dict."""
    keys = feature_dicts[0].keys()
    return {k: np.stack([d[k] for d in feature_dicts], axis=0) for k in keys}
