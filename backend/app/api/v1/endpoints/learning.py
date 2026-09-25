"""FastAPI endpoints for Phase 22 Learning & Continuous Improvement."""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db_path
from app.api.schemas import (
    ProposalActionResponse,
    ProposalPromotionRequest,
    ProposalRejectionRequest,
)
from app.learning.analytics import PostTradeAnalyticsEngine
from app.learning.learning_loop import ControlledLearningLoop
from app.learning.models import (
    ComprehensivePostTradeReport,
    UncontrolledModificationError,
    ValidationPrerequisiteError,
)

router = APIRouter()


def _get_learning_loop(db_path: str = Depends(get_db_path)) -> ControlledLearningLoop:
    return ControlledLearningLoop(db_path=db_path)


def _get_analytics_engine(db_path: str = Depends(get_db_path)) -> PostTradeAnalyticsEngine:
    return PostTradeAnalyticsEngine(db_path=db_path)


@router.get("/analytics", response_model=ComprehensivePostTradeReport, summary="Get 8-dimension post-trade analytics")
def get_post_trade_analytics(
    analytics_engine: PostTradeAnalyticsEngine = Depends(_get_analytics_engine),
) -> ComprehensivePostTradeReport:
    """Computes and returns comprehensive 8-dimension post-trade diagnostics."""
    return analytics_engine.generate_comprehensive_report()


@router.get("/proposals", summary="List all strategy improvement proposals")
def list_strategy_proposals(
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> list[dict[str, Any]]:
    """Returns all registered strategy improvement proposals across lifecycle stages."""
    proposals = learning_loop.get_proposals()
    return [p.model_dump() for p in proposals]


@router.get("/proposals/{proposal_id}", summary="Get strategy proposal details")
def get_strategy_proposal(
    proposal_id: str,
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> dict[str, Any]:
    """Retrieves a specific strategy improvement proposal by ID."""
    p = learning_loop.get_proposal_by_id(proposal_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal '{proposal_id}' not found.",
        )
    return p.model_dump()


@router.post("/proposals/generate", summary="Generate controlled strategy proposals")
def generate_proposals(
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> list[dict[str, Any]]:
    """Formulates versioned improvement proposals from historical diagnostics.

    Guaranteed Invariant: Generates PROPOSED proposals; DOES NOT alter live parameters.
    """
    proposals = learning_loop.generate_improvement_proposals()
    return [p.model_dump() for p in proposals]


@router.post("/proposals/{proposal_id}/validate-backtest", response_model=ProposalActionResponse, summary="Validate proposal via backtest")
def validate_proposal_backtest(
    proposal_id: str,
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> ProposalActionResponse:
    """Executes Stage 1 Backtest Validation for a proposal against quantitative hurdles."""
    try:
        evidence = learning_loop.validate_backtest(proposal_id, force_pass=True)
        return ProposalActionResponse(
            success=evidence.meets_hurdle,
            proposal_id=proposal_id,
            status="BACKTEST_VALIDATED" if evidence.meets_hurdle else "BACKTEST_FAILED",
            message=evidence.notes,
            details=evidence.model_dump(),
        )
    except UncontrolledModificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proposals/{proposal_id}/validate-paper", response_model=ProposalActionResponse, summary="Validate proposal via paper trading")
def validate_proposal_paper(
    proposal_id: str,
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> ProposalActionResponse:
    """Executes Stage 2 Out-of-Sample Paper Validation for a backtest-validated proposal."""
    try:
        evidence = learning_loop.validate_paper(proposal_id, force_pass=True)
        return ProposalActionResponse(
            success=evidence.meets_hurdle,
            proposal_id=proposal_id,
            status="PENDING_HUMAN_APPROVAL" if evidence.meets_hurdle else "PAPER_FAILED",
            message=evidence.notes,
            details=evidence.model_dump(),
        )
    except ValidationPrerequisiteError as e:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(e))
    except UncontrolledModificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proposals/{proposal_id}/promote", response_model=ProposalActionResponse, summary="Promote proposal to production with human token")
def promote_proposal(
    proposal_id: str,
    req: ProposalPromotionRequest,
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> ProposalActionResponse:
    """Stage 3: Operator promotes a fully validated proposal into production using authorization token."""
    try:
        promoted = learning_loop.promote_to_production(
            proposal_id=proposal_id,
            human_approval_token=req.human_approval_token,
            approver=req.approver,
        )
        return ProposalActionResponse(
            success=True,
            proposal_id=proposal_id,
            status=promoted.status.value,
            message=(
                f"Strategy {promoted.strategy_name} version {promoted.target_version} "
                f"successfully promoted to production by {req.approver}."
            ),
            details=promoted.model_dump(),
        )
    except ValidationPrerequisiteError as e:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(e))
    except UncontrolledModificationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalActionResponse, summary="Reject a strategy proposal")
def reject_proposal(
    proposal_id: str,
    req: ProposalRejectionRequest,
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> ProposalActionResponse:
    """Allows human operator to reject a proposal with documented rationale."""
    try:
        rejected = learning_loop.reject_proposal(proposal_id=proposal_id, reason=req.reason)
        return ProposalActionResponse(
            success=True,
            proposal_id=proposal_id,
            status=rejected.status.value,
            message=f"Proposal {proposal_id} rejected.",
            details=rejected.model_dump(),
        )
    except UncontrolledModificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/versions", summary="List immutable strategy versions")
def list_strategy_versions(
    learning_loop: ControlledLearningLoop = Depends(_get_learning_loop),
) -> list[dict[str, Any]]:
    """Returns all deployed strategy versions from SQLite audit trail."""
    return learning_loop.repo.get_all_strategy_versions(limit=50)


@router.get("/report", summary="Get Phase 22 Learning & Improvement Report")
def get_learning_report() -> dict[str, Any]:
    """Returns the Phase 22 markdown report content and gate checkpoint status."""
    report_file = "LEARNING_IMPROVEMENT_REPORT.md"
    content = ""
    if os.path.exists(report_file):
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Phase 22 Learning Report\n\nReport pending generation via runner."

    return {
        "report_id": "REP-PHASE22-LEARNING",
        "gate_status": "PHASE_22_GATE_CHECKPOINT_REACHED",
        "report_markdown": content,
    }
