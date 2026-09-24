"""Pydantic schemas and Data Transfer Objects (DTOs) for API v1.

Strictly segregated into:
1. Safe read/query response models
2. Guarded mutation request/response models
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.contracts import (
    ApprovalMode,
    Candidate,
    ChallengerCritique,
    FeatureSnapshot,
    MarketRegime,
    MarketThesis,
    PositionSnapshot,
    TradePlan,
    TradeRecord,
)

# =====================================================================
# 1. Safe Read / Query Response Schemas
# =====================================================================


class DashboardSummaryResponse(BaseModel):
    """High-level real-time trading command center summary."""

    total_equity: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: float
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    win_rate: float
    open_positions_count: int
    total_trades_count: int
    active_candidates_count: int
    system_status: str = "HEALTHY"
    system_mode: str = "PAPER"
    live_trading_allowed: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CapitalResponse(BaseModel):
    """Account capital, balances, buying power, and drawdowns."""

    total_capital: Decimal
    available_capital: Decimal
    deployed_capital: Decimal
    buying_power: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    daily_drawdown_amount: Decimal
    daily_drawdown_pct: Decimal
    high_water_mark: Decimal
    currency: str = "INR"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketScannerItem(BaseModel):
    """Symbol discovery and market indicator overview."""

    symbol: str
    price: Decimal
    vwap: Decimal
    relative_volume: Decimal
    momentum_score: Decimal
    spread_pct: Decimal
    liquidity_score: Decimal
    regime: MarketRegime
    timestamp: datetime


class PnLSummaryResponse(BaseModel):
    """Aggregated P/L and Indian market friction deductions."""

    realized_pnl: Decimal
    unrealized_pnl: Decimal
    gross_pnl: Decimal
    total_friction: Decimal
    net_pnl: Decimal
    daily_drawdown_amount: Decimal
    daily_drawdown_pct: float
    currency: str = "INR"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIAnalysesResponse(BaseModel):
    """Dual-model AI Council qualitative output for a candidate."""

    candidate_id: str
    symbol: str
    analyst_thesis: MarketThesis | None = None
    challenger_critique: ChallengerCritique | None = None
    council_resolution: str | None = None
    is_fallback_used: bool = False
    combined_latency_ms: int = 0


class ModelLatencyStats(BaseModel):
    """AI inference latency and fallback statistics."""

    model_name: str
    role: str
    call_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    fallback_rate_pct: float


class RiskStatusResponse(BaseModel):
    """Real-time risk governance, limits, and circuit breaker metrics."""

    circuit_breaker_tripped: bool
    daily_drawdown_amount: Decimal
    daily_drawdown_pct: Decimal
    max_daily_drawdown_pct: Decimal
    open_positions_count: int
    max_positions_cap: int
    total_capital: Decimal
    available_capital: Decimal
    can_take_trades: bool
    status: str = "NORMAL"


class RiskLimitsResponse(BaseModel):
    """Static and dynamic risk rules."""

    starting_capital: Decimal
    max_daily_drawdown_pct: Decimal
    max_position_size_pct: Decimal
    max_risk_per_trade_pct: Decimal
    autonomous_threshold: Decimal
    hard_stop_loss_pct: Decimal
    intraday_cutoff_ist: str = "15:15 IST"


class SystemHealthResponse(BaseModel):
    """Multi-component operational health status."""

    status: str  # HEALTHY, WARNING, CRITICAL
    database: str  # CONNECTED_WAL, DISCONNECTED
    position_watcher: str  # ACTIVE, INACTIVE
    execution_engine: str  # ACTIVE, IDLE
    ai_council: str  # ONLINE, DEGRADED, OFFLINE
    mode: str  # PAPER, LIVE
    live_trading_allowed: bool
    uptime_seconds: float
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditTrailResponse(BaseModel):
    """Reconstructed decision provenance for compliance and verification."""

    candidate_id: str
    plan_id: str | None = None
    timestamp: datetime
    is_fully_reproducible: bool
    reproducibility_notes: list[str] = Field(default_factory=list)
    candidate: Candidate | None = None
    features: FeatureSnapshot | None = None
    ai_analyses: list[dict[str, Any]] = Field(default_factory=list)
    trade_plan: TradePlan | None = None
    orders: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[TradeRecord] = Field(default_factory=list)
    positions: list[PositionSnapshot] = Field(default_factory=list)


# =====================================================================
# 2. Guarded Mutation Request / Response Schemas
# =====================================================================


class PlanApprovalRequest(BaseModel):
    """Explicit human operator approval for a pending TradePlan."""

    confirm: bool = True
    auth_token: str | None = None
    operator_notes: str | None = None


class PlanApprovalResponse(BaseModel):
    """Result of TradePlan approval and dispatch."""

    success: bool
    plan_id: str
    approval_mode: ApprovalMode
    client_order_id: str | None = None
    message: str


class PlanRejectionRequest(BaseModel):
    """Explicit rejection of a pending TradePlan."""

    reason: str = "Operator manual rejection"


class PlanRejectionResponse(BaseModel):
    """Result of TradePlan rejection."""

    success: bool
    plan_id: str
    approval_mode: ApprovalMode = ApprovalMode.REJECTED
    message: str


class KillSwitchRequest(BaseModel):
    """Emergency halt trigger."""

    confirm: bool
    reason: str = "Manual operator intervention"


class KillSwitchResponse(BaseModel):
    """Outcome of emergency liquidation and trading suspension."""

    success: bool
    message: str
    positions_closed: int
    orders_cancelled: int
    system_halted: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModeSwitchRequest(BaseModel):
    """Guarded request to switch system operational mode."""

    target_mode: str  # PAPER or LIVE
    confirmation: bool = False
    live_trading_approval_token: str | None = None


class ModeSwitchResponse(BaseModel):
    """Outcome of mode switch request."""

    success: bool
    current_mode: str
    message: str
