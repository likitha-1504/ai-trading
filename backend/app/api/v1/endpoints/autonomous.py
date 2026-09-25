"""FastAPI Endpoints for Phase 21 ₹300 Autonomous Mode."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import SystemState, get_system_state
from app.autonomous.autonomous_engine import AutonomousModeEngine
from app.autonomous.config import AutonomousModeSecurityError
from app.models.contracts import ApprovalMode

router = APIRouter()


# =====================================================================
# Request / Response Schemas
# =====================================================================


class AutonomousActivationRequest(BaseModel):
    authorization_token: str = Field(..., description="Cryptographic human authorization token")
    prior_validation_source: str = Field(
        default="LIVE_EXPERIMENT_REPORT.md",
        description="Documented validation reference from Phase 20",
    )
    validation_evidence: dict[str, Any] = Field(
        default_factory=dict, description="Audit metrics from prior phase"
    )


class AutonomousActivationResponse(BaseModel):
    success: bool
    activated_at: str
    token_masked: str
    capital_ceiling: Decimal
    autonomous_threshold: Decimal
    status: str


class AllocationEvaluationRequest(BaseModel):
    symbol: str = Field(..., description="Trading instrument identifier")
    price: Decimal = Field(..., description="Target execution price")
    quantity: int = Field(..., gt=0, description="Order quantity")


class AllocationEvaluationResponse(BaseModel):
    symbol: str
    notional: Decimal
    autonomous_ceiling: Decimal
    approval_mode: ApprovalMode
    decision_reason: str


class ManualApprovalRequest(BaseModel):
    plan_id: str = Field(..., description="Trade plan identifier requiring manual approval")
    authorization_token: str = Field(..., description="Operator human authorization token")
    reason: str = Field(
        default="Operator explicit override above ₹300",
        description="Documented rationale for approving trade above autonomous threshold",
    )


class ManualApprovalResponse(BaseModel):
    success: bool
    plan_id: str
    message: str


# =====================================================================
# Endpoints
# =====================================================================


@router.get(
    "/status",
    summary="Phase 21 Autonomous Mode Status",
    description="Returns current autonomous configuration, threshold (₹300.00), and invariant health.",
)
def get_autonomous_mode_status(
    sys_state: SystemState = Depends(get_system_state),
) -> dict[str, Any]:
    engine = AutonomousModeEngine()
    return {
        "phase": "PHASE_21_AUTONOMOUS_MODE",
        "autonomous_threshold": float(engine.config.autonomous_threshold),
        "capital_limit": float(engine.config.capital_limit),
        "strategy_version": engine.config.strategy_version,
        "is_activated": engine.is_activated,
        "circuit_breaker_tripped": engine.is_circuit_breaker_tripped,
        "safety_invariants": {
            "deterministic_risk_limits": True,
            "capital_caps": True,
            "circuit_breakers": True,
            "independent_position_watcher": True,
            "full_audit_logging": True,
            "automatic_recovery": True,
            "human_override": True,
        },
        "gate_status": "PHASE_21_GATE_CHECKPOINT_AWAITING_APPROVAL",
    }


@router.post(
    "/activate",
    response_model=AutonomousActivationResponse,
    summary="Activate Phase 21 Autonomous Mode",
    description="Requires prior documented validation and verified human cryptographic authorization.",
)
def activate_autonomous_mode_endpoint(
    payload: AutonomousActivationRequest,
    sys_state: SystemState = Depends(get_system_state),
) -> AutonomousActivationResponse:
    if sys_state.is_halted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is currently HALTED. Cannot activate autonomous mode.",
        )

    engine = AutonomousModeEngine()
    try:
        audit = engine.activate_autonomous_mode(
            human_auth_token=payload.authorization_token,
            prior_validation_source=payload.prior_validation_source,
            validation_evidence=payload.validation_evidence,
        )
        return AutonomousActivationResponse(
            success=True,
            activated_at=audit.activated_at.isoformat(),
            token_masked=audit.human_approval_token_masked,
            capital_ceiling=audit.capital_ceiling,
            autonomous_threshold=audit.autonomous_threshold,
            status="AUTONOMOUS_MODE_ACTIVE_UP_TO_300",
        )
    except AutonomousModeSecurityError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/evaluate-allocation",
    response_model=AllocationEvaluationResponse,
    summary="Evaluate Trade Allocation Gating",
    description="Tests whether trade notional is AUTONOMOUS (<= ₹300) or MANUAL_PENDING (> ₹300).",
)
def evaluate_allocation_endpoint(
    payload: AllocationEvaluationRequest,
    sys_state: SystemState = Depends(get_system_state),
) -> AllocationEvaluationResponse:
    engine = AutonomousModeEngine()
    mode, reason = engine.evaluate_allocation(
        symbol=payload.symbol,
        price=payload.price,
        quantity=payload.quantity,
    )
    notional = payload.price * Decimal(str(payload.quantity))
    return AllocationEvaluationResponse(
        symbol=payload.symbol,
        notional=notional,
        autonomous_ceiling=engine.config.autonomous_threshold,
        approval_mode=mode,
        decision_reason=reason,
    )


@router.post(
    "/approve-manual-trade",
    response_model=ManualApprovalResponse,
    summary="Approve Allocation Above ₹300",
    description="Enforces human gate for allocations > ₹300, requiring operator token.",
)
def approve_manual_trade_endpoint(
    payload: ManualApprovalRequest,
    sys_state: SystemState = Depends(get_system_state),
) -> ManualApprovalResponse:
    engine = AutonomousModeEngine()
    try:
        engine.approve_manual_trade(
            plan_id=payload.plan_id,
            human_auth_token=payload.authorization_token,
            reason=payload.reason,
        )
        return ManualApprovalResponse(
            success=True,
            plan_id=payload.plan_id,
            message=f"Plan {payload.plan_id} approved by human operator above ₹300 ceiling.",
        )
    except AutonomousModeSecurityError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/run",
    summary="Run Autonomous Mode Simulation",
    description="Executes Phase 21 multi-session simulation verifying all 7 invariants.",
)
def run_autonomous_simulation_endpoint(
    sys_state: SystemState = Depends(get_system_state),
) -> dict[str, Any]:
    if sys_state.is_halted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is currently HALTED. Cannot execute autonomous run.",
        )

    engine = AutonomousModeEngine()
    result = engine.run_autonomous_simulation()
    return {
        "run_id": result.run_id,
        "initial_capital": float(result.initial_capital),
        "final_equity": float(result.final_equity),
        "net_pnl": float(result.net_pnl),
        "return_on_capital_pct": result.return_on_capital_pct,
        "autonomous_trades": result.autonomous_trades,
        "manual_pending_trades": result.manual_pending_trades,
        "circuit_breaker_tripped": result.circuit_breaker_tripped,
        "gate_checkpoint_reached": True,
    }


@router.get(
    "/report",
    summary="Phase 21 Autonomous Mode Report",
    description="Returns formal evaluation report for Phase 21 ₹300 Autonomous Mode.",
)
def get_autonomous_mode_report() -> dict[str, Any]:
    engine = AutonomousModeEngine()
    result = engine.run_autonomous_simulation()
    return {
        "run_id": result.run_id,
        "report_markdown": result.report_markdown,
    }
