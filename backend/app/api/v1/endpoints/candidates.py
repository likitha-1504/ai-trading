"""Candidate setup discovery endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_db_repo
from app.db.repository import DatabaseRepository
from app.models.contracts import Candidate

router = APIRouter()


@router.get(
    "",
    response_model=list[Candidate],
    summary="List trade candidates discovered by strategies",
    description="Returns candidates ranked by Momentum Continuation or Early Move Detection strategies.",
)
def list_candidates(
    symbol: str | None = Query(default=None, description="Filter by ticker symbol"),
    strategy: str | None = Query(default=None, description="Filter by strategy type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[Candidate]:
    candidates = repo.get_recent_candidates(limit=limit)
    if symbol:
        candidates = [c for c in candidates if c.symbol == symbol.upper()]
    if strategy:
        candidates = [c for c in candidates if c.strategy_type.value == strategy]
    return candidates


@router.get(
    "/{candidate_id}",
    response_model=Candidate,
    summary="Get single candidate by ID",
    description="Returns complete candidate configuration, quantitative evidence, and entry trigger prices.",
)
def get_candidate_by_id(
    candidate_id: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> Candidate:
    cand = repo.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found",
        )
    return cand
