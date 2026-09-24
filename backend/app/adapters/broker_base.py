"""Abstract base interface for broker adapters.

Ensures the trading and execution engines remain 100% decoupled from broker SDKs,
vendor-specific network protocols, or proprietary APIs.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from app.models.contracts import (
    AccountBalance,
    BrokerPosition,
    OrderEvent,
    OrderRequest,
    PositionSnapshot,
    ReconciliationReport,
)

logger = logging.getLogger(__name__)


class BrokerAdapter(ABC):
    """Abstract interface for all broker connectivity and order routing implementations."""

    def __init__(self) -> None:
        self._order_callbacks: list[Callable[[OrderEvent], None]] = []

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connection to the broker gateway is active."""
        ...

    @abstractmethod
    def connect(self) -> bool:
        """Establish session connection and authenticate with broker."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully disconnect and terminate active session."""
        ...

    @abstractmethod
    def get_account_balance(self) -> AccountBalance:
        """Query account cash balance, margin utilization, and equity."""
        ...

    @abstractmethod
    def get_positions(self) -> list[BrokerPosition]:
        """Fetch all currently open positions as reported by broker."""
        ...

    @abstractmethod
    def get_orders(self) -> list[OrderEvent]:
        """Fetch all orders submitted during the current session."""
        ...

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderEvent:
        """Submit an order request to the broker.

        Returns immediate submission/acknowledgement event.
        """
        ...

    @abstractmethod
    def cancel_order(self, client_order_id: str) -> OrderEvent:
        """Request cancellation of an active, unfilled, or partially filled order."""
        ...

    @abstractmethod
    def reconcile(
        self, local_positions: list[PositionSnapshot]
    ) -> ReconciliationReport:
        """Audit local position state against broker positions and report mismatches."""
        ...

    def register_order_callback(
        self, callback: Callable[[OrderEvent], None]
    ) -> None:
        """Register a callback handler for async order state updates."""
        self._order_callbacks.append(callback)

    def _notify_order_event(self, event: OrderEvent) -> None:
        """Internal helper to dispatch order events to registered listeners."""
        for callback in self._order_callbacks:
            try:
                callback(event)
            except Exception as e:  # noqa: BLE001 - Prevent faulty listener from crashing adapter
                logger.error("Error in order callback listener: %s", e)
