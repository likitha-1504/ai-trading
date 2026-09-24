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

from pydantic import BaseModel, Field, field_validator, model_validator

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


class MarketThesisAction(str, Enum):
    PROCEED = "PROCEED"
    CAUTION = "CAUTION"
    REJECT = "REJECT"


class MarketThesis(BaseModel):
    """Qwen3 Primary Analyst output schema."""

    candidate_id: str
    model_name: str = "qwen3:latest"
    model_version: str = "v1.0"
    prompt_version: str
    thesis_summary: str
    catalyst_identified: str | None = None
    bullish_evidence: list[str]
    invalidation_conditions: list[str]
    perceived_risks: list[str]
    confidence_score: Decimal = Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    context_summary: str | None = None
    suggested_action: MarketThesisAction = MarketThesisAction.PROCEED
    latency_ms: int
    token_count: int | None = None
    is_fallback: bool = False
    raw_response: str | None = None


class ChallengerSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    SEVERE = "SEVERE"


class ChallengerRecommendation(str, Enum):
    CONFIRM = "CONFIRM"
    CONTEST = "CONTEST"
    VETO_CANDIDATE = "VETO_CANDIDATE"


class ChallengerCritique(BaseModel):
    """DeepSeek-R1 Adversarial Reasoner output schema."""

    candidate_id: str
    model_name: str = "deepseek-r1:latest"
    model_version: str = "v1.0"
    prompt_version: str
    critique_summary: str
    identified_vulnerabilities: list[str]
    contradictory_signals: list[str]
    missing_evidence: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
    worst_case_scenario: str
    downside_severity: ChallengerSeverity = ChallengerSeverity.MEDIUM
    recommendation_flag: ChallengerRecommendation = ChallengerRecommendation.CONFIRM
    latency_ms: int
    token_count: int | None = None
    is_fallback: bool = False
    raw_response: str | None = None


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


class RiskLimits(BaseModel):
    """Risk constraints and capital limits applied to the TradePlan."""

    max_loss_amount: Decimal
    max_capital_allocation: Decimal
    max_position_size_pct: Decimal = Decimal("0.015")
    max_daily_drawdown_pct: Decimal = Decimal("0.03")


class StopProtection(BaseModel):
    """Deterministic exit triggers and protective stop levels."""

    hard_stop_price: Decimal
    trailing_trigger_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    time_exit_time: str = "15:15 IST"
    max_holding_bars: int = 60


class TradePlan(BaseModel):
    """Immutable, authorized execution blueprint generated by the Deterministic Trade Gate."""

    plan_id: str
    candidate_id: str
    created_at: datetime
    instrument: str = ""
    symbol: str = ""  # alias for instrument
    side: TradeSide
    quantity: int
    entry_price_target: Decimal
    entry_context: dict[str, Any] = Field(default_factory=dict)
    strategy: StrategyType = StrategyType.MOMENTUM_CONTINUATION
    expected_edge: Decimal = Decimal("0.00")
    expected_gross_edge: Decimal = Decimal("0.00")
    expected_net_edge: Decimal = Decimal("0.00")  # alias for expected_edge
    estimated_costs: FrictionBreakdown | None = None
    friction: FrictionBreakdown | None = None  # alias for estimated_costs
    risk_limits: RiskLimits | None = None
    stop_protection: StopProtection | None = None
    hard_stop_price: Decimal | None = None  # alias for stop_protection.hard_stop_price
    take_profit_price: Decimal | None = None
    trailing_trigger_price: Decimal | None = None
    invalidation: list[str] = Field(default_factory=list)
    ai_evidence_references: dict[str, Any] = Field(default_factory=dict)
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

    @model_validator(mode="before")
    @classmethod
    def sync_and_default_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync instrument <-> symbol
            if "instrument" in data and not data.get("symbol"):
                data["symbol"] = data["instrument"]
            elif "symbol" in data and not data.get("instrument"):
                data["instrument"] = data["symbol"]

            # Sync estimated_costs <-> friction
            if "estimated_costs" in data and not data.get("friction"):
                data["friction"] = data["estimated_costs"]
            elif "friction" in data and not data.get("estimated_costs"):
                data["estimated_costs"] = data["friction"]

            # Sync expected_edge <-> expected_net_edge
            if "expected_edge" in data and "expected_net_edge" not in data:
                data["expected_net_edge"] = data["expected_edge"]
            elif "expected_net_edge" in data and "expected_edge" not in data:
                data["expected_edge"] = data["expected_net_edge"]

            # Sync hard_stop_price and stop_protection
            if "stop_protection" in data and data["stop_protection"] is not None:
                sp = data["stop_protection"]
                if isinstance(sp, StopProtection):
                    data.setdefault("hard_stop_price", sp.hard_stop_price)
                    data.setdefault("take_profit_price", sp.take_profit_price)
                    data.setdefault("trailing_trigger_price", sp.trailing_trigger_price)
                elif isinstance(sp, dict):
                    data.setdefault("hard_stop_price", sp.get("hard_stop_price"))
                    data.setdefault("take_profit_price", sp.get("take_profit_price"))
                    data.setdefault("trailing_trigger_price", sp.get("trailing_trigger_price"))
            elif "hard_stop_price" in data and data["hard_stop_price"] is not None:
                data["stop_protection"] = StopProtection(
                    hard_stop_price=data["hard_stop_price"],
                    trailing_trigger_price=data.get("trailing_trigger_price"),
                    take_profit_price=data.get("take_profit_price"),
                )

            # Default risk_limits if omitted
            if "risk_limits" not in data or data["risk_limits"] is None:
                data["risk_limits"] = RiskLimits(
                    max_loss_amount=Decimal("1.50"),
                    max_capital_allocation=Decimal("100.00"),
                )
        return data


class CapitalSnapshot(BaseModel):
    """Snapshot of account capital, balances, buying power, and drawdowns."""

    timestamp: datetime
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


class RiskEvaluationResult(BaseModel):
    """Result of deterministic risk, capital, and cost evaluation for a trade candidate."""

    approved: bool
    approval_mode: ApprovalMode
    symbol: str
    approved_quantity: int
    allocated_capital: Decimal
    max_loss_potential: Decimal
    friction: FrictionBreakdown
    expected_gross_edge: Decimal
    expected_net_edge: Decimal
    is_circuit_breaker_tripped: bool
    rejection_reasons: list[str] = Field(default_factory=list)


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


class BrokerPosition(BaseModel):
    """Position record as reported directly by the broker."""

    symbol: str
    side: TradeSide
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal


class AccountBalance(BaseModel):
    """Broker account equity and margin state."""

    currency: str = "INR"
    cash_balance: Decimal
    available_margin: Decimal
    used_margin: Decimal
    total_equity: Decimal


class ReconciliationMismatch(BaseModel):
    """Specific discrepancy detected between local state and broker state."""

    symbol: str
    local_quantity: int
    broker_quantity: int
    discrepancy_type: str
    details: str


class ReconciliationReport(BaseModel):
    """Comprehensive portfolio reconciliation outcome report."""

    timestamp: datetime
    is_clean: bool
    positions_checked: int
    mismatches: list[ReconciliationMismatch] = Field(default_factory=list)


class ExecutionMetricsSnapshot(BaseModel):
    """Aggregated execution latency, fill rates, and performance metrics."""

    total_orders_submitted: int
    total_orders_acknowledged: int
    total_orders_filled: int
    total_orders_partially_filled: int
    total_orders_cancelled: int
    total_orders_rejected: int
    total_quantity_ordered: int
    total_quantity_filled: int
    total_slippage_incurred: Decimal
    avg_submission_latency_ms: float
    avg_ack_latency_ms: float
    avg_fill_latency_ms: float



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


# =====================================================================
# 8. Backtest, Paper Trading & Performance Contracts
# =====================================================================


class TradeRecord(BaseModel):
    """Detailed immutable historical trade journal record."""

    trade_id: str
    plan_id: str
    symbol: str
    side: TradeSide
    strategy: StrategyType
    quantity: int
    entry_timestamp: datetime
    entry_price: Decimal
    entry_slippage: Decimal
    exit_timestamp: datetime
    exit_price: Decimal
    exit_slippage: Decimal
    exit_trigger: WatcherExitTrigger
    gross_pnl: Decimal
    friction: FrictionBreakdown
    net_pnl: Decimal
    holding_duration_seconds: float
    market_regime_at_entry: MarketRegime
    market_regime_at_exit: MarketRegime


class EquityPoint(BaseModel):
    """Point-in-time portfolio valuation for equity curve tracking."""

    timestamp: datetime
    total_equity: Decimal
    cash_balance: Decimal
    unrealized_pnl: Decimal
    drawdown_amount: Decimal
    drawdown_pct: float


class PerformanceMetrics(BaseModel):
    """Exhaustive backtest and paper performance telemetry."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_pnl: Decimal
    total_friction: Decimal
    net_pnl: Decimal
    profit_factor: float
    expectancy: Decimal
    average_trade: Decimal
    average_win: Decimal
    average_loss: Decimal
    max_drawdown_amount: Decimal
    max_drawdown_pct: float
    trade_frequency_per_day: float
    friction_pct_of_gross_profit: float
    regime_pnl: dict[str, Decimal] = Field(default_factory=dict)
    regime_trades: dict[str, int] = Field(default_factory=dict)


class BacktestReport(BaseModel):
    """Comprehensive backtesting run evaluation outcome."""

    run_id: str
    start_time: datetime
    end_time: datetime
    initial_capital: Decimal
    final_equity: Decimal
    slippage_ticks: int
    metrics: PerformanceMetrics
    trades: list[TradeRecord]
    equity_curve: list[EquityPoint]


class WalkForwardWindow(BaseModel):
    """In-sample and out-of-sample partition evaluation for a single walk-forward window."""

    window_index: int
    in_sample_start: datetime
    in_sample_end: datetime
    out_of_sample_start: datetime
    out_of_sample_end: datetime
    in_sample_metrics: PerformanceMetrics
    out_of_sample_metrics: PerformanceMetrics
    out_of_sample_degradation_pct: float


class WalkForwardReport(BaseModel):
    """Walk-forward / out-of-sample stability analysis report."""

    total_windows: int
    windows: list[WalkForwardWindow]
    avg_out_of_sample_profit_factor: float
    avg_out_of_sample_expectancy: Decimal
    is_overfitted: bool


class SlippageSensitivityPoint(BaseModel):
    """Backtest performance at a specific simulated slippage level."""

    slippage_ticks: int
    net_pnl: Decimal
    profit_factor: float
    expectancy: Decimal
    total_slippage_cost: Decimal


class SlippageSensitivityReport(BaseModel):
    """Slippage sensitivity evaluation comparing zero-slippage vs multiple slippage levels."""

    base_ticks: int
    evaluations: list[SlippageSensitivityPoint]
    is_viable_at_high_slippage: bool

