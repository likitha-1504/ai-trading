"""Research Sandbox Package for Phase 35.

Provides production isolation, cryptographically hashed reproducible datasets,
versioned experiment configurations, simulation engine, and governed promotion gate.
"""

from app.sandbox.dataset_registry import (
    ReproducibleDatasetRegistry,
    compute_bars_sha256,
)
from app.sandbox.isolation_guard import (
    SandboxIsolationGuard,
    _sandbox_active_var,
)
from app.sandbox.models import (
    DatasetReproducibilityError,
    DatasetSplit,
    ProductionIsolationError,
    PromotionEvaluation,
    PromotionGateError,
    PromotionHurdles,
    PromotionRequest,
    PromotionResult,
    PromotionStage,
    ReproducibleDataset,
    SandboxBar,
    SandboxExecutionMetrics,
    SandboxExecutionResult,
    SandboxIsolationState,
    SilentPromotionError,
    VersionedExperimentConfig,
)
from app.sandbox.promotion_gate import ExplicitPromotionGate
from app.sandbox.sandbox_engine import (
    ResearchSandboxEngine,
    compute_execution_hash,
)
from app.sandbox.versioned_config import (
    VersionedConfigManager,
    compute_config_hash,
)

__all__ = [
    "DatasetReproducibilityError",
    "DatasetSplit",
    "ExplicitPromotionGate",
    "ProductionIsolationError",
    "PromotionEvaluation",
    "PromotionGateError",
    "PromotionHurdles",
    "PromotionRequest",
    "PromotionResult",
    "PromotionStage",
    "ReproducibleDataset",
    "ReproducibleDatasetRegistry",
    "ResearchSandboxEngine",
    "SandboxBar",
    "SandboxExecutionMetrics",
    "SandboxExecutionResult",
    "SandboxIsolationGuard",
    "SandboxIsolationState",
    "SilentPromotionError",
    "VersionedConfigManager",
    "VersionedExperimentConfig",
    "_sandbox_active_var",
    "compute_bars_sha256",
    "compute_config_hash",
    "compute_execution_hash",
]
