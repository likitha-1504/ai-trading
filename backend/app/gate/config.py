"""Configuration settings for Deterministic Trade Gate."""

from decimal import Decimal

from pydantic import BaseModel, Field


class TradeGateConfig(BaseModel):
    """Thresholds and operational parameters for the Deterministic Trade Gate."""

    # Candidate gate thresholds
    max_tolerable_spread_pct: Decimal = Field(
        default=Decimal("0.0015"), description="Max 15 bps spread"
    )
    min_tolerable_liquidity: Decimal = Field(
        default=Decimal("70.0"), description="Min liquidity score"
    )
    market_close_cutoff_time: str = Field(
        default="15:15", description="Intraday market cut-off (IST)"
    )

    # AI Council hurdles
    min_qwen_confidence: Decimal = Field(
        default=Decimal("0.60"), description="Minimum Qwen3 confidence hurdle"
    )

    # Capital & Execution autonomy ceilings
    autonomous_threshold: Decimal = Field(
        default=Decimal("300.00"),
        description="Max INR value executed autonomously; higher amounts require manual approval",
    )
    max_capital_allocation: Decimal = Field(
        default=Decimal("100.00"),
        description="Initial micro-capital baseline cap per trade",
    )
    max_loss_per_trade_pct: Decimal = Field(
        default=Decimal("0.015"),
        description="Max risk budget per trade: 1.5% of equity",
    )
    max_daily_drawdown_pct: Decimal = Field(
        default=Decimal("0.03"),
        description="Daily drawdown circuit breaker: 3% of capital",
    )
    max_active_positions: int = Field(
        default=2,
        description="Maximum concurrent active positions",
    )
    hurdle_rate: Decimal = Field(
        default=Decimal("0.00"),
        description="Minimum net edge required after all Indian friction fees",
    )
