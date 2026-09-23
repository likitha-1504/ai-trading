"""Account capital state tracking and balance management.

Maintains total capital, available cash, deployed margin, realized and unrealized P/L,
buying power, daily drawdown, high-water mark, and position concentrations.
"""

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.capital.config import CapitalConfig
from app.models.contracts import CapitalSnapshot, PositionSnapshot, PositionStatus

logger = logging.getLogger(__name__)


class CapitalManager:
    """Manages account equity, cash reserves, margin allocation, and telemetry."""

    def __init__(self, config: CapitalConfig | None = None) -> None:
        self.config = config or CapitalConfig()

        self.available_capital: Decimal = self.config.starting_capital
        self.deployed_capital: Decimal = Decimal("0.00")
        self.realized_pnl: Decimal = Decimal("0.00")
        self.unrealized_pnl: Decimal = Decimal("0.00")

        self.daily_baseline_capital: Decimal = self.config.starting_capital
        self.high_water_mark: Decimal = self.config.starting_capital

        # Active position capital allocations: position_id -> allocated_amount
        self._allocations: dict[str, Decimal] = {}
        # Symbol to allocated capital for concentration tracking
        self._symbol_allocations: dict[str, Decimal] = {}

    @property
    def total_capital(self) -> Decimal:
        """Current account equity: cash + deployed capital + floating P/L."""
        return (
            self.available_capital + self.deployed_capital + self.unrealized_pnl
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def buying_power(self) -> Decimal:
        """Total purchasing power based on available cash and leverage multiplier."""
        return (self.available_capital * self.config.leverage_multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def deposit(self, amount: Decimal) -> None:
        """Deposit funds into account equity."""
        if amount <= Decimal("0.00"):
            raise ValueError(f"Deposit amount must be positive, got {amount}")
        self.available_capital += amount
        self.high_water_mark = max(self.high_water_mark, self.total_capital)
        logger.info(
            "Deposited %s INR. Available capital now %s INR",
            amount,
            self.available_capital,
        )

    def withdraw(self, amount: Decimal) -> bool:
        """Withdraw unencumbered cash from available capital."""
        if amount <= Decimal("0.00"):
            raise ValueError(f"Withdrawal amount must be positive, got {amount}")
        if amount > self.available_capital:
            logger.warning(
                "Withdrawal rejected: requested %s exceeds available cash %s",
                amount,
                self.available_capital,
            )
            return False

        self.available_capital -= amount
        logger.info(
            "Withdrew %s INR. Available capital now %s INR",
            amount,
            self.available_capital,
        )
        return True

    def allocate_capital(
        self, position_id: str, symbol: str, quantity: int, price: Decimal
    ) -> bool:
        """Reserve capital required to open an equity position."""
        required = (Decimal(quantity) * price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if required > self.buying_power:
            logger.warning(
                "Capital allocation failed for %s: required %s > buying power %s",
                symbol,
                required,
                self.buying_power,
            )
            return False

        self.available_capital -= required
        self.deployed_capital += required
        self._allocations[position_id] = required

        sym_key = symbol.upper()
        self._symbol_allocations[sym_key] = (
            self._symbol_allocations.get(sym_key, Decimal("0.00")) + required
        )

        logger.info(
            "Allocated %s INR for %s (pos: %s). Available cash: %s",
            required,
            sym_key,
            position_id,
            self.available_capital,
        )
        return True

    def release_capital(
        self,
        position_id: str,
        symbol: str,
        quantity: int,
        exit_price: Decimal,
        gross_realized_pnl: Decimal,
        friction: Decimal,
    ) -> None:
        """Release capital upon position closure, settling net realized P/L."""
        allocated = self._allocations.pop(
            position_id,
            (Decimal(quantity) * exit_price).quantize(Decimal("0.01")),
        )
        self.deployed_capital = max(Decimal("0.00"), self.deployed_capital - allocated)

        sym_key = symbol.upper()
        if sym_key in self._symbol_allocations:
            self._symbol_allocations[sym_key] = max(
                Decimal("0.00"), self._symbol_allocations[sym_key] - allocated
            )
            if self._symbol_allocations[sym_key] == Decimal("0.00"):
                del self._symbol_allocations[sym_key]

        net_pnl = gross_realized_pnl - friction
        self.realized_pnl += net_pnl
        # Return principal + net P/L to available cash
        self.available_capital += allocated + net_pnl

        self.high_water_mark = max(self.high_water_mark, self.total_capital)

        logger.info(
            "Released %s INR for %s (pos: %s) with net PnL %s INR. Available cash: %s",
            allocated,
            sym_key,
            position_id,
            net_pnl,
            self.available_capital,
        )

    def update_unrealized_pnl(self, positions: list[PositionSnapshot]) -> None:
        """Recalculate floating P/L across all currently open positions."""
        open_positions = [p for p in positions if p.status == PositionStatus.OPEN]
        self.unrealized_pnl = sum(
            (p.unrealized_pnl for p in open_positions), Decimal("0.00")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self.high_water_mark = max(self.high_water_mark, self.total_capital)

    def get_daily_drawdown(self) -> tuple[Decimal, Decimal]:
        """Compute daily drawdown in currency amount and percentage from daily baseline.

        Returns:
            tuple[Decimal, Decimal]: (drawdown_amount, drawdown_pct)
        """
        if self.daily_baseline_capital <= Decimal("0.00"):
            return Decimal("0.00"), Decimal("0.00")

        # Total P&L today = realized_pnl + unrealized_pnl
        today_pnl = self.realized_pnl + self.unrealized_pnl
        if today_pnl < Decimal("0.00"):
            drawdown_amt = (-today_pnl).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            drawdown_pct = (drawdown_amt / self.daily_baseline_capital).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            return drawdown_amt, drawdown_pct

        return Decimal("0.00"), Decimal("0.00")

    def get_position_concentration(self, symbol: str) -> Decimal:
        """Calculate fraction of total capital allocated to a given symbol."""
        if self.total_capital <= Decimal("0.00"):
            return Decimal("0.00")
        allocated = self._symbol_allocations.get(symbol.upper(), Decimal("0.00"))
        return (allocated / self.total_capital).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    def reset_daily_baseline(self) -> None:
        """Reset the baseline equity for a new trading day."""
        self.daily_baseline_capital = self.total_capital
        self.realized_pnl = Decimal("0.00")
        logger.info(
            "Reset daily baseline equity to %s INR", self.daily_baseline_capital
        )

    def get_capital_snapshot(
        self, timestamp: datetime | None = None
    ) -> CapitalSnapshot:
        """Generate a complete telemetry snapshot of account capital state."""
        ts = timestamp or datetime.now(timezone.utc)
        dd_amt, dd_pct = self.get_daily_drawdown()
        return CapitalSnapshot(
            timestamp=ts,
            total_capital=self.total_capital,
            available_capital=self.available_capital.quantize(Decimal("0.01")),
            deployed_capital=self.deployed_capital.quantize(Decimal("0.01")),
            buying_power=self.buying_power,
            realized_pnl=self.realized_pnl.quantize(Decimal("0.01")),
            unrealized_pnl=self.unrealized_pnl.quantize(Decimal("0.01")),
            daily_drawdown_amount=dd_amt,
            daily_drawdown_pct=dd_pct,
            high_water_mark=self.high_water_mark.quantize(Decimal("0.01")),
            currency=self.config.currency,
        )
