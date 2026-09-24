"""Slippage Sensitivity Analysis Module.

Assesses strategy edge resilience by stress-testing execution against varying tick slippage levels.
"""

import logging
from decimal import Decimal

from app.backtesting.simulator import BacktestEngine
from app.models.contracts import (
    NormalizedMarketEvent,
    SlippageSensitivityPoint,
    SlippageSensitivityReport,
)

logger = logging.getLogger(__name__)


class SlippageSensitivityAnalyzer:
    """Stress tests backtesting execution across multiple slippage configurations."""

    def __init__(
        self,
        test_slippage_levels: list[int] | None = None,
        initial_capital: Decimal = Decimal("100.00"),
    ) -> None:
        self.slippage_levels = test_slippage_levels or [0, 1, 2, 3]
        self.initial_capital = initial_capital

    def evaluate(self, events: list[NormalizedMarketEvent]) -> SlippageSensitivityReport:
        """Run backtest iteratively across all configured slippage tick levels."""
        evaluations: list[SlippageSensitivityPoint] = []

        for ticks in self.slippage_levels:
            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                slippage_ticks=ticks,
            )
            report = engine.run(events)

            # Sum total slippage friction incurred
            total_slippage = sum(
                (
                    (t.entry_slippage + t.exit_slippage) * Decimal(t.quantity)
                    for t in report.trades
                ),
                Decimal("0.00"),
            )

            evaluations.append(
                SlippageSensitivityPoint(
                    slippage_ticks=ticks,
                    net_pnl=report.metrics.net_pnl,
                    profit_factor=report.metrics.profit_factor,
                    expectancy=report.metrics.expectancy,
                    total_slippage_cost=total_slippage.quantize(Decimal("0.01")),
                )
            )

        # Viable at highest slippage if profit factor >= 1.0 and net_pnl > 0
        worst_case = evaluations[-1]
        is_viable = worst_case.profit_factor >= 1.0 and worst_case.net_pnl > Decimal("0.00")

        return SlippageSensitivityReport(
            base_ticks=self.slippage_levels[0] if self.slippage_levels else 0,
            evaluations=evaluations,
            is_viable_at_high_slippage=is_viable,
        )
