"""Unified Execution Optimizer for Phase 32.

Synthesizes:
- Slippage and Market Impact Modeling
- Liquidity-Aware Sizing
- Order Timing & Urgency Scheduling
- Comparative Paper Execution Studies
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.execution_opt.liquidity_sizer import LiquidityAwareSizer
from app.execution_opt.models import (
    ExecutionOptimizationStudy,
    ExecutionUrgency,
    LiquiditySizingRecommendation,
    SlippageEstimate,
)
from app.execution_opt.order_scheduler import OrderScheduler
from app.execution_opt.paper_validator import ExecutionPaperValidator
from app.execution_opt.slippage_model import SlippageModel
from app.models.contracts import StrategyType, TradeSide


class ExecutionOptimizer:
    """Unified engine for optimizing trade execution parameters."""

    def __init__(self) -> None:
        self._last_study: ExecutionOptimizationStudy | None = None

    def optimize_order(
        self,
        symbol: str,
        strategy_type: StrategyType,
        requested_qty: int,
        expected_price: Decimal,
        bar_volume: int = 15000,
        spread_pct: Decimal = Decimal("0.0200"),
        realized_volatility: Decimal = Decimal("0.50"),
        rank_score: Decimal = Decimal("85.00"),
        side: TradeSide = TradeSide.BUY,
        timestamp: datetime | None = None,
    ) -> tuple[LiquiditySizingRecommendation, ExecutionUrgency, str, SlippageEstimate]:
        """Produces optimized execution parameters for an incoming order."""
        # 1. Liquidity-Aware Sizing
        sizing = LiquidityAwareSizer.size_order(
            symbol=symbol,
            requested_qty=requested_qty,
            bar_volume=bar_volume,
            spread_pct=spread_pct,
        )

        # 2. Timing and Urgency Scheduling
        urgency, order_type, _rationale = OrderScheduler.schedule_execution(
            strategy_type=strategy_type,
            rank_score=rank_score,
            spread_pct=spread_pct,
            volume_participation_pct=sizing.volume_participation_pct,
            timestamp=timestamp,
        )

        # 3. Slippage and Friction Estimation on Optimized Size
        slippage = SlippageModel.estimate_slippage(
            symbol=symbol,
            order_qty=sizing.recommended_qty,
            expected_price=expected_price,
            spread_pct=spread_pct,
            bar_volume=bar_volume,
            realized_volatility=realized_volatility,
            side=side,
        )

        return sizing, urgency, order_type, slippage

    def run_comparative_study(self, orders_count: int = 50) -> ExecutionOptimizationStudy:
        """Executes comparative paper validation study and caches results."""
        study = ExecutionPaperValidator.run_study(sample_orders_count=orders_count)
        self._last_study = study
        return study

    def get_latest_study(self) -> ExecutionOptimizationStudy:
        """Retrieves latest study or runs a default benchmark study."""
        if self._last_study is None:
            self._last_study = self.run_comparative_study(orders_count=50)
        return self._last_study
