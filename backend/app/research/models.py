"""Data contracts and schemas for Phase 27: Strategy Research & Optimization.

Defines schemas for experiment versioning, leakage audits, walk-forward validation,
realistic cost/slippage parameters, and explicit promotion gates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    """Lifecycle statuses for a strategy research experiment."""

    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    VALIDATED = "VALIDATED"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"


class SilentProductionEntryError(RuntimeError):
    """Raised when an unapproved experiment attempts to enter production silently."""


class StrategyHypothesis(BaseModel):
    """Formal qualitative and quantitative hypothesis for an experiment."""

    title: str = Field(..., description="Short descriptive title of the hypothesis")
    description: str = Field(..., description="Mechanistic market rationale for why edge exists")
    expected_edge_bps: float = Field(..., description="Estimated gross edge in basis points")
    risk_rationale: str = Field(..., description="Why downside risk remains bounded")


class LeakageAuditReport(BaseModel):
    """Formal verification report for look-ahead bias and information leakage."""

    is_leakage_free: bool = Field(..., description="True if zero leakage/lookahead detected")
    timestamp_monotonic: bool = Field(..., description="True if all event timestamps are monotonic")
    lookahead_bias_detected: bool = Field(..., description="True if future data accessed in signals")
    split_contamination_detected: bool = Field(..., description="True if train stats leak into test split")
    future_target_referenced: bool = Field(..., description="True if future bar HLC is accessed")
    checked_events_count: int = Field(..., description="Number of events inspected in audit")
    details: str = Field(..., description="Detailed findings and audit trail")


class WalkForwardSummary(BaseModel):
    """Walk-forward and out-of-sample statistical robustness summary."""

    num_windows: int = Field(3, description="Number of walk-forward rolling windows")
    in_sample_ratio: float = Field(0.70, description="Train / validation split ratio")
    avg_oos_profit_factor: float = Field(..., description="Average out-of-sample profit factor")
    avg_oos_expectancy_inr: float = Field(..., description="Average out-of-sample net expectancy per trade")
    window_stability_score: float = Field(..., description="Stability metric across split windows (0-1)")
    is_robust: bool = Field(..., description="True if all windows maintain positive expectancy")


class ExperimentVersion(BaseModel):
    """Immutable record of a versioned strategy research experiment."""

    experiment_id: str = Field(..., description="Unique experiment ID (e.g. EXP-STRAT-001)")
    version_tag: str = Field(..., description="Semantic version tag (e.g. v1.0.0-baseline)")
    parent_version: str | None = Field(None, description="Prior version this was derived from")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ExperimentStatus = Field(default=ExperimentStatus.COMPLETED)
    hypothesis: StrategyHypothesis
    parameters: dict[str, Any] = Field(default_factory=dict)
    initial_capital_inr: float = Field(100.00, description="Capital ceiling during research")
    in_sample_pnl_inr: float = 0.0
    oos_pnl_inr: float = 0.0
    oos_sharpe: float = 0.0
    oos_win_rate_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    turnover_inr: float = 0.0
    fee_drag_pct: float = 0.0
    slippage_drag_bps: float = 0.0
    leakage_audit: LeakageAuditReport
    walk_forward: WalkForwardSummary
    paper_validated: bool = False
    promotion_candidate: bool = False
    promotion_rejection_reason: str | None = None
    notes: str = ""


class PromotionRequest(BaseModel):
    """Payload required to request promoting a candidate experiment to production."""

    experiment_id: str
    operator_authorization_token: str
    target_environment: str = Field(default="paper", description="Target environment (must be paper)")
    rationale: str
