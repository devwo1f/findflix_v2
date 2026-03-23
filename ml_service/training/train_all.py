"""One-command training pipeline: trains both retrieval and reranker models,
builds the ANN index, and restarts the service.

Usage (inside the ml_service container):
    python -m ml_service.training.train_all

Or from docker compose:
    docker compose exec ml_service python -m ml_service.training.train_all
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import structlog

from ml_service.core.config import settings

logger = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train all FindFlix ML models")
    parser.add_argument("--epochs-retrieval", type=int, default=15)
    parser.add_argument("--epochs-reranker", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument(
        "--database-url",
        type=str,
        default=settings.DATABASE_URL,
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=settings.MODEL_PATH,
    )
    args = parser.parse_args()

    retrieval_dir = os.path.join(args.model_dir, settings.RETRIEVAL_MODEL_DIR)
    reranker_dir = os.path.join(args.model_dir, settings.RERANKER_MODEL_DIR)

    # ── Step 1: Train retrieval model ──────────────────────────────
    logger.info("step_1_training_retrieval")
    from ml_service.training.train_retrieval import (
        evaluate,
        load_training_data,
        prepare_dataset,
        save_model,
        train,
    )

    interactions, items = load_training_data(args.database_url)
    logger.info("retrieval_data_loaded", interactions=len(interactions), items=len(items))

    train_ds, val_ds = prepare_dataset(interactions, batch_size=args.batch_size)
    model = train(train_ds, val_ds, epochs=args.epochs_retrieval, learning_rate=args.lr)
    metrics = evaluate(model, val_ds)
    save_model(model, retrieval_dir)
    logger.info("retrieval_training_done", metrics=metrics)

    # ── Step 2: Build item index ───────────────────────────────────
    logger.info("step_2_building_index")
    from ml_service.pipeline.retrieval import RetrievalPipeline

    pipeline = RetrievalPipeline(model_path=retrieval_dir)
    if pipeline._item_tower is not None:
        try:
            item_ids = [str(i) for i in range(len(items))]
            pipeline.build_index(item_ids, items)
            logger.info("index_built", items=len(items))
        except Exception as exc:
            logger.warning("index_build_failed", error=str(exc))

    # ── Step 3: Train reranker ─────────────────────────────────────
    logger.info("step_3_training_reranker")
    from ml_service.training.train_reranker import (
        evaluate as eval_reranker,
        load_interaction_sequences,
        prepare_sequences,
        save_model as save_reranker,
        train as train_reranker,
    )

    sequences = load_interaction_sequences(args.database_url)
    logger.info("reranker_data_loaded", sequences=len(sequences))

    train_ds_r, val_ds_r = prepare_sequences(sequences)
    reranker = train_reranker(train_ds_r, val_ds_r, epochs=args.epochs_reranker, base_lr=args.lr)
    r_metrics = eval_reranker(reranker, val_ds_r)
    save_reranker(reranker, reranker_dir)
    logger.info("reranker_training_done", metrics=r_metrics)

    logger.info(
        "all_training_complete",
        retrieval_path=retrieval_dir,
        reranker_path=reranker_dir,
    )
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print(f"  Retrieval model: {retrieval_dir}")
    print(f"  Reranker model:  {reranker_dir}")
    print("=" * 60)
    print("\nRestart the ML service to load the trained models:")
    print("  docker compose restart ml_service")


if __name__ == "__main__":
    main()
