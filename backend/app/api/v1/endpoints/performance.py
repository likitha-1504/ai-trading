"""Performance aggregation and execution telemetry endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_performance_aggregator
from app.db.performance import PerformanceAggregator

router = APIRouter()


@router.get(
    "",
    response_model=dict[str, Any],
    summary="Get aggregated performance metrics",
    description="Returns win rate, profit factor, expectancy, average win/loss, maximum drawdown, and trade counts.",
)
def get_performance_summary(
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> dict[str, Any]:
    m = perf_agg.calculate_metrics()
    return {
        "total_trades": m.total_trades,
        "winning_trades": m.winning_trades,
        "losing_trades": m.losing_trades,
        "breakeven_trades": m.breakeven_trades,
        "win_rate": m.win_rate_pct,
        "win_rate_pct": m.win_rate_pct,
        "gross_pnl": float(m.total_gross_pnl),
        "total_friction": float(m.total_friction),
        "net_pnl": float(m.total_net_pnl),
        "profit_factor": m.profit_factor,
        "expectancy": float(m.expectancy),
        "average_trade": float(m.average_trade_net),
        "max_drawdown_amount": float(m.max_drawdown_amount),
        "max_drawdown_pct": m.max_drawdown_pct,
        "friction_pct_of_gross_profit": m.friction_pct_of_gross,
    }


@router.get(
    "/strategies",
    response_model=dict[str, Any],
    summary="Get performance stratified by strategy",
    description="Compares performance metrics between Momentum Continuation and Early Move Detection strategies.",
)
def get_strategy_performance(
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> dict[str, Any]:
    return perf_agg.calculate_strategy_metrics()


@router.get(
    "/execution",
    response_model=dict[str, Any],
    summary="Get broker execution latency and fill telemetry",
    description="Returns order submission latency, ACK latency, fill latency, fill rate, and total slippage.",
)
def get_execution_performance(
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> dict[str, Any]:
    return perf_agg.get_execution_latency_metrics()
