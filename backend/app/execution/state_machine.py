"""Order lifecycle state machine and transition validation.

Enforces strict sequencing:
CREATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED / CANCELLED / REJECTED
"""

from typing import ClassVar

from app.models.contracts import OrderStatus


class InvalidOrderStateTransitionError(ValueError):
    """Raised when an order transition violates lifecycle rules."""


class OrderStateMachine:
    """Validates and enforces strict order lifecycle state transitions."""

    # Valid transitions mapping: current_state -> set of allowed next_states
    _ALLOWED_TRANSITIONS: ClassVar[dict[OrderStatus, set[OrderStatus]]] = {
        OrderStatus.CREATED: {
            OrderStatus.SUBMITTED,
            OrderStatus.REJECTED,
        },
        OrderStatus.SUBMITTED: {
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.REJECTED,
        },
        OrderStatus.ACKNOWLEDGED: {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        },
        OrderStatus.PARTIALLY_FILLED: {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
        },
        OrderStatus.FILLED: set(),  # Terminal state
        OrderStatus.CANCELLED: set(),  # Terminal state
        OrderStatus.REJECTED: set(),  # Terminal state
    }

    _TERMINAL_STATES: ClassVar[set[OrderStatus]] = {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
    }

    @classmethod
    def is_terminal(cls, status: OrderStatus) -> bool:
        """Return True if the status represents a final, immutable order state."""
        return status in cls._TERMINAL_STATES

    @classmethod
    def can_transition(
        cls, current_status: OrderStatus, next_status: OrderStatus
    ) -> bool:
        """Check if transitioning from current_status to next_status is valid."""
        allowed = cls._ALLOWED_TRANSITIONS.get(current_status, set())
        return next_status in allowed

    @classmethod
    def validate_transition(
        cls, client_order_id: str, current_status: OrderStatus, next_status: OrderStatus
    ) -> None:
        """Validate state transition; raise InvalidOrderStateTransitionError if illegal."""
        if not cls.can_transition(current_status, next_status):
            raise InvalidOrderStateTransitionError(
                f"Illegal order state transition for order {client_order_id}: "
                f"{current_status.value} -> {next_status.value}"
            )
