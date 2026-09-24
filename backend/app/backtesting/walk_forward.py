"""Walk-Forward and Out-of-Sample Validation Engine.

Evaluates strategy robustness and detects overfitting by executing sequential
walk-forward splits with decoupled in-sample and out-of-sample windows.
"""

import logging
from decimal import Decimal

from app.backtesting.simulator import BacktestEngine
from app.models.contracts import (
    NormalizedMarketEvent,
    WalkForwardReport,
    WalkForwardWindow,
)

logger = logging.getLogger(__name__)


class WalkForwardAnalyzer:
    """Executes sequential walk-forward evaluation across partitioned historical event streams."""

    def __init__(
        self,
        num_windows: int = 3,
        in_sample_ratio: float = 0.70,
        initial_capital: Decimal = Decimal("100.00"),
        slippage_ticks: int = 1,
    ) -> None:
        if num_windows < 1:
            raise ValueError(f"num_windows must be >= 1, got {num_windows}")
        if not (0.1 <= in_sample_ratio <= 0.9):
            raise ValueError(f"in_sample_ratio must be between 0.1 and 0.9, got {in_sample_ratio}")

        self.num_windows = num_windows
        self.in_sample_ratio = in_sample_ratio
        self.initial_capital = initial_capital
        self.slippage_ticks = slippage_ticks

    def evaluate(self, events: list[NormalizedMarketEvent]) -> WalkForwardReport:
        """Run walk-forward evaluation across partitions of chronological events."""
        total_events = len(events)
        if total_events < self.num_windows * 10:
            raise ValueError(
                f"Insufficient events ({total_events}) for {self.num_windows} walk-forward windows"
            )

        window_size = total_events // self.num_windows
        windows: list[WalkForwardWindow] = []

        total_oos_pf = 0.0
        total_oos_exp = Decimal("0.00")

        for idx in range(self.num_windows):
            start_idx = idx * window_size
            end_idx = start_idx + window_size if idx < self.num_windows - 1 else total_events
            window_events = events[start_idx:end_idx]

            split_pt = int(len(window_events) * self.in_sample_ratio)
            in_sample_events = window_events[:split_pt]
            out_of_sample_events = window_events[split_pt:]

            if not in_sample_events or not out_of_sample_events:
                continue

            # Run in-sample backtest
            engine_is = BacktestEngine(
                initial_capital=self.initial_capital,
                slippage_ticks=self.slippage_ticks,
            )
            report_is = engine_is.run(in_sample_events)

            # Run out-of-sample backtest
            engine_oos = BacktestEngine(
                initial_capital=self.initial_capital,
                slippage_ticks=self.slippage_ticks,
            )
            report_oos = engine_oos.run(out_of_sample_events)

            # Calculate degradation
            is_pf = report_is.metrics.profit_factor
            oos_pf = report_oos.metrics.profit_factor
            if is_pf > 0:
                degradation = max(0.0, (is_pf - oos_pf) / is_pf)
            else:
                degradation = 0.0

            total_oos_pf += oos_pf
            total_oos_exp += report_oos.metrics.expectancy

            windows.append(
                WalkForwardWindow(
                    window_index=idx + 1,
                    in_sample_start=in_sample_events[0].exchange_timestamp,
                    in_sample_end=in_sample_events[-1].exchange_timestamp,
                    out_of_sample_start=out_of_sample_events[0].exchange_timestamp,
                    out_of_sample_end=out_of_sample_events[-1].exchange_timestamp,
                    in_sample_metrics=report_is.metrics,
                    out_of_sample_metrics=report_oos.metrics,
                    out_of_sample_degradation_pct=round(degradation, 4),
                )
            )

        window_count = len(windows)
        avg_oos_pf = total_oos_pf / window_count if window_count > 0 else 0.0
        avg_oos_exp = (
            (total_oos_exp / Decimal(window_count)).quantize(Decimal("0.01"))
            if window_count > 0
            else Decimal("0.00")
        )

        # Flag overfitting: if average OOS profit factor < 1.0 or expectancy < 0
        is_overfitted = avg_oos_pf < 1.0 or avg_oos_exp < Decimal("0.00")

        return WalkForwardReport(
            total_windows=window_count,
            windows=windows,
            avg_out_of_sample_profit_factor=round(avg_oos_pf, 3),
            avg_out_of_sample_expectancy=avg_oos_exp,
            is_overfitted=is_overfitted,
        )
