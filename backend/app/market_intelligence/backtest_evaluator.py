"""Backtesting and Regime-Conditioned Feature Evaluator.

Performs quantitative backtesting of trading strategies across distinct market regimes,
evaluates performance enhancements from regime filtering and sector tailwinds,
and verifies zero-leakage compliance on event streams.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.models import (
    RegimeBacktestMetric,
    RegimeBacktestSummary,
    TrendRegime,
    VolatilityState,
)
from app.research.leakage_auditor import LeakageAuditor

_PREC_2 = Decimal("0.01")
_PREC_4 = Decimal("0.0001")


@dataclass(slots=True)
class SimulatedTrade:
    """Historical trade record with regime attribution."""

    trade_id: str
    timestamp: datetime
    symbol: str
    trend_regime: TrendRegime
    volatility_state: VolatilityState
    has_sector_tailwind: bool
    pnl: Decimal
    return_pct: Decimal
    is_win: bool


class RegimeBacktestEvaluator:
    """Evaluates strategy performance partitioned across market regimes and filters."""

    @classmethod
    def run_regime_backtest(
        cls,
        trades: Sequence[SimulatedTrade] | None = None,
        bars: Sequence[Bar] | None = None,
    ) -> RegimeBacktestSummary:
        """Executes regime-conditioned backtesting evaluation.

        Args:
            trades: Optional historical simulated trades; if None, standard benchmark dataset is used.
            bars: Optional bars stream to verify leakage on.

        Returns:
            RegimeBacktestSummary comparing baseline vs intelligence-filtered performance.
        """
        sample_trades = list(trades) if trades is not None else cls._generate_standard_evaluation_trades()

        # 1. Leakage Verification
        leakage_passed = True
        if bars:
            report = LeakageAuditor.audit_event_stream(bars)
            if not report.is_leakage_free:
                leakage_passed = False

        trade_audit = LeakageAuditor.audit_event_stream(sample_trades)
        if not trade_audit.is_leakage_free:
            leakage_passed = False

        # 2. Baseline Metrics (All Trades)
        baseline_metric = cls._calculate_performance(sample_trades, "BASELINE")

        # 3. Filtered Trades:
        # Rule: Exclude EXTREME_VOLATILITY_CIRCUIT and require either sector tailwind or trend momentum
        filtered_trades = [
            t
            for t in sample_trades
            if t.volatility_state != VolatilityState.EXTREME_VOLATILITY_CIRCUIT
            and (t.has_sector_tailwind or t.trend_regime == TrendRegime.BULL_MOMENTUM)
        ]

        filtered_metric = cls._calculate_performance(filtered_trades, "INTELLIGENCE_FILTERED")

        # 4. Regime Breakdown
        regime_breakdowns: list[RegimeBacktestMetric] = []
        for regime in TrendRegime:
            r_trades = [t for t in sample_trades if t.trend_regime == regime]
            if r_trades:
                regime_breakdowns.append(cls._calculate_performance(r_trades, regime.value))

        # 5. Improvements
        dd_reduction = Decimal("0.00")
        if baseline_metric.max_drawdown_pct > Decimal("0.00"):
            dd_diff = baseline_metric.max_drawdown_pct - filtered_metric.max_drawdown_pct
            dd_reduction = (dd_diff / baseline_metric.max_drawdown_pct) * Decimal("100.00")

        sharpe_improvement = Decimal("0.00")
        if baseline_metric.sharpe_ratio > Decimal("0.00"):
            sharpe_diff = filtered_metric.sharpe_ratio - baseline_metric.sharpe_ratio
            sharpe_improvement = (sharpe_diff / baseline_metric.sharpe_ratio) * Decimal("100.00")

        return RegimeBacktestSummary(
            backtest_id=f"BKT-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            baseline_trades=baseline_metric.trades_count,
            baseline_win_rate_pct=baseline_metric.win_rate_pct,
            baseline_profit_factor=baseline_metric.profit_factor,
            baseline_sharpe=baseline_metric.sharpe_ratio,
            baseline_max_drawdown_pct=baseline_metric.max_drawdown_pct,
            filtered_trades=filtered_metric.trades_count,
            filtered_win_rate_pct=filtered_metric.win_rate_pct,
            filtered_profit_factor=filtered_metric.profit_factor,
            filtered_sharpe=filtered_metric.sharpe_ratio,
            filtered_max_drawdown_pct=filtered_metric.max_drawdown_pct,
            drawdown_reduction_pct=max(Decimal("0.00"), dd_reduction).quantize(_PREC_2),
            sharpe_improvement_pct=max(Decimal("0.00"), sharpe_improvement).quantize(_PREC_2),
            regime_breakdown=regime_breakdowns,
            leakage_audit_passed=leakage_passed,
        )

    @classmethod
    def _calculate_performance(
        cls,
        trades: Sequence[SimulatedTrade],
        label: str,
    ) -> RegimeBacktestMetric:
        """Calculates quantitative performance metrics for a subset of trades."""
        if not trades:
            return RegimeBacktestMetric(
                regime=label,
                trades_count=0,
                win_rate_pct=Decimal("0.00"),
                profit_factor=Decimal("1.00"),
                sharpe_ratio=Decimal("0.00"),
                max_drawdown_pct=Decimal("0.00"),
                total_pnl=Decimal("0.00"),
            )

        total_trades = len(trades)
        wins = [t for t in trades if t.is_win]
        win_rate = (Decimal(len(wins)) / Decimal(total_trades)) * Decimal("100.00")

        gross_profit = sum((t.pnl for t in trades if t.pnl > Decimal(0)), Decimal(0))
        gross_loss = abs(sum((t.pnl for t in trades if t.pnl < Decimal(0)), Decimal(0)))

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > Decimal(0)
            else (Decimal("9.99") if gross_profit > Decimal(0) else Decimal("1.00"))
        )

        total_pnl = sum((t.pnl for t in trades), Decimal(0))

        # Sharpe ratio calculation over trade returns
        returns = [float(t.return_pct) for t in trades]
        mean_ret = sum(returns) / float(len(returns))
        var = sum((r - mean_ret) ** 2 for r in returns) / float(len(returns))
        std_ret = math.sqrt(var) if var > 0 else 0.0001
        # Annualized Sharpe proxy (sqrt(252 trades/year))
        sharpe = (mean_ret / std_ret) * math.sqrt(min(252, len(returns))) if std_ret > 0 else 0.0

        # Maximum Drawdown calculation
        cumulative: float = 0.0
        peak: float = 0.0
        max_dd: float = 0.0

        for t in trades:
            cumulative += float(t.pnl)
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)

        max_dd_pct = (max_dd / 100.0) * 100.0  # normalized to baseline ₹100 capital

        return RegimeBacktestMetric(
            regime=label,
            trades_count=total_trades,
            win_rate_pct=win_rate.quantize(_PREC_2),
            profit_factor=profit_factor.quantize(_PREC_2),
            sharpe_ratio=Decimal(str(round(sharpe, 2))).quantize(_PREC_2),
            max_drawdown_pct=Decimal(str(round(max_dd_pct, 2))).quantize(_PREC_2),
            total_pnl=total_pnl.quantize(_PREC_2),
        )

    @classmethod
    def _generate_standard_evaluation_trades(cls) -> list[SimulatedTrade]:
        """Generates a standardized, deterministic test harness dataset of 100 trades."""
        import datetime as dt

        trades: list[SimulatedTrade] = []
        base_time = dt.datetime(2026, 9, 1, 9, 15, tzinfo=dt.timezone.utc)

        # 40 BULL_MOMENTUM trades (high win rate 70%)
        for i in range(40):
            ts = base_time + dt.timedelta(minutes=i * 15)
            is_win = (i % 10) not in (3, 7, 9)
            pnl = Decimal("1.80") if is_win else Decimal("-1.10")
            ret = Decimal("1.8") if is_win else Decimal("-1.1")
            trades.append(
                SimulatedTrade(
                    trade_id=f"TRD-BULL-{i:03d}",
                    timestamp=ts,
                    symbol="RELIANCE",
                    trend_regime=TrendRegime.BULL_MOMENTUM,
                    volatility_state=VolatilityState.NORMAL_VOLATILITY,
                    has_sector_tailwind=True,
                    pnl=pnl,
                    return_pct=ret,
                    is_win=is_win,
                )
            )

        # 25 MEAN_REVERTING_RANGE trades (52% win rate)
        for i in range(25):
            ts = base_time + dt.timedelta(minutes=(40 + i) * 15)
            is_win = (i % 2 == 0)
            pnl = Decimal("0.90") if is_win else Decimal("-0.95")
            ret = Decimal("0.9") if is_win else Decimal("-0.95")
            trades.append(
                SimulatedTrade(
                    trade_id=f"TRD-RANGE-{i:03d}",
                    timestamp=ts,
                    symbol="INFY",
                    trend_regime=TrendRegime.MEAN_REVERTING_RANGE,
                    volatility_state=VolatilityState.VOLATILITY_COMPRESSION,
                    has_sector_tailwind=False,
                    pnl=pnl,
                    return_pct=ret,
                    is_win=is_win,
                )
            )

        # 20 NEUTRAL_CHOP / HIGH_VOL trades (40% win rate)
        for i in range(20):
            ts = base_time + dt.timedelta(minutes=(65 + i) * 15)
            is_win = (i % 5 in (0, 2))
            pnl = Decimal("1.10") if is_win else Decimal("-1.40")
            ret = Decimal("1.1") if is_win else Decimal("-1.4")
            trades.append(
                SimulatedTrade(
                    trade_id=f"TRD-CHOP-{i:03d}",
                    timestamp=ts,
                    symbol="TCS",
                    trend_regime=TrendRegime.NEUTRAL_CHOP,
                    volatility_state=VolatilityState.HIGH_VOLATILITY,
                    has_sector_tailwind=False,
                    pnl=pnl,
                    return_pct=ret,
                    is_win=is_win,
                )
            )

        # 15 EXTREME_VOLATILITY trades (20% win rate, severe drawdown)
        for i in range(15):
            ts = base_time + dt.timedelta(minutes=(85 + i) * 15)
            is_win = (i % 5 == 0)
            pnl = Decimal("2.50") if is_win else Decimal("-2.20")
            ret = Decimal("2.5") if is_win else Decimal("-2.2")
            trades.append(
                SimulatedTrade(
                    trade_id=f"TRD-EXTR-{i:03d}",
                    timestamp=ts,
                    symbol="TATAMOTORS",
                    trend_regime=TrendRegime.VOLATILE_BREAKOUT,
                    volatility_state=VolatilityState.EXTREME_VOLATILITY_CIRCUIT,
                    has_sector_tailwind=False,
                    pnl=pnl,
                    return_pct=ret,
                    is_win=is_win,
                )
            )

        return sorted(trades, key=lambda t: t.timestamp)
