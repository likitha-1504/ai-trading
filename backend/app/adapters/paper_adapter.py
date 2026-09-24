"""Simulated Paper Broker Adapter for development, testing, and paper trading.

Fulfills Phase 08 requirements:
- High-fidelity order simulation with configurable latency and realistic slippage
- Full lifecycle emulation: CREATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED/CANCELLED/REJECTED
- Fault injection: broker disconnects, simulated rejections, partial fills
- Portfolio reconciliation against local position snapshots
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.adapters.broker_base import BrokerAdapter
from app.models.contracts import (
    AccountBalance,
    BrokerPosition,
    OrderEvent,
    OrderRequest,
    OrderStatus,
    PositionSnapshot,
    PositionStatus,
    ReconciliationMismatch,
    ReconciliationReport,
    TradeSide,
)

logger = logging.getLogger(__name__)


class PaperAdapter(BrokerAdapter):
    """Realistic paper execution adapter with simulated liquidity, slippage, and state transitions."""

    def __init__(
        self,
        initial_cash: Decimal = Decimal("100.00"),
        slippage_ticks: int = 1,
        tick_size: Decimal = Decimal("0.05"),
        simulated_latency_ms: float = 0.0,
    ) -> None:
        super().__init__()
        self._connected: bool = True
        self.initial_cash = initial_cash
        self.cash_balance: Decimal = initial_cash
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size
        self.simulated_latency_ms = simulated_latency_ms

        # Internal paper records
        self._orders: dict[str, OrderEvent] = {}
        self._positions: dict[str, BrokerPosition] = {}

        # Fault injection controls
        self.simulate_rejection_symbols: set[str] = set()
        self.simulate_partial_fill: bool = False
        self.partial_fill_qty: int = 1

    @property
    def is_connected(self) -> bool:
        """Connection status."""
        return self._connected

    def connect(self) -> bool:
        """Establish paper connection."""
        self._connected = True
        logger.info("PaperAdapter connected successfully")
        return True

    def disconnect(self) -> None:
        """Disconnect paper adapter."""
        self._connected = False
        logger.warning("PaperAdapter disconnected")

    def get_account_balance(self) -> AccountBalance:
        """Query account balance, used margin, and equity."""
        used_margin = sum(
            (p.entry_price * Decimal(p.quantity) for p in self._positions.values()),
            Decimal("0.00"),
        )
        floating_pnl = sum(
            (p.unrealized_pnl for p in self._positions.values()),
            Decimal("0.00"),
        )
        total_equity = self.cash_balance + used_margin + floating_pnl
        return AccountBalance(
            currency="INR",
            cash_balance=self.cash_balance.quantize(Decimal("0.01")),
            available_margin=max(Decimal("0.00"), self.cash_balance).quantize(Decimal("0.01")),
            used_margin=used_margin.quantize(Decimal("0.01")),
            total_equity=total_equity.quantize(Decimal("0.01")),
        )

    def get_positions(self) -> list[BrokerPosition]:
        """Fetch all currently open positions."""
        return list(self._positions.values())

    def get_orders(self) -> list[OrderEvent]:
        """Fetch all orders submitted."""
        return list(self._orders.values())

    def update_market_price(self, symbol: str, current_price: Decimal) -> None:
        """Update simulated market price for an active paper position."""
        sym_key = symbol.upper()
        if sym_key in self._positions:
            pos = self._positions[sym_key]
            pos.current_price = current_price
            if pos.side == TradeSide.BUY:
                pos.unrealized_pnl = (current_price - pos.entry_price) * Decimal(pos.quantity)
            else:
                pos.unrealized_pnl = (pos.entry_price - current_price) * Decimal(pos.quantity)

    def submit_order(self, request: OrderRequest) -> OrderEvent:
        """Process order submission through complete simulated broker lifecycle."""
        now = datetime.now(timezone.utc)
        sym_key = request.symbol.upper()

        if not self._connected:
            rejected_event = OrderEvent(
                client_order_id=request.client_order_id,
                broker_order_id=None,
                symbol=sym_key,
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                remaining_quantity=request.quantity,
                rejection_reason="Broker adapter connection offline",
                timestamp=now,
            )
            self._orders[request.client_order_id] = rejected_event
            self._notify_order_event(rejected_event)
            return rejected_event

        # 1. Fault injection: Check simulated rejection
        if sym_key in self.simulate_rejection_symbols:
            rejected_event = OrderEvent(
                client_order_id=request.client_order_id,
                broker_order_id=f"brk-{uuid.uuid4().hex[:8]}",
                symbol=sym_key,
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                remaining_quantity=request.quantity,
                rejection_reason=f"Risk check failed: instrument {sym_key} blocked by broker",
                timestamp=now,
            )
            self._orders[request.client_order_id] = rejected_event
            self._notify_order_event(rejected_event)
            return rejected_event

        broker_order_id = f"brk-{uuid.uuid4().hex[:8]}"

        # 2. Emulate SUBMITTED -> ACKNOWLEDGED
        ack_event = OrderEvent(
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            symbol=sym_key,
            status=OrderStatus.ACKNOWLEDGED,
            filled_quantity=0,
            remaining_quantity=request.quantity,
            timestamp=now,
        )
        self._orders[request.client_order_id] = ack_event
        self._notify_order_event(ack_event)

        # 3. Compute realistic fill price with slippage
        base_price = request.price or Decimal("100.00")
        slippage_amount = self.tick_size * Decimal(self.slippage_ticks)
        if request.side == TradeSide.BUY:
            fill_price = base_price + slippage_amount
        else:
            fill_price = base_price - slippage_amount
        fill_price = fill_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 4. Check for partial fill simulation
        if self.simulate_partial_fill and request.quantity > self.partial_fill_qty:
            partial_filled = self.partial_fill_qty
            remaining = request.quantity - partial_filled
            partial_event = OrderEvent(
                client_order_id=request.client_order_id,
                broker_order_id=broker_order_id,
                symbol=sym_key,
                status=OrderStatus.PARTIALLY_FILLED,
                filled_quantity=partial_filled,
                remaining_quantity=remaining,
                average_fill_price=fill_price,
                timestamp=datetime.now(timezone.utc),
            )
            self._orders[request.client_order_id] = partial_event
            self._apply_fill(sym_key, request.side, partial_filled, fill_price)
            self._notify_order_event(partial_event)
            return partial_event

        # 5. Full Fill execution
        filled_event = OrderEvent(
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            symbol=sym_key,
            status=OrderStatus.FILLED,
            filled_quantity=request.quantity,
            remaining_quantity=0,
            average_fill_price=fill_price,
            timestamp=datetime.now(timezone.utc),
        )
        self._orders[request.client_order_id] = filled_event
        self._apply_fill(sym_key, request.side, request.quantity, fill_price)
        self._notify_order_event(filled_event)
        return filled_event

    def cancel_order(self, client_order_id: str) -> OrderEvent:
        """Cancel an unfilled or partially filled order."""
        if client_order_id not in self._orders:
            raise KeyError(f"Order {client_order_id} not found")

        current_event = self._orders[client_order_id]
        if current_event.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            raise ValueError(f"Cannot cancel order in terminal state {current_event.status.value}")

        cancelled_event = OrderEvent(
            client_order_id=client_order_id,
            broker_order_id=current_event.broker_order_id,
            symbol=current_event.symbol,
            status=OrderStatus.CANCELLED,
            filled_quantity=current_event.filled_quantity,
            remaining_quantity=0,
            average_fill_price=current_event.average_fill_price,
            timestamp=datetime.now(timezone.utc),
        )
        self._orders[client_order_id] = cancelled_event
        self._notify_order_event(cancelled_event)
        logger.info("Order %s successfully cancelled", client_order_id)
        return cancelled_event

    def reconcile(
        self, local_positions: list[PositionSnapshot]
    ) -> ReconciliationReport:
        """Reconcile local system positions against simulated broker records."""
        now = datetime.now(timezone.utc)
        open_local = {
            p.symbol.upper(): p for p in local_positions if p.status == PositionStatus.OPEN
        }
        broker_positions = {p.symbol.upper(): p for p in self._positions.values()}

        mismatches: list[ReconciliationMismatch] = []
        checked_symbols = set(open_local.keys()) | set(broker_positions.keys())

        for sym in checked_symbols:
            loc = open_local.get(sym)
            brk = broker_positions.get(sym)

            if loc is not None and brk is None:
                mismatches.append(
                    ReconciliationMismatch(
                        symbol=sym,
                        local_quantity=loc.quantity,
                        broker_quantity=0,
                        discrepancy_type="MISSING_IN_BROKER",
                        details=f"Position {sym} exists locally ({loc.quantity} qty) but not in broker",
                    )
                )
            elif loc is None and brk is not None:
                mismatches.append(
                    ReconciliationMismatch(
                        symbol=sym,
                        local_quantity=0,
                        broker_quantity=brk.quantity,
                        discrepancy_type="MISSING_IN_LOCAL",
                        details=f"Position {sym} exists in broker ({brk.quantity} qty) but not locally",
                    )
                )
            elif loc is not None and brk is not None and loc.quantity != brk.quantity:
                mismatches.append(
                    ReconciliationMismatch(
                        symbol=sym,
                        local_quantity=loc.quantity,
                        broker_quantity=brk.quantity,
                        discrepancy_type="QUANTITY_MISMATCH",
                        details=f"Quantity mismatch for {sym}: local={loc.quantity}, broker={brk.quantity}",
                    )
                )

        is_clean = len(mismatches) == 0
        if not is_clean:
            logger.critical(
                "RECONCILIATION MISMATCH DETECTED: %d discrepancies found!",
                len(mismatches),
            )

        return ReconciliationReport(
            timestamp=now,
            is_clean=is_clean,
            positions_checked=len(checked_symbols),
            mismatches=mismatches,
        )

    def _apply_fill(
        self, symbol: str, side: TradeSide, quantity: int, fill_price: Decimal
    ) -> None:
        """Update internal simulated positions and balances after a fill."""
        sym_key = symbol.upper()
        trade_cost = Decimal(quantity) * fill_price

        if side == TradeSide.BUY:
            self.cash_balance -= trade_cost
            if sym_key in self._positions:
                existing = self._positions[sym_key]
                new_qty = existing.quantity + quantity
                # Weighted average entry price
                new_entry = (
                    (existing.entry_price * Decimal(existing.quantity)) + trade_cost
                ) / Decimal(new_qty)
                existing.quantity = new_qty
                existing.entry_price = new_entry.quantize(Decimal("0.01"))
            else:
                self._positions[sym_key] = BrokerPosition(
                    symbol=sym_key,
                    side=TradeSide.BUY,
                    quantity=quantity,
                    entry_price=fill_price,
                    current_price=fill_price,
                    unrealized_pnl=Decimal("0.00"),
                )
        else:
            # SELL
            self.cash_balance += trade_cost
            if sym_key in self._positions:
                existing = self._positions[sym_key]
                if existing.quantity <= quantity:
                    del self._positions[sym_key]
                else:
                    existing.quantity -= quantity
