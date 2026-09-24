"""Execution metrics and latency telemetry tracker.

Measures order submission, acknowledgement, and fill latencies,
slippage impact, fill ratios, and rejection statistics.
"""

import logging
from datetime import datetime
from decimal import Decimal

from app.models.contracts import ExecutionMetricsSnapshot

logger = logging.getLogger(__name__)


class ExecutionMetricsTracker:
    """Tracks latency metrics, execution slippage, and order lifecycle counts."""

    def __init__(self) -> None:
        self.total_orders_submitted: int = 0
        self.total_orders_acknowledged: int = 0
        self.total_orders_filled: int = 0
        self.total_orders_partially_filled: int = 0
        self.total_orders_cancelled: int = 0
        self.total_orders_rejected: int = 0

        self.total_quantity_ordered: int = 0
        self.total_quantity_filled: int = 0
        self.total_slippage_incurred: Decimal = Decimal("0.00")

        # Order creation and milestone timestamps: client_order_id -> datetime
        self._created_timestamps: dict[str, datetime] = {}
        self._submitted_timestamps: dict[str, datetime] = {}
        self._ack_timestamps: dict[str, datetime] = {}

        # Latency lists in milliseconds
        self._submission_latencies_ms: list[float] = []
        self._ack_latencies_ms: list[float] = []
        self._fill_latencies_ms: list[float] = []

    def record_created(self, client_order_id: str, timestamp: datetime, quantity: int) -> None:
        """Record when an order is created locally."""
        self._created_timestamps[client_order_id] = timestamp
        self.total_quantity_ordered += quantity

    def record_submitted(self, client_order_id: str, timestamp: datetime) -> None:
        """Record order dispatch to broker adapter."""
        self.total_orders_submitted += 1
        self._submitted_timestamps[client_order_id] = timestamp

        if client_order_id in self._created_timestamps:
            delta = (timestamp - self._created_timestamps[client_order_id]).total_seconds() * 1000.0
            self._submission_latencies_ms.append(max(0.0, delta))

    def record_acknowledged(self, client_order_id: str, timestamp: datetime) -> None:
        """Record order acceptance / ACK by broker."""
        self.total_orders_acknowledged += 1
        self._ack_timestamps[client_order_id] = timestamp

        if client_order_id in self._submitted_timestamps:
            delta = (timestamp - self._submitted_timestamps[client_order_id]).total_seconds() * 1000.0
            self._ack_latencies_ms.append(max(0.0, delta))

    def record_partially_filled(
        self, client_order_id: str, filled_qty: int, fill_price: Decimal, expected_price: Decimal | None
    ) -> None:
        """Record a partial execution event."""
        self.total_orders_partially_filled += 1
        self.total_quantity_filled += filled_qty

        if expected_price is not None:
            slippage = abs(fill_price - expected_price) * Decimal(filled_qty)
            self.total_slippage_incurred += slippage

    def record_filled(
        self,
        client_order_id: str,
        timestamp: datetime,
        filled_qty: int,
        fill_price: Decimal,
        expected_price: Decimal | None,
    ) -> None:
        """Record full order execution."""
        self.total_orders_filled += 1
        self.total_quantity_filled += filled_qty

        # Fill latency from acknowledgement
        start_ts = self._ack_timestamps.get(client_order_id, self._submitted_timestamps.get(client_order_id))
        if start_ts is not None:
            delta = (timestamp - start_ts).total_seconds() * 1000.0
            self._fill_latencies_ms.append(max(0.0, delta))

        if expected_price is not None:
            slippage = abs(fill_price - expected_price) * Decimal(filled_qty)
            self.total_slippage_incurred += slippage

    def record_cancelled(self, client_order_id: str) -> None:
        """Record order cancellation."""
        self.total_orders_cancelled += 1

    def record_rejected(self, client_order_id: str) -> None:
        """Record order rejection."""
        self.total_orders_rejected += 1

    def get_snapshot(self) -> ExecutionMetricsSnapshot:
        """Generate point-in-time execution telemetry snapshot."""
        avg_sub = (
            sum(self._submission_latencies_ms) / len(self._submission_latencies_ms)
            if self._submission_latencies_ms
            else 0.0
        )
        avg_ack = (
            sum(self._ack_latencies_ms) / len(self._ack_latencies_ms)
            if self._ack_latencies_ms
            else 0.0
        )
        avg_fill = (
            sum(self._fill_latencies_ms) / len(self._fill_latencies_ms)
            if self._fill_latencies_ms
            else 0.0
        )

        return ExecutionMetricsSnapshot(
            total_orders_submitted=self.total_orders_submitted,
            total_orders_acknowledged=self.total_orders_acknowledged,
            total_orders_filled=self.total_orders_filled,
            total_orders_partially_filled=self.total_orders_partially_filled,
            total_orders_cancelled=self.total_orders_cancelled,
            total_orders_rejected=self.total_orders_rejected,
            total_quantity_ordered=self.total_quantity_ordered,
            total_quantity_filled=self.total_quantity_filled,
            total_slippage_incurred=self.total_slippage_incurred.quantize(Decimal("0.01")),
            avg_submission_latency_ms=round(avg_sub, 3),
            avg_ack_latency_ms=round(avg_ack, 3),
            avg_fill_latency_ms=round(avg_fill, 3),
        )
