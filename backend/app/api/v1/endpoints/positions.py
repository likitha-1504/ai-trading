"""Position monitor endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_db_repo
from app.db.repository import DatabaseRepository
from app.models.contracts import PositionSnapshot

router = APIRouter()


@router.get(
    "",
    response_model=list[PositionSnapshot],
    summary="List positions tracked by system",
    description="Returns active, closing, and closed positions with stop-loss and trailing protection levels.",
)
def list_positions(
    position_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status (OPEN, CLOSING, CLOSED)",
    ),
    symbol: str | None = Query(default=None, description="Filter by ticker symbol"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[PositionSnapshot]:
    if position_status and position_status.upper() == "OPEN":
        positions = repo.get_open_positions()
    else:
        positions = repo.get_all_positions()

    if position_status and position_status.upper() != "OPEN":
        positions = [
            p for p in positions if p.status.value == position_status.upper()
        ]
    if symbol:
        positions = [p for p in positions if p.symbol == symbol.upper()]

    return positions


@router.get(
    "/{position_id}",
    response_model=PositionSnapshot,
    summary="Get position details by ID",
    description="Returns entry price, hard stop, take profit, trailing trigger, unrealized P/L, and exit reasons.",
)
def get_position_by_id(
    position_id: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> PositionSnapshot:
    pos = repo.get_position(position_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found",
        )
    return pos
