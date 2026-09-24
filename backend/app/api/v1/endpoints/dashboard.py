"""Dashboard summary and capital telemetry endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.deps import (
    SystemState,
    get_capital_manager,
    get_db_repo,
    get_performance_aggregator,
    get_system_state,
)
from app.api.schemas import CapitalResponse, DashboardSummaryResponse
from app.capital.capital_manager import CapitalManager
from app.db.performance import PerformanceAggregator
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get real-time dashboard summary telemetry",
    description="Returns aggregate portfolio valuation, daily P&L, win rate, open positions, and system status.",
)
def get_dashboard_summary(
    repo: DatabaseRepository = Depends(get_db_repo),
    cap_mgr: CapitalManager = Depends(get_capital_manager),
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
    sys_state: SystemState = Depends(get_system_state),
) -> DashboardSummaryResponse:
    cap_snap = cap_mgr.get_capital_snapshot()
    perf = perf_agg.calculate_metrics()
    open_positions = repo.get_open_positions()
    candidates = repo.get_recent_candidates(limit=50)

    # Determine status string
    status_str = "HALTED" if sys_state.is_halted else "HEALTHY"
    if not sys_state.is_halted and cap_snap.daily_drawdown_pct >= Decimal("0.02"):
        status_str = "WARNING"

    daily_pnl = cap_snap.realized_pnl + cap_snap.unrealized_pnl
    daily_pnl_pct = (
        float(daily_pnl / cap_snap.total_capital) * 100
        if cap_snap.total_capital > 0
        else 0.0
    )

    return DashboardSummaryResponse(
        total_equity=cap_snap.total_capital,
        daily_pnl=daily_pnl,
        daily_pnl_pct=round(daily_pnl_pct, 4),
        realized_pnl=cap_snap.realized_pnl,
        unrealized_pnl=cap_snap.unrealized_pnl,
        win_rate=perf.win_rate_pct,
        open_positions_count=len(open_positions),
        total_trades_count=perf.total_trades,
        active_candidates_count=len(candidates),
        system_status=status_str,
        system_mode=sys_state.mode,
        live_trading_allowed=sys_state.live_trading_allowed,
    )


@router.get(
    "/capital",
    response_model=CapitalResponse,
    summary="Get account capital allocation state",
    description="Detailed breakdown of total capital, buying power, deployed margin, and high-water mark.",
)
def get_capital_telemetry(
    cap_mgr: CapitalManager = Depends(get_capital_manager),
) -> CapitalResponse:
    snap = cap_mgr.get_capital_snapshot()
    return CapitalResponse(
        total_capital=snap.total_capital,
        available_capital=snap.available_capital,
        deployed_capital=snap.deployed_capital,
        buying_power=snap.buying_power,
        realized_pnl=snap.realized_pnl,
        unrealized_pnl=snap.unrealized_pnl,
        daily_drawdown_amount=snap.daily_drawdown_amount,
        daily_drawdown_pct=snap.daily_drawdown_pct,
        high_water_mark=snap.high_water_mark,
        currency=snap.currency,
    )
