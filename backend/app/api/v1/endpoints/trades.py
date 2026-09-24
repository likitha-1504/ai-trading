"""Trade journal and guarded TradePlan approval endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    SystemState,
    get_db_repo,
    get_execution_engine,
    get_system_state,
)
from app.api.schemas import (
    PlanApprovalRequest,
    PlanApprovalResponse,
    PlanRejectionRequest,
    PlanRejectionResponse,
)
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import ExecutionEngine
from app.models.contracts import (
    ApprovalMode,
    OrderRequest,
    OrderStatus,
    OrderType,
    TradeRecord,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[TradeRecord],
    summary="List executed trades",
    description="Returns trade journal entries with entry/exit timestamps, prices, and Indian statutory friction breakdown.",
)
def list_trades(
    symbol: str | None = Query(default=None, description="Filter by ticker symbol"),
    strategy: str | None = Query(default=None, description="Filter by strategy type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max trades to return"),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[TradeRecord]:
    trades = repo.get_recent_trades(limit=limit)
    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]
    if strategy:
        trades = [t for t in trades if t.strategy.value == strategy]
    return trades


@router.get(
    "/{trade_id}",
    response_model=TradeRecord,
    summary="Get single trade by ID",
    description="Returns detailed trade fill record, execution slippage, holding duration, and net P/L.",
)
def get_trade_by_id(
    trade_id: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> TradeRecord:
    trade = repo.get_trade(trade_id)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade {trade_id} not found",
        )
    return trade


@router.post(
    "/approve/{plan_id}",
    response_model=PlanApprovalResponse,
    summary="Approve a pending TradePlan (Guarded Mutation)",
    description="Operator authorization for a TradePlan held in MANUAL_PENDING mode. Dispatches to execution engine.",
)
def approve_pending_trade_plan(
    plan_id: str,
    payload: PlanApprovalRequest = PlanApprovalRequest(),
    repo: DatabaseRepository = Depends(get_db_repo),
    exec_engine: ExecutionEngine = Depends(get_execution_engine),
    sys_state: SystemState = Depends(get_system_state),
) -> PlanApprovalResponse:
    if sys_state.is_halted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is currently halted. Approvals are suspended.",
        )

    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation is required to approve trade plan.",
        )

    plan = repo.get_trade_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TradePlan {plan_id} not found",
        )

    if plan.approval_mode != ApprovalMode.MANUAL_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TradePlan {plan_id} is in status '{plan.approval_mode.value}', cannot approve.",
        )

    # Dispatch order according strictly to the validated TradePlan
    client_order_id = f"ord-{plan.plan_id}"
    order_req = OrderRequest(
        client_order_id=client_order_id,
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        side=plan.side,
        order_type=OrderType.MARKET,
        quantity=plan.quantity,
        price=plan.entry_price_target,
        stop_price=plan.hard_stop_price,
    )

    # Persist updated status
    repo.update_trade_plan_approval(plan_id, ApprovalMode.MANUAL_APPROVED)
    repo.save_order(order_req, status=OrderStatus.SUBMITTED)
    exec_engine.submit_order(order_req)

    return PlanApprovalResponse(
        success=True,
        plan_id=plan_id,
        approval_mode=ApprovalMode.MANUAL_APPROVED,
        client_order_id=client_order_id,
        message=f"TradePlan {plan_id} manually approved and dispatched to execution engine.",
    )


@router.post(
    "/reject/{plan_id}",
    response_model=PlanRejectionResponse,
    summary="Reject a pending TradePlan (Guarded Mutation)",
    description="Operator rejection for a TradePlan held in MANUAL_PENDING mode.",
)
def reject_pending_trade_plan(
    plan_id: str,
    payload: PlanRejectionRequest = PlanRejectionRequest(),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> PlanRejectionResponse:
    plan = repo.get_trade_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TradePlan {plan_id} not found",
        )

    if plan.approval_mode != ApprovalMode.MANUAL_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TradePlan {plan_id} is in status '{plan.approval_mode.value}', cannot reject.",
        )

    repo.update_trade_plan_approval(plan_id, ApprovalMode.REJECTED)

    return PlanRejectionResponse(
        success=True,
        plan_id=plan_id,
        approval_mode=ApprovalMode.REJECTED,
        message=f"TradePlan {plan_id} has been rejected: {payload.reason}",
    )
