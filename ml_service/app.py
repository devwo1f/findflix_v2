"""FastAPI application for the FindFlix ML recommendation service.

Endpoints
---------
POST /retrieve       - top-K candidate retrieval from user embedding
POST /rank           - rerank a candidate list for a user
POST /embed/user     - generate a user embedding from features
POST /embed/title    - generate a title embedding from features
GET  /model/info     - model versions and readiness
GET  /health         - health check
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ml_service.core.config import settings
from ml_service.features.item_features import extract_item_features
from ml_service.features.user_features import extract_user_features
from ml_service.pipeline.orchestrator import RecommendationOrchestrator
from ml_service.pipeline.ranking import RankingPipeline
from ml_service.pipeline.retrieval import RetrievalPipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.LOG_LEVEL.upper()),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("ml_service.app")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FindFlix ML Service",
    version="1.0.0",
    description="Movie & TV recommendation ML service",
)

# ---------------------------------------------------------------------------
# Singletons (initialised lazily at startup)
# ---------------------------------------------------------------------------

_retrieval: Optional[RetrievalPipeline] = None
_ranking: Optional[RankingPipeline] = None
_orchestrator: Optional[RecommendationOrchestrator] = None


@app.on_event("startup")
async def _startup() -> None:
    global _retrieval, _ranking, _orchestrator
    logger.info("ml_service_starting")
    _retrieval = RetrievalPipeline()
    _ranking = RankingPipeline()
    _orchestrator = RecommendationOrchestrator(
        retrieval=_retrieval, ranking=_ranking
    )
    logger.info(
        "ml_service_ready",
        retrieval_ready=_retrieval.is_ready,
        ranking_ready=_ranking.is_ready,
    )


# ---------------------------------------------------------------------------
# Middleware: request logging
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(elapsed * 1000, 2),
    )
    return response


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class RetrievalRequest(BaseModel):
    user_embedding: List[float] = Field(..., description="User embedding vector")
    top_k: int = Field(default=settings.TOP_K, ge=1, le=1000)


class ScoredTitle(BaseModel):
    title_id: str
    score: float


class RetrievalResponse(BaseModel):
    candidates: List[ScoredTitle]


class RankRequest(BaseModel):
    user_sequence: List[List[float]] = Field(..., description="Recent interaction embeddings")
    candidates: List[Dict[str, Any]] = Field(
        ..., description="Candidate dicts with title_id and features"
    )


class RankResponse(BaseModel):
    ranked: List[ScoredTitle]


class UserEmbedRequest(BaseModel):
    questionnaire: Dict[str, Any] = Field(default_factory=dict)
    watch_history: List[Dict[str, Any]] = Field(default_factory=list)
    feedback_events: List[Dict[str, Any]] = Field(default_factory=list)


class EmbeddingResponse(BaseModel):
    embedding: List[float]


class TitleEmbedRequest(BaseModel):
    title_metadata: Dict[str, Any]


class ModelInfoResponse(BaseModel):
    retrieval_ready: bool
    ranking_ready: bool
    embedding_dim: int
    top_k_default: int
    model_path: str


class HealthResponse(BaseModel):
    status: str
    retrieval_ready: bool
    ranking_ready: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(req: RetrievalRequest) -> RetrievalResponse:
    """Return top-K candidate title IDs with scores."""
    if _retrieval is None:
        raise HTTPException(status_code=503, detail="Service not initialised")
    if not _retrieval.is_ready:
        raise HTTPException(status_code=503, detail="Retrieval model not ready")

    user_emb = np.array(req.user_embedding, dtype=np.float32)
    if user_emb.shape != (settings.EMBEDDING_DIM,):
        raise HTTPException(
            status_code=422,
            detail=f"Expected embedding of dim {settings.EMBEDDING_DIM}, got {user_emb.shape}",
        )

    results = _retrieval.retrieve(user_emb, top_k=req.top_k)
    return RetrievalResponse(
        candidates=[ScoredTitle(title_id=tid, score=s) for tid, s in results]
    )


@app.post("/rank", response_model=RankResponse)
async def rank(req: RankRequest) -> RankResponse:
    """Rerank candidates for a user."""
    if _ranking is None:
        raise HTTPException(status_code=503, detail="Service not initialised")

    user_seq = np.array(req.user_sequence, dtype=np.float32)
    candidates = []
    for c in req.candidates:
        features = c.get("features")
        if features is None:
            features = [0.0] * settings.EMBEDDING_DIM
        candidates.append({
            "title_id": c["title_id"],
            "features": np.array(features, dtype=np.float32),
            "retrieval_score": c.get("retrieval_score", 0.0),
        })

    ranked = _ranking.rank(
        user_context={"user_sequence": user_seq},
        candidates=candidates,
    )
    return RankResponse(
        ranked=[ScoredTitle(title_id=r["title_id"], score=r["score"]) for r in ranked]
    )


@app.post("/embed/user", response_model=EmbeddingResponse)
async def embed_user(req: UserEmbedRequest) -> EmbeddingResponse:
    """Generate user embedding from features."""
    if _retrieval is None or _retrieval._user_tower is None:
        raise HTTPException(status_code=503, detail="User tower not loaded")

    try:
        features = extract_user_features(
            req.questionnaire, req.watch_history, req.feedback_events
        )
        emb = _retrieval.embed_user(features)
        return EmbeddingResponse(embedding=emb.tolist())
    except Exception as exc:
        logger.exception("embed_user_error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/embed/title", response_model=EmbeddingResponse)
async def embed_title(req: TitleEmbedRequest) -> EmbeddingResponse:
    """Generate title embedding from features."""
    if _retrieval is None or _retrieval._item_tower is None:
        raise HTTPException(status_code=503, detail="Item tower not loaded")

    try:
        features = extract_item_features(req.title_metadata)
        emb = _retrieval.embed_item(features)
        return EmbeddingResponse(embedding=emb.tolist())
    except Exception as exc:
        logger.exception("embed_title_error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info() -> ModelInfoResponse:
    """Return model versions and status."""
    return ModelInfoResponse(
        retrieval_ready=_retrieval.is_ready if _retrieval else False,
        ranking_ready=_ranking.is_ready if _ranking else False,
        embedding_dim=settings.EMBEDDING_DIM,
        top_k_default=settings.TOP_K,
        model_path=settings.MODEL_PATH,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check."""
    return HealthResponse(
        status="ok",
        retrieval_ready=_retrieval.is_ready if _retrieval else False,
        ranking_ready=_ranking.is_ready if _ranking else False,
    )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
