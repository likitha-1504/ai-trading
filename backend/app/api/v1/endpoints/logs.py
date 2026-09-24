"""System event logging and decision audit trail reconstruction endpoints."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_manager, get_db_repo
from app.api.schemas import AuditTrailResponse
from app.db.audit import DecisionAuditTrailManager
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "/system",
    response_model=list[dict[str, Any]],
    summary="List system operational logs",
    description="Returns recorded system events filtered by severity level and source component.",
)
def list_system_logs(
    level: str | None = Query(default=None, description="Filter by level (INFO, WARNING, CRITICAL)"),
    source: str | None = Query(default=None, description="Filter by source component"),
    limit: int = Query(default=50, ge=1, le=200, description="Max logs to return"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[dict[str, Any]]:
    logs = repo.get_recent_system_events(limit=limit)
    if level:
        logs = [log for log in logs if log.get("level") == level.upper()]
    if source:
        logs = [log for log in logs if log.get("source") == source.upper()]
    return logs


@router.get(
    "/audit/{candidate_id}",
    response_model=AuditTrailResponse,
    summary="Reconstruct complete decision audit trail",
    description="Rebuilds end-to-end decision provenance: Candidate -> Features -> AI Council -> TradePlan -> Orders -> Trades -> Positions.",
)
def get_decision_audit_trail(
    candidate_id: str,
    audit_mgr: DecisionAuditTrailManager = Depends(get_audit_manager),
) -> AuditTrailResponse:
    trail = audit_mgr.reconstruct_trail(candidate_id=candidate_id)
    if not trail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision trail found for candidate {candidate_id}",
        )

    ts = (
        trail.candidate.detected_at
        if trail.candidate
        else datetime.now(timezone.utc)
    )

    return AuditTrailResponse(
        candidate_id=trail.candidate_id,
        plan_id=trail.plan_id,
        timestamp=ts,
        is_fully_reproducible=trail.is_fully_reproducible,
        reproducibility_notes=trail.reproducibility_notes,
        candidate=trail.candidate,
        features=trail.feature_snapshot,
        ai_analyses=trail.ai_analyses,
        trade_plan=trail.trade_plan,
        orders=trail.orders,
        trades=trail.trades,
        positions=trail.positions,
    )
