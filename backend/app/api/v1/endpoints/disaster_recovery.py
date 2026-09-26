"""FastAPI Endpoints for Phase 33 Disaster Recovery and Fault Tolerance."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.disaster_recovery.models import (
    DisasterRecoveryAuditResult,
    QuoteFreshnessReport,
    SafeResumeAttestation,
    StateReconstructionReport,
)
from app.disaster_recovery.recovery_orchestrator import DisasterRecoveryOrchestrator

router = APIRouter(prefix="/disaster-recovery", tags=["Disaster Recovery"])

_orchestrator = DisasterRecoveryOrchestrator()


@router.get("/status", response_model=dict[str, Any])
def get_disaster_recovery_status() -> dict[str, Any]:
    """Returns high-level continuity status, database health, and broker connectivity."""
    db_health = _orchestrator.db_resilience.evaluate_db_health()
    broker_online = _orchestrator.broker_resilience.check_connection()
    status_str = _orchestrator.safe_resume.current_status.value

    return {
        "system_status": status_str,
        "database_health": db_health.model_dump(),
        "broker_connected": broker_online,
        "is_safe_halted": status_str == "SAFE_HALTED",
        "last_audit_id": (
            _orchestrator._last_audit.audit_id if _orchestrator._last_audit else None
        ),
    }


@router.post("/check-stale-data", response_model=QuoteFreshnessReport)
def check_quote_freshness(
    symbol: str = Query("RELIANCE", description="Ticker symbol to check"),
) -> QuoteFreshnessReport:
    """Evaluates market quote freshness for a specific symbol against strict thresholds."""
    return _orchestrator.stale_guard.check_quote_freshness(symbol=symbol)


@router.post("/reconstruct-state", response_model=StateReconstructionReport)
def reconstruct_and_reconcile_state() -> StateReconstructionReport:
    """Executes full cross-ledger reconciliation between SQLite WAL database and broker."""
    return _orchestrator.state_reconstructor.reconstruct_and_reconcile()


@router.post("/safe-resume", response_model=SafeResumeAttestation)
def request_safe_resumption(
    operator_token: str = Query(
        ...,
        description="Operator authorization token starting with 'OPERATOR-RESUME-'",
    ),
) -> SafeResumeAttestation:
    """Validates pre-resumption checklist and issues formal safe resumption attestation."""
    attestation = _orchestrator.safe_resume.request_safe_resume(
        operator_token=operator_token, active_broker=_orchestrator.broker
    )
    if not attestation.resumption_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Safe resumption rejected by pre-resumption safety checklist",
                "attestation": attestation.model_dump(),
            },
        )
    return attestation


@router.post("/run-drill", response_model=DisasterRecoveryAuditResult)
def run_disaster_recovery_drill() -> DisasterRecoveryAuditResult:
    """Executes full 6-scenario automated disaster recovery fault injection drill."""
    return _orchestrator.run_comprehensive_disaster_drill()
