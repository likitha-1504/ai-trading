"""Models, schemas, and security exceptions for Phase 22 Learning & Continuous Improvement."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# 1. Enums and Exceptions
# =============================================================================


class ProposalStatus(str, Enum):
    """Lifecycle status states for versioned strategy improvement proposals."""

    PROPOSED = "PROPOSED"
    BACKTEST_VALIDATING = "BACKTEST_VALIDATING"
    BACKTEST_VALIDATED = "BACKTEST_VALIDATED"
    BACKTEST_FAILED = "BACKTEST_FAILED"
    PAPER_VALIDATING = "PAPER_VALIDATING"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    PAPER_FAILED = "PAPER_FAILED"
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    ACTIVE_IN_PRODUCTION = "ACTIVE_IN_PRODUCTION"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class FalsePositiveCategory(str, Enum):
    """Root-cause classification of false positive candidate trades."""

    PENNY_STOCK_SPREAD_EROSION = "PENNY_STOCK_SPREAD_EROSION"
    MOMENTUM_STALL = "MOMENTUM_STALL"
    CHOP_WHIPSAW = "CHOP_WHIPSAW"
    SLIPPAGE_EXCESS = "SLIPPAGE_EXCESS"
    ADVERSE_REVERSAL = "ADVERSE_REVERSAL"
    OTHER_LOSS = "OTHER_LOSS"


class UncontrolledModificationError(RuntimeError):
    """Raised when an action violates controlled learning, attempts automatic self-modification,
    silent live parameter alteration, or promotion without verified human approval."""


class ValidationPrerequisiteError(ValueError):
    """Raised when an operation attempts to deploy or promote a strategy proposal
    before satisfying mandatory backtest and out-of-sample paper validation prerequisites."""


class StrategyProposalError(ValueError):
    """Base error for strategy improvement proposal operations."""


# =============================================================================
# 2. Analytics Dimension Models
# =============================================================================


class StrategyPerformanceMetric(BaseModel):
    """Detailed financial and risk KPIs stratified by strategy."""

    strategy: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate_pct: float
    gross_pnl: Decimal
    friction: Decimal
    net_pnl: Decimal
    profit_factor: float
    expectancy: Decimal
    max_drawdown_amount: Decimal
    max_drawdown_pct: float
    avg_trade_net: Decimal
    avg_holding_duration_seconds: float
    friction_pct_of_gross: float


class RegimePerformanceMetric(BaseModel):
    """Trading performance stratified across distinct market regimes."""

    regime: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    gross_pnl: Decimal
    friction: Decimal
    net_pnl: Decimal
    profit_factor: float
    avg_trade_net: Decimal
    is_underperforming: bool
    reasons: list[str] = Field(default_factory=list)


class FeatureUsefulnessMetric(BaseModel):
    """Empirical assessment of feature predictive power and noise level."""

    feature_name: str
    correlation_with_net_pnl: float
    winner_mean: float
    loser_mean: float
    separation_score: float
    usefulness_grade: str  # HIGH_SIGNAL, MODERATE_SIGNAL, LOW_SIGNAL, NOISY_REDUNDANT
    recommendation: str


class FalsePositiveBreakdown(BaseModel):
    """Categorized diagnosis and remediation recommendations for losing trades."""

    category: str
    trade_ids: list[str] = Field(default_factory=list)
    count: int
    pct_of_total_losses: float
    total_loss_amount: Decimal
    characteristic_features: dict[str, Any] = Field(default_factory=dict)
    remediation_suggestion: str


class FalseExitMetric(BaseModel):
    """Analysis of exit efficiency, premature profit-taking, and whipsaws."""

    exit_trigger: str
    count: int
    avg_net_pnl: Decimal
    premature_exits: int
    whipsaw_shakeouts: int
    avg_mfe_captured_pct: float
    recommendations: list[str] = Field(default_factory=list)


class AIReasoningQualityMetric(BaseModel):
    """Audit of AI Analyst (Qwen3) and Challenger (DeepSeek-R1) reasoning quality."""

    model_name: str
    role: str
    total_calls: int
    successful_calls: int
    fallback_calls: int
    avg_confidence: float
    high_confidence_win_rate_pct: float
    moderate_confidence_win_rate_pct: float
    challenge_accuracy_pct: float
    unanimous_win_rate_pct: float
    contested_win_rate_pct: float
    avg_latency_ms: float
    p95_latency_ms: float


class ExecutionQualityMetric(BaseModel):
    """Audit of broker execution latency, fill rates, and slippage distribution."""

    total_orders: int
    filled_orders: int
    rejected_orders: int
    fill_rate_pct: float
    avg_slippage_bps: float
    zero_slippage_count: int
    adverse_slippage_count: int
    favorable_slippage_count: int
    max_slippage_bps: float
    slippage_drag_total: Decimal


class CostLeakageMetric(BaseModel):
    """Detailed statutory friction audit, drag ratio, and micro-capital sensitivity."""

    total_gross_pnl: Decimal
    total_friction: Decimal
    net_pnl: Decimal
    friction_drag_ratio_pct: float
    brokerage_total: Decimal
    stt_total: Decimal
    exchange_fees_total: Decimal
    sebi_charges_total: Decimal
    stamp_duty_total: Decimal
    gst_total: Decimal
    friction_pct_at_100_cap: float
    friction_pct_at_300_cap: float
    friction_pct_at_1000_cap: float
    min_profitable_move_bps: float


class ComprehensivePostTradeReport(BaseModel):
    """Consolidated post-trade analytics across all 8 mandatory dimensions."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_trades_analyzed: int
    strategy_performance: dict[str, StrategyPerformanceMetric]
    regime_performance: dict[str, RegimePerformanceMetric]
    feature_usefulness: list[FeatureUsefulnessMetric]
    false_positives: list[FalsePositiveBreakdown]
    false_exits: list[FalseExitMetric]
    ai_reasoning: dict[str, AIReasoningQualityMetric]
    execution_quality: ExecutionQualityMetric
    cost_leakage: CostLeakageMetric
    identified_weaknesses: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


# =============================================================================
# 3. Controlled Learning & Versioned Proposal Models
# =============================================================================


class ParameterChange(BaseModel):
    """Specific parameter adjustment within a versioned improvement proposal."""

    parameter_name: str
    old_value: Any
    new_value: Any
    unit: str = ""
    rationale: str


class BacktestValidationEvidence(BaseModel):
    """Empirical proof of quantitative backtest hurdle compliance."""

    backtest_id: str
    dataset_period: str
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    net_pnl: Decimal
    max_drawdown_pct: float
    meets_hurdle: bool
    notes: str = ""
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaperValidationEvidence(BaseModel):
    """Empirical proof of out-of-sample paper trading validation compliance."""

    validation_id: str
    sessions_evaluated: int
    total_trades: int
    win_rate_pct: float
    net_pnl: Decimal
    risk_violations: int
    sub_50ms_watcher_compliance_pct: float
    meets_hurdle: bool
    notes: str = ""
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyImprovementProposal(BaseModel):
    """Auditable, immutable strategy improvement proposal subjected to multi-stage gating."""

    id: str
    strategy_name: str
    target_version: str
    current_version: str
    title: str
    empirical_weakness: str
    parameter_changes: list[ParameterChange]
    proposed_by: str = "LEARNING_LOOP_ENGINE"
    status: ProposalStatus = ProposalStatus.PROPOSED
    backtest_evidence: BacktestValidationEvidence | None = None
    paper_evidence: PaperValidationEvidence | None = None
    approved_by: str | None = None
    approval_token_masked: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
