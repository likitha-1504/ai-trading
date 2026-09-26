"""FastAPI Endpoints for Phase 37 Long-Term Autonomous System.

Provides REST interfaces for:
- Operational status & lifecycle state query
- Multi-phase prerequisite verification audit
- Human release gate token evaluation and enforcement
- Autonomous session activation, square-off, and reconciliation
- Dynamic strategy portfolio rebalancing proposals & application
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.long_term_autonomous.lifecycle_orchestrator import LongTermAutonomousOrchestrator
from app.long_term_autonomous.models import (
    DynamicRebalanceProposal,
    LongTermAutonomousError,
    ReleaseGateRequest,
    UnapprovedReleaseError,
)

router = APIRouter(prefix="/long-term-autonomous", tags=["long-term-autonomous"])

# Shared singleton orchestrator
_orchestrator: LongTermAutonomousOrchestrator | None = None


def get_orchestrator() -> LongTermAutonomousOrchestrator:
    """Returns or lazily creates shared orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LongTermAutonomousOrchestrator()
    return _orchestrator


class StartSessionRequest(BaseModel):
    operator_id: str = "OPERATOR_ADMIN"
    operator_token: str


class RebalanceProposeRequest(BaseModel):
    method: str = "SHARPE_WEIGHTED"


class RebalanceApplyRequest(BaseModel):
    proposal_id: str
    method: str
    proposed_weights: dict[str, float]
    rationale: str
    operator_id: str = "OPERATOR_ADMIN"
    operator_token: str


class ResetSafetyRequest(BaseModel):
    operator_id: str = "OPERATOR_ADMIN"
    operator_token: str


@router.get("/status", summary="Get Long-Term Autonomous System Status")
def get_system_status() -> dict[str, Any]:
    """Returns real-time status of the long-term autonomous system, state, and portfolio."""
    orch = get_orchestrator()
    return orch.get_system_status()


@router.post("/prerequisites/verify", summary="Verify Multi-Phase Prerequisites")
def verify_prerequisites(strict: bool = False) -> dict[str, Any]:
    """Audits all 7 prerequisite dimensions from earlier phases (Phase 21-36)."""
    orch = get_orchestrator()
    audit = orch.execute_pre_market_audit()
    return audit.model_dump(mode="json")


@router.post("/session/start", summary="Start Autonomous Trading Session")
def start_session(req: StartSessionRequest) -> dict[str, Any]:
    """Starts an autonomous trading session after verifying human release gate token."""
    orch = get_orchestrator()
    try:
        if orch.state.value == "OFFLINE":
            orch.execute_pre_market_audit()
        session_id = orch.start_session(operator_id=req.operator_id, operator_token=req.operator_token)
        return {"session_id": session_id, "state": orch.state.value, "capital": float(orch.capital)}
    except UnapprovedReleaseError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except LongTermAutonomousError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/session/cutoff", summary="Trigger 15:15 IST Auto-Square-Off")
def trigger_cutoff() -> dict[str, Any]:
    """Triggers mandatory 15:15 IST intraday auto-square-off of all open positions."""
    orch = get_orchestrator()
    try:
        closed_count = orch.trigger_intraday_cutoff()
        return {"state": orch.state.value, "positions_squared_off": closed_count}
    except LongTermAutonomousError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/session/reconcile", summary="Execute Post-Market Reconciliation")
def reconcile_session() -> dict[str, Any]:
    """Executes post-session PnL reconciliation, ledger hashing, and session archiving."""
    orch = get_orchestrator()
    try:
        summary = orch.execute_post_market_reconciliation()
        return summary.model_dump(mode="json")
    except LongTermAutonomousError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/portfolio/rebalance/propose", summary="Generate Dynamic Rebalance Proposal")
def propose_rebalance(req: RebalanceProposeRequest) -> dict[str, Any]:
    """Generates an empirical multi-strategy rebalance proposal."""
    orch = get_orchestrator()
    try:
        proposal = orch.portfolio_governor.generate_rebalance_proposal(method=req.method)
        return proposal.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/portfolio/rebalance/apply", summary="Apply Governed Rebalance Proposal")
def apply_rebalance(req: RebalanceApplyRequest) -> dict[str, Any]:
    """Applies a dynamic rebalance proposal with operator release gate verification."""
    orch = get_orchestrator()
    try:
        weights_decimal = {k: Decimal(str(v)) for k, v in req.proposed_weights.items()}
        proposal = DynamicRebalanceProposal(
            proposal_id=req.proposal_id,
            method=req.method,
            proposed_weights=weights_decimal,
            rationale=req.rationale,
            approved=False,
        )
        applied = orch.portfolio_governor.apply_rebalance_proposal(
            proposal=proposal,
            operator_token=req.operator_token,
            operator_id=req.operator_id,
        )
        return {
            "applied_weights": {k: float(v) for k, v in applied.items()},
            "status": "APPLIED_SUCCESSFULLY",
        }
    except UnapprovedReleaseError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/release-gate/evaluate", summary="Evaluate Release Gate Request")
def evaluate_release_gate(req: ReleaseGateRequest) -> dict[str, Any]:
    """Evaluates an explicit human release gate request."""
    orch = get_orchestrator()
    decision = orch.release_gate.evaluate_release(req)
    return decision.model_dump(mode="json")


@router.post("/safety/reset", summary="Reset Safety Halt / Circuit Breaker")
def reset_safety_halt(req: ResetSafetyRequest) -> dict[str, Any]:
    """Resets safety breaker or halt with operator authorization token."""
    orch = get_orchestrator()
    try:
        orch.reset_safety_halt(operator_id=req.operator_id, operator_token=req.operator_token)
        return {"status": "SAFETY_HALT_RESET", "state": orch.state.value}
    except UnapprovedReleaseError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
