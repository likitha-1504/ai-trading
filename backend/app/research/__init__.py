"""Phase 27: Strategy Research & Optimization package."""

from app.research.experiment_registry import (
    StrategyExperimentRegistry,
    get_experiment_registry,
)
from app.research.leakage_auditor import LeakageAuditor
from app.research.models import (
    ExperimentStatus,
    ExperimentVersion,
    LeakageAuditReport,
    PromotionRequest,
    SilentProductionEntryError,
    StrategyHypothesis,
    WalkForwardSummary,
)
from app.research.research_engine import (
    ExperimentComparisonRow,
    StrategyResearchEngine,
    StrategyResearchSummary,
)

__all__ = [
    "ExperimentComparisonRow",
    "ExperimentStatus",
    "ExperimentVersion",
    "LeakageAuditReport",
    "LeakageAuditor",
    "PromotionRequest",
    "SilentProductionEntryError",
    "StrategyExperimentRegistry",
    "StrategyHypothesis",
    "StrategyResearchEngine",
    "StrategyResearchSummary",
    "WalkForwardSummary",
    "get_experiment_registry",
]
