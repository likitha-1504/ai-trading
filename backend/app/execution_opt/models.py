"""Formal data models and contracts for Phase 32 Execution Optimization.

Defines schemas for:
- Slippage and Market Impact Modeling
- Liquidity-Aware Sizing Recommendations
- Execution Timing and Urgency Scheduling
- Latency Profiling and Telemetry
- Paper Execution Validation Study Metrics
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionUrgency(str, Enum):
    """Urgency schedule determining order placement aggression."""

    AGGRESSIVE = "AGGRESSIVE"          # Market order at touch/crossing spread
    PASSIVE_PEG = "PASSIVE_PEG"        # Limit order posted at bid/ask touch
    LIQUIDITY_SEEKING = "LIQUIDITY_SEEKING"  # Sliced participation to minimize impact


class TimeOfDayRegime(str, Enum):
    """Intraday market hours regime affecting execution behavior."""

    OPENING_AUCTION_RUSH = "OPENING_AUCTION_RUSH"    # 09:15 - 09:45 (High volatility, wide spreads)
    MORNING_TREND = "MORNING_TREND"                  # 09:45 - 11:30 (Institutional momentum)
    MIDDAY_CONSOLIDATION = "MIDDAY_CONSOLIDATION"    # 11:30 - 13:30 (Low volume, thin book)
    AFTERNOON_SESSION = "AFTERNOON_SESSION"          # 13:30 - 15:00 (Renewed volume expansion)
    INTRADAY_CUTOFF_RISK = "INTRADAY_CUTOFF_RISK"    # 15:00 - 15:30 (Squaring off, high danger)


class SlippageEstimate(BaseModel):
    """Point-in-time estimated execution slippage and market impact."""

    symbol: str
    order_qty: int
    expected_price: Decimal
    spread_cost_bps: Decimal = Field(..., description="Half-spread cost in basis points")
    market_impact_bps: Decimal = Field(..., description="Estimated market impact in basis points")
    total_slippage_bps: Decimal = Field(..., description="Combined expected slippage in basis points")
    estimated_fill_price: Decimal = Field(..., description="Predicted average execution fill price")
    slippage_drag_inr: Decimal = Field(..., description="Estimated rupee friction impact")


class LiquiditySizingRecommendation(BaseModel):
    """Liquidity-aware position sizing guidance."""

    symbol: str
    requested_qty: int
    recommended_qty: int
    volume_participation_pct: Decimal = Field(..., description="Order size as % of bar/average volume")
    max_participation_cap_pct: Decimal = Field(..., description="Maximum allowed volume participation (e.g. 2.0%)")
    spread_penalty_applied: bool
    size_scaled_down: bool
    scale_factor: Decimal = Field(..., description="Multiplier applied to requested size (0.0 to 1.0)")
    rationale: str


class ExecutionLatencyProfile(BaseModel):
    """Microsecond/millisecond latency decomposition for an execution cycle."""

    dispatch_latency_ms: float = Field(..., description="Engine to broker adapter dispatch delay")
    broker_ack_latency_ms: float = Field(..., description="Broker ACK transit delay")
    fill_latency_ms: float = Field(..., description="Broker matching engine fill delay")
    watcher_handshake_ms: float = Field(..., description="Position watcher registration delay")
    total_end_to_end_ms: float = Field(..., description="Total execution cycle time")


class ExecutionOptimizationStudy(BaseModel):
    """Empirical comparative study: Baseline Execution vs Optimized Execution."""

    study_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    orders_analyzed_count: int
    baseline_avg_slippage_bps: Decimal
    optimized_avg_slippage_bps: Decimal
    slippage_reduction_pct: Decimal = Field(..., description="Percentage reduction in execution slippage")
    baseline_total_friction_inr: Decimal
    optimized_total_friction_inr: Decimal
    friction_savings_inr: Decimal
    fill_rate_baseline_pct: Decimal
    fill_rate_optimized_pct: Decimal
    p95_fill_latency_baseline_ms: float
    p95_fill_latency_optimized_ms: float
    latency_improvement_pct: Decimal
    paper_validated: bool = True
    key_findings: list[str] = Field(default_factory=list)
