"""System restart recovery manager for resilient crash recovery from SQLite WAL storage."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.capital.capital_manager import CapitalManager
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import ExecutionEngine
from app.models.contracts import (
    OrderRequest,
    OrderType,
    PositionSnapshot,
    TradeSide,
)
from app.watcher.position_watcher import IndependentPositionWatcher

logger = logging.getLogger(__name__)


@dataclass
class SystemRecoveryState:
    """Summary of state recovered from database upon agent restart."""

    recovery_timestamp: datetime
    recovered_positions: list[PositionSnapshot] = field(default_factory=list)
    recovered_orders: list[dict[str, Any]] = field(default_factory=list)
    latest_equity: Decimal = Decimal("100.00")
    available_capital: Decimal = Decimal("100.00")
    high_water_mark: Decimal = Decimal("100.00")
    daily_drawdown: Decimal = Decimal("0.00")
    status: str = "RECOVERED"


class RestartRecoveryManager:
    """Restores portfolio positions, capital state, and non-terminal orders upon process restart."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        db_path: str | None = None,
    ) -> None:
        self.repo = repository or DatabaseRepository(db_path=db_path)
        self.db_path = db_path

    def recover_system_state(
        self,
        position_watcher: IndependentPositionWatcher | None = None,
        capital_manager: CapitalManager | None = None,
        execution_engine: ExecutionEngine | None = None,
    ) -> SystemRecoveryState:
        """Scan SQLite database and rehydrate live in-memory controllers."""
        now = datetime.now(timezone.utc)
        logger.info("Initiating system restart recovery from SQLite WAL database...")

        # 1. Recover Capital State
        latest_cap = self.repo.get_latest_capital_state()
        latest_equity = Decimal("100.00")
        avail_cap = Decimal("100.00")
        hwm = Decimal("100.00")
        daily_dd = Decimal("0.00")

        if latest_cap:
            latest_equity = Decimal(str(latest_cap["total_capital"]))
            avail_cap = Decimal(str(latest_cap["available_capital"]))
            hwm = Decimal(str(latest_cap["high_water_mark"]))
            daily_dd = Decimal(str(latest_cap["daily_drawdown"]))

            if capital_manager:
                capital_manager.available_capital = avail_cap
                capital_manager.deployed_capital = Decimal(str(latest_cap["deployed_capital"]))
                capital_manager.realized_pnl = Decimal(str(latest_cap["realized_pnl"]))
                capital_manager.unrealized_pnl = Decimal(str(latest_cap["unrealized_pnl"]))
                capital_manager.high_water_mark = hwm
                logger.info(
                    "CapitalManager recovered: Equity=%s, Available=%s, HWM=%s",
                    latest_equity,
                    avail_cap,
                    hwm,
                )

        # 2. Recover Open Positions
        open_positions = self.repo.get_open_positions()
        if position_watcher:
            for pos in open_positions:
                position_watcher.open_position(pos)
                logger.info(
                    "PositionWatcher: Restored position %s for %s (%d shares, stop=%s)",
                    pos.position_id,
                    pos.symbol,
                    pos.quantity,
                    pos.hard_stop_price,
                )

        # 3. Recover Active / Non-Terminal Orders
        open_orders = self.repo.get_open_orders()
        if execution_engine:
            for ord_row in open_orders:
                client_id = ord_row["client_order_id"]
                side_val = ord_row["side"]
                req = OrderRequest(
                    client_order_id=client_id,
                    plan_id=ord_row["plan_id"] or "",
                    symbol=ord_row["symbol"],
                    side=TradeSide(side_val),
                    order_type=OrderType(ord_row["order_type"]),
                    quantity=ord_row["quantity"],
                    price=Decimal(str(ord_row["price"])) if ord_row["price"] else None,
                    stop_price=Decimal(str(ord_row["stop_price"])) if ord_row["stop_price"] else None,
                )
                execution_engine._order_requests[client_id] = req
                execution_engine._submitted_timestamps[client_id] = datetime.fromisoformat(
                    ord_row["created_at"]
                )
                logger.info("ExecutionEngine: Restored pending order %s", client_id)

        recovery_state = SystemRecoveryState(
            recovery_timestamp=now,
            recovered_positions=open_positions,
            recovered_orders=open_orders,
            latest_equity=latest_equity,
            available_capital=avail_cap,
            high_water_mark=hwm,
            daily_drawdown=daily_dd,
            status="SUCCESS",
        )

        logger.info(
            "System restart recovery complete: %d open positions, %d active orders recovered.",
            len(open_positions),
            len(open_orders),
        )
        return recovery_state
