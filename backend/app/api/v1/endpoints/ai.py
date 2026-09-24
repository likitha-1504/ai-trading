"""Dual-Model AI Council analysis and latency endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_db_repo, get_performance_aggregator
from app.api.schemas import ModelLatencyStats
from app.db.performance import PerformanceAggregator
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "/analyses",
    response_model=list[dict[str, Any]],
    summary="List recent AI Council analyses",
    description="Returns qualitative theses and adversarial critiques from Qwen3 and DeepSeek-R1.",
)
def list_ai_analyses(
    model_name: str | None = Query(default=None, description="Filter by model name"),
    role: str | None = Query(default=None, description="Filter by role (ANALYST, CHALLENGER)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max analyses to return"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[dict[str, Any]]:
    analyses = repo.get_all_ai_analyses(limit=limit)
    if model_name:
        analyses = [a for a in analyses if a.get("model_name") == model_name]
    if role:
        analyses = [a for a in analyses if a.get("role") == role.upper()]
    return analyses


@router.get(
    "/analyses/{candidate_id}",
    response_model=dict[str, Any],
    summary="Get AI Council analysis for a candidate",
    description="Returns dual-model synthesis: Qwen3 Primary Analyst thesis and DeepSeek-R1 Adversarial Critique.",
)
def get_ai_analyses_for_candidate(
    candidate_id: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> dict[str, Any]:
    analyses = repo.get_ai_analyses_for_candidate(candidate_id)
    if not analyses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI analysis found for candidate {candidate_id}",
        )

    cand = repo.get_candidate(candidate_id)
    symbol = cand.symbol if cand else "UNKNOWN"

    analyst_thesis = next((a for a in analyses if a.get("role") == "ANALYST"), None)
    challenger_critique = next((a for a in analyses if a.get("role") == "CHALLENGER"), None)

    total_latency = sum(int(a.get("latency_ms", 0)) for a in analyses)
    has_fallback = any(bool(a.get("is_fallback", 0)) for a in analyses)

    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "analyst_thesis": analyst_thesis,
        "challenger_critique": challenger_critique,
        "total_latency_ms": total_latency,
        "has_fallback": has_fallback,
        "all_records": analyses,
    }


@router.get(
    "/latency",
    response_model=dict[str, ModelLatencyStats],
    summary="Get AI model latency and fallback telemetry",
    description="Returns average latency, P95 latency, call count, and fallback rate for Qwen3 and DeepSeek-R1.",
)
def get_model_latency_stats(
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> dict[str, ModelLatencyStats]:
    stats = perf_agg.get_model_latency_metrics()
    result: dict[str, ModelLatencyStats] = {}
    for model_name, s in stats.items():
        role = (
            "CHALLENGER"
            if "deepseek" in model_name.lower() or "r1" in model_name.lower()
            else "ANALYST"
        )
        total_calls = s["total_calls"]
        fallback_calls = s["fallback_calls"]
        fb_rate = (
            round((fallback_calls / total_calls) * 100, 2)
            if total_calls > 0
            else 0.0
        )
        result[model_name] = ModelLatencyStats(
            model_name=model_name,
            role=role,
            call_count=total_calls,
            avg_latency_ms=s["avg_latency_ms"],
            p95_latency_ms=s["p95_latency_ms"],
            fallback_rate_pct=fb_rate,
        )
    return result
