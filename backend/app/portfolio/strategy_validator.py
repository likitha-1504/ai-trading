"""Independent Strategy Validator for Phase 31 Multi-Strategy Portfolio.

Enforces the core rule: 'Add strategy allocation only after independent validation'.
Evaluates candidate strategies across minimum trade counts, win rate hurdles,
profit factor floors, Sharpe ratios, and max drawdown limits before permitting capital allocation.
"""

from __future__ import annotations

from decimal import Decimal

from app.models.contracts import StrategyType
from app.portfolio.models import (
    StrategyValidationReport,
    StrategyValidationStatus,
)

_PREC_2 = Decimal("0.01")


class StrategyValidator:
    """Evaluates individual quantitative trading strategies for independent validation."""

    # Validation criteria thresholds
    MIN_TRADES: int = 15
    MIN_WIN_RATE_PCT: Decimal = Decimal("50.00")
    MIN_PROFIT_FACTOR: Decimal = Decimal("1.20")
    MIN_SHARPE_RATIO: Decimal = Decimal("0.50")
    MAX_DRAWDOWN_PCT: Decimal = Decimal("20.00")

    @classmethod
    def validate_strategy(
        cls,
        strategy_type: StrategyType,
        trades_count: int,
        win_rate_pct: Decimal,
        profit_factor: Decimal,
        sharpe_ratio: Decimal,
        max_drawdown_pct: Decimal,
    ) -> StrategyValidationReport:
        """Evaluates strategy metrics against strict independent validation gates.

        Args:
            strategy_type: The StrategyType being audited.
            trades_count: Total closed trades in the validation sample.
            win_rate_pct: Realized win rate percentage (0 - 100).
            profit_factor: Gross profit / Gross loss ratio.
            sharpe_ratio: Annualized or per-trade Sharpe ratio.
            max_drawdown_pct: Maximum peak-to-trough equity drawdown percentage.

        Returns:
            StrategyValidationReport.
        """
        rejection_reasons: list[str] = []

        if trades_count < cls.MIN_TRADES:
            rejection_reasons.append(
                f"Sample size insufficient: {trades_count} trades < required {cls.MIN_TRADES} trades."
            )

        if win_rate_pct < cls.MIN_WIN_RATE_PCT:
            rejection_reasons.append(
                f"Win rate below threshold: {win_rate_pct:.1f}% < required {cls.MIN_WIN_RATE_PCT:.1f}%."
            )

        if profit_factor < cls.MIN_PROFIT_FACTOR:
            rejection_reasons.append(
                f"Profit factor below hurdle: {profit_factor:.2f} < required {cls.MIN_PROFIT_FACTOR:.2f}."
            )

        if sharpe_ratio < cls.MIN_SHARPE_RATIO:
            rejection_reasons.append(
                f"Sharpe ratio below hurdle: {sharpe_ratio:.2f} < required {cls.MIN_SHARPE_RATIO:.2f}."
            )

        if max_drawdown_pct > cls.MAX_DRAWDOWN_PCT:
            rejection_reasons.append(
                f"Drawdown exceeds tolerance: {max_drawdown_pct:.1f}% > allowed {cls.MAX_DRAWDOWN_PCT:.1f}%."
            )

        if not rejection_reasons:
            status = StrategyValidationStatus.VALIDATED
            is_valid = True
            details = f"Strategy {strategy_type.value} passed all independent validation hurdles and is eligible for portfolio capital allocation."
        elif trades_count < cls.MIN_TRADES and len(rejection_reasons) == 1:
            status = StrategyValidationStatus.PROBATION
            is_valid = False
            details = f"Strategy {strategy_type.value} in probation status awaiting additional trade samples."
        else:
            status = StrategyValidationStatus.DISQUALIFIED
            is_valid = False
            details = f"Strategy {strategy_type.value} rejected due to: {'; '.join(rejection_reasons)}."

        return StrategyValidationReport(
            strategy_type=strategy_type,
            status=status,
            trades_count=trades_count,
            win_rate_pct=win_rate_pct.quantize(_PREC_2),
            profit_factor=profit_factor.quantize(_PREC_2),
            sharpe_ratio=sharpe_ratio.quantize(_PREC_2),
            max_drawdown_pct=max_drawdown_pct.quantize(_PREC_2),
            is_validated=is_valid,
            rejection_reasons=rejection_reasons,
            details=details,
        )
