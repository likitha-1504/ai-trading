"""Risk governance, circuit breaker, and limits endpoints."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_capital_manager, get_db_repo
from app.api.schemas import RiskLimitsResponse, RiskStatusResponse
from app.capital.capital_manager import CapitalManager
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "/status",
    response_model=RiskStatusResponse,
    summary="Get real-time risk monitoring status",
    description="Returns daily drawdown against 3% circuit breaker limit and active position concentration.",
)
def get_risk_status(
    cap_mgr: CapitalManager = Depends(get_capital_manager),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> RiskStatusResponse:
    snap = cap_mgr.get_capital_snapshot()
    open_positions = repo.get_open_positions()

    is_tripped = snap.daily_drawdown_pct >= Decimal("0.03")
    max_cap = 2
    can_trade = (not is_tripped) and (len(open_positions) < max_cap)

    status_str = "CRITICAL" if is_tripped else ("WARNING" if snap.daily_drawdown_pct >= Decimal("0.02") else "NORMAL")

    return RiskStatusResponse(
        circuit_breaker_tripped=is_tripped,
        daily_drawdown_amount=snap.daily_drawdown_amount,
        daily_drawdown_pct=snap.daily_drawdown_pct,
        max_daily_drawdown_pct=Decimal("0.03"),
        open_positions_count=len(open_positions),
        max_positions_cap=max_cap,
        total_capital=snap.total_capital,
        available_capital=snap.available_capital,
        can_take_trades=can_trade,
        status=status_str,
    )


@router.get(
    "/events",
    response_model=list[dict[str, Any]],
    summary="List recent risk and circuit breaker events",
    description="Returns risk log entries including drawdown warnings, limit rejections, and circuit breaker checks.",
)
def list_risk_events(
    limit: int = Query(default=50, ge=1, le=200),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[dict[str, Any]]:
    return repo.get_recent_risk_events(limit=limit)


@router.get(
    "/limits",
    response_model=RiskLimitsResponse,
    summary="Get active risk limits and trading guardrails",
    description="Returns hard capital limits, max drawdown percentages, position size caps, and intraday exit cutoffs.",
)
def get_risk_limits(
    cap_mgr: CapitalManager = Depends(get_capital_manager),
) -> RiskLimitsResponse:
    cfg = cap_mgr.config
    return RiskLimitsResponse(
        starting_capital=cfg.starting_capital,
        max_daily_drawdown_pct=Decimal("0.03"),
        max_position_size_pct=Decimal("0.015"),
        max_risk_per_trade_pct=Decimal("0.015"),
        autonomous_threshold=cfg.autonomous_threshold,
        hard_stop_loss_pct=Decimal("0.01"),
        intraday_cutoff_ist="15:15 IST",
    )
