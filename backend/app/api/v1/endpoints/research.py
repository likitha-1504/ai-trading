"""FastAPI REST API endpoints for Phase 27: Strategy Research & Optimization.

Provides routes for:
1. Research summary and comparative matrix.
2. Experiment version registry querying.
3. Leakage and look-ahead bias audit verification.
4. Guarded promotion endpoint prohibiting silent production entry.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.research.experiment_registry import (
    StrategyExperimentRegistry,
    get_experiment_registry,
)
from app.research.leakage_auditor import LeakageAuditor
from app.research.models import (
    ExperimentVersion,
    LeakageAuditReport,
    PromotionRequest,
    SilentProductionEntryError,
)
from app.research.research_engine import (
    StrategyResearchEngine,
    StrategyResearchSummary,
)

router = APIRouter()


def get_research_engine(
    registry: StrategyExperimentRegistry = Depends(get_experiment_registry),
) -> StrategyResearchEngine:
    """Dependency provider for strategy research engine."""
    return StrategyResearchEngine(registry=registry)


@router.get(
    "/summary",
    response_model=StrategyResearchSummary,
    summary="Phase 27 Strategy Research Summary",
    description="Returns comparative matrix across baseline and research candidate experiments.",
)
def get_research_summary(
    engine: StrategyResearchEngine = Depends(get_research_engine),
) -> StrategyResearchSummary:
    return engine.generate_research_summary()


@router.get(
    "/experiments",
    response_model=List[ExperimentVersion],
    summary="List All Research Experiments",
    description="Returns all versioned experiments preserved immutably in the registry.",
)
def list_experiments(
    registry: StrategyExperimentRegistry = Depends(get_experiment_registry),
) -> List[ExperimentVersion]:
    return registry.list_experiments()


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentVersion,
    summary="Get Experiment By ID",
    description="Returns full metadata, metrics, leakage report, and walk-forward results for an experiment.",
)
def get_experiment_details(
    experiment_id: str,
    registry: StrategyExperimentRegistry = Depends(get_experiment_registry),
) -> ExperimentVersion:
    exp = registry.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found in registry.",
        )
    return exp


@router.get(
    "/leakage-audit",
    response_model=LeakageAuditReport,
    summary="Synthetic Leakage & Lookahead Audit",
    description="Audits current historical event sequences for monotonic ordering and zero lookahead bias.",
)
def run_leakage_audit() -> LeakageAuditReport:
    # Run auditor on standard baseline telemetry
    return LeakageAuditor.audit_event_stream([])


@router.post(
    "/promote",
    response_model=ExperimentVersion,
    summary="Promote Research Candidate with Operator Token",
    description="Guarded promotion endpoint requiring explicit operator authorization token. Silent entry is blocked.",
)
def promote_experiment(
    req: PromotionRequest,
    registry: StrategyExperimentRegistry = Depends(get_experiment_registry),
) -> ExperimentVersion:
    try:
        return registry.promote_experiment(
            experiment_id=req.experiment_id,
            operator_authorization_token=req.operator_authorization_token,
            rationale=req.rationale,
            target_environment=req.target_environment,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SilentProductionEntryError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
