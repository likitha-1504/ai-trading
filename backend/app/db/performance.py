"""Performance aggregation, P/L analytics, strategy-level metrics, and latency tracking."""

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.db.connection import get_connection
from app.models.contracts import StrategyType, TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class AggregatedPerformanceMetrics:
    """Comprehensive performance snapshot calculated across historical and paper trades."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate_pct: float
    total_gross_pnl: Decimal
    total_friction: Decimal
    total_net_pnl: Decimal
    profit_factor: float
    expectancy: Decimal
    max_drawdown_amount: Decimal
    max_drawdown_pct: float
    average_trade_net: Decimal
    average_holding_duration_seconds: float
    friction_pct_of_gross: float


class PerformanceAggregator:
    """Computes financial KPIs, strategy-level stratification, and telemetry latencies."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    # =========================================================================
    # 1. Portfolio-Wide P/L & KPI Aggregation
    # =========================================================================

    def calculate_metrics(
        self, trades: list[TradeRecord] | None = None
    ) -> AggregatedPerformanceMetrics:
        """Compute performance metrics from a list of TradeRecords or database."""
        trade_list = trades if trades is not None else self._load_trades_from_db()

        if not trade_list:
            return AggregatedPerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate_pct=0.0,
                total_gross_pnl=Decimal("0.00"),
                total_friction=Decimal("0.00"),
                total_net_pnl=Decimal("0.00"),
                profit_factor=0.0,
                expectancy=Decimal("0.00"),
                max_drawdown_amount=Decimal("0.00"),
                max_drawdown_pct=0.0,
                average_trade_net=Decimal("0.00"),
                average_holding_duration_seconds=0.0,
                friction_pct_of_gross=0.0,
            )

        total_trades = len(trade_list)
        wins = [t for t in trade_list if t.net_pnl > Decimal("0.00")]
        losses = [t for t in trade_list if t.net_pnl < Decimal("0.00")]
        breakevens = [t for t in trade_list if t.net_pnl == Decimal("0.00")]

        winning_trades = len(wins)
        losing_trades = len(losses)
        breakeven_trades = len(breakevens)
        win_rate = round((winning_trades / total_trades) * 100, 2)

        total_gross = sum((t.gross_pnl for t in trade_list), Decimal("0.00"))
        total_friction = sum(
            (t.friction.total_friction for t in trade_list), Decimal("0.00")
        )
        total_net = sum((t.net_pnl for t in trade_list), Decimal("0.00"))

        gross_profits = sum((t.net_pnl for t in wins), Decimal("0.00"))
        gross_losses = abs(sum((t.net_pnl for t in losses), Decimal("0.00")))
        profit_factor = (
            round(float(gross_profits / gross_losses), 2)
            if gross_losses > Decimal("0.00")
            else (999.0 if gross_profits > Decimal("0.00") else 0.0)
        )

        avg_win = (
            (gross_profits / Decimal(winning_trades))
            if winning_trades > 0
            else Decimal("0.00")
        )
        avg_loss = (
            (gross_losses / Decimal(losing_trades))
            if losing_trades > 0
            else Decimal("0.00")
        )
        win_prob = Decimal(str(win_rate / 100.0))
        loss_prob = Decimal(str((100.0 - win_rate) / 100.0))
        expectancy = ((win_prob * avg_win) - (loss_prob * avg_loss)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Max Drawdown computation over cumulative net equity curve
        cum_pnl = Decimal("0.00")
        peak = Decimal("0.00")
        max_dd = Decimal("0.00")
        for t in trade_list:
            cum_pnl += t.net_pnl
            peak = max(peak, cum_pnl)
            dd = peak - cum_pnl
            max_dd = max(max_dd, dd)

        starting_cap = Decimal("100.00")
        max_dd_pct = (
            round(float((max_dd / (starting_cap + peak)) * 100), 2)
            if (starting_cap + peak) > Decimal("0.00")
            else 0.0
        )

        avg_trade = (total_net / Decimal(total_trades)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        durations = [t.holding_duration_seconds for t in trade_list]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

        friction_ratio = (
            round(float((total_friction / abs(total_gross)) * 100), 2)
            if total_gross != Decimal("0.00")
            else 0.0
        )

        return AggregatedPerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            win_rate_pct=win_rate,
            total_gross_pnl=total_gross,
            total_friction=total_friction,
            total_net_pnl=total_net,
            profit_factor=profit_factor,
            expectancy=expectancy,
            max_drawdown_amount=max_dd,
            max_drawdown_pct=max_dd_pct,
            average_trade_net=avg_trade,
            average_holding_duration_seconds=avg_duration,
            friction_pct_of_gross=friction_ratio,
        )

    # =========================================================================
    # 2. Strategy-Level Metrics Stratification
    # =========================================================================

    def calculate_strategy_metrics(
        self, trades: list[TradeRecord] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Stratify performance metrics by strategy type."""
        trade_list = trades if trades is not None else self._load_trades_from_db()
        results: dict[str, dict[str, Any]] = {}

        for strat in StrategyType:
            strat_trades = [t for t in trade_list if t.strategy == strat]
            if not strat_trades:
                results[strat.value] = {
                    "total_trades": 0,
                    "win_rate_pct": 0.0,
                    "gross_pnl": "0.00",
                    "friction": "0.00",
                    "net_pnl": "0.00",
                    "profit_factor": 0.0,
                    "expectancy": "0.00",
                }
                continue

            metrics = self.calculate_metrics(strat_trades)
            results[strat.value] = {
                "total_trades": metrics.total_trades,
                "win_rate_pct": metrics.win_rate_pct,
                "gross_pnl": str(metrics.total_gross_pnl),
                "friction": str(metrics.total_friction),
                "net_pnl": str(metrics.total_net_pnl),
                "profit_factor": metrics.profit_factor,
                "expectancy": str(metrics.expectancy),
            }

        return results

    # =========================================================================
    # 3. Model Latency Metrics
    # =========================================================================

    def get_model_latency_metrics(self) -> dict[str, Any]:
        """Aggregate AI model latency, tokens, and error metrics from database."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT
                    model_name,
                    COUNT(*) as total_calls,
                    SUM(success) as successful_calls,
                    SUM(is_fallback) as fallback_calls,
                    AVG(latency_ms) as avg_latency_ms,
                    MIN(latency_ms) as min_latency_ms,
                    MAX(latency_ms) as max_latency_ms,
                    SUM(COALESCE(token_count, 0)) as total_tokens
                FROM model_calls
                GROUP BY model_name
                """
            )
            rows = cur.fetchall()

        summary: dict[str, Any] = {}
        for r in rows:
            m_name = r["model_name"]
            total = r["total_calls"]
            succ = r["successful_calls"] or 0
            fallbacks = r["fallback_calls"] or 0
            avg_lat = round(r["avg_latency_ms"] or 0.0, 1)

            # Compute p95 latency
            p95 = self._compute_model_p95(m_name)

            summary[m_name] = {
                "total_calls": total,
                "successful_calls": succ,
                "fallback_calls": fallbacks,
                "success_rate_pct": round((succ / total) * 100, 2) if total > 0 else 0.0,
                "avg_latency_ms": avg_lat,
                "p95_latency_ms": p95,
                "min_latency_ms": r["min_latency_ms"] or 0,
                "max_latency_ms": r["max_latency_ms"] or 0,
                "total_tokens": r["total_tokens"] or 0,
            }

        return summary

    def _compute_model_p95(self, model_name: str) -> float:
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT latency_ms FROM model_calls WHERE model_name = ? ORDER BY latency_ms ASC",
                (model_name,),
            )
            latencies = [row[0] for row in cur.fetchall()]
        if not latencies:
            return 0.0
        idx = int(len(latencies) * 0.95)
        return float(latencies[min(idx, len(latencies) - 1)])

    # =========================================================================
    # 4. Execution Latency & Fill Metrics
    # =========================================================================

    def get_execution_latency_metrics(self) -> dict[str, Any]:
        """Aggregate order submission, ACK, and fill latencies."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_orders,
                    SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_orders,
                    AVG(average_fill_price) as avg_price
                FROM orders
                """
            )
            r = cur.fetchone()

        total = r["total_orders"] if r else 0
        filled = r["filled_orders"] if r else 0
        rejected = r["rejected_orders"] if r else 0

        return {
            "total_orders": total,
            "filled_orders": filled,
            "rejected_orders": rejected,
            "fill_rate_pct": round((filled / total) * 100, 2) if total > 0 else 0.0,
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def _load_trades_from_db(self) -> list[TradeRecord]:
        from app.db.repository import DatabaseRepository

        repo = DatabaseRepository(db_path=self.db_path)
        return repo.get_trades(limit=1000)
