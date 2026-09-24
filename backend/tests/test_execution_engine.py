"""Comprehensive test suite for Phase 08: Execution Engine + Broker Abstraction.

Verifies:
1. BrokerAdapter interface and PaperAdapter fidelity (simulation of fills, slippage, margin)
2. Order lifecycle state machine (CREATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED/CANCELLED/REJECTED)
3. Illegal state transition rejection
4. Idempotency and 60-second duplicate order prevention
5. Acknowledgement and partial fill handling
6. Order cancellations and rejection handling
7. Portfolio reconciliation between local positions and broker
8. Reconnect recovery procedure
9. Execution metrics and latency tracking
10. Broker abstraction purity and live trading lockout
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.adapters.paper_adapter import PaperAdapter
from app.execution.execution_engine import DuplicateOrderError, ExecutionEngine
from app.execution.state_machine import (
    InvalidOrderStateTransitionError,
    OrderStateMachine,
)
from app.models.contracts import (
    OrderEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
)


def make_request(
    client_order_id: str = "ord-001",
    symbol: str = "RELIANCE",
    side: TradeSide = TradeSide.BUY,
    quantity: int = 1,
    price: str = "100.00",
) -> OrderRequest:
    """Helper to construct an OrderRequest."""
    return OrderRequest(
        client_order_id=client_order_id,
        plan_id=f"plan-{client_order_id}",
        symbol=symbol,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=Decimal(price),
    )


def make_position(
    symbol: str = "RELIANCE",
    quantity: int = 1,
    entry_price: str = "100.00",
) -> PositionSnapshot:
    """Helper to construct a PositionSnapshot for reconciliation tests."""
    t0 = datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    return PositionSnapshot(
        position_id=f"pos-{symbol}",
        plan_id=f"plan-{symbol}",
        symbol=symbol,
        side=TradeSide.BUY,
        quantity=quantity,
        entry_price=Decimal(entry_price),
        current_price=Decimal(entry_price),
        hard_stop_price=Decimal("98.00"),
        unrealized_pnl=Decimal("0.00"),
        status=PositionStatus.OPEN,
        opened_at=t0,
        last_evaluated_at=t0,
    )


# =============================================================================
# 1. Order Lifecycle State Machine
# =============================================================================


def test_state_machine_valid_transitions():
    """Verify all valid legal transitions in the order state machine."""
    sm = OrderStateMachine

    # CREATED -> SUBMITTED
    assert sm.can_transition(OrderStatus.CREATED, OrderStatus.SUBMITTED) is True
    # SUBMITTED -> ACKNOWLEDGED
    assert sm.can_transition(OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED) is True
    # ACKNOWLEDGED -> PARTIALLY_FILLED
    assert sm.can_transition(OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED) is True
    # PARTIALLY_FILLED -> FILLED
    assert sm.can_transition(OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED) is True

    # Terminal checks
    assert sm.is_terminal(OrderStatus.FILLED) is True
    assert sm.is_terminal(OrderStatus.CANCELLED) is True
    assert sm.is_terminal(OrderStatus.REJECTED) is True
    assert sm.is_terminal(OrderStatus.ACKNOWLEDGED) is False


def test_state_machine_invalid_transitions():
    """Verify that illegal transitions raise InvalidOrderStateTransitionError."""
    sm = OrderStateMachine

    # Cannot cancel an already FILLED order
    assert sm.can_transition(OrderStatus.FILLED, OrderStatus.CANCELLED) is False
    with pytest.raises(InvalidOrderStateTransitionError):
        sm.validate_transition("ord-1", OrderStatus.FILLED, OrderStatus.CANCELLED)

    # Cannot fill a CREATED order directly without submission
    assert sm.can_transition(OrderStatus.CREATED, OrderStatus.FILLED) is False
    with pytest.raises(InvalidOrderStateTransitionError):
        sm.validate_transition("ord-2", OrderStatus.CREATED, OrderStatus.FILLED)

    # Cannot resubmit a REJECTED order
    assert sm.can_transition(OrderStatus.REJECTED, OrderStatus.SUBMITTED) is False
    with pytest.raises(InvalidOrderStateTransitionError):
        sm.validate_transition("ord-3", OrderStatus.REJECTED, OrderStatus.SUBMITTED)


# =============================================================================
# 2. PaperAdapter Execution & Slippage
# =============================================================================


def test_paper_adapter_order_execution_and_slippage():
    """Verify PaperAdapter fills orders with realistic tick slippage."""
    adapter = PaperAdapter(
        initial_cash=Decimal("1000.00"),
        slippage_ticks=1,
        tick_size=Decimal("0.05"),
    )

    # BUY 2 shares at 100.00 -> fill price = 100.00 + 0.05 = 100.05
    req = make_request(client_order_id="ord-buy-01", side=TradeSide.BUY, quantity=2, price="100.00")
    event = adapter.submit_order(req)

    assert event.status == OrderStatus.FILLED
    assert event.filled_quantity == 2
    assert event.remaining_quantity == 0
    assert event.average_fill_price == Decimal("100.05")

    # Check broker positions
    positions = adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "RELIANCE"
    assert positions[0].quantity == 2
    assert positions[0].entry_price == Decimal("100.05")

    # SELL 1 share at 102.00 -> fill price = 102.00 - 0.05 = 101.95
    req_sell = make_request(
        client_order_id="ord-sell-01",
        side=TradeSide.SELL,
        quantity=1,
        price="102.00",
    )
    sell_event = adapter.submit_order(req_sell)
    assert sell_event.status == OrderStatus.FILLED
    assert sell_event.average_fill_price == Decimal("101.95")

    # Remaining position is 1 share
    assert adapter.get_positions()[0].quantity == 1


def test_paper_adapter_partial_fill_simulation():
    """Verify PaperAdapter partial fill simulation."""
    adapter = PaperAdapter(initial_cash=Decimal("500.00"))
    adapter.simulate_partial_fill = True
    adapter.partial_fill_qty = 2

    req = make_request(client_order_id="ord-part-01", quantity=5, price="50.00")
    event = adapter.submit_order(req)

    assert event.status == OrderStatus.PARTIALLY_FILLED
    assert event.filled_quantity == 2
    assert event.remaining_quantity == 3


def test_paper_adapter_order_cancellation():
    """Verify order cancellation on uncompleted orders."""
    adapter = PaperAdapter()
    adapter.simulate_partial_fill = True
    adapter.partial_fill_qty = 1

    # Partially fill order
    req = make_request(client_order_id="ord-cancel-01", quantity=3)
    adapter.submit_order(req)

    # Cancel remainder
    cancel_event = adapter.cancel_order("ord-cancel-01")
    assert cancel_event.status == OrderStatus.CANCELLED
    assert cancel_event.filled_quantity == 1
    assert cancel_event.remaining_quantity == 0


def test_paper_adapter_rejection_fault_injection():
    """Verify fault injection triggers order rejection."""
    adapter = PaperAdapter()
    adapter.simulate_rejection_symbols.add("BLOCKED_STOCK")

    req = make_request(client_order_id="ord-rej-01", symbol="BLOCKED_STOCK")
    event = adapter.submit_order(req)

    assert event.status == OrderStatus.REJECTED
    assert "blocked by broker" in event.rejection_reason.lower()


# =============================================================================
# 3. Execution Engine & Idempotency
# =============================================================================


def test_execution_engine_idempotent_duplicate_protection():
    """Verify duplicate order submissions within 60s window are blocked."""
    engine = ExecutionEngine(dedup_window_seconds=60.0)
    req = make_request(client_order_id="ord-dup-01")

    # First submission succeeds
    event1 = engine.submit_order(req)
    assert event1.status == OrderStatus.FILLED

    # Second submission with same ID within 60s raises DuplicateOrderError
    with pytest.raises(DuplicateOrderError):
        engine.submit_order(req)


def test_execution_engine_cancellation():
    """Verify execution engine handles order cancellation."""
    adapter = PaperAdapter()
    adapter.simulate_partial_fill = True
    adapter.partial_fill_qty = 1

    engine = ExecutionEngine(broker_adapter=adapter)
    req = make_request(client_order_id="ord-eng-cancel", quantity=4)
    engine.submit_order(req)

    # Cancel remainder
    cancel_event = engine.cancel_order("ord-eng-cancel")
    assert cancel_event.status == OrderStatus.CANCELLED
    assert engine.get_order("ord-eng-cancel").status == OrderStatus.CANCELLED


def test_execution_engine_reconciliation_and_mismatch_detection():
    """Verify portfolio reconciliation against broker positions."""
    adapter = PaperAdapter()
    engine = ExecutionEngine(broker_adapter=adapter)

    # Fill 2 shares of RELIANCE in broker
    engine.submit_order(make_request(client_order_id="ord-rec-1", symbol="RELIANCE", quantity=2))

    # Case A: Local matches broker perfectly -> clean report
    local_pos = [make_position(symbol="RELIANCE", quantity=2)]
    report = engine.reconcile_positions(local_pos)
    assert report.is_clean is True
    assert len(report.mismatches) == 0

    # Case B: Local has 1 share but broker has 2 -> QUANTITY_MISMATCH
    mismatch_pos = [make_position(symbol="RELIANCE", quantity=1)]
    report_bad = engine.reconcile_positions(mismatch_pos)
    assert report_bad.is_clean is False
    assert len(report_bad.mismatches) == 1
    assert report_bad.mismatches[0].discrepancy_type == "QUANTITY_MISMATCH"

    # Case C: Local has INFY which broker does not have -> MISSING_IN_BROKER
    missing_broker = [
        make_position(symbol="RELIANCE", quantity=2),
        make_position(symbol="INFY", quantity=1),
    ]
    report_missing = engine.reconcile_positions(missing_broker)
    assert report_missing.is_clean is False
    assert any(m.discrepancy_type == "MISSING_IN_BROKER" for m in report_missing.mismatches)


def test_execution_engine_reconnect_recovery():
    """Verify reconnect recovery establishes connection and runs reconciliation."""
    adapter = PaperAdapter()
    engine = ExecutionEngine(broker_adapter=adapter)

    # Disconnect broker
    adapter.disconnect()
    assert adapter.is_connected is False

    # Attempting order while disconnected results in REJECTED
    req = make_request(client_order_id="ord-offline-01")
    event = engine.submit_order(req)
    assert event.status == OrderStatus.REJECTED

    # Reconnect procedure recovers session and reconciles
    report = engine.handle_reconnect([])
    assert adapter.is_connected is True
    assert report.is_clean is True


def test_execution_engine_metrics_telemetry():
    """Verify execution metrics and latency telemetry accumulation."""
    adapter = PaperAdapter()
    engine = ExecutionEngine(broker_adapter=adapter)

    # Submit 2 filled orders
    engine.submit_order(make_request(client_order_id="ord-met-1", price="100.00"))
    engine.submit_order(make_request(client_order_id="ord-met-2", price="100.00"))

    metrics = engine.get_metrics()
    assert metrics.total_orders_submitted == 2
    assert metrics.total_orders_filled == 2
    assert metrics.total_quantity_ordered == 2
    assert metrics.total_quantity_filled == 2
    assert metrics.total_slippage_incurred > Decimal("0.00")
    assert metrics.avg_submission_latency_ms >= 0.0


def test_execution_engine_purity_and_live_lock():
    """Verify broker abstraction purity and live trading lockout invariant."""
    engine = ExecutionEngine()
    # Live trading must remain strictly locked False in Phase 08
    assert engine.is_live is False


def test_paper_adapter_account_balance_and_floating_pnl():
    """Verify paper adapter balance, used margin, and floating unrealized PnL."""
    adapter = PaperAdapter(initial_cash=Decimal("500.00"), slippage_ticks=0)
    req = make_request(client_order_id="ord-bal-1", symbol="SBIN", quantity=2, price="100.00")
    adapter.submit_order(req)

    bal = adapter.get_account_balance()
    assert bal.cash_balance == Decimal("300.00")
    assert bal.used_margin == Decimal("200.00")
    assert bal.total_equity == Decimal("500.00")

    # Update market price to 110.00 (+10/share -> +20 unrealized)
    adapter.update_market_price("SBIN", Decimal("110.00"))
    bal_after = adapter.get_account_balance()
    assert bal_after.total_equity == Decimal("520.00")


def test_execution_engine_cancel_terminal_and_missing_order_errors():
    """Verify error handling when cancelling missing or already terminal orders."""
    engine = ExecutionEngine()
    # Nonexistent order raises KeyError
    with pytest.raises(KeyError):
        engine.cancel_order("non-existent-order")

    # FILLED order cannot be cancelled
    req = make_request(client_order_id="ord-term-1")
    engine.submit_order(req)
    with pytest.raises(ValueError, match="terminal state"):
        engine.cancel_order("ord-term-1")


def test_execution_engine_partial_to_full_fill_metrics_accumulation():
    """Verify delta quantity and telemetry when an order transitions from partial to full fill."""
    adapter = PaperAdapter()
    engine = ExecutionEngine(broker_adapter=adapter)

    # Simulate an order that fills partially (2 shares) then fills the rest (3 shares)
    req = make_request(client_order_id="ord-multi-fill", quantity=5, price="100.00")
    engine._order_requests["ord-multi-fill"] = req
    now = datetime.now(timezone.utc)
    engine._submitted_timestamps["ord-multi-fill"] = now
    engine.metrics.record_created("ord-multi-fill", now, 5)
    engine.metrics.record_submitted("ord-multi-fill", now)

    engine._process_order_event(
        adapter._orders.get(
            "ord-multi-fill",
            OrderEvent(
                client_order_id="ord-multi-fill",
                symbol="RELIANCE",
                status=OrderStatus.ACKNOWLEDGED,
                filled_quantity=0,
                remaining_quantity=5,
                timestamp=now,
            ),
        )
    )

    # First partial fill: 2 shares
    engine._process_order_event(
        OrderEvent(
            client_order_id="ord-multi-fill",
            symbol="RELIANCE",
            status=OrderStatus.PARTIALLY_FILLED,
            filled_quantity=2,
            remaining_quantity=3,
            average_fill_price=Decimal("100.05"),
            timestamp=now,
        )
    )

    # Full fill: remaining 3 shares (total 5)
    engine._process_order_event(
        OrderEvent(
            client_order_id="ord-multi-fill",
            symbol="RELIANCE",
            status=OrderStatus.FILLED,
            filled_quantity=5,
            remaining_quantity=0,
            average_fill_price=Decimal("100.05"),
            timestamp=now,
        )
    )

    metrics = engine.get_metrics()
    assert metrics.total_quantity_ordered == 5
    assert metrics.total_quantity_filled == 5
    assert metrics.total_orders_partially_filled == 1
    assert metrics.total_orders_filled == 1

