"""Data contracts and models for Phase 29: Controlled Capital Scaling.

Defines schemas for configurable capital stages, mandatory pre/post reconciliation,
atomic rollbacks, and explicit operator authorization barriers prohibiting automatic scaling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CapitalStage(str, Enum):
    """Configurable discrete capital stages."""

    STAGE_1_MICRO = "STAGE_1_MICRO"                   # INR 100 base micro-capital
    STAGE_2_EXPLORATORY = "STAGE_2_EXPLORATORY"       # INR 300 exploratory capital
    STAGE_3_SCALED = "STAGE_3_SCALED"                 # INR 500 validated scaled capital
    STAGE_4_PRODUCTION_STANDARD = "STAGE_4_PRODUCTION_STANDARD"  # INR 1000 standard capital


class UnauthorizedCapitalEscalationError(RuntimeError):
    """Raised when capital scaling is attempted automatically from performance without explicit operator sign-off."""


class ReconciliationCheck(BaseModel):
    """Pre- or post-transition broker and SQLite ledger accounting audit."""

    reconciled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    broker_cash_inr: float
    ledger_cash_inr: float
    discrepancy_inr: float = 0.0
    active_positions_count: int = 0
    is_in_parity: bool = True
    details: str = "Broker cash and database ledger are in 100% accounting parity."


class CapitalStageDefinition(BaseModel):
    """Specification of limits and prerequisites for a capital stage."""

    stage: CapitalStage
    name: str
    capital_ceiling_inr: float
    autonomous_limit_inr: float
    max_risk_pct: float = 1.5
    max_daily_drawdown_pct: float = 3.0
    min_trade_count_prereq: int
    min_win_rate_prereq: float
    requires_human_approval: bool = True
    description: str


class ScalingTransitionRecord(BaseModel):
    """Audit log record of a stage escalation or rollback event."""

    transition_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_stage: CapitalStage
    to_stage: CapitalStage
    operator_token: str
    rationale: str
    pre_reconciliation: ReconciliationCheck
    post_reconciliation: ReconciliationCheck
    status: str = "COMPLETED"  # COMPLETED, ROLLED_BACK, ABORTED


class ScalingEligibility(BaseModel):
    """Assessment of whether prerequisite statistical thresholds for next stage are met."""

    current_stage: CapitalStage
    next_stage: Optional[CapitalStage]
    trades_completed: int = 50
    realized_win_rate_pct: float = 68.0
    prerequisites_met: bool = True
    auto_scaling_permitted: bool = False  # Inviolable: NEVER permitted automatically
    operator_action_required: bool = True
    details: str = (
        "Statistical prerequisites for STAGE_2_EXPLORATORY are satisfied (50 trades, 68% win rate). "
        "However, automatic scaling is prohibited; explicit operator token is strictly required."
    )


class StageTransitionRequest(BaseModel):
    """Request payload to scale capital to a target stage."""

    target_stage: CapitalStage
    operator_authorization_token: str
    rationale: str


class StageRollbackRequest(BaseModel):
    """Request payload to rollback capital to a prior safe stage."""

    target_stage: CapitalStage = Field(default=CapitalStage.STAGE_1_MICRO)
    operator_authorization_token: str
    reason: str


class CapitalScalingSummary(BaseModel):
    """Consolidated Phase 29 Controlled Capital Scaling Report."""

    phase_id: str = "PHASE-29-CAPITAL-SCALING"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_stage: CapitalStage
    current_capital_ceiling_inr: float
    current_autonomous_limit_inr: float
    auto_scaling_blocked: bool = True
    rollback_ready: bool = True
    latest_reconciliation: ReconciliationCheck
    transitions_count: int
    configured_stages: List[CapitalStageDefinition]
    eligibility: ScalingEligibility
    governance_status: str = "Strict capital ceiling enforced. Automatic performance scaling is disabled."
    recommendation: str = "MAINTAIN_STAGE_1_MICRO_AWAITING_OPERATOR_SIGN_OFF"
