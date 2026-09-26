"""Phase 37 Long-Term Autonomous System Package.

Provides broader autonomous operations, dynamic strategy portfolio management,
multi-phase prerequisite verification, and cryptographically enforced explicit release gates.
"""

from app.long_term_autonomous.lifecycle_orchestrator import LongTermAutonomousOrchestrator
from app.long_term_autonomous.models import (
    AutonomousLifecycleError,
    AutonomousSystemState,
    DailyAutonomousSessionSummary,
    DynamicRebalanceProposal,
    LongTermAutonomousError,
    LongTermStrategyProfile,
    PortfolioBreachError,
    PrerequisiteDimension,
    PrerequisiteNotMetError,
    PrerequisitePhaseAudit,
    ReleaseGateDecision,
    ReleaseGateRequest,
    ReleaseGateType,
    StrategyLifecycleStage,
    UnapprovedReleaseError,
)
from app.long_term_autonomous.portfolio_governor import AutonomousPortfolioGovernor
from app.long_term_autonomous.prerequisite_gate import LongTermPrerequisiteGate
from app.long_term_autonomous.release_gate import AutonomousReleaseGate

__all__ = [
    "AutonomousLifecycleError",
    "AutonomousPortfolioGovernor",
    "AutonomousReleaseGate",
    "AutonomousSystemState",
    "DailyAutonomousSessionSummary",
    "DynamicRebalanceProposal",
    "LongTermAutonomousError",
    "LongTermAutonomousOrchestrator",
    "LongTermPrerequisiteGate",
    "LongTermStrategyProfile",
    "PortfolioBreachError",
    "PrerequisiteDimension",
    "PrerequisiteNotMetError",
    "PrerequisitePhaseAudit",
    "ReleaseGateDecision",
    "ReleaseGateRequest",
    "ReleaseGateType",
    "StrategyLifecycleStage",
    "UnapprovedReleaseError",
]
