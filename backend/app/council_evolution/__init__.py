"""AI Council Evolution Package for Phase 36.

Enforces measurable justification for model additions and guarantees absolute
independence of deterministic Trade Gate and Position Watcher from model availability.
"""

from app.council_evolution.admission_gate import ModelAdmissionGate
from app.council_evolution.evolution_orchestrator import CouncilEvolutionOrchestrator
from app.council_evolution.independence_guard import CouncilIndependenceGuard
from app.council_evolution.models import (
    AdmissionStatus,
    CandidateModelBenchmark,
    CouncilEvolutionReport,
    CouncilIndependenceAttestation,
    CouncilRole,
    MeasurableHurdles,
    ModelDependencyViolationError,
    ModelJustificationScorecard,
    UnjustifiedModelError,
)

__all__ = [
    "AdmissionStatus",
    "CandidateModelBenchmark",
    "CouncilEvolutionOrchestrator",
    "CouncilEvolutionReport",
    "CouncilIndependenceAttestation",
    "CouncilIndependenceGuard",
    "CouncilRole",
    "MeasurableHurdles",
    "ModelAdmissionGate",
    "ModelDependencyViolationError",
    "ModelJustificationScorecard",
    "UnjustifiedModelError",
]
