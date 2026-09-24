"""Order lifecycle read/query endpoints.

NOTE: Strict architectural security invariant:
Arbitrary order creation (e.g. POST /orders) is deliberately NOT exposed.
All orders must originate deterministically from evaluated TradePlans.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_db_repo
from app.db.repository import DatabaseRepository

router = APIRouter()


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List broker orders",
    description="Returns submitted, acknowledged, filled, or rejected orders with fill tracking.",
)
def list_orders(
    order_status: str | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    symbol: str | None = Query(default=None, description="Filter by ticker symbol"),
    limit: int = Query(default=50, ge=1, le=200, description="Max orders to return"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[dict[str, Any]]:
    if order_status and order_status.upper() == "OPEN":
        orders = repo.get_open_orders()
    else:
        orders = repo.get_all_orders(limit=limit)

    if order_status and order_status.upper() != "OPEN":
        orders = [o for o in orders if o.get("status") == order_status.upper()]
    if symbol:
        orders = [o for o in orders if o.get("symbol") == symbol.upper()]

    return orders


@router.get(
    "/{client_order_id}",
    response_model=dict[str, Any],
    summary="Get order details by client_order_id",
    description="Returns order quantity, type, prices, average fill price, and timestamps.",
)
def get_order_by_id(
    client_order_id: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> dict[str, Any]:
    order = repo.get_order(client_order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {client_order_id} not found",
        )
    return order
