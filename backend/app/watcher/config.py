"""Configuration thresholds for the Independent Position Watcher and SELL Engine.

Eliminates magic numbers by formalizing all risk bounds, timeouts,
trailing rules, circuit breakers, and emergency liquidation limits.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class WatcherConfig(BaseModel):
    """Configuration settings for Position Watcher and risk intervention triggers."""

    # Stale data & timeouts
    stale_quote_timeout_seconds: float = Field(
        default=15.0,
        description="Max allowed seconds without quotes before emergency exit",
    )
    max_holding_seconds: int = Field(
        default=3600,
        description="Max allowed trade duration in seconds before time expiry",
    )
    auto_square_off_time_ist: str = Field(
        default="15:15", description="Daily intraday square-off time in IST (HH:MM)"
    )

    # Catastrophic protection
    catastrophic_spread_pct: Decimal = Field(
        default=Decimal("0.0050"),
        description="Catastrophic spread % threshold (50 bps)",
    )
    catastrophic_liquidity_threshold: Decimal = Field(
        default=Decimal("15.0"),
        description="Catastrophic minimum liquidity score threshold",
    )
    spread_widening_threshold: Decimal = Field(
        default=Decimal("0.0025"),
        description="Defensive exit spread threshold (25 bps)",
    )

    # Daily circuit breaker
    capital_base: Decimal = Field(
        default=Decimal("100.00"),
        description="Baseline equity in INR for drawdown limits",
    )
    max_daily_drawdown_pct: Decimal = Field(
        default=Decimal("0.030"),
        description="Max daily drawdown limit (3.0% of equity)",
    )

    # Trailing stop & Profit taking
    trailing_activation_multiple: Decimal = Field(
        default=Decimal("1.5"),
        description="R-multiple required to activate trailing stop (1.5R)",
    )
    trailing_distance_multiple: Decimal = Field(
        default=Decimal("1.0"),
        description="Trailing distance in R-multiples behind peak price",
    )

    # Technical deterioration limits
    momentum_deterioration_threshold: Decimal = Field(
        default=Decimal("-0.50"),
        description="Momentum ROC % threshold indicating trend breakdown",
    )
    price_deceleration_threshold: Decimal = Field(
        default=Decimal("-1.00"),
        description="Price acceleration % threshold indicating sharp exhaustion",
    )
