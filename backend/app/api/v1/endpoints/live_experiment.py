"""API Endpoints for Phase 20 Controlled ₹100 Live Experiment."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import SystemState, get_system_state
from app.live.experiment_engine import (
    LiveExperimentEngine,
    LiveExperimentSecurityError,
)

router = APIRouter()


# =====================================================================
# Request / Response Schemas
# =====================================================================


class StrategyVersionRequest(BaseModel):
    version: str = Field(..., description="Semantic strategy version identifier (e.g., v1.0.1)")
    reason: str = Field(..., min_length=5, description="Documented reason for in-flight optimization")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Updated strategy parameters")


class CapitalIncreaseRequest(BaseModel):
    requested_capital: Decimal = Field(..., description="Target capital limit (must not exceed ₹100 in Phase 20)")
    authorization_token: str = Field(..., description="Cryptographic human authorization token")


class CapitalIncreaseResponse(BaseModel):
    success: bool
    current_capital: Decimal
    message: str


class ExperimentRunResponse(BaseModel):
    experiment_id: str
    initial_capital: Decimal
    final_equity: Decimal
    net_pnl: Decimal
    return_on_capital_pct: float
    total_trades: int
    fill_rate_pct: float
    avg_fill_latency_ms: float
    gate_checkpoint_reached: bool = True
    report_saved: bool = True


# =====================================================================
# Endpoints
# =====================================================================


@router.get(
    "/status",
    summary="Phase 20 Live Experiment Status",
    description="Returns telemetry metrics across all 9 operational dimensions.",
)
def get_live_experiment_status(
    sys_state: SystemState = Depends(get_system_state),
) -> dict[str, Any]:
    engine = LiveExperimentEngine()
    result = engine.run_controlled_experiment()
    return {
        "experiment_id": result.experiment_id,
        "strategy_version": result.strategy_version,
        "initial_capital": float(result.initial_capital),
        "final_equity": float(result.final_equity),
        "net_pnl": float(result.net_pnl_metrics.total_net_pnl),
        "return_on_capital_pct": result.net_pnl_metrics.return_on_capital_pct,
        "metrics": {
            "net_pnl_metrics": {
                "gross_pnl": float(result.net_pnl_metrics.total_gross_pnl),
                "brokerage": float(result.net_pnl_metrics.total_brokerage),
                "stt": float(result.net_pnl_metrics.total_stt),
                "exchange_charges": float(result.net_pnl_metrics.total_exchange_charges),
                "sebi_charges": float(result.net_pnl_metrics.total_sebi_charges),
                "stamp_duty": float(result.net_pnl_metrics.total_stamp_duty),
                "gst": float(result.net_pnl_metrics.total_gst),
                "total_friction": float(result.net_pnl_metrics.total_friction),
                "net_pnl": float(result.net_pnl_metrics.total_net_pnl),
            },
            "execution_quality": {
                "orders_submitted": result.execution_quality.orders_submitted,
                "orders_filled": result.execution_quality.orders_filled,
                "fill_rate_pct": result.execution_quality.fill_rate_pct,
                "avg_fill_latency_ms": result.execution_quality.avg_fill_latency_ms,
            },
            "slippage": {
                "avg_slippage_bps": result.slippage_metrics.avg_slippage_bps,
                "max_slippage_bps": result.slippage_metrics.max_slippage_bps,
                "tick_distribution": result.slippage_metrics.tick_slippage_distribution,
            },
            "rejected_orders": {
                "total_rejections": result.rejected_orders.total_rejections,
                "capital_cap_rejections": result.rejected_orders.capital_cap_rejections,
                "reasons": result.rejected_orders.rejections_by_reason,
            },
            "watcher_response": {
                "total_evaluations": result.watcher_response.total_evaluations,
                "median_latency_us": result.watcher_response.median_latency_us,
                "sub_50ms_compliance_pct": result.watcher_response.sub_50ms_compliance_pct,
                "exits_triggered": result.watcher_response.exits_triggered,
                "llm_independence_verified": result.watcher_response.llm_independence_verified,
            },
            "model_latency": {
                "qwen3_avg_ms": result.model_latency.qwen3_avg_latency_ms,
                "deepseek_r1_avg_ms": result.model_latency.deepseek_r1_avg_latency_ms,
            },
            "model_disagreement": {
                "total_evaluations": result.model_disagreement.total_council_evaluations,
                "disagreement_rate_pct": result.model_disagreement.disagreement_rate_pct,
                "arbitrations_approved": result.model_disagreement.arbitrations_approved,
            },
            "trade_frequency": {
                "total_trades": result.trade_frequency.total_trades,
                "trades_per_session": result.trade_frequency.trades_per_session,
                "avg_holding_duration_seconds": result.trade_frequency.avg_holding_duration_seconds,
            },
            "failure_events": {
                "total_failure_events": result.failure_events.total_failure_events,
                "unhandled_exceptions": result.failure_events.unhandled_exceptions,
            },
        },
        "gate_status": "PHASE_20_GATE_CHECKPOINT_AWAITING_APPROVAL",
    }


@router.get(
    "/report",
    summary="Phase 20 Live Experiment Markdown Report",
    description="Returns formal markdown report content for Phase 20 live experiment.",
)
def get_live_experiment_report() -> dict[str, Any]:
    engine = LiveExperimentEngine()
    result = engine.run_controlled_experiment()
    return {
        "experiment_id": result.experiment_id,
        "strategy_version": result.strategy_version,
        "report_markdown": result.report_markdown,
    }


@router.post(
    "/run",
    response_model=ExperimentRunResponse,
    summary="Execute Controlled Live Experiment",
    description="Executes a controlled live experiment session under ₹100 capital ceiling.",
)
def run_live_experiment_iteration(
    sys_state: SystemState = Depends(get_system_state),
) -> ExperimentRunResponse:
    if sys_state.is_halted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is currently HALTED. Live experiment cannot execute.",
        )

    engine = LiveExperimentEngine()
    result = engine.run_controlled_experiment()
    return ExperimentRunResponse(
        experiment_id=result.experiment_id,
        initial_capital=result.initial_capital,
        final_equity=result.final_equity,
        net_pnl=result.net_pnl_metrics.total_net_pnl,
        return_on_capital_pct=result.net_pnl_metrics.return_on_capital_pct,
        total_trades=result.trade_frequency.total_trades,
        fill_rate_pct=result.execution_quality.fill_rate_pct,
        avg_fill_latency_ms=result.execution_quality.avg_fill_latency_ms,
        gate_checkpoint_reached=True,
        report_saved=True,
    )


@router.post(
    "/strategy-version",
    summary="Record Strategy Version Mutation",
    description="Records strategy parameter adjustments during experiment with mandatory documented reason.",
)
def record_strategy_version_endpoint(
    payload: StrategyVersionRequest,
    sys_state: SystemState = Depends(get_system_state),
) -> dict[str, Any]:
    engine = LiveExperimentEngine()
    try:
        audit = engine.record_strategy_version(
            version=payload.version,
            reason=payload.reason,
            parameters=payload.parameters,
        )
        return {
            "success": True,
            "version": audit.version,
            "recorded_at": audit.recorded_at.isoformat(),
            "reason": audit.reason,
            "status": "LOCKED",
        }
    except LiveExperimentSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/capital-request",
    response_model=CapitalIncreaseResponse,
    summary="Guarded Capital Increase Request",
    description="Enforces strict Phase 20 ₹100 limit, blocking unauthorized capital raises.",
)
def request_capital_increase_endpoint(
    payload: CapitalIncreaseRequest,
    sys_state: SystemState = Depends(get_system_state),
) -> CapitalIncreaseResponse:
    engine = LiveExperimentEngine()
    try:
        engine.request_capital_increase(
            new_capital=payload.requested_capital,
            human_auth_token=payload.authorization_token,
        )
        return CapitalIncreaseResponse(
            success=True,
            current_capital=payload.requested_capital,
            message=f"Capital limit elevated to ₹{payload.requested_capital:.2f} with authorized human token.",
        )
    except LiveExperimentSecurityError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
