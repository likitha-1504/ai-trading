"""Formal data contracts and event schemas for the AI Micro-Trading Agent pipeline.

Locked pipeline boundaries:
Market Data -> Normalizer -> Feature Engine -> Momentum/Early-Move Strategies
-> Candidate Ranker -> AI Queue -> Deterministic Trade Gate -> Execution
-> Position Watcher -> Journal/Performance.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# =====================================================================
# 1. Market Data & Normalization Contracts
# =====================================================================


class MarketSource(str, Enum):
    SIMULATED = "SIMULATED"
    PAPER = "PAPER"
    ZERODHA = "ZERODHA"
    GROWW = "GROWW"
    UPSTOX = "UPSTOX"


class RawMarketTick(BaseModel):
    """Raw tick ingested from market WebSocket/REST provider."""

    source: MarketSource
    symbol: str
    timestamp: datetime
    last_price: Decimal
    volume: int
    bid_price: Decimal | None = None
    bid_quantity: int | None = None
    ask_price: Decimal | None = None
    ask_quantity: int | None = None


class NormalizedMarketEvent(BaseModel):
    """Normalized, timestamp-validated market event."""

    symbol: str
    source: MarketSource
    exchange_timestamp: datetime
    ingest_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_price: Decimal
    volume: int
    bid_price: Decimal
    ask_price: Decimal
    bid_quantity: int
    ask_quantity: int
    spread_pct: Decimal
    is_stale: bool = False

    @field_validator("spread_pct")
    @classmethod
    def validate_spread(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Spread percentage cannot be negative")
        return v


# =====================================================================
# 2. Feature Engine Contracts
# =====================================================================


class MarketRegime(str, Enum):
    BULLISH_TRENDING = "BULLISH_TRENDING"
    BEARISH_TRENDING = "BEARISH_TRENDING"
    HIGH_VOLATILITY_CHOP = "HIGH_VOLATILITY_CHOP"
    LOW_VOLATILITY_COMPRESSION = "LOW_VOLATILITY_COMPRESSION"


class FeatureSnapshot(BaseModel):
    """Timestamp-safe indicator snapshot consumed by strategies and AI."""

    symbol: str
    timestamp: datetime
    bar_timeframe: str = "1m"
    vwap: Decimal
    current_price: Decimal
    vwap_distance_pct: Decimal = Decimal(0)
    momentum_score: Decimal = Decimal(0)
    relative_volume_10: Decimal  # RVOL over 10-bar baseline
    volume_acceleration: Decimal
    price_acceleration: Decimal
    realized_volatility_15: Decimal
    spread_pct: Decimal
    liquidity_score: Decimal
    market_index_direction: str  # BULLISH / BEARISH / NEUTRAL
    sector_strength: Decimal = Decimal(0)
    price_structure: str = (
        "RANGE"  # HIGHER_HIGHS, LOWER_LOWS, COMPRESSION, BREAKOUT, RANGE
    )
    regime: MarketRegime


# =====================================================================
# 3. Strategy & Candidate Ranker Contracts
# =====================================================================


class StrategyType(str, Enum):
    MOMENTUM_CONTINUATION = "MOMENTUM_CONTINUATION"
    EARLY_MOVE_DETECTION = "EARLY_MOVE_DETECTION"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Candidate(BaseModel):
    """Deterministic candidate discovered by strategy modules."""

    candidate_id: str
    detected_at: datetime
    symbol: str
    strategy_type: StrategyType
    side: TradeSide = TradeSide.BUY
    trigger_price: Decimal
    initial_stop_price: Decimal
    suggested_target_price: Decimal
    rank_score: Decimal
    quantitative_evidence: dict[str, Any]
    feature_snapshot: FeatureSnapshot


# =====================================================================
# 4. Dual-Model AI Council Contracts (Qualitative, Non-Emergency)
# =====================================================================


class AIModelRole(str, Enum):
    ANALYST = "ANALYST"  # Qwen3
    CHALLENGER = "CHALLENGER"  # DeepSeek-R1


class MarketThesis(BaseModel):
    """Qwen3 Primary Analyst output schema."""

    candidate_id: str
    model_name: str = "qwen3:latest"
    thesis_summary: str
    catalyst_identified: str | None = None
    bullish_evidence: list[str]
    invalidation_conditions: list[str]
    perceived_risks: list[str]
    confidence_score: Decimal = Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    suggested_action: str  # PROCEED / CAUTION / REJECT
    latency_ms: int
    prompt_version: str


class ChallengerCritique(BaseModel):
    """DeepSeek-R1 Adversarial Reasoner output schema."""

    candidate_id: str
    model_name: str = "deepseek-r1:latest"
    critique_summary: str
    identified_vulnerabilities: list[str]
    contradictory_signals: list[str]
    worst_case_scenario: str
    downside_severity: str  # LOW / MEDIUM / SEVERE
    recommendation_flag: str  # CONFIRM / CONTEST / VETO_CANDIDATE
    latency_ms: int
    prompt_version: str


# =====================================================================
# 5. Deterministic Trade Gate Contracts
# =====================================================================


class ApprovalMode(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    MANUAL_PENDING = "MANUAL_PENDING"
    MANUAL_APPROVED = "MANUAL_APPROVED"
    REJECTED = "REJECTED"


class FrictionBreakdown(BaseModel):
    """Transaction cost breakdown for Indian equity micro-trading."""

    brokerage: Decimal
    stt: Decimal
    exchange_charges: Decimal
    sebi_charges: Decimal
    stamp_duty: Decimal
    gst: Decimal
    expected_slippage: Decimal
    total_friction: Decimal


class TradePlan(BaseModel):
    """Immutable, authorized execution blueprint generated by the Trade Gate."""

    plan_id: str
    candidate_id: str
    created_at: datetime
    symbol: str
    side: TradeSide
    quantity: int
    entry_price_target: Decimal
    hard_stop_price: Decimal
    take_profit_price: Decimal | None = None
    trailing_trigger_price: Decimal | None = None
    expected_gross_edge: Decimal
    friction: FrictionBreakdown
    expected_net_edge: Decimal
    decision_reason: str
    approval_mode: ApprovalMode
    ai_thesis_ref: MarketThesis | None = None
    ai_critique_ref: ChallengerCritique | None = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


# =====================================================================
# 6. Execution & Broker Adapter Contracts
# =====================================================================


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


class OrderRequest(BaseModel):
    """Order dispatch request payload."""

    client_order_id: str
    plan_id: str
    symbol: str
    side: TradeSide
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    stop_price: Decimal | None = None


class OrderEvent(BaseModel):
    """Order status lifecycle update emitted by broker adapter."""

    client_order_id: str
    broker_order_id: str | None = None
    symbol: str
    status: OrderStatus
    filled_quantity: int
    remaining_quantity: int
    average_fill_price: Decimal | None = None
    rejection_reason: str | None = None
    timestamp: datetime


# =====================================================================
# 7. Independent Position Watcher Contracts (Zero LLM Dependency)
# =====================================================================


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class WatcherExitTrigger(str, Enum):
    HARD_STOP = "HARD_STOP"
    TRAILING_STOP = "TRAILING_STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_EXPIRY = "TIME_EXPIRY"
    STALE_DATA_EMERGENCY = "STALE_DATA_EMERGENCY"
    CATASTROPHIC_LIQUIDITY_LOSS = "CATASTROPHIC_LIQUIDITY_LOSS"
    DAILY_CIRCUIT_BREAKER = "DAILY_CIRCUIT_BREAKER"
    MANUAL_KILL_SWITCH = "MANUAL_KILL_SWITCH"
    MOMENTUM_DETERIORATION = "MOMENTUM_DETERIORATION"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"
    SPREAD_WIDENING = "SPREAD_WIDENING"
    MARKET_REVERSAL = "MARKET_REVERSAL"
    AI_THESIS_INVALIDATION = "AI_THESIS_INVALIDATION"


class PositionSnapshot(BaseModel):
    """Active position tracked in real-time by the Position Watcher."""

    position_id: str
    plan_id: str
    symbol: str
    side: TradeSide
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    hard_stop_price: Decimal
    trailing_stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    highest_price_seen: Decimal | None = None
    unrealized_pnl: Decimal
    status: PositionStatus
    opened_at: datetime
    last_evaluated_at: datetime


class WatcherInterventionEvent(BaseModel):
    """Emergency or safety action taken autonomously by the Position Watcher."""

    event_id: str
    timestamp: datetime
    position_id: str
    symbol: str
    trigger: WatcherExitTrigger
    trigger_price: Decimal
    executed_exit_order_id: str
    details: str
