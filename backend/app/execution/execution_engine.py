"""Execution Engine and Broker-Neutral Order Lifecycle Manager.

Fulfills Phase 08 requirements:
- Strictly decoupled from broker-specific code
- Live trading prohibited (pure paper/simulated safety lock)
- Strict state machine enforcement: CREATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED/CANCELLED/REJECTED
- Idempotent submission and 60-second duplicate order protection
- Portfolio reconciliation and reconnect recovery
- Comprehensive execution and latency metrics tracking
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal

from app.adapters.broker_base import BrokerAdapter
from app.adapters.paper_adapter import PaperAdapter
from app.execution.metrics import ExecutionMetricsTracker
from app.execution.state_machine import OrderStateMachine
from app.models.contracts import (
    ExecutionMetricsSnapshot,
    OrderEvent,
    OrderRequest,
    OrderStatus,
    PositionSnapshot,
    ReconciliationReport,
)

logger = logging.getLogger(__name__)


class DuplicateOrderError(ValueError):
    """Raised when an identical client order ID is submitted within the deduplication window."""


class ExecutionEngine:
    """Orchestrates order dispatches, lifecycle progression, reconciliation, and telemetry."""

    def __init__(
        self,
        broker_adapter: BrokerAdapter | None = None,
        dedup_window_seconds: float = 60.0,
    ) -> None:
        self.broker_adapter = broker_adapter or PaperAdapter()
        self.dedup_window_seconds = dedup_window_seconds

        # State machine and metrics tracker
        self.state_machine = OrderStateMachine()
        self.metrics = ExecutionMetricsTracker()

        # Local order registry
        self._orders: dict[str, OrderEvent] = {}
        self._order_requests: dict[str, OrderRequest] = {}
        self._submitted_timestamps: dict[str, datetime] = {}

        # Event callbacks
        self._listeners: list[Callable[[OrderEvent], None]] = []

        # Connect to adapter async stream if provided
        self.broker_adapter.register_order_callback(self._on_broker_order_event)

    @property
    def is_live(self) -> bool:
        """Safety invariant: Live trading is strictly disabled in this phase."""
        return False

    def submit_order(self, request: OrderRequest) -> OrderEvent:
        """Submit an order request with strict idempotency and lifecycle verification."""
        now = datetime.now(timezone.utc)
        client_order_id = request.client_order_id

        # 1. Idempotency & Duplicate Protection Check (60-second window)
        if client_order_id in self._submitted_timestamps:
            prev_ts = self._submitted_timestamps[client_order_id]
            elapsed_sec = (now - prev_ts).total_seconds()
            if elapsed_sec <= self.dedup_window_seconds:
                logger.warning(
                    "Duplicate order submission rejected for %s: submitted %0.1fs ago (within %0.1fs window)",
                    client_order_id,
                    elapsed_sec,
                    self.dedup_window_seconds,
                )
                raise DuplicateOrderError(
                    f"Duplicate order {client_order_id} submitted within {self.dedup_window_seconds}s deduplication window"
                )

        # 2. Record locally in CREATED state
        self._order_requests[client_order_id] = request
        self._submitted_timestamps[client_order_id] = now
        self.metrics.record_created(client_order_id, now, request.quantity)

        # Validate CREATED -> SUBMITTED transition
        self.state_machine.validate_transition(
            client_order_id, OrderStatus.CREATED, OrderStatus.SUBMITTED
        )
        self.metrics.record_submitted(client_order_id, now)

        # 3. Route to Broker Adapter
        try:
            order_event = self.broker_adapter.submit_order(request)
        except Exception as exc:  # noqa: BLE001 - Protect engine from broker driver crashes
            logger.error(
                "Broker adapter error during submission of %s: %s",
                client_order_id,
                exc,
            )
            order_event = OrderEvent(
                client_order_id=client_order_id,
                broker_order_id=None,
                symbol=request.symbol,
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                remaining_quantity=request.quantity,
                average_fill_price=Decimal("0.00"),
                rejection_reason=f"Broker disconnected: {exc}",
                timestamp=now,
            )

        # 4. Ingest and record outcome
        self._process_order_event(order_event, expected_price=request.price)
        return order_event

    def cancel_order(self, client_order_id: str) -> OrderEvent:
        """Cancel an unfilled or partially filled order."""
        if client_order_id not in self._orders:
            raise KeyError(f"Order {client_order_id} not found in execution engine")

        current_event = self._orders[client_order_id]
        if self.state_machine.is_terminal(current_event.status):
            raise ValueError(
                f"Cannot cancel order {client_order_id} in terminal state {current_event.status.value}"
            )

        # Dispatch cancel request to broker
        cancel_event = self.broker_adapter.cancel_order(client_order_id)
        self._process_order_event(cancel_event, expected_price=None)
        return cancel_event

    def reconcile_positions(
        self, local_positions: list[PositionSnapshot]
    ) -> ReconciliationReport:
        """Perform portfolio reconciliation between local position state and broker records."""
        report = self.broker_adapter.reconcile(local_positions)
        if not report.is_clean:
            logger.critical(
                "RECONCILIATION MISMATCH: %d discrepancies found between local and broker state!",
                len(report.mismatches),
            )
        else:
            logger.info("Reconciliation complete: all %d positions match cleanly", report.positions_checked)
        return report

    def handle_reconnect(
        self, local_positions: list[PositionSnapshot]
    ) -> ReconciliationReport:
        """Handle recovery following a broker disconnect event by reconciling state."""
        logger.warning("Initiating reconnect recovery procedure...")
        self.broker_adapter.connect()
        return self.reconcile_positions(local_positions)

    def get_order(self, client_order_id: str) -> OrderEvent | None:
        """Retrieve latest known order status event."""
        return self._orders.get(client_order_id)

    def get_all_orders(self) -> list[OrderEvent]:
        """Fetch all recorded order events."""
        return list(self._orders.values())

    def get_metrics(self) -> ExecutionMetricsSnapshot:
        """Retrieve aggregated execution telemetry and latency metrics."""
        return self.metrics.get_snapshot()

    def register_listener(self, listener: Callable[[OrderEvent], None]) -> None:
        """Register a callback for execution order events."""
        self._listeners.append(listener)

    def _on_broker_order_event(self, event: OrderEvent) -> None:
        """Callback handler invoked when broker adapter emits async updates."""
        req = self._order_requests.get(event.client_order_id)
        expected_price = req.price if req else None
        self._process_order_event(event, expected_price=expected_price)

    def _process_order_event(
        self, event: OrderEvent, expected_price: Decimal | None = None
    ) -> None:
        """Internal helper to validate state machine transitions and update telemetry."""
        client_order_id = event.client_order_id
        prev_event = self._orders.get(client_order_id)
        prev_status = prev_event.status if prev_event else OrderStatus.SUBMITTED
        prev_filled_qty = prev_event.filled_quantity if prev_event else 0

        # Exact duplicate detection: ignore redundant events with identical status and fill qty
        if (
            prev_event is not None
            and prev_event.status == event.status
            and prev_event.filled_quantity == event.filled_quantity
        ):
            return

        # If status actually changed, validate transition
        if prev_status != event.status:
            self.state_machine.validate_transition(
                client_order_id, prev_status, event.status
            )

        self._orders[client_order_id] = event

        delta_qty = max(0, event.filled_quantity - prev_filled_qty)
        if expected_price is None:
            req = self._order_requests.get(client_order_id)
            if req:
                expected_price = req.price

        # Update metrics based on new status
        if event.status == OrderStatus.ACKNOWLEDGED:
            self.metrics.record_acknowledged(client_order_id, event.timestamp)
        elif event.status == OrderStatus.PARTIALLY_FILLED:
            if event.average_fill_price is not None:
                self.metrics.record_partially_filled(
                    client_order_id,
                    delta_qty,
                    event.average_fill_price,
                    expected_price,
                )
        elif event.status == OrderStatus.FILLED:
            if event.average_fill_price is not None:
                fill_qty = delta_qty if prev_filled_qty > 0 else event.filled_quantity
                self.metrics.record_filled(
                    client_order_id,
                    event.timestamp,
                    fill_qty,
                    event.average_fill_price,
                    expected_price,
                )
        elif event.status == OrderStatus.CANCELLED:
            self.metrics.record_cancelled(client_order_id)
        elif event.status == OrderStatus.REJECTED:
            self.metrics.record_rejected(client_order_id)

        # Notify external listeners
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:  # noqa: BLE001 - Prevent faulty listener from crashing execution engine
                logger.error("Error in execution engine listener: %s", e)
