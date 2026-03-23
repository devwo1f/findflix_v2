"""Training script for the transformer reranker model.

Usage:
    python -m ml_service.training.train_reranker \
        --epochs 15 \
        --batch-size 64 \
        --output-dir /app/models/reranker
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import structlog
import tensorflow as tf

from ml_service.core.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_interaction_sequences(
    database_url: str,
) -> List[Dict[str, Any]]:
    """Load user interaction sequences from the database.

    Falls back to synthetic data when the database is unavailable or has
    insufficient data.
    """
    try:
        import json as _json

        import pandas as pd
        import sqlalchemy

        from ml_service.features.item_features import extract_item_features

        engine = sqlalchemy.create_engine(database_url)
        query = """
            SELECT wh.user_id,
                   t.genres, t.overview, t.runtime,
                   t.popularity, t.vote_average,
                   t.release_date, t.original_language
            FROM watch_history wh
            JOIN titles t ON t.id = wh.title_id
            ORDER BY wh.user_id, wh.watched_at
        """
        df = pd.read_sql(query, engine)

        if len(df) < 20:
            logger.warning("insufficient_sequence_data", rows=len(df))
            return _generate_synthetic_sequences()

        user_sequences: Dict[str, List[np.ndarray]] = {}
        for _, row in df.iterrows():
            uid = str(row["user_id"])
            genres_raw = row["genres"]
            if isinstance(genres_raw, str):
                genres_raw = _json.loads(genres_raw)
            genre_ids = []
            if isinstance(genres_raw, list):
                for g in genres_raw:
                    if isinstance(g, dict) and g.get("id"):
                        genre_ids.append(int(g["id"]))

            meta = {
                "genre_ids": genre_ids,
                "overview": str(row.get("overview", "")),
                "runtime": row.get("runtime"),
                "popularity": row.get("popularity", 0),
                "vote_average": row.get("vote_average", 0),
                "vote_count": 0,
                "release_date": str(row.get("release_date", "")),
                "original_language": str(row.get("original_language", "en")),
                "providers": [],
            }
            feats = extract_item_features(meta)
            feat_vec = np.concatenate([v.flatten() for v in feats.values()])
            if uid not in user_sequences:
                user_sequences[uid] = []
            user_sequences[uid].append(feat_vec)

        sequences = []
        feat_dim = settings.EMBEDDING_DIM
        rng = np.random.RandomState(42)
        for uid, feat_list in user_sequences.items():
            if len(feat_list) < 3:
                continue
            arr = np.array(feat_list, dtype=np.float32)
            if arr.shape[1] != feat_dim:
                proj = rng.randn(arr.shape[1], feat_dim).astype(np.float32) * 0.1
                arr = arr @ proj
            sequences.append({
                "user_id": uid,
                "sequence_features": arr[:-1],
                "positive_features": arr[-1],
                "negative_features": rng.randn(5, feat_dim).astype(np.float32),
            })

        logger.info("loaded_sequences", count=len(sequences))
        if len(sequences) < 10:
            return _generate_synthetic_sequences()
        return sequences

    except Exception as exc:
        logger.warning("db_load_failed_using_synthetic", error=str(exc))
        return _generate_synthetic_sequences()


def _generate_synthetic_sequences(
    num_users: int = 500,
    seq_len: int = 20,
    feat_dim: int = settings.EMBEDDING_DIM,
) -> List[Dict[str, Any]]:
    """Generate synthetic sequence data."""
    rng = np.random.RandomState(123)
    sequences = []
    for uid in range(num_users):
        seq = rng.randn(seq_len, feat_dim).astype(np.float32)
        # The positive item is the last in the sequence
        sequences.append({
            "user_id": str(uid),
            "sequence_features": seq[:-1],
            "positive_features": seq[-1],
            "negative_features": rng.randn(5, feat_dim).astype(np.float32),
        })
    logger.info("synthetic_sequences_generated", count=num_users)
    return sequences


# ---------------------------------------------------------------------------
# Dataset preparation
# ---------------------------------------------------------------------------

def prepare_sequences(
    sequences: List[Dict[str, Any]],
    max_seq_len: int = 20,
    feat_dim: int = settings.EMBEDDING_DIM,
    num_negatives: int = 5,
    val_split: float = 0.1,
) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
    """Convert sequences into training pairs.

    For each user sequence we create a sample where:
      - user_sequence = the N-1 preceding items
      - candidates = [positive, negatives...]
      - labels = [1, 0, 0, ...]
    """
    user_seqs = []
    candidate_sets = []
    label_sets = []

    for rec in sequences:
        seq = rec.get("sequence_features")
        pos = rec.get("positive_features")
        negs = rec.get("negative_features")
        if seq is None or pos is None or negs is None:
            continue

        seq = np.array(seq, dtype=np.float32)
        pos = np.array(pos, dtype=np.float32)
        negs = np.array(negs, dtype=np.float32)

        # Pad sequence
        if seq.shape[0] < max_seq_len:
            pad = np.zeros((max_seq_len - seq.shape[0], feat_dim), dtype=np.float32)
            seq = np.concatenate([pad, seq], axis=0)
        else:
            seq = seq[-max_seq_len:]

        # Candidates: positive first, then negatives
        cands = np.concatenate([pos[np.newaxis, :], negs], axis=0)
        labels = np.zeros(cands.shape[0], dtype=np.float32)
        labels[0] = 1.0

        user_seqs.append(seq)
        candidate_sets.append(cands)
        label_sets.append(labels)

    user_seqs_arr = np.stack(user_seqs)
    cands_arr = np.stack(candidate_sets)
    labels_arr = np.stack(label_sets)

    n = len(user_seqs_arr)
    split = int(n * (1 - val_split))

    def _make_ds(start: int, end: int, shuffle: bool = False) -> tf.data.Dataset:
        ds = tf.data.Dataset.from_tensor_slices((
            {
                "user_sequence": user_seqs_arr[start:end],
                "candidates": cands_arr[start:end],
            },
            labels_arr[start:end],
        ))
        if shuffle:
            ds = ds.shuffle(10_000)
        return ds.batch(64).prefetch(tf.data.AUTOTUNE)

    train_ds = _make_ds(0, split, shuffle=True)
    val_ds = _make_ds(split, n)
    return train_ds, val_ds


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

import keras


@keras.saving.register_keras_serializable(package="findflix")
class WarmupCosineSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
    """Linear warmup followed by cosine decay."""

    def __init__(self, base_lr: float, warmup_steps: int, total_steps: int):
        super().__init__()
        self.base_lr = base_lr
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps

    def __call__(self, step: tf.Tensor) -> tf.Tensor:
        step = tf.cast(step, tf.float32)
        warmup = tf.minimum(step / tf.cast(self.warmup_steps, tf.float32), 1.0)
        decay_steps = tf.cast(self.total_steps - self.warmup_steps, tf.float32)
        cosine = 0.5 * (1.0 + tf.cos(
            math.pi * tf.minimum(
                (step - tf.cast(self.warmup_steps, tf.float32)) / decay_steps,
                1.0,
            )
        ))
        return self.base_lr * warmup * cosine

    def get_config(self) -> Dict[str, Any]:
        return {
            "base_lr": self.base_lr,
            "warmup_steps": self.warmup_steps,
            "total_steps": self.total_steps,
        }


def train(
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    epochs: int = 15,
    base_lr: float = 1e-3,
) -> tf.keras.Model:
    """Train the transformer reranker."""
    from ml_service.models.reranker import TransformerReranker

    model = TransformerReranker()

    # Estimate total steps for LR schedule
    num_train_batches = sum(1 for _ in train_ds)
    total_steps = num_train_batches * epochs
    warmup_steps = int(total_steps * 0.1)

    lr_schedule = WarmupCosineSchedule(base_lr, warmup_steps, total_steps)
    optimizer = tf.keras.optimizers.Adam(learning_rate=lr_schedule)

    model.compile(
        optimizer=optimizer,
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=False),
        metrics=[
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
        ],
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=3, restore_best_weights=True
        ),
    ]

    logger.info("reranker_training_started", epochs=epochs, total_steps=total_steps)

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
    )

    logger.info("reranker_training_complete")
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model: tf.keras.Model, val_ds: tf.data.Dataset) -> Dict[str, float]:
    """Evaluate the reranker using NDCG-style metrics."""
    all_labels = []
    all_scores = []

    for batch_inputs, batch_labels in val_ds:
        preds = model(batch_inputs, training=False).numpy()
        all_scores.append(preds)
        all_labels.append(batch_labels.numpy())

    all_scores_arr = np.concatenate(all_scores, axis=0)
    all_labels_arr = np.concatenate(all_labels, axis=0)

    # Per-query NDCG
    ndcg_scores = []
    for scores, labels in zip(all_scores_arr, all_labels_arr):
        ndcg_scores.append(_ndcg(labels, scores))

    mean_ndcg = float(np.mean(ndcg_scores))
    metrics = {"ndcg": mean_ndcg}
    logger.info("reranker_evaluation_complete", **metrics)
    return metrics


def _ndcg(labels: np.ndarray, scores: np.ndarray, k: int = 10) -> float:
    """Compute NDCG@k."""
    order = np.argsort(scores)[::-1][:k]
    dcg = sum(labels[i] / math.log2(rank + 2) for rank, i in enumerate(order))
    ideal_order = np.argsort(labels)[::-1][:k]
    idcg = sum(labels[i] / math.log2(rank + 2) for rank, i in enumerate(ideal_order))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_model(model: tf.keras.Model, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "model.keras")
    model.save(path)
    logger.info("reranker_model_saved", path=path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Train transformer reranker")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--output-dir", type=str, default="/app/models/reranker")
    parser.add_argument(
        "--database-url",
        type=str,
        default="postgresql://findflix:findflix@localhost:5432/findflix",
    )
    args = parser.parse_args()

    sequences = load_interaction_sequences(args.database_url)
    train_ds, val_ds = prepare_sequences(sequences)
    model = train(train_ds, val_ds, epochs=args.epochs, base_lr=args.lr)
    metrics = evaluate(model, val_ds)
    save_model(model, args.output_dir)
    logger.info("reranker_pipeline_finished", metrics=metrics, output=args.output_dir)


if __name__ == "__main__":
    main()
