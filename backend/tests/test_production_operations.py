"""Comprehensive test suite for Phase 25: Production Operations & Observability.

Verifies:
1. Data-feed health monitoring (freshness, stale ticks >15s, spread compliance).
2. Broker connectivity status (paper, live, heartbeat latency, circuit breakers).
3. Database health (WAL journal mode, file size, write latency, integrity checks).
4. Latency and error telemetry (sub-50ms Watcher SLA, rolling error rates).
5. Hot backup operations health and freshness auditing.
6. Consolidated ProductionOperationsReport generation and status aggregation.
7. FastAPI REST API endpoints (/api/v1/operations/*).
8. CLI operational monitor execution.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_path
from app.db.connection import init_db
from app.main import app
from app.ops.production_operations import (
    BrokerConnectivityStatus,
    DataFeedHealth,
    DatabaseHealth,
    LatencyErrorMetrics,
    ProductionOperationsMonitor,
    ProductionOperationsReport,
)
import sys

_scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from ops_monitor import main as ops_cli_main


@pytest.fixture
def temp_ops_db():
    """Create isolated SQLite database for operations monitoring tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    for p in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def test_data_feed_health_nominal():
    """Verify nominal data feed reports HEALTHY with valid age and spread."""
    monitor = ProductionOperationsMonitor()
    feed = monitor.check_data_feed_health(override_spread_bps=8.0)

    assert feed.status == "HEALTHY"
    assert feed.spread_compliant is True
    assert feed.age_seconds <= 1.0
    assert feed.stale_threshold_seconds == 15.0
    assert "nominal" in feed.details.lower()


def test_data_feed_health_stale_detection():
    """Verify tick age > 15s triggers STALE status."""
    monitor = ProductionOperationsMonitor()
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=20)
    feed = monitor.check_data_feed_health(override_tick_time=stale_time)

    assert feed.status == "STALE"
    assert feed.age_seconds >= 19.0
    assert "STALE" in feed.details


def test_data_feed_health_spread_degradation():
    """Verify excessive spread (>15 bps) triggers DEGRADED status."""
    monitor = ProductionOperationsMonitor()
    feed = monitor.check_data_feed_health(override_spread_bps=22.5)

    assert feed.status == "DEGRADED"
    assert feed.spread_compliant is False
    assert "exceeds" in feed.details


def test_broker_connectivity_status():
    """Verify broker connectivity reports adapter details and heartbeat."""
    monitor = ProductionOperationsMonitor()
    status = monitor.check_broker_connectivity()

    assert status.status in ("CONNECTED", "STANDBY")
    assert "BrokerAdapter" in status.adapter_name
    assert status.circuit_breaker_armed is True
    assert status.reconnect_attempts == 0
    assert status.max_reconnect_attempts == 5

    # Simulated disconnected
    disconn = monitor.check_broker_connectivity(simulated_state="DISCONNECTED")
    assert disconn.status == "DISCONNECTED"
    assert disconn.reconnect_attempts == 1


def test_database_health_checks(temp_ops_db: str):
    """Verify database health accurately inspects WAL mode, integrity, and sizing."""
    monitor = ProductionOperationsMonitor(db_path=temp_ops_db)
    db_health = monitor.check_database_health()

    assert db_health.status == "HEALTHY"
    assert db_health.journal_mode in ("WAL", "MEMORY")
    assert db_health.integrity_ok is True
    assert db_health.accounting_reconciled is True
    assert db_health.db_size_bytes > 0
    assert db_health.write_latency_ms >= 0.0

    # Non-existent DB file triggers CRITICAL
    bad_mon = ProductionOperationsMonitor(db_path="non_existent_random_db.db")
    bad_db = bad_mon.check_database_health()
    assert bad_db.status == "CRITICAL"


def test_latency_and_error_tracking():
    """Verify sliding window latency tracking and error recording."""
    monitor = ProductionOperationsMonitor()
    monitor.record_request_metric(latency_ms=12.5, is_error=False)
    monitor.record_request_metric(latency_ms=15.0, is_error=False)
    monitor.record_request_metric(latency_ms=45.0, is_error=True, error_msg="Simulated test error")

    metrics = monitor.check_latency_and_errors()
    assert metrics.total_requests >= 3
    assert metrics.total_errors >= 1
    assert metrics.error_rate_pct > 0.0
    assert len(metrics.recent_errors) >= 1
    assert metrics.watcher_compliance_pct == 100.0


def test_backup_operations_health(temp_ops_db: str):
    """Verify backup operations health probe inspects backup directory."""
    monitor = ProductionOperationsMonitor(db_path=temp_ops_db)
    bkp = monitor.check_backup_health()

    assert bkp.status in ("HEALTHY", "DEGRADED")
    assert bkp.auto_rotation_limit == 10


def test_consolidated_operations_report(temp_ops_db: str):
    """Verify full consolidated production operations report aggregates all probes."""
    monitor = ProductionOperationsMonitor(db_path=temp_ops_db)
    report = monitor.generate_operations_report()

    assert isinstance(report, ProductionOperationsReport)
    assert report.system_status in ("HEALTHY", "DEGRADED", "CRITICAL")
    assert report.uptime_seconds >= 0.0
    assert report.version == "1.0.0"
    assert isinstance(report.data_feed, DataFeedHealth)
    assert isinstance(report.broker_connectivity, BrokerConnectivityStatus)
    assert isinstance(report.database, DatabaseHealth)
    assert isinstance(report.latency_errors, LatencyErrorMetrics)
    assert "pid" in report.diagnostics
    assert "python_version" in report.diagnostics


def test_operations_api_endpoints(temp_ops_db: str):
    """Verify all 6 FastAPI REST API routes under /api/v1/operations/*."""
    app.dependency_overrides[get_db_path] = lambda: temp_ops_db
    client = TestClient(app)

    try:
        # 1. Full report
        res = client.get("/api/v1/operations/report")
        assert res.status_code == 200
        data = res.json()
        assert "system_status" in data
        assert "data_feed" in data
        assert "broker_connectivity" in data

        # 2. Data feed
        res = client.get("/api/v1/operations/data-feed")
        assert res.status_code == 200
        assert "spread_bps" in res.json()

        # 3. Broker connectivity
        res = client.get("/api/v1/operations/broker-connectivity")
        assert res.status_code == 200
        assert "adapter_name" in res.json()

        # 4. Database
        res = client.get("/api/v1/operations/database")
        assert res.status_code == 200
        assert "journal_mode" in res.json()

        # 5. Telemetry
        res = client.get("/api/v1/operations/telemetry")
        assert res.status_code == 200
        assert "watcher_sla_target_ms" in res.json()

        # 6. Backups
        res = client.get("/api/v1/operations/backups")
        assert res.status_code == 200
        assert "auto_rotation_limit" in res.json()
    finally:
        app.dependency_overrides.pop(get_db_path, None)


def test_cli_operational_monitor(monkeypatch):
    """Verify CLI operational monitor script runs and returns success code."""
    monkeypatch.setattr("sys.argv", ["ops_monitor.py", "--json"])
    exit_code = ops_cli_main()
    assert exit_code in (0, 1)
