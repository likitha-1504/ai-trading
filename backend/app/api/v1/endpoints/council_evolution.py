"""FastAPI Endpoints for Phase 36 AI Council Evolution & Safety Decoupling."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.council_evolution.evolution_orchestrator import CouncilEvolutionOrchestrator
from app.council_evolution.models import (
    CouncilEvolutionReport,
    CouncilIndependenceAttestation,
    ModelJustificationScorecard,
    UnjustifiedModelError,
)

router = APIRouter(prefix="/council-evolution", tags=["AI Council Evolution"])

_orchestrator = CouncilEvolutionOrchestrator()


@router.get("/status", response_model=dict[str, Any])
def get_council_evolution_status() -> dict[str, Any]:
    """Retrieves current AI Council composition and candidate evaluation status."""
    active = _orchestrator.admission_gate.get_active_council()
    candidates = _orchestrator.admission_gate.list_candidate_scorecards()
    return {
        "active_council_models": active,
        "active_models_count": len(active),
        "candidates_evaluated_count": len(candidates),
        "justified_candidates_count": sum(1 for c in candidates if c.is_justified),
    }


@router.get("/candidates", response_model=list[ModelJustificationScorecard])
def list_candidate_scorecards() -> list[ModelJustificationScorecard]:
    """Lists all candidate models with their measurable justification scorecards."""
    return _orchestrator.admission_gate.list_candidate_scorecards()


@router.post("/evaluate-candidate", response_model=ModelJustificationScorecard)
def evaluate_candidate_model(
    candidate_id: str = Query(..., description="ID of candidate model to evaluate"),
) -> ModelJustificationScorecard:
    """Evaluates candidate model against all 5 measurable justification hurdles."""
    try:
        return _orchestrator.admission_gate.evaluate_candidate(candidate_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/admit-model", response_model=ModelJustificationScorecard)
def admit_candidate_model(
    candidate_id: str = Query(..., description="ID of candidate model to admit"),
    operator_token: str = Query(..., description="Signed operator authorization token"),
    operator_id: str = Query("OPERATOR_01", description="Operator identity"),
) -> ModelJustificationScorecard:
    """Admits a candidate model to active council if measurable justification is satisfied."""
    try:
        return _orchestrator.admission_gate.admit_model(
            candidate_id=candidate_id,
            operator_token=operator_token,
            operator_id=operator_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UnjustifiedModelError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/audit-independence", response_model=CouncilIndependenceAttestation)
def audit_safety_independence() -> CouncilIndependenceAttestation:
    """Executes drill verifying Trade Gate and Position Watcher survive total AI blackouts."""
    return _orchestrator.independence_guard.audit_complete_independence()


@router.get("/audit", response_model=CouncilEvolutionReport)
def run_full_council_audit() -> CouncilEvolutionReport:
    """Executes comprehensive Phase 36 audit across model justification and safety decoupling."""
    return _orchestrator.run_council_evolution_audit()
