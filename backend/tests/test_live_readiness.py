"""Comprehensive test suite for Phase 19 Controlled ₹100 Live Readiness Gate."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.live_broker_adapter import LiveBrokerAdapter, LiveBrokerSecurityError
from app.api.deps import SystemState
from app.live.audit_runner import main as runner_main
from app.live.readiness_audit import (
    LiveReadinessAuditor,
    LiveReadinessAuditResult,
)
from app.main import app
from app.models.contracts import (
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
)


@pytest.fixture
def clean_db(tmp_path: str) -> str:
    """Provide isolated SQLite database path for tests."""
    return os.path.join(str(tmp_path), "test_live_readiness.db")


@pytest.fixture
def test_system_state() -> SystemState:
    """Provide fresh SystemState instance."""
    return SystemState()


@pytest.fixture
def live_adapter() -> LiveBrokerAdapter:
    """Provide initialized LiveBrokerAdapter."""
    return LiveBrokerAdapter(
        broker_name="ZERODHA",
        api_key="KITE_API_KEY_LIVE_9981",
        api_secret="KITE_API_SECRET_LIVE_4412",
        access_token="KITE_ACCESS_TOKEN_LIVE_7700",
        account_id="ACC_MICRO_100",
        is_sandbox=True,
        initial_cash=Decimal("100.00"),
    )


def test_credential_audit_valid(clean_db: str, live_adapter: LiveBrokerAdapter) -> None:
    """Verify credential audit passes when valid API credentials are provided."""
    auditor = LiveReadinessAuditor(broker_adapter=live_adapter, db_path=clean_db)
    report = auditor.audit_credentials()

    assert report.passed is True
    assert report.api_key_configured is True
    assert report.api_secret_configured is True
    assert "****" in report.api_key_masked
    assert report.gitignore_protected is True


def test_credential_audit_missing_keys(clean_db: str) -> None:
    """Verify credential audit fails when credentials are empty or invalid."""
    bad_adapter = LiveBrokerAdapter(api_key="", api_secret="")
    auditor = LiveReadinessAuditor(broker_adapter=bad_adapter, db_path=clean_db)
    report = auditor.audit_credentials()

    assert report.passed is False
    assert report.api_key_configured is False
    assert report.api_secret_configured is False


def test_broker_connection_and_latency(live_adapter: LiveBrokerAdapter, clean_db: str) -> None:
    """Verify broker connection handshake and latency measurement."""
    auditor = LiveReadinessAuditor(broker_adapter=live_adapter, db_path=clean_db)
    report = auditor.audit_broker_connection()

    assert report.passed is True
    assert report.broker_connected is True
    assert report.roundtrip_latency_ms < 500.0
    assert report.currency_is_inr is True
    assert report.account_balance_inr >= Decimal("100.00")
    assert report.reconciliation_verified is True


def test_broker_adapter_order_submission_and_cap(live_adapter: LiveBrokerAdapter) -> None:
    """Verify order submission within ₹100 limit succeeds in sandbox."""
    live_adapter.connect()

    # Valid order: 1 share of SUZLON @ ₹54.50 = ₹54.50 (<= ₹100)
    req = OrderRequest(
        client_order_id="ord-live-test-1",
        plan_id="plan-1",
        symbol="SUZLON",
        side=TradeSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=Decimal("54.50"),
    )
    event = live_adapter.submit_order(req)
    assert event.status == OrderStatus.FILLED
    assert event.filled_quantity == 1
    assert event.client_order_id == "ord-live-test-1"

    # Orders query
    orders = live_adapter.get_orders()
    assert len(orders) == 1

    # Positions query
    positions = live_adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "SUZLON"


def test_broker_adapter_rejects_exceeding_100_cap(live_adapter: LiveBrokerAdapter) -> None:
    """Verify order exceeding ₹100 capital cap is immediately rejected."""
    live_adapter.connect()

    # Invalid order: 2 shares @ ₹60.00 = ₹120.00 (> ₹100 limit)
    req = OrderRequest(
        client_order_id="ord-live-exceed-cap",
        plan_id="plan-2",
        symbol="TATASTEEL",
        side=TradeSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=2,
        price=Decimal("60.00"),
    )
    event = live_adapter.submit_order(req)
    assert event.status == OrderStatus.REJECTED
    assert "exceeds ₹100 live capital cap" in (event.rejection_reason or "")


def test_broker_adapter_safety_lock_live_orders_blocked() -> None:
    """Verify LiveBrokerSecurityError is raised if live mode is attempted with IS_PAPER_TRADING=True."""
    adapter = LiveBrokerAdapter(
        api_key="VALID_KEY_12345",
        api_secret="VALID_SECRET_12345",
        is_sandbox=False,  # Simulating live mode
    )
    adapter.connect()

    req = OrderRequest(
        client_order_id="ord-live-blocked",
        plan_id="plan-3",
        symbol="SUZLON",
        side=TradeSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=Decimal("54.00"),
    )

    with pytest.raises(LiveBrokerSecurityError, match="strictly prohibited"):
        adapter.submit_order(req)


def test_broker_adapter_reconciliation(live_adapter: LiveBrokerAdapter) -> None:
    """Verify position reconciliation detects missing positions."""
    live_adapter.connect()

    # Local position exists, but broker has no positions
    now = datetime(2026, 9, 25, 9, 30, tzinfo=timezone.utc)
    local_pos = [
        PositionSnapshot(
            position_id="pos-loc-1",
            plan_id="plan-1",
            symbol="SUZLON",
            side=TradeSide.BUY,
            quantity=1,
            entry_price=Decimal("54.00"),
            current_price=Decimal("54.50"),
            hard_stop_price=Decimal("53.00"),
            unrealized_pnl=Decimal("0.50"),
            status=PositionStatus.OPEN,
            opened_at=now,
            last_evaluated_at=now,
        )
    ]
    report = live_adapter.reconcile(local_pos)
    assert report.is_clean is False
    assert len(report.mismatches) == 1
    assert report.mismatches[0].symbol == "SUZLON"
    assert report.mismatches[0].local_quantity == 1
    assert report.mismatches[0].broker_quantity == 0


def test_safety_mechanisms_kill_switch_and_caps(clean_db: str, live_adapter: LiveBrokerAdapter) -> None:
    """Verify emergency kill switch cancels orders, closes positions, and sets halt flag."""
    auditor = LiveReadinessAuditor(broker_adapter=live_adapter, db_path=clean_db)
    report = auditor.audit_safety_mechanisms()

    assert report.passed is True
    assert report.kill_switch_operational is True
    assert report.orders_cancelled_on_kill_switch is True
    assert report.positions_liquidated_on_kill_switch is True
    assert report.system_halt_flag_propagated is True
    assert report.initial_capital_cap_enforced is True
    assert report.autonomous_threshold_cap_enforced is True
    assert report.max_loss_per_trade_enforced is True
    assert report.max_daily_drawdown_enforced is True
    assert report.intraday_square_off_rule_verified is True
    assert report.stale_data_liquidation_rule_verified is True
    assert report.spread_widening_liquidation_rule_verified is True


def test_approval_gate_unauthorized_switch_rejected(clean_db: str) -> None:
    """Verify mode switch endpoint blocks unauthorized switches to LIVE."""
    client = TestClient(app)

    # 1. Without confirmation
    res = client.post("/api/v1/system/mode", json={"target_mode": "LIVE"})
    assert res.status_code == 400

    # 2. With confirmation but IS_PAPER_TRADING is True
    res = client.post(
        "/api/v1/system/mode",
        json={
            "target_mode": "LIVE",
            "confirmation": True,
            "live_trading_approval_token": "WRONG_TOKEN",
        },
    )
    assert res.status_code == 403


def test_full_live_readiness_audit_execution(clean_db: str, live_adapter: LiveBrokerAdapter) -> None:
    """Verify end-to-end execution of Phase 19 Live Readiness Audit."""
    auditor = LiveReadinessAuditor(broker_adapter=live_adapter, db_path=clean_db)
    result = auditor.run_full_audit()

    assert isinstance(result, LiveReadinessAuditResult)
    assert result.overall_status == "READY_FOR_APPROVAL"
    assert result.total_checks == 12
    assert result.passed_checks == 12
    assert result.failed_checks == 0
    assert result.approval_gate.gate_status == "AWAITING_EXPLICIT_HUMAN_APPROVAL"
    assert len(result.recommendations) > 0


def test_audit_runner_cli() -> None:
    """Verify Phase 19 audit runner CLI executes successfully."""
    exit_code = runner_main()
    assert exit_code == 0


def test_live_readiness_api_endpoint() -> None:
    """Verify GET /api/v1/system/live-readiness returns complete audit payload."""
    client = TestClient(app)
    res = client.get("/api/v1/system/live-readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "READY_FOR_APPROVAL"
    assert data["total_checks"] == 12
    assert data["passed_checks"] == 12
    assert data["approval_gate"]["gate_status"] == "AWAITING_EXPLICIT_HUMAN_APPROVAL"
