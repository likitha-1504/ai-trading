"""Data Models, Enums, and Telemetry Schemas for Phase 37 Long-Term Autonomous System.

Defines schemas for:
- Autonomous Session Lifecycle State Machine
- Dynamic Strategy Portfolio Lifecycle & Performance Tracking
- Explicit Release Gates & Human Approval Tokens
- Multi-Phase Prerequisite Verification
- Daily Session Summaries & Tamper-Evident Ledgers
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AutonomousSystemState(str, Enum):
    """Lifecycle state machine for long-term autonomous operations."""

    OFFLINE = "OFFLINE"                                    # Standing by, not trading
    PRE_MARKET_AUDIT = "PRE_MARKET_AUDIT"                  # Verifying health, WAL, broker, state
    ACTIVE_AUTONOMOUS = "ACTIVE_AUTONOMOUS"                # Intraday autonomous execution
    PAUSED_CIRCUIT_BREAKER = "PAUSED_CIRCUIT_BREAKER"      # Halted on drawdown / loss limit
    INTRADAY_CUTOFF = "INTRADAY_CUTOFF"                    # 15:15 IST auto-square-off active
    POST_MARKET_RECONCILIATION = "POST_MARKET_RECONCILIATION"  # Reconciling PnL, cash, orders
    SESSION_ARCHIVED = "SESSION_ARCHIVED"                  # Closed, state persisted to WAL
    EMERGENCY_HALT = "EMERGENCY_HALT"                      # Kill-switch engaged


class StrategyLifecycleStage(str, Enum):
    """Governed lifecycle stages for portfolio strategies."""

    RESEARCH = "RESEARCH"              # Quarantined in Phase 35 sandbox
    CANDIDATE = "CANDIDATE"            # Passed sandbox statistical hurdles
    PROBATION = "PROBATION"            # Live paper trading with restricted allocation (e.g. <=15%)
    ACTIVE = "ACTIVE"                  # Fully validated active portfolio member
    DEGRADED = "DEGRADED"              # Performance decay detected, capital frozen
    DECOMMISSIONED = "DECOMMISSIONED"  # Disqualified due to drawdown / negative edge


class ReleaseGateType(str, Enum):
    """Categorization of explicit human approval release gates."""

    SYSTEM_ACTIVATION = "SYSTEM_ACTIVATION"        # Activating long-term autonomous session
    STRATEGY_PROMOTION = "STRATEGY_PROMOTION"      # Promoting strategy (e.g. PROBATION -> ACTIVE)
    PORTFOLIO_REBALANCE = "PORTFOLIO_REBALANCE"    # Dynamic multi-strategy weight reallocation
    CAPITAL_TIER_SCALE = "CAPITAL_TIER_SCALE"      # Escalating capital tier limit
    SAFETY_RESET = "SAFETY_RESET"                  # Resetting tripped circuit breaker / halt


class PrerequisiteDimension(str, Enum):
    """The 7 foundational phase validations required before Phase 37 execution."""

    OPS_PREFLIGHT = "OPS_PREFLIGHT"                        # Phase 25/23 Ops & Health probes
    CAPITAL_LIMITS = "CAPITAL_LIMITS"                      # Phase 29 Capital scaling caps & paper lock
    PORTFOLIO_CONCENTRATION = "PORTFOLIO_CONCENTRATION"    # Phase 31 Multi-strategy concentration engine
    DISASTER_RECOVERY = "DISASTER_RECOVERY"                # Phase 33 State reconstruction & WAL integrity
    SECURITY_LEAST_PRIVILEGE = "SECURITY_LEAST_PRIVILEGE"  # Phase 34 Cryptographic audit & RBAC
    RESEARCH_SANDBOX = "RESEARCH_SANDBOX"                  # Phase 35 Quarantined validation & datasets
    AI_COUNCIL_DECOUPLING = "AI_COUNCIL_DECOUPLING"        # Phase 36 Measurable hurdles & safety decoupling


class PrerequisitePhaseAudit(BaseModel):
    """Verification record of all prior phase requirements."""

    audit_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_all_passed: bool
    dimension_results: dict[PrerequisiteDimension, bool]
    details: dict[str, str] = Field(default_factory=dict)


class LongTermStrategyProfile(BaseModel):
    """Long-term statistical and lifecycle profile of an autonomous strategy."""

    strategy_id: str
    strategy_name: str
    lifecycle_stage: StrategyLifecycleStage
    target_weight_pct: Decimal = Decimal("50.00")
    deployed_capital: Decimal = Decimal("0.00")
    allocated_capital: Decimal = Decimal("50.00")
    rolling_win_rate_pct: Decimal = Decimal("60.00")
    rolling_profit_factor: Decimal = Decimal("1.50")
    rolling_sharpe: Decimal = Decimal("1.60")
    rolling_max_drawdown_pct: Decimal = Decimal("8.00")
    total_trades: int = 40
    consecutive_losses: int = 0
    is_active: bool = True
    quarantine_reason: str | None = None
    last_evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DynamicRebalanceProposal(BaseModel):
    """Proposed dynamic multi-strategy weight distribution."""

    proposal_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    method: str
    proposed_weights: dict[str, Decimal]
    rationale: str
    approved: bool = False
    rebalance_token: str | None = None


class ReleaseGateRequest(BaseModel):
    """Request payload for an explicit human release gate."""

    release_type: ReleaseGateType
    operator_id: str
    operator_token: str
    target_identifier: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReleaseGateDecision(BaseModel):
    """Cryptographically logged decision on a release gate request."""

    decision_id: str
    request: ReleaseGateRequest
    is_approved: bool
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_hash: str | None = None


class DailyAutonomousSessionSummary(BaseModel):
    """Post-market reconciliation and telemetry summary for an autonomous session."""

    session_id: str
    date: str
    state: AutonomousSystemState
    start_time: datetime
    end_time: datetime | None = None
    initial_capital: Decimal
    final_capital: Decimal
    realized_pnl: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    circuit_breaker_tripped: bool
    square_off_completed: bool
    reconciliation_hash: str = ""


# Domain Exceptions
class LongTermAutonomousError(Exception):
    """Base exception for long-term autonomous system errors."""


class PrerequisiteNotMetError(LongTermAutonomousError):
    """Raised when earlier post-V1 phases fail prerequisite validation."""


class UnapprovedReleaseError(LongTermAutonomousError):
    """Raised when an autonomous action is attempted without an approved release gate token."""


class AutonomousLifecycleError(LongTermAutonomousError):
    """Raised on invalid lifecycle state transitions or invariant breaches."""


class PortfolioBreachError(LongTermAutonomousError):
    """Raised when a dynamic portfolio operation breaches concentration or safety boundaries."""
