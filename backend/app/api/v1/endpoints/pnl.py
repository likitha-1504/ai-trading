"""P/L telemetry and Indian statutory friction breakdown endpoints."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_capital_manager,
    get_db_repo,
    get_performance_aggregator,
)
from app.api.schemas import PnLSummaryResponse
from app.capital.capital_manager import CapitalManager
from app.db.performance import PerformanceAggregator
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "",
    response_model=PnLSummaryResponse,
    summary="Get comprehensive P/L summary",
    description="Returns gross P/L, total Indian friction deducted, net P/L, and current drawdown amount.",
)
def get_pnl_summary(
    cap_mgr: CapitalManager = Depends(get_capital_manager),
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> PnLSummaryResponse:
    cap = cap_mgr.get_capital_snapshot()
    perf = perf_agg.calculate_metrics()

    return PnLSummaryResponse(
        realized_pnl=cap.realized_pnl,
        unrealized_pnl=cap.unrealized_pnl,
        gross_pnl=perf.total_gross_pnl,
        total_friction=perf.total_friction,
        net_pnl=perf.total_net_pnl,
        daily_drawdown_amount=cap.daily_drawdown_amount,
        daily_drawdown_pct=float(cap.daily_drawdown_pct),
        currency=cap.currency,
    )


@router.get(
    "/breakdown",
    response_model=dict[str, Any],
    summary="Get detailed P/L and friction itemization",
    description="Itemizes Indian statutory fees (STT, GST, Exchange charges, SEBI, stamp duty) and strategy-level P/L.",
)
def get_pnl_breakdown(
    repo: DatabaseRepository = Depends(get_db_repo),
    perf_agg: PerformanceAggregator = Depends(get_performance_aggregator),
) -> dict[str, Any]:
    trades = repo.get_recent_trades(limit=500)
    strat_metrics = perf_agg.calculate_strategy_metrics()

    total_brokerage = Decimal("0.00")
    total_stt = Decimal("0.00")
    total_exchange = Decimal("0.00")
    total_sebi = Decimal("0.00")
    total_stamp = Decimal("0.00")
    total_gst = Decimal("0.00")
    total_slippage = Decimal("0.00")

    for t in trades:
        f = t.friction
        total_brokerage += f.brokerage
        total_stt += f.stt
        total_exchange += f.exchange_charges
        total_sebi += f.sebi_charges
        total_stamp += f.stamp_duty
        total_gst += f.gst
        total_slippage += f.expected_slippage

    return {
        "friction_itemization": {
            "brokerage": float(total_brokerage),
            "stt": float(total_stt),
            "exchange_charges": float(total_exchange),
            "sebi_charges": float(total_sebi),
            "stamp_duty": float(total_stamp),
            "gst": float(total_gst),
            "slippage": float(total_slippage),
            "total_friction": float(
                total_brokerage
                + total_stt
                + total_exchange
                + total_sebi
                + total_stamp
                + total_gst
                + total_slippage
            ),
        },
        "strategy_stratification": strat_metrics,
        "total_trades_analyzed": len(trades),
    }
