"""Training script for the two-tower retrieval model.

Usage:
    python -m ml_service.training.train_retrieval \
        --epochs 20 \
        --batch-size 256 \
        --output-dir /app/models/two_tower
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
import structlog
import tensorflow as tf

logger = structlog.get_logger(__name__)


def load_training_data(database_url: str) -> Tuple[List[Dict], List[Dict]]:
    """Load user-item interaction pairs from PostgreSQL.

    Returns
    -------
    interactions : list[dict]
        Each dict: {user_features: dict, item_features: dict}
    item_catalog : list[dict]
        All items for the candidate index.
    """
    # In production this would query the database.  For now we create
    # synthetic data so the script is runnable end-to-end.
    try:
        import pandas as pd
        import sqlalchemy

        engine = sqlalchemy.create_engine(database_url)
        query = """
            SELECT u.id AS user_id,
                   u.questionnaire,
                   t.id AS title_id,
                   t.metadata
            FROM users u
            JOIN watch_history wh ON wh.user_id = u.id
            JOIN titles t ON t.id = wh.title_id
            ORDER BY wh.watched_at DESC
        """
        df = pd.read_sql(query, engine)
        logger.info("loaded_training_data", rows=len(df))
        # Transform into feature dicts (implementation depends on schema)
        interactions = []
        items = {}
        for _, row in df.iterrows():
            interactions.append({
                "user": _parse_user_features(row["questionnaire"]),
                "item": _parse_item_features(row["metadata"]),
            })
            items[row["title_id"]] = _parse_item_features(row["metadata"])
        return interactions, list(items.values())
    except Exception as exc:
        logger.warning("db_load_failed_using_synthetic", error=str(exc))
        return _generate_synthetic_data()


def _parse_user_features(questionnaire: Any) -> Dict[str, np.ndarray]:
    """Parse a stored questionnaire JSON into user tower inputs."""
    from ml_service.core.config import settings
    from ml_service.features.user_features import extract_user_features

    if isinstance(questionnaire, str):
        import json
        questionnaire = json.loads(questionnaire)
    return extract_user_features(questionnaire or {}, [], [])


def _parse_item_features(metadata: Any) -> Dict[str, np.ndarray]:
    """Parse stored title metadata JSON into item tower inputs."""
    from ml_service.features.item_features import extract_item_features

    if isinstance(metadata, str):
        import json
        metadata = json.loads(metadata)
    return extract_item_features(metadata or {})


def _generate_synthetic_data(
    num_users: int = 1000,
    num_items: int = 500,
    num_interactions: int = 5000,
) -> Tuple[List[Dict], List[Dict]]:
    """Generate synthetic training data for development."""
    from ml_service.core.config import settings

    rng = np.random.RandomState(42)

    def _random_user() -> Dict[str, np.ndarray]:
        return {
            "genre_preferences": (rng.rand(settings.NUM_GENRES) > 0.7).astype(np.float32),
            "mood_preferences": (rng.rand(settings.NUM_MOODS) > 0.7).astype(np.float32),
            "pacing": rng.rand(1).astype(np.float32),
            "tone": rng.rand(1).astype(np.float32),
            "intensity": rng.rand(1).astype(np.float32),
            "runtime_preference": rng.rand(1).astype(np.float32),
            "rewatch_tolerance": rng.rand(1).astype(np.float32),
            "watch_history_embeddings": rng.randn(
                settings.MAX_WATCH_HISTORY, settings.EMBEDDING_DIM
            ).astype(np.float32),
            "region_id": np.array(rng.randint(0, settings.NUM_REGIONS), dtype=np.int32),
            "language_id": np.array(rng.randint(0, settings.NUM_LANGUAGES), dtype=np.int32),
        }

    def _random_item() -> Dict[str, np.ndarray]:
        return {
            "genres": (rng.rand(settings.NUM_GENRES) > 0.7).astype(np.float32),
            "cast_embedding": rng.randn(settings.CAST_EMBEDDING_DIM).astype(np.float32),
            "plot_embedding": rng.randn(settings.PLOT_EMBEDDING_DIM).astype(np.float32),
            "runtime": rng.rand(1).astype(np.float32),
            "popularity": rng.rand(1).astype(np.float32),
            "vote_average": rng.rand(1).astype(np.float32),
            "release_year": rng.rand(1).astype(np.float32),
            "provider_count": rng.rand(1).astype(np.float32),
            "language_id": np.array(rng.randint(0, settings.NUM_LANGUAGES), dtype=np.int32),
        }

    users = [_random_user() for _ in range(num_users)]
    items = [_random_item() for _ in range(num_items)]

    interactions = []
    for _ in range(num_interactions):
        u_idx = rng.randint(0, num_users)
        i_idx = rng.randint(0, num_items)
        interactions.append({"user": users[u_idx], "item": items[i_idx]})

    logger.info(
        "synthetic_data_generated",
        users=num_users,
        items=num_items,
        interactions=num_interactions,
    )
    return interactions, items


def prepare_dataset(
    interactions: List[Dict],
    batch_size: int = 256,
    val_split: float = 0.1,
) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
    """Create tf.data.Datasets from interaction dicts."""
    n = len(interactions)
    split = int(n * (1 - val_split))

    def _to_tf_dict(inter_list: List[Dict]) -> Dict[str, Dict[str, tf.Tensor]]:
        user_keys = inter_list[0]["user"].keys()
        item_keys = inter_list[0]["item"].keys()
        result: Dict[str, Any] = {"user": {}, "item": {}}
        for k in user_keys:
            result["user"][k] = np.stack([i["user"][k] for i in inter_list])
        for k in item_keys:
            result["item"][k] = np.stack([i["item"][k] for i in inter_list])
        return result

    train_dict = _to_tf_dict(interactions[:split])
    val_dict = _to_tf_dict(interactions[split:])

    train_ds = tf.data.Dataset.from_tensor_slices(
        {"user": train_dict["user"], "item": train_dict["item"]}
    ).shuffle(10_000).batch(batch_size).prefetch(tf.data.AUTOTUNE)

    val_ds = tf.data.Dataset.from_tensor_slices(
        {"user": val_dict["user"], "item": val_dict["item"]}
    ).batch(batch_size).prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds


def train(
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    epochs: int = 20,
    patience: int = 3,
    learning_rate: float = 1e-3,
) -> "TwoTowerModel":
    """Fit the two-tower model."""
    from ml_service.models.two_tower import TwoTowerModel

    model = TwoTowerModel()
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate))

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_total_loss",
        patience=patience,
        restore_best_weights=True,
    )

    logger.info("training_started", epochs=epochs, lr=learning_rate)

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=[early_stop],
    )

    logger.info("training_complete")
    return model


def evaluate(
    model: Any,
    val_ds: tf.data.Dataset,
) -> Dict[str, float]:
    """Compute recall@K metrics on validation data."""
    metrics = model.evaluate(val_ds, return_dict=True)
    logger.info("evaluation_complete", metrics=metrics)
    return metrics


def save_model(model: Any, output_dir: str) -> None:
    """Export the trained towers as SavedModels."""
    os.makedirs(output_dir, exist_ok=True)
    model.save_towers(output_dir)
    logger.info("model_saved", path=output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train two-tower retrieval model")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--output-dir", type=str, default="/app/models/two_tower")
    parser.add_argument(
        "--database-url",
        type=str,
        default="postgresql://findflix:findflix@localhost:5432/findflix",
    )
    args = parser.parse_args()

    interactions, items = load_training_data(args.database_url)
    train_ds, val_ds = prepare_dataset(interactions, batch_size=args.batch_size)
    model = train(train_ds, val_ds, epochs=args.epochs, patience=args.patience, learning_rate=args.lr)
    metrics = evaluate(model, val_ds)
    save_model(model, args.output_dir)

    logger.info("pipeline_finished", metrics=metrics, output=args.output_dir)


if __name__ == "__main__":
    main()
