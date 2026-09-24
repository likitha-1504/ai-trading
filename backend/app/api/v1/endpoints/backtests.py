"""Backtest report query endpoints."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.models.contracts import (
    BacktestReport,
    EquityPoint,
    PerformanceMetrics,
)

router = APIRouter()

# In-memory store for backtest evaluation reports
_backtest_store: dict[str, BacktestReport] = {}


def _ensure_default_report() -> None:
    if not _backtest_store:
        now = datetime.now(timezone.utc)
        metrics = PerformanceMetrics(
            total_trades=15,
            winning_trades=10,
            losing_trades=5,
            win_rate=66.67,
            gross_pnl=Decimal("45.50"),
            total_friction=Decimal("7.50"),
            net_pnl=Decimal("38.00"),
            profit_factor=2.45,
            expectancy=Decimal("2.53"),
            average_trade=Decimal("2.53"),
            average_win=Decimal("4.55"),
            average_loss=Decimal("-1.50"),
            max_drawdown_amount=Decimal("3.20"),
            max_drawdown_pct=0.032,
            trade_frequency_per_day=5.0,
            friction_pct_of_gross_profit=16.48,
        )
        report = BacktestReport(
            run_id="backtest-sample-001",
            start_time=now,
            end_time=now,
            initial_capital=Decimal("100.00"),
            final_equity=Decimal("138.00"),
            slippage_ticks=1,
            metrics=metrics,
            trades=[],
            equity_curve=[
                EquityPoint(
                    timestamp=now,
                    total_equity=Decimal("100.00"),
                    cash_balance=Decimal("100.00"),
                    unrealized_pnl=Decimal("0.00"),
                    drawdown_amount=Decimal("0.00"),
                    drawdown_pct=0.0,
                ),
                EquityPoint(
                    timestamp=now,
                    total_equity=Decimal("138.00"),
                    cash_balance=Decimal("138.00"),
                    unrealized_pnl=Decimal("0.00"),
                    drawdown_amount=Decimal("0.00"),
                    drawdown_pct=0.0,
                ),
            ],
        )
        _backtest_store[report.run_id] = report


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List backtest runs",
    description="Returns high-level metadata for backtesting evaluations.",
)
def list_backtests(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict[str, Any]]:
    _ensure_default_report()
    results: list[dict[str, Any]] = []
    for r in list(_backtest_store.values())[:limit]:
        results.append(
            {
                "run_id": r.run_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "initial_capital": float(r.initial_capital),
                "final_equity": float(r.final_equity),
                "net_pnl": float(r.metrics.net_pnl),
                "win_rate": r.metrics.win_rate,
                "profit_factor": r.metrics.profit_factor,
                "total_trades": r.metrics.total_trades,
            }
        )
    return results


@router.get(
    "/{run_id}",
    response_model=BacktestReport,
    summary="Get full backtest report by ID",
    description="Returns detailed financial KPIs, trade-by-trade journal, and equity curve points.",
)
def get_backtest_by_id(run_id: str) -> BacktestReport:
    _ensure_default_report()
    report = _backtest_store.get(run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run {run_id} not found",
        )
    return report
