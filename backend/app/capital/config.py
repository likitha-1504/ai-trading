"""Configuration models for Capital, Risk, and Cost Engine.

Enforces zero magic numbers by formalizing all transaction fee rates,
capital parameters, risk thresholds, circuit breakers, and autonomy limits.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class CostModelConfig(BaseModel):
    """Configuration for Indian market transaction costs, statutory levies, and friction."""

    # Brokerage configuration (percentage rate and flat cap per order)
    brokerage_rate: Decimal = Field(
        default=Decimal("0.0003"),
        description="Brokerage fee rate (default 0.03% or 3 bps)",
    )
    brokerage_flat_cap: Decimal = Field(
        default=Decimal("20.00"),
        description="Maximum brokerage fee cap per order leg in INR (default ₹20.00)",
    )

    # Statutory charges: STT (Securities Transaction Tax)
    stt_intraday_rate: Decimal = Field(
        default=Decimal("0.00025"),
        description="STT rate on equity intraday sell leg turnover (0.025%)",
    )
    stt_delivery_rate: Decimal = Field(
        default=Decimal("0.0010"),
        description="STT rate on equity delivery buy and sell turnover (0.10%)",
    )

    # Exchange transaction charges (NSE equity cash turnover charge)
    exchange_txn_charge_rate: Decimal = Field(
        default=Decimal("0.0000345"),
        description="Exchange transaction charge rate (NSE equity cash 0.00345%)",
    )

    # Regulatory: SEBI turnover charges
    sebi_turnover_charge_rate: Decimal = Field(
        default=Decimal("0.000001"),
        description="SEBI turnover charge rate (₹10 per crore = 0.0001%)",
    )

    # State Stamp Duty (charged strictly on BUY leg)
    stamp_duty_intraday_rate: Decimal = Field(
        default=Decimal("0.00003"),
        description="Stamp duty rate on buy leg for intraday (0.003%)",
    )
    stamp_duty_delivery_rate: Decimal = Field(
        default=Decimal("0.00015"),
        description="Stamp duty rate on buy leg for delivery (0.015%)",
    )

    # Goods and Services Tax (GST: 18% on Brokerage + Exchange + SEBI)
    gst_rate: Decimal = Field(
        default=Decimal("0.18"),
        description="GST rate applied to brokerage, exchange, and SEBI charges (18%)",
    )

    # Slippage modeling
    slippage_ticks: int = Field(
        default=1,
        description="Estimated slippage in ticks per transaction leg (default 1 tick entry + 1 tick exit)",
    )
    tick_size: Decimal = Field(
        default=Decimal("0.05"),
        description="Minimum price tick size in INR (default ₹0.05)",
    )

    # Trade mode
    is_intraday: bool = Field(
        default=True,
        description="True for intraday equity rules; False for delivery equity rules",
    )


class RiskLimitsConfig(BaseModel):
    """Configuration for portfolio risk limits, drawdown caps, and trade gating."""

    max_loss_per_trade_pct: Decimal = Field(
        default=Decimal("0.015"),
        description="Maximum permissible loss per trade as a fraction of current equity (1.5%)",
    )
    max_daily_drawdown_pct: Decimal = Field(
        default=Decimal("0.030"),
        description="Maximum daily drawdown limit before circuit breaker trips (3.0% of baseline equity)",
    )
    max_active_positions: int = Field(
        default=2,
        description="Maximum concurrent active positions allowed in portfolio",
    )
    max_position_concentration_pct: Decimal = Field(
        default=Decimal("0.50"),
        description="Maximum capital concentration in a single position (50% of equity)",
    )
    min_economical_trade_size: Decimal = Field(
        default=Decimal("10.00"),
        description="Minimum order notional value in INR required for economical feasibility (₹10.00)",
    )
    min_expected_net_edge: Decimal = Field(
        default=Decimal("0.05"),
        description="Minimum expected net profit in INR after all friction (hurdle rate ₹0.05)",
    )
    default_win_probability: Decimal = Field(
        default=Decimal("0.55"),
        description="Baseline win probability estimate for quantitative setups (55%)",
    )


class CapitalConfig(BaseModel):
    """Configuration for capital allocation, buying power, and autonomy ceilings."""

    starting_capital: Decimal = Field(
        default=Decimal("100.00"),
        description="Initial sandbox/live micro-capital base in INR (₹100.00)",
    )
    autonomous_threshold: Decimal = Field(
        default=Decimal("300.00"),
        description="Autonomous execution threshold in INR (₹300.00). Allocations above require human approval",
    )
    leverage_multiplier: Decimal = Field(
        default=Decimal("1.0"),
        description="Buying power multiplier (1.0 = cash only without leverage)",
    )
    currency: str = Field(
        default="INR",
        description="Base currency for accounting and clearing",
    )
