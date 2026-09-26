"""Comprehensive Test Suite for Phase 33 Disaster Recovery and Fault Resilience.

Tests:
- Crash / Restart In-Memory State Rehydration
- Broker Disconnect, Retry Backoff, and Order/Position Resync
- Stale Market Data Detection & Trade Execution Blocking
- SQLite WAL Integrity, Checkpointing, and Resilience
- Persistent Idempotency Across Process Crashes & Fingerprint Matching
- Cross-Ledger State Reconstruction & Orphan/Phantom Detection
- Safe Resumption Checklist Governance & Attestation
- FastAPI Disaster Recovery Endpoints
- Operational CLI Runner Execution
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.paper_adapter import PaperAdapter
from app.db.connection import init_db
from app.db.repository import DatabaseRepository
from app.disaster_recovery.broker_resilience import BrokerResilienceManager
from app.disaster_recovery.db_resilience import DatabaseResilienceManager
from app.disaster_recovery.idempotency_manager import IdempotencyManager
from app.disaster_recovery.models import (
    SystemRecoveryStatus,
)
from app.disaster_recovery.recovery_orchestrator import DisasterRecoveryOrchestrator
from app.disaster_recovery.safe_resume import SafeResumeController
from app.disaster_recovery.stale_data_guard import StaleDataGuard, StaleMarketDataError
from app.disaster_recovery.state_reconstructor import StateReconstructor
from app.execution.execution_engine import DuplicateOrderError
from app.main import app
from app.models.contracts import (
    BrokerPosition,
    TradeSide,
)


@pytest.fixture
def temp_db():
    """Provides an isolated SQLite WAL database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    for ext in ["", "-wal", "-shm"]:
        p = f"{path}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# =========================================================================
# 1. Stale Market Data Guard Tests
# =========================================================================

def test_stale_data_guard_fresh_quote() -> None:
    guard = StaleDataGuard()
    guard.update_quote("RELIANCE", Decimal("2450.00"))
    report = guard.check_quote_freshness("RELIANCE")
    assert not report.is_stale
    assert report.status == "FRESH"
    assert report.age_seconds < 1.0

    # assert_quote_fresh should not raise
    verified = guard.assert_quote_fresh("RELIANCE")
    assert verified.symbol == "RELIANCE"


def test_stale_data_guard_stale_quote_exception() -> None:
    guard = StaleDataGuard()
    stale_ts = datetime.fromtimestamp(time.time() - 10.0, tz=timezone.utc)
    guard.update_quote("TCS", Decimal("3500.00"), quote_timestamp=stale_ts)

    report = guard.check_quote_freshness("TCS")
    assert report.is_stale
    assert report.status == "STALE"
    assert report.age_seconds >= 9.5

    with pytest.raises(StaleMarketDataError) as exc_info:
        guard.assert_quote_fresh("TCS")
    assert "is stale" in str(exc_info.value)


def test_stale_data_guard_missing_symbol() -> None:
    guard = StaleDataGuard()
    report = guard.check_quote_freshness("NONEXISTENT")
    assert report.is_stale
    assert report.status == "NO_DATA"

    with pytest.raises(StaleMarketDataError):
        guard.assert_quote_fresh("NONEXISTENT")


def test_stale_data_guard_feed_heartbeat() -> None:
    guard = StaleDataGuard()
    assert not guard.is_feed_alive("PRIMARY_FEED")

    guard.record_feed_heartbeat("PRIMARY_FEED")
    assert guard.is_feed_alive("PRIMARY_FEED")


# =========================================================================
# 2. Idempotency & Duplicate Order Prevention Tests
# =========================================================================

def test_idempotency_first_submission_succeeds(temp_db: str) -> None:
    mgr = IdempotencyManager(db_path=temp_db)
    rec = mgr.check_and_register_order(
        client_order_id="ORD-001",
        symbol="INFY",
        side="BUY",
        quantity=15,
        price_level=Decimal("1480.00"),
        plan_id="PLAN-001",
    )
    assert rec.client_order_id == "ORD-001"
    assert len(rec.order_fingerprint) == 64
    assert mgr.count_records() == 1


def test_idempotency_duplicate_client_order_id_rejected(temp_db: str) -> None:
    mgr = IdempotencyManager(db_path=temp_db)
    mgr.check_and_register_order(
        client_order_id="ORD-DUP-01",
        symbol="INFY",
        side="BUY",
        quantity=10,
        price_level=Decimal("1480.00"),
        plan_id="PLAN-001",
    )

    with pytest.raises(DuplicateOrderError) as exc_info:
        mgr.check_and_register_order(
            client_order_id="ORD-DUP-01",
            symbol="INFY",
            side="BUY",
            quantity=10,
            price_level=Decimal("1480.00"),
            plan_id="PLAN-001",
        )
    assert "Duplicate order" in str(exc_info.value)


def test_idempotency_duplicate_fingerprint_rejected(temp_db: str) -> None:
    mgr = IdempotencyManager(db_path=temp_db)
    mgr.check_and_register_order(
        client_order_id="ORD-FP-01",
        symbol="INFY",
        side="BUY",
        quantity=20,
        price_level=Decimal("1500.00"),
        plan_id="PLAN-002",
    )

    # Different client_order_id but same parameters in time bucket
    with pytest.raises(DuplicateOrderError) as exc_info:
        mgr.check_and_register_order(
            client_order_id="ORD-FP-02-DIFFERENT-ID",
            symbol="INFY",
            side="BUY",
            quantity=20,
            price_level=Decimal("1500.00"),
            plan_id="PLAN-002",
        )
    assert "Duplicate order fingerprint" in str(exc_info.value)


def test_idempotency_persistent_across_restarts(temp_db: str) -> None:
    # Process 1 registers order
    mgr1 = IdempotencyManager(db_path=temp_db)
    mgr1.check_and_register_order(
        client_order_id="ORD-RESTART-01",
        symbol="WIPRO",
        side="BUY",
        quantity=50,
        price_level=Decimal("450.00"),
        plan_id="PLAN-003",
    )

    # Process 2 (simulating fresh start) initialises fresh manager on same DB
    mgr2 = IdempotencyManager(db_path=temp_db)
    with pytest.raises(DuplicateOrderError) as exc_info:
        mgr2.check_and_register_order(
            client_order_id="ORD-RESTART-01",
            symbol="WIPRO",
            side="BUY",
            quantity=50,
            price_level=Decimal("450.00"),
            plan_id="PLAN-003",
        )
    assert "persistent storage" in str(exc_info.value)


# =========================================================================
# 3. Broker Connection Resilience & Disconnect Tests
# =========================================================================

def test_broker_resilience_probe() -> None:
    adapter = PaperAdapter()
    mgr = BrokerResilienceManager(broker_adapter=adapter)
    assert mgr.check_connection() is True


def test_broker_resilience_disconnect_and_reconnect() -> None:
    adapter = PaperAdapter()
    mgr = BrokerResilienceManager(broker_adapter=adapter, max_reconnect_retries=2, initial_backoff_seconds=0.01)
    telemetry = mgr.simulate_disconnect_drill()

    assert telemetry.reconnected_cleanly is True
    assert telemetry.status == "RECONNECTED_AND_RECONCILED"
    assert telemetry.retry_attempts >= 1
    assert adapter.is_connected is True


# =========================================================================
# 4. Database Resilience & Checkpoint Tests
# =========================================================================

def test_database_resilience_health_check(temp_db: str) -> None:
    mgr = DatabaseResilienceManager(db_path=temp_db)
    health = mgr.evaluate_db_health()

    assert health.integrity_ok is True
    assert health.wal_journal_mode == "wal"
    assert health.foreign_keys_enabled is True
    assert health.active_connections_ok is True
    assert health.status == "HEALTHY"


def test_database_resilience_force_checkpoint(temp_db: str) -> None:
    mgr = DatabaseResilienceManager(db_path=temp_db)
    success = mgr.force_wal_checkpoint(mode="TRUNCATE")
    assert success is True


# =========================================================================
# 5. State Reconstruction & Cross-Ledger Reconciliation Tests
# =========================================================================

def test_state_reconstruction_matched(temp_db: str) -> None:
    repo = DatabaseRepository(db_path=temp_db)
    broker = PaperAdapter()

    reconstructor = StateReconstructor(repository=repo, broker_adapter=broker, db_path=temp_db)
    report = reconstructor.reconstruct_and_reconcile()

    assert not report.is_divergent
    assert report.reconstruction_action in ("NO_ACTION_REQUIRED", "STATE_FULLY_CONSISTENT")
    assert len(report.orphaned_positions) == 0
    assert len(report.phantom_positions) == 0


def test_state_reconstruction_detects_orphan(temp_db: str) -> None:
    repo = DatabaseRepository(db_path=temp_db)
    broker = PaperAdapter()

    # Inject position into broker that doesn't exist in DB
    broker._positions["ORPHAN_STOCK"] = BrokerPosition(
        symbol="ORPHAN_STOCK",
        side=TradeSide.BUY,
        quantity=100,
        entry_price=Decimal("120.00"),
        current_price=Decimal("125.00"),
        unrealized_pnl=Decimal("500.00"),
    )

    reconstructor = StateReconstructor(repository=repo, broker_adapter=broker, db_path=temp_db)
    report = reconstructor.reconstruct_and_reconcile()

    assert report.is_divergent is True
    assert len(report.orphaned_positions) == 1
    assert "ORPHAN_STOCK" in report.orphaned_positions[0]
    assert report.reconstruction_action == "OPERATOR_INTERVENTION_REQUIRED"


# =========================================================================
# 6. Safe Resumption Governance Tests
# =========================================================================

def test_safe_resume_controller_approval(temp_db: str) -> None:
    repo = DatabaseRepository(db_path=temp_db)
    broker = PaperAdapter()

    stale_guard = StaleDataGuard()
    db_res = DatabaseResilienceManager(db_path=temp_db)
    brk_res = BrokerResilienceManager(broker_adapter=broker)
    state_rec = StateReconstructor(repository=repo, broker_adapter=broker, db_path=temp_db)

    controller = SafeResumeController(
        db_resilience=db_res,
        broker_resilience=brk_res,
        state_reconstructor=state_rec,
        stale_data_guard=stale_guard,
    )

    token = "OPERATOR-RESUME-AUTH-12345"
    attestation = controller.request_safe_resume(operator_token=token, active_broker=broker)

    assert attestation.resumption_approved is True
    assert attestation.operational_mode == "RESUMED_ACTIVE_WITH_SAFEGUARDS"
    assert controller.current_status == SystemRecoveryStatus.RESUMED
    assert attestation.db_integrity_verified is True
    assert attestation.broker_connected is True


def test_safe_resume_controller_invalid_token(temp_db: str) -> None:
    repo = DatabaseRepository(db_path=temp_db)
    broker = PaperAdapter()

    stale_guard = StaleDataGuard()
    db_res = DatabaseResilienceManager(db_path=temp_db)
    brk_res = BrokerResilienceManager(broker_adapter=broker)
    state_rec = StateReconstructor(repository=repo, broker_adapter=broker, db_path=temp_db)

    controller = SafeResumeController(
        db_resilience=db_res,
        broker_resilience=brk_res,
        state_reconstructor=state_rec,
        stale_data_guard=stale_guard,
    )

    invalid_token = "INVALID-TOKEN-FORMAT"
    attestation = controller.request_safe_resume(operator_token=invalid_token, active_broker=broker)

    assert attestation.resumption_approved is False
    assert attestation.operational_mode == "SAFE_HALTED"
    assert controller.current_status == SystemRecoveryStatus.SAFE_HALTED
    assert any("Operator token must start" in note for note in attestation.notes)


# =========================================================================
# 7. Unified Orchestrator Full Drill Test
# =========================================================================

def test_disaster_orchestrator_full_drill(temp_db: str) -> None:
    broker = PaperAdapter()
    orchestrator = DisasterRecoveryOrchestrator(db_path=temp_db, broker_adapter=broker)
    audit = orchestrator.run_comprehensive_disaster_drill()

    assert audit.scenarios_tested == 6
    assert audit.scenarios_passed == 6
    assert audit.all_passed is True
    assert audit.system_status == SystemRecoveryStatus.HEALTHY
    assert audit.attestation is not None
    assert audit.attestation.resumption_approved is True


# =========================================================================
# 8. FastAPI REST Endpoints Tests
# =========================================================================

def test_fastapi_disaster_recovery_endpoints(client: TestClient) -> None:
    # 1. GET /status
    res_status = client.get("/api/v1/disaster-recovery/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "system_status" in data_status
    assert "broker_connected" in data_status

    # 2. POST /check-stale-data
    res_stale = client.post("/api/v1/disaster-recovery/check-stale-data?symbol=RELIANCE")
    assert res_stale.status_code == 200
    data_stale = res_stale.json()
    assert data_stale["symbol"] == "RELIANCE"

    # 3. POST /reconstruct-state
    res_recon = client.post("/api/v1/disaster-recovery/reconstruct-state")
    assert res_recon.status_code == 200
    data_recon = res_recon.json()
    assert "db_positions_count" in data_recon

    # 4. POST /safe-resume with valid token
    res_resume = client.post(
        "/api/v1/disaster-recovery/safe-resume?operator_token=OPERATOR-RESUME-API-TEST"
    )
    assert res_resume.status_code == 200
    data_resume = res_resume.json()
    assert data_resume["resumption_approved"] is True

    # 5. POST /run-drill
    res_drill = client.post("/api/v1/disaster-recovery/run-drill")
    assert res_drill.status_code == 200
    data_drill = res_drill.json()
    assert data_drill["all_passed"] is True
    assert data_drill["scenarios_tested"] == 6


# =========================================================================
# 9. CLI Runner Subprocess Test
# =========================================================================

def test_cli_runner_execution() -> None:
    cmd = [sys.executable, "backend/scripts/disaster_recovery_runner.py", "--run-drill"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0
    assert "PHASE 33 DISASTER RECOVERY & FAULT TOLERANCE AUDIT" in result.stdout
    assert "All Scenarios Passed: True" in result.stdout
