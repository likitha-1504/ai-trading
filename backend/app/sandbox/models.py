"""Data Models and Exceptions for Phase 35 Research Sandbox.

Defines schemas for reproducible datasets, versioned experiment configurations,
isolated execution results, and the explicit promotion protocol.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SandboxIsolationState(str, Enum):
    """Lifecycle state of the research sandbox isolation boundary."""

    QUARANTINED = "QUARANTINED"
    ACTIVE = "ACTIVE"
    VIOLATION_DETECTED = "VIOLATION_DETECTED"


class PromotionStage(str, Enum):
    """Progression pipeline of strategy experiments through governance."""

    DRAFT = "DRAFT"
    SANDBOX_EXECUTED = "SANDBOX_EXECUTED"
    REPRODUCIBILITY_VERIFIED = "REPRODUCIBILITY_VERIFIED"
    PROMOTION_REQUESTED = "PROMOTION_REQUESTED"
    APPROVED_CANDIDATE = "APPROVED_CANDIDATE"
    REJECTED = "REJECTED"


class DatasetSplit(str, Enum):
    """Partition classification for temporal datasets."""

    TRAIN = "TRAIN"
    TEST = "TEST"
    WALK_FORWARD = "WALK_FORWARD"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"


class SandboxBar(BaseModel):
    """OHLCV market bar for reproducible simulation."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ReproducibleDataset(BaseModel):
    """Cryptographically fingerprinted dataset for deterministic simulations."""

    dataset_id: str
    name: str
    version: str
    record_count: int
    sha256_hash: str
    seed: int = 42
    start_time: datetime
    end_time: datetime
    split: DatasetSplit = DatasetSplit.TRAIN
    metadata: dict[str, Any] = Field(default_factory=dict)
    bars: list[SandboxBar] = Field(default_factory=list)


class VersionedExperimentConfig(BaseModel):
    """Versioned configuration linking code, parameters, risk bounds, and dataset."""

    experiment_id: str
    strategy_name: str
    version: str
    parameters: dict[str, Any]
    risk_limits: dict[str, float]
    code_hash: str
    dataset_id: str
    dataset_hash: str
    config_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""


class SandboxExecutionMetrics(BaseModel):
    """Quantitative performance metrics generated within the sandbox."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    net_pnl: float
    gross_pnl: float
    total_fees_slippage: float


class SandboxExecutionResult(BaseModel):
    """Execution telemetry captured from an isolated sandbox experiment run."""

    run_id: str
    experiment_id: str
    dataset_id: str
    dataset_hash: str
    config_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: SandboxExecutionMetrics
    execution_hash: str
    isolation_verified: bool
    reproducibility_verified: bool = False


class PromotionHurdles(BaseModel):
    """Statistical thresholds required for promotion out of the sandbox."""

    min_trades: int = 20
    min_win_rate: float = 0.50
    min_profit_factor: float = 1.30
    min_sharpe_ratio: float = 1.20
    max_drawdown_pct: float = 2.50


class PromotionEvaluation(BaseModel):
    """Evaluation scorecard of a candidate against promotion criteria."""

    experiment_id: str
    passed_statistical_hurdles: bool
    reproducibility_verified: bool
    leakage_free: bool
    operator_token_valid: bool
    target_stage: PromotionStage
    rejection_reasons: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromotionRequest(BaseModel):
    """Formal operator submission requesting strategy promotion."""

    experiment_id: str
    target_environment: str = "PAPER_CANDIDATE"
    operator_token: str
    operator_id: str = "OPERATOR_01"
    rationale: str


class PromotionResult(BaseModel):
    """Outcome of promotion gate evaluation and audit logging."""

    success: bool
    experiment_id: str
    stage: PromotionStage
    promoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_ledger_id: str | None = None
    message: str


# =========================================================================
# Domain Exceptions
# =========================================================================

class ProductionIsolationError(Exception):
    """Raised when sandbox code attempts to touch production database or live broker."""


class DatasetReproducibilityError(Exception):
    """Raised when re-executing an experiment produces divergent statistical results."""


class PromotionGateError(Exception):
    """Raised when promotion criteria are breached."""


class SilentPromotionError(PromotionGateError):
    """Raised when an unauthenticated or silent attempt to promote an experiment occurs."""
