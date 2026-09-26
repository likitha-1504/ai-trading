"""FastAPI REST API Endpoints for Phase 32 Execution Optimization.

Exposes endpoints for:
- Comparative Execution Optimization Studies
- Real-time Slippage and Market Impact Estimation
- Liquidity-Aware Sizing Recommendations
- On-demand Paper Execution Validation Runs
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query

from app.execution_opt.execution_optimizer import ExecutionOptimizer
from app.execution_opt.liquidity_sizer import LiquidityAwareSizer
from app.execution_opt.models import (
    ExecutionOptimizationStudy,
    LiquiditySizingRecommendation,
    SlippageEstimate,
)
from app.execution_opt.slippage_model import SlippageModel
from app.models.contracts import TradeSide

router = APIRouter(prefix="/execution-opt", tags=["Execution Optimization"])

_optimizer = ExecutionOptimizer()


@router.get("/study", response_model=ExecutionOptimizationStudy)
def get_execution_optimization_study() -> ExecutionOptimizationStudy:
    """Returns the latest comparative paper execution optimization study."""
    return _optimizer.get_latest_study()


@router.post("/estimate-slippage", response_model=SlippageEstimate)
def estimate_order_slippage(
    symbol: str = Query("RELIANCE", description="Ticker symbol"),
    order_qty: int = Query(25, ge=1),
    expected_price: Decimal = Query(Decimal("2450.00"), gt=0.0),
    spread_pct: Decimal = Query(Decimal("0.02"), ge=0.0),
    bar_volume: int = Query(15000, ge=1),
    realized_volatility: Decimal = Query(Decimal("0.50"), ge=0.0),
    side: TradeSide = Query(TradeSide.BUY),
) -> SlippageEstimate:
    """Estimates half-spread cost, market impact, and total rupee drag for an order."""
    return SlippageModel.estimate_slippage(
        symbol=symbol,
        order_qty=order_qty,
        expected_price=expected_price,
        spread_pct=spread_pct,
        bar_volume=bar_volume,
        realized_volatility=realized_volatility,
        side=side,
    )


@router.post("/size-order", response_model=LiquiditySizingRecommendation)
def size_order_liquidity_aware(
    symbol: str = Query("RELIANCE", description="Ticker symbol"),
    requested_qty: int = Query(50, ge=1),
    bar_volume: int = Query(15000, ge=1),
    spread_pct: Decimal = Query(Decimal("0.02"), ge=0.0),
) -> LiquiditySizingRecommendation:
    """Calculates liquidity-aware size modulated by volume participation and spread penalties."""
    return LiquidityAwareSizer.size_order(
        symbol=symbol,
        requested_qty=requested_qty,
        bar_volume=bar_volume,
        spread_pct=spread_pct,
    )


@router.post("/run-paper-validation", response_model=ExecutionOptimizationStudy)
def run_paper_validation_study(
    orders_count: int = Query(50, ge=10, le=500),
) -> ExecutionOptimizationStudy:
    """Executes on-demand empirical paper execution validation study."""
    return _optimizer.run_comparative_study(orders_count=orders_count)
