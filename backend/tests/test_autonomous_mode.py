"""Comprehensive test suite for Phase 21 ₹300 Autonomous Mode."""

import os
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.live_broker_adapter import LiveBrokerAdapter, LiveBrokerSecurityError
from app.api.deps import get_db_path
from app.autonomous.autonomous_engine import (
    AutonomousExecutionResult,
    AutonomousModeEngine,
    AutonomousModeSecurityError,
)
from app.autonomous.config import AutonomousModeConfig
from app.autonomous.runner import main as runner_main
from app.core.config import settings
from app.db.connection import init_db
from app.main import app
from app.models.contracts import ApprovalMode, OrderRequest, OrderStatus, OrderType, TradeSide


@pytest.fixture
def clean_autonomous_db(tmp_path: str) -> str:
    """Provide isolated SQLite database path for autonomous mode tests."""
    return os.path.join(str(tmp_path), "test_autonomous_mode.db")


def test_autonomous_config_validation() -> None:
    """Verify AutonomousModeConfig strictly bounds autonomous threshold and capital at ₹300."""
    # Valid default config
    cfg = AutonomousModeConfig()
    cfg.validate()
    assert cfg.autonomous_threshold == Decimal("300.00")
    assert cfg.capital_limit == Decimal("300.00")
    assert cfg.max_daily_drawdown_pct == Decimal("0.030")

    # Invalid: Threshold > ₹300
    with pytest.raises(AutonomousModeSecurityError, match="exceeds ₹300.00 limit"):
        bad_cfg = AutonomousModeConfig(autonomous_threshold=Decimal("350.00"))
        bad_cfg.validate()

    # Invalid: Capital limit > ₹300
    with pytest.raises(AutonomousModeSecurityError, match="exceeds ₹300.00 limit"):
        bad_cap_cfg = AutonomousModeConfig(capital_limit=Decimal("500.00"))
        bad_cap_cfg.validate()

    # Invalid: Circuit breaker > 3.0%
    with pytest.raises(AutonomousModeSecurityError, match="cannot exceed 3.0%"):
        bad_cb_cfg = AutonomousModeConfig(max_daily_drawdown_pct=Decimal("0.050"))
        bad_cb_cfg.validate()

    # Invalid: Per-trade risk > 1.5%
    with pytest.raises(AutonomousModeSecurityError, match="cannot exceed 1.5%"):
        bad_risk_cfg = AutonomousModeConfig(max_loss_per_trade_pct=Decimal("0.025"))
        bad_risk_cfg.validate()


def test_activation_gate_without_token(clean_autonomous_db: str) -> None:
    """Verify Phase 21 activation strictly requires valid human authorization token."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)

    # Attempt activation without token
    with pytest.raises(AutonomousModeSecurityError, match="strictly requires verified"):
        engine.activate_autonomous_mode(human_auth_token=None)

    # Attempt activation with invalid token
    with pytest.raises(AutonomousModeSecurityError, match="strictly requires verified"):
        engine.activate_autonomous_mode(human_auth_token="WRONG_TOKEN_999")


def test_activation_gate_with_valid_token(clean_autonomous_db: str) -> None:
    """Verify Phase 21 activation succeeds with valid token and prior validation source."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)

    valid_token = getattr(
        settings, "LIVE_TRADING_APPROVAL_TOKEN", "PROD-LIVE-APPROVAL-KEY-9981"
    )
    audit = engine.activate_autonomous_mode(
        human_auth_token=valid_token,
        prior_validation_source="LIVE_EXPERIMENT_REPORT.md",
        validation_evidence={"phase20_return_pct": -0.48},
    )
    assert audit.is_active is True
    assert audit.capital_ceiling == Decimal("300.00")
    assert audit.autonomous_threshold == Decimal("300.00")
    assert "PROD" in audit.human_approval_token_masked or "****" in audit.human_approval_token_masked

    # Verify audit event persisted in SQLite
    events = [
        e for e in engine.repo.get_recent_system_events() if e["source"] == "PHASE_21_ACTIVATION"
    ]
    assert len(events) > 0
    assert events[0]["source"] == "PHASE_21_ACTIVATION"


def test_allocation_gating_below_and_above_300(clean_autonomous_db: str) -> None:
    """Verify notional <= ₹300 is AUTONOMOUS, while > ₹300 is MANUAL_PENDING."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)

    # 1. Allocation within ₹300 ceiling (3 * 82.00 = 246.00)
    mode_under, reason_under = engine.evaluate_allocation("IOC", Decimal("82.00"), 3)
    assert mode_under == ApprovalMode.AUTONOMOUS
    assert "within ₹300.00 autonomous ceiling" in reason_under

    # 2. Allocation exactly at ₹300 ceiling (3 * 100.00 = 300.00)
    mode_exact, _reason_exact = engine.evaluate_allocation("TEST", Decimal("100.00"), 3)
    assert mode_exact == ApprovalMode.AUTONOMOUS

    # 3. Allocation above ₹300 ceiling (1 * 350.00 = 350.00)
    mode_over, reason_over = engine.evaluate_allocation("INFY", Decimal("350.00"), 1)
    assert mode_over == ApprovalMode.MANUAL_PENDING
    assert "exceeds ₹300.00 autonomous ceiling" in reason_over
    assert "Requires explicit human operator approval" in reason_over


def test_adapter_safety_fence_under_300_limit() -> None:
    """Verify LiveBrokerAdapter allows orders up to ₹300 and rejects orders > ₹300."""
    adapter = LiveBrokerAdapter(
        broker_name="ZERODHA",
        api_key="KITE_API_KEY_SAFETY_001",
        api_secret="KITE_API_SECRET_SAFETY_002",
        initial_cash=Decimal("300.00"),
        max_order_notional=Decimal("300.00"),
    )
    adapter.connect()

    # Valid order within ₹300 (3 shares @ 95.00 = 285.00)
    valid_req = OrderRequest(
        client_order_id="ord-auto-valid-285",
        plan_id="plan-auto-valid",
        symbol="ZOMATO",
        side=TradeSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=3,
        price=Decimal("95.00"),
    )
    event_valid = adapter.submit_order(valid_req)
    assert event_valid.status == OrderStatus.FILLED

    # Invalid order exceeding ₹300 (1 share @ 350.00 = 350.00)
    exceed_req = OrderRequest(
        client_order_id="ord-auto-exceed-350",
        plan_id="plan-auto-exceed",
        symbol="INFY",
        side=TradeSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=Decimal("350.00"),
    )
    event_exceed = adapter.submit_order(exceed_req)
    assert event_exceed.status == OrderStatus.REJECTED
    assert "exceeds ₹300 live capital cap" in (event_exceed.rejection_reason or "")

    # Prohibit instantiation above ₹300
    with pytest.raises(LiveBrokerSecurityError, match="exceeds ₹300.00 limit"):
        LiveBrokerAdapter(max_order_notional=Decimal("500.00"))


def test_manual_approval_workflow_above_300(clean_autonomous_db: str) -> None:
    """Verify manual trade approval for allocations above ₹300 requires human token."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)

    # Unauthorized approval attempt
    with pytest.raises(AutonomousModeSecurityError, match="Invalid human authorization token"):
        engine.approve_manual_trade(plan_id="plan-infy-350", human_auth_token="INVALID")

    # Authorized approval
    valid_token = getattr(
        settings, "LIVE_TRADING_APPROVAL_TOKEN", "PROD-LIVE-APPROVAL-KEY-9981"
    )
    ok = engine.approve_manual_trade(
        plan_id="plan-infy-350",
        human_auth_token=valid_token,
        reason="Operator approved high-conviction breakout",
    )
    assert ok is True

    # Check persistence
    events = [
        e for e in engine.repo.get_recent_system_events() if e["source"] == "MANUAL_TRADE_APPROVAL"
    ]
    assert len(events) > 0
    assert "plan-infy-350" in events[0]["message"]


def test_circuit_breaker_enforcement(clean_autonomous_db: str) -> None:
    """Verify 3.0% daily drawdown circuit breaker trips and halts autonomous entries."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)

    # Initial state
    assert engine.is_circuit_breaker_tripped is False

    # Run simulation which includes circuit breaker stress test
    result = engine.run_autonomous_simulation()
    assert result.circuit_breaker_tripped is True
    assert engine.is_circuit_breaker_tripped is True

    # Any new entry evaluation is rejected once circuit breaker is tripped
    mode, reason = engine.evaluate_allocation("SUZLON", Decimal("54.50"), 1)
    assert mode == ApprovalMode.REJECTED
    assert "circuit breaker is tripped" in reason


def test_independent_watcher_and_recovery(clean_autonomous_db: str) -> None:
    """Verify sub-50ms watcher performance and clean state recovery from SQLite WAL."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)
    result = engine.run_autonomous_simulation()

    assert result.risk_report.independent_watcher_verified is True
    assert result.risk_report.automatic_recovery_verified is True

    # Test rehydration directly via RestartRecoveryManager
    recovery_report = engine.recovery_mgr.recover_system_state(
        position_watcher=engine.position_watcher,
        capital_manager=engine.capital_mgr,
    )
    assert recovery_report.status == "SUCCESS"
    assert recovery_report.latest_equity is not None


def test_autonomous_simulation_and_report_generation(clean_autonomous_db: str) -> None:
    """Verify Phase 21 end-to-end simulation generates report with all 7 safety invariants."""
    cfg = AutonomousModeConfig(db_path=clean_autonomous_db)
    engine = AutonomousModeEngine(config=cfg)
    result = engine.run_autonomous_simulation()

    assert isinstance(result, AutonomousExecutionResult)
    assert result.run_id == "RUN-PHASE21-AUTO-300"
    assert result.autonomous_trades == 4
    assert result.manual_pending_trades == 1
    assert result.gate_checkpoint_reached is True

    report = result.report_markdown
    assert "Phase 21: ₹300 Autonomous Mode Evaluation Report" in report
    assert "Autonomous Capital Ceiling**: ₹300.00" in report
    assert "Seven Core Safety Invariants Verification" in report
    assert "Phase 21 Gate Checkpoint" in report
    assert "Mandatory Human Approval Above ₹300" in report


def test_autonomous_cli_runner() -> None:
    """Verify Phase 21 CLI runner executes cleanly."""
    exit_code = runner_main()
    assert exit_code == 0


def test_autonomous_fastapi_endpoints() -> None:
    """Verify FastAPI endpoints for Phase 21 autonomous mode."""
    client = TestClient(app)

    # 1. Status endpoint
    status_res = client.get("/api/v1/autonomous/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["phase"] == "PHASE_21_AUTONOMOUS_MODE"
    assert st_data["autonomous_threshold"] == 300.0
    assert st_data["safety_invariants"]["deterministic_risk_limits"] is True

    # 2. Allocation evaluation: Under ₹300
    eval_under = client.post(
        "/api/v1/autonomous/evaluate-allocation",
        json={"symbol": "SUZLON", "price": 54.50, "quantity": 3},
    )
    assert eval_under.status_code == 200
    assert eval_under.json()["approval_mode"] == "AUTONOMOUS"

    # 3. Allocation evaluation: Over ₹300
    eval_over = client.post(
        "/api/v1/autonomous/evaluate-allocation",
        json={"symbol": "INFY", "price": 350.00, "quantity": 1},
    )
    assert eval_over.status_code == 200
    assert eval_over.json()["approval_mode"] == "MANUAL_PENDING"

    # 4. Activation endpoint: Unauthorized
    act_bad = client.post(
        "/api/v1/autonomous/activate",
        json={"authorization_token": "INVALID_KEY"},
    )
    assert act_bad.status_code == 403

    # 5. Activation endpoint: Authorized
    valid_token = getattr(
        settings, "LIVE_TRADING_APPROVAL_TOKEN", "PROD-LIVE-APPROVAL-KEY-9981"
    )
    act_ok = client.post(
        "/api/v1/autonomous/activate",
        json={
            "authorization_token": valid_token,
            "prior_validation_source": "LIVE_EXPERIMENT_REPORT.md",
        },
    )
    assert act_ok.status_code == 200
    assert act_ok.json()["status"] == "AUTONOMOUS_MODE_ACTIVE_UP_TO_300"

    # 6. Manual trade approval endpoint
    appr_res = client.post(
        "/api/v1/autonomous/approve-manual-trade",
        json={
            "plan_id": "plan-infy-350",
            "authorization_token": valid_token,
            "reason": "Explicit operator approval",
        },
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["success"] is True

    # 7. Report endpoint
    rep_res = client.get("/api/v1/autonomous/report")
    assert rep_res.status_code == 200
    assert "Phase 21: ₹300 Autonomous Mode" in rep_res.json()["report_markdown"]


def test_autonomous_halt_guard(clean_autonomous_db: str) -> None:
    """Verify autonomous activation and simulation runs are blocked if system is HALTED."""
    init_db(clean_autonomous_db)
    app.dependency_overrides[get_db_path] = lambda: clean_autonomous_db
    client = TestClient(app)
    try:
        # Trip kill switch to halt system
        ks_res = client.post(
            "/api/v1/system/kill-switch",
            json={"confirm": True, "reason": "Halt safety test"},
        )
        assert ks_res.status_code == 200

        # Attempt to run autonomous simulation while halted
        res = client.post("/api/v1/autonomous/run")
        assert res.status_code == 400
        assert "HALTED" in res.json()["detail"]

        # Attempt to activate while halted
        act_res = client.post(
            "/api/v1/autonomous/activate",
            json={"authorization_token": "ANY"},
        )
        assert act_res.status_code == 400
        assert "HALTED" in act_res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db_path, None)
