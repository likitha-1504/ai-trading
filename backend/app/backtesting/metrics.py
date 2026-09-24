"""Performance Metrics Calculation and Analysis Suite.

Computes financial expectancy, profit factor, maximum drawdown, trade frequency,
cost contribution, and market regime breakdown from trade journal records.
"""

import logging
from datetime import datetime
from decimal import Decimal

from app.models.contracts import EquityPoint, PerformanceMetrics, TradeRecord

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """Calculates quantitative performance, expectancy, risk, and regime statistics."""

    @classmethod
    def calculate(
        cls,
        trades: list[TradeRecord],
        equity_curve: list[EquityPoint],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> PerformanceMetrics:
        """Compute exhaustive performance metrics from completed trades and equity history."""
        total_trades = len(trades)

        if total_trades == 0:
            return cls._empty_metrics()

        winning_trades: list[TradeRecord] = []
        losing_trades: list[TradeRecord] = []
        total_gross = Decimal("0.00")
        total_friction = Decimal("0.00")
        total_net = Decimal("0.00")

        gross_wins = Decimal("0.00")
        gross_losses = Decimal("0.00")

        regime_pnl: dict[str, Decimal] = {}
        regime_trades: dict[str, int] = {}

        for t in trades:
            total_gross += t.gross_pnl
            total_friction += t.friction.total_friction
            total_net += t.net_pnl

            # Regime grouping
            reg_key = t.market_regime_at_entry.value
            regime_pnl[reg_key] = regime_pnl.get(reg_key, Decimal("0.00")) + t.net_pnl
            regime_trades[reg_key] = regime_trades.get(reg_key, 0) + 1

            if t.net_pnl > Decimal("0.00"):
                winning_trades.append(t)
                gross_wins += t.net_pnl
            else:
                losing_trades.append(t)
                gross_losses += abs(t.net_pnl)

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades

        # Profit Factor
        if gross_losses > Decimal("0.00"):
            profit_factor = float(gross_wins / gross_losses)
        elif gross_wins > Decimal("0.00"):
            profit_factor = 999.0  # Infinite profit factor capped for numerical stability
        else:
            profit_factor = 0.0

        # Average win, loss, and expectancy
        avg_win = (gross_wins / Decimal(win_count)).quantize(Decimal("0.01")) if win_count > 0 else Decimal("0.00")
        avg_loss = (gross_losses / Decimal(loss_count)).quantize(Decimal("0.01")) if loss_count > 0 else Decimal("0.00")
        avg_trade = (total_net / Decimal(total_trades)).quantize(Decimal("0.01"))

        # Expectancy: (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        expectancy = (
            (Decimal(str(win_rate)) * avg_win) - (Decimal(str(1.0 - win_rate)) * avg_loss)
        ).quantize(Decimal("0.01"))

        # Max Drawdown from equity curve
        max_dd_amount, max_dd_pct = cls._calculate_drawdown(equity_curve)

        # Trade frequency (per day)
        t_start = start_time or trades[0].entry_timestamp
        t_end = end_time or trades[-1].exit_timestamp
        duration_days = max(1.0 / 24.0, (t_end - t_start).total_seconds() / 86400.0)
        freq_per_day = round(total_trades / duration_days, 2)

        # Friction as percentage of gross profit
        if gross_wins > Decimal("0.00"):
            friction_pct = float((total_friction / gross_wins) * Decimal("100.0"))
        else:
            friction_pct = 0.0

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=round(win_rate, 4),
            gross_pnl=total_gross.quantize(Decimal("0.01")),
            total_friction=total_friction.quantize(Decimal("0.01")),
            net_pnl=total_net.quantize(Decimal("0.01")),
            profit_factor=round(profit_factor, 3),
            expectancy=expectancy,
            average_trade=avg_trade,
            average_win=avg_win,
            average_loss=avg_loss,
            max_drawdown_amount=max_dd_amount,
            max_drawdown_pct=round(max_dd_pct, 4),
            trade_frequency_per_day=freq_per_day,
            friction_pct_of_gross_profit=round(friction_pct, 2),
            regime_pnl=regime_pnl,
            regime_trades=regime_trades,
        )

    @classmethod
    def _calculate_drawdown(cls, equity_curve: list[EquityPoint]) -> tuple[Decimal, float]:
        """Calculate peak-to-trough maximum drawdown amount and percentage."""
        if not equity_curve:
            return Decimal("0.00"), 0.0

        peak = Decimal("0.00")
        max_dd_amount = Decimal("0.00")
        max_dd_pct = 0.0

        for pt in equity_curve:
            peak = max(peak, pt.total_equity)

            dd_amount = peak - pt.total_equity
            max_dd_amount = max(max_dd_amount, dd_amount)

            if peak > Decimal("0.00"):
                dd_pct = float(dd_amount / peak)
                max_dd_pct = max(max_dd_pct, dd_pct)

        return max_dd_amount.quantize(Decimal("0.01")), max_dd_pct

    @classmethod
    def _empty_metrics(cls) -> PerformanceMetrics:
        """Return zeroed metrics when no trades exist."""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            gross_pnl=Decimal("0.00"),
            total_friction=Decimal("0.00"),
            net_pnl=Decimal("0.00"),
            profit_factor=0.0,
            expectancy=Decimal("0.00"),
            average_trade=Decimal("0.00"),
            average_win=Decimal("0.00"),
            average_loss=Decimal("0.00"),
            max_drawdown_amount=Decimal("0.00"),
            max_drawdown_pct=0.0,
            trade_frequency_per_day=0.0,
            friction_pct_of_gross_profit=0.0,
            regime_pnl={},
            regime_trades={},
        )
