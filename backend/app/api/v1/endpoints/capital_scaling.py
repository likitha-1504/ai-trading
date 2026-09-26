"""FastAPI REST API endpoints for Phase 29: Controlled Capital Scaling.

Provides routes for:
1. Capital scaling summary and active ceiling telemetry.
2. Configured discrete capital stage parameters.
3. Scaling prerequisite eligibility auditing.
4. Transition and rollback audit history.
5. Guarded stage escalation endpoint prohibiting automatic scaling from performance.
6. Atomic rollback endpoint.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.capital_scaling.models import (
    CapitalScalingSummary,
    CapitalStageDefinition,
    ScalingEligibility,
    ScalingTransitionRecord,
    StageRollbackRequest,
    StageTransitionRequest,
    UnauthorizedCapitalEscalationError,
)
from app.capital_scaling.scaling_manager import (
    ControlledCapitalScalingManager,
    get_capital_scaling_manager,
)

router = APIRouter()


def get_scaling_mgr(
    manager: ControlledCapitalScalingManager = Depends(get_capital_scaling_manager),
) -> ControlledCapitalScalingManager:
    """Dependency provider for controlled capital scaling manager."""
    return manager


@router.get(
    "/summary",
    response_model=CapitalScalingSummary,
    summary="Phase 29 Capital Scaling Summary",
    description="Returns current active capital stage, ceiling, autonomous limits, and reconciliation status.",
)
def get_scaling_summary(
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> CapitalScalingSummary:
    return manager.generate_scaling_summary()


@router.get(
    "/stages",
    response_model=List[CapitalStageDefinition],
    summary="List Configured Capital Stages",
    description="Returns discrete capital stages, capital limits, risk parameters, and promotion prerequisites.",
)
def list_capital_stages(
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> List[CapitalStageDefinition]:
    return manager.list_stage_definitions()


@router.get(
    "/eligibility",
    response_model=ScalingEligibility,
    summary="Scaling Prerequisite Eligibility",
    description="Audits current performance against prerequisite criteria for the next capital stage.",
)
def get_scaling_eligibility(
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> ScalingEligibility:
    return manager.evaluate_eligibility()


@router.get(
    "/history",
    response_model=List[ScalingTransitionRecord],
    summary="Transition and Rollback Audit History",
    description="Returns chronologically ordered audit log of all capital stage escalations and defensive rollbacks.",
)
def get_transition_history(
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> List[ScalingTransitionRecord]:
    return manager.get_transition_history()


@router.post(
    "/transition",
    response_model=ScalingTransitionRecord,
    summary="Transition to Target Capital Stage",
    description="Escalates capital stage with mandatory operator authorization token. Automatic scaling is rejected.",
)
def transition_stage(
    req: StageTransitionRequest,
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> ScalingTransitionRecord:
    try:
        return manager.transition_stage(
            target_stage=req.target_stage,
            operator_authorization_token=req.operator_authorization_token,
            rationale=req.rationale,
        )
    except UnauthorizedCapitalEscalationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/rollback",
    response_model=ScalingTransitionRecord,
    summary="Rollback Capital to Safe Stage",
    description="Atomically rolls back capital stage with pre/post reconciliation and mandatory operator rollback token.",
)
def rollback_stage(
    req: StageRollbackRequest,
    manager: ControlledCapitalScalingManager = Depends(get_scaling_mgr),
) -> ScalingTransitionRecord:
    try:
        return manager.rollback_to_stage(
            target_stage=req.target_stage,
            operator_authorization_token=req.operator_authorization_token,
            reason=req.reason,
        )
    except UnauthorizedCapitalEscalationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
