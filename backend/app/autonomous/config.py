"""Phase 21: Configuration and Safety Parameters for ₹300 Autonomous Mode.

Enforces Phase 21 requirements:
- Autonomous operation only up to the configured ₹300 threshold.
- Capital caps: ₹300.00.
- Strict prohibition of silent threshold elevation.
- Deterministic risk limits: 1.5% max risk per trade, 3.0% daily drawdown circuit breaker.
"""

from dataclasses import dataclass
from decimal import Decimal


class AutonomousModeSecurityError(RuntimeError):
    """Raised when an operation violates Phase 21 autonomous mode safety rules."""


@dataclass
class AutonomousModeConfig:
    """Configuration for Phase 21 ₹300 Autonomous Mode."""

    capital_limit: Decimal = Decimal("300.00")
    autonomous_threshold: Decimal = Decimal("300.00")
    max_loss_per_trade_pct: Decimal = Decimal("0.015")  # 1.5%
    max_daily_drawdown_pct: Decimal = Decimal("0.030")  # 3.0%
    max_active_positions: int = 2
    strategy_version: str = "v1.0.0-phase21"
    db_path: str = "autonomous_trading.db"
    num_sessions: int = 5
    tick_size: Decimal = Decimal("0.05")

    def validate(self) -> None:
        """Validate strict Phase 21 invariants.
        
        PDF Rule: Above ₹300, require explicit human approval. Do not silently raise the threshold.
        """
        if self.autonomous_threshold > Decimal("300.00"):
            raise AutonomousModeSecurityError(
                f"Autonomous threshold ₹{self.autonomous_threshold} exceeds ₹300.00 limit. "
                "Silent elevation of autonomous ceiling is strictly prohibited."
            )
        if self.capital_limit > Decimal("300.00"):
            raise AutonomousModeSecurityError(
                f"Autonomous capital limit ₹{self.capital_limit} exceeds ₹300.00 limit. "
                "Capital above ₹300 requires explicit human approval."
            )
        if self.max_daily_drawdown_pct > Decimal("0.030"):
            raise AutonomousModeSecurityError(
                f"Daily drawdown circuit breaker {float(self.max_daily_drawdown_pct)*100:.1f}% "
                "cannot exceed 3.0% safety boundary."
            )
        if self.max_loss_per_trade_pct > Decimal("0.015"):
            raise AutonomousModeSecurityError(
                f"Per-trade risk limit {float(self.max_loss_per_trade_pct)*100:.1f}% "
                "cannot exceed 1.5% safety boundary."
            )
