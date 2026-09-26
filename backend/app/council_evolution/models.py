"""Data Models and Exceptions for Phase 36 AI Council Evolution.

Defines schemas for measurable model justification scorecards, candidate model
benchmarks, council roles, and deterministic gate/watcher independence attestations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CouncilRole(str, Enum):
    """Functional role of an AI model in the deliberation council."""

    PRIMARY_ANALYST = "PRIMARY_ANALYST"
    ADVERSARIAL_CHALLENGER = "ADVERSARIAL_CHALLENGER"
    MACRO_SENTIMENT_SPECIALIST = "MACRO_SENTIMENT_SPECIALIST"
    MICROSTRUCTURE_ANALYST = "MICROSTRUCTURE_ANALYST"
    CANDIDATE_MODEL = "CANDIDATE_MODEL"


class AdmissionStatus(str, Enum):
    """Lifecycle status of a candidate model undergoing council evaluation."""

    PROPOSED = "PROPOSED"
    BENCHMARKING = "BENCHMARKING"
    JUSTIFIED = "JUSTIFIED"
    REJECTED = "REJECTED"
    ADMITTED = "ADMITTED"


class MeasurableHurdles(BaseModel):
    """Strict quantitative criteria required before admitting any new model to the council."""

    min_accuracy_uplift_pct: float = 3.0       # Minimum directional win rate / precision uplift
    min_downside_capital_saved: float = 20.0   # Downside capital preserved through distinct critiques
    min_diversity_score: float = 0.25          # Disagreement entropy / reasoning orthogonal index
    max_p95_latency_ms: float = 2500.0         # Strict sub-2.5s inference latency budget
    max_token_cost_ratio: float = 1.50         # Cost efficiency ceiling


class CandidateModelBenchmark(BaseModel):
    """Empirical evaluation metrics collected across benchmark test suites."""

    candidate_id: str
    name: str
    proposed_role: CouncilRole
    test_cases_evaluated: int
    directional_accuracy_pct: float
    accuracy_uplift_pct: float
    downside_capital_saved_inr: float
    reasoning_diversity_score: float
    p95_latency_ms: float
    token_cost_ratio: float
    benchmark_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelJustificationScorecard(BaseModel):
    """Formal audit scorecard determining measurable justification for model admission."""

    candidate_id: str
    model_name: str
    role: CouncilRole
    status: AdmissionStatus
    is_justified: bool
    hurdles_evaluated: MeasurableHurdles
    realized_metrics: CandidateModelBenchmark
    admission_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CouncilIndependenceAttestation(BaseModel):
    """Cryptographic attestation proving Trade Gate & Position Watcher independence from AI availability."""

    trade_gate_zero_llm_dependency: bool
    position_watcher_zero_llm_dependency: bool
    models_offline_blackout_tested: bool
    unanimous_ai_buy_override_blocked: bool
    position_watcher_sub_50ms_sla: bool
    realized_watcher_latency_us: float
    attestation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attestation_hash: str
    evidence_details: dict[str, Any] = Field(default_factory=dict)


class CouncilEvolutionReport(BaseModel):
    """Master telemetry report for Phase 36 AI Council Evolution audit."""

    audit_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_council_models: list[dict[str, str]]
    candidate_scorecards: list[ModelJustificationScorecard]
    independence_attestation: CouncilIndependenceAttestation
    overall_status: str


# =========================================================================
# Domain Exceptions
# =========================================================================

class UnjustifiedModelError(Exception):
    """Raised when attempting to admit a model without meeting measurable justification hurdles."""


class ModelDependencyViolationError(Exception):
    """Raised when deterministic Trade Gate or Position Watcher is found to depend on AI availability."""
