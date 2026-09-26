"""Formal data models and contracts for Phase 30 Advanced Market Intelligence.

Defines schemas for:
- Market Regime Classification (Trend, ADX, Moving Average alignment)
- Volatility Regime (ATR percentiles, Squeeze Momentum, Bandwidth)
- Sector Context (Relative Strength, Sector ranking, Sector tailwinds)
- Market Breadth (Advance/Decline, Moving Average participation)
- Point-in-Time Intelligence Snapshot
- Regime-Conditioned Backtesting Evaluation
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TrendRegime(str, Enum):
    """Directional trend classification."""

    BULL_MOMENTUM = "BULL_MOMENTUM"
    BEAR_MOMENTUM = "BEAR_MOMENTUM"
    MEAN_REVERTING_RANGE = "MEAN_REVERTING_RANGE"
    VOLATILE_BREAKOUT = "VOLATILE_BREAKOUT"
    NEUTRAL_CHOP = "NEUTRAL_CHOP"


class VolatilityState(str, Enum):
    """Volatility dispersion classification."""

    VOLATILITY_COMPRESSION = "VOLATILITY_COMPRESSION"
    NORMAL_VOLATILITY = "NORMAL_VOLATILITY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    EXTREME_VOLATILITY_CIRCUIT = "EXTREME_VOLATILITY_CIRCUIT"


class BreadthRegime(str, Enum):
    """Cross-sectional market participation classification."""

    STRONG_EXPANSION = "STRONG_EXPANSION"
    HEALTHY_BULL = "HEALTHY_BULL"
    NEUTRAL_CHURN = "NEUTRAL_CHURN"
    WEAK_BEAR = "WEAK_BEAR"
    STRONG_LIQUIDATION = "STRONG_LIQUIDATION"


class MarketIntelligenceAction(str, Enum):
    """Prescribed strategy adaptation action based on composite market intelligence."""

    FAVOR_TREND_FOLLOWING = "FAVOR_TREND_FOLLOWING"
    FAVOR_MEAN_REVERSION = "FAVOR_MEAN_REVERSION"
    FAVOR_VOLATILITY_BREAKOUT = "FAVOR_VOLATILITY_BREAKOUT"
    DEFENSIVE_REDUCE_SIZE = "DEFENSIVE_REDUCE_SIZE"
    HALT_NEW_POSITIONS = "HALT_NEW_POSITIONS"


class RegimeClassification(BaseModel):
    """Point-in-time trend and directional regime classification."""

    trend_regime: TrendRegime
    adx: Decimal = Field(..., description="Average Directional Index (14-period)")
    plus_di: Decimal = Field(..., description="Positive Directional Indicator (+DI)")
    minus_di: Decimal = Field(..., description="Negative Directional Indicator (-DI)")
    trend_strength: Decimal = Field(..., description="Normalized trend strength score (0-100)")
    ema_alignment: str = Field(..., description="EMA stack: BULLISH_STACK, BEARISH_STACK, or TANGLED")
    details: str = Field(..., description="Human-readable regime explanation")


class VolatilityClassification(BaseModel):
    """Point-in-time volatility and dispersion state."""

    volatility_state: VolatilityState
    atr: Decimal = Field(..., description="Average True Range (14-period)")
    atr_percentile: Decimal = Field(..., description="ATR historical percentile over lookback window (0-100)")
    bollinger_bandwidth: Decimal = Field(..., description="Normalized Bollinger Bandwidth ((Upper - Lower) / SMA)")
    is_squeeze: bool = Field(..., description="True if Bollinger Bands are inside Keltner Channels")
    risk_multiplier: Decimal = Field(..., description="Suggested capital risk multiplier (0.0 to 1.0)")
    details: str = Field(..., description="Human-readable volatility explanation")


class SectorPerformance(BaseModel):
    """Individual sector benchmark performance metrics."""

    sector_name: str
    relative_strength: Decimal = Field(..., description="Mansfield Relative Strength vs broad index")
    momentum_score: Decimal = Field(..., description="Short-term sector momentum score")
    is_leader: bool = Field(..., description="True if sector is ranked in top 33%")
    trend: str = Field(..., description="BULLISH, BEARISH, or NEUTRAL")


class SectorContextSummary(BaseModel):
    """Sector context relative to individual asset."""

    symbol: str
    assigned_sector: str
    sector_relative_strength: Decimal = Field(..., description="Asset's Mansfield RS vs sector benchmark")
    sector_trend: str = Field(..., description="Assigned sector's trend (BULLISH/BEARISH/NEUTRAL)")
    has_sector_tailwind: bool = Field(..., description="True if asset direction aligns with sector leadership")
    sector_rankings: list[SectorPerformance] = Field(default_factory=list)


class MarketBreadthSummary(BaseModel):
    """Cross-sectional market breadth metrics."""

    breadth_regime: BreadthRegime
    advancing_count: int
    declining_count: int
    unchanged_count: int
    ad_ratio: Decimal = Field(..., description="Advance/Decline ratio")
    pct_above_20_ma: Decimal = Field(..., description="Percentage of tracked universe above 20 EMA (0-100)")
    pct_above_50_ma: Decimal = Field(..., description="Percentage of tracked universe above 50 SMA (0-100)")
    breadth_thrust_active: bool = Field(..., description="True if acute breadth thrust detected")


class AdvancedMarketIntelligenceSnapshot(BaseModel):
    """Unified composite market intelligence snapshot evaluated point-in-time."""

    snapshot_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    regime: RegimeClassification
    volatility: VolatilityClassification
    sector_context: SectorContextSummary
    breadth: MarketBreadthSummary
    recommended_action: MarketIntelligenceAction
    suggested_size_multiplier: Decimal = Field(..., description="Composite position size multiplier (0.0 to 1.0)")
    is_trade_allowed: bool = Field(..., description="False if extreme volatility or adverse breadth warrants circuit halt")
    leakage_free: bool = Field(default=True, description="Strictly verified zero-lookahead compliance")


class RegimeBacktestMetric(BaseModel):
    """Backtest performance breakdown per market regime."""

    regime: str
    trades_count: int
    win_rate_pct: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    total_pnl: Decimal


class RegimeBacktestSummary(BaseModel):
    """Backtesting validation comparing baseline vs regime-conditioned intelligence."""

    backtest_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    baseline_trades: int
    baseline_win_rate_pct: Decimal
    baseline_profit_factor: Decimal
    baseline_sharpe: Decimal
    baseline_max_drawdown_pct: Decimal
    filtered_trades: int
    filtered_win_rate_pct: Decimal
    filtered_profit_factor: Decimal
    filtered_sharpe: Decimal
    filtered_max_drawdown_pct: Decimal
    drawdown_reduction_pct: Decimal
    sharpe_improvement_pct: Decimal
    regime_breakdown: list[RegimeBacktestMetric] = Field(default_factory=list)
    leakage_audit_passed: bool = True
