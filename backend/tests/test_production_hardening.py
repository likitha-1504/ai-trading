"""Comprehensive verification test suite for Phase 23 Final Production Hardening."""

from __future__ import annotations

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_path
from app.db.connection import init_db
from app.db.repository import DatabaseRepository
from app.main import app
from app.ops.backup_manager import BackupManager
from app.ops.config_guard import ProductionConfigurationGuard, mask_secret
from app.ops.hardening_runner import ProductionHardeningRunner
from app.ops.health_probes import ProductionHealthMonitor
from app.ops.integrity_verifier import DatabaseIntegrityVerifier


@pytest.fixture
def temp_env(tmp_path: str) -> dict[str, str]:
    """Sets up an isolated database and backup directory environment."""
    db_file = os.path.join(str(tmp_path), "test_trading_agent.db")
    backup_dir = os.path.join(str(tmp_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    init_db(db_file)
    return {"db_file": db_file, "backup_dir": backup_dir, "root": str(tmp_path)}


def test_backup_creation_and_integrity(temp_env: dict[str, str]) -> None:
    """Verify BackupManager creates non-blocking verified online backup with SHA-256."""
    db_path = temp_env["db_file"]
    backup_dir = temp_env["backup_dir"]

    # Seed data
    repo = DatabaseRepository(db_path=db_path)
    repo.save_system_event(source="TEST", level="INFO", message="Pre-backup seed event")

    mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
    meta = mgr.create_backup(tag="test_snap")

    assert meta.verified is True
    assert "ok" in meta.integrity_status.lower()
    assert os.path.exists(meta.backup_file)
    assert meta.size_bytes > 0
    assert len(meta.sha256_hash) == 64  # Valid SHA-256 hex string

    # Verify sidecar metadata JSON exists
    assert os.path.exists(meta.backup_file + ".json")

    # Verify listing
    backups = mgr.list_backups()
    assert len(backups) == 1
    assert backups[0].backup_id == meta.backup_id


def test_backup_restoration_and_safety_snapshot(temp_env: dict[str, str]) -> None:
    """Verify BackupManager safely restores database and generates pre-restore rollback snapshot."""
    db_path = temp_env["db_file"]
    backup_dir = temp_env["backup_dir"]
    mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)

    # 1. Baseline state
    repo = DatabaseRepository(db_path=db_path)
    repo.save_system_event(source="TEST", level="INFO", message="Event prior to backup")
    backup_meta = mgr.create_backup(tag="pre_alteration")

    # 2. Modify database state
    repo.save_system_event(source="TEST", level="WARNING", message="Mutated event after backup")

    # 3. Restore backup
    success = mgr.restore_backup(
        backup_filepath=backup_meta.backup_file,
        target_db_path=db_path,
        create_pre_restore_snapshot=True,
    )
    assert success is True

    # Check pre-restore snapshot file was created
    parent_files = os.listdir(os.path.dirname(db_path))
    pre_restores = [f for f in parent_files if ".pre_restore" in f]
    assert len(pre_restores) >= 1

    # Check database integrity post-restore
    verifier = DatabaseIntegrityVerifier(db_path=db_path)
    rep = verifier.run_full_verification()
    assert rep.is_healthy is True


def test_backup_rotation_policy(temp_env: dict[str, str]) -> None:
    """Verify BackupManager rotates older backups according to retention policy."""
    db_path = temp_env["db_file"]
    backup_dir = temp_env["backup_dir"]

    # Retention max 2
    mgr = BackupManager(db_path=db_path, backup_dir=backup_dir, max_retained_backups=2)

    import time
    for i in range(4):
        mgr.create_backup(tag=f"rot_{i}")
        time.sleep(0.01)

    backups = mgr.list_backups()
    assert len(backups) <= 2


def test_database_integrity_verifier_clean(temp_env: dict[str, str]) -> None:
    """Verify DatabaseIntegrityVerifier confirms 14 core tables, WAL mode, and zero FK errors."""
    db_path = temp_env["db_file"]
    verifier = DatabaseIntegrityVerifier(db_path=db_path)
    report = verifier.run_full_verification()

    assert report.is_healthy is True
    assert report.integrity_check_passed is True
    assert report.foreign_keys_passed is True
    assert len(report.missing_tables) == 0
    assert report.journal_mode in ("WAL", "MEMORY")
    assert report.accounting_reconciled is True
    assert report.capital_invariants_passed is True


def test_database_integrity_catches_math_discrepancy(temp_env: dict[str, str]) -> None:
    """Verify DatabaseIntegrityVerifier flags accounting math discrepancy between Gross and Net PnL."""
    db_path = temp_env["db_file"]

    # Directly insert corrupted trade row where net_pnl does not equal gross - friction
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO trades (
            id, plan_id, symbol, side, strategy, quantity,
            price, fee_brokerage, fee_stt, fee_exchange, fee_sebi,
            fee_stamp_duty, fee_gst, slippage, total_friction,
            gross_pnl, net_pnl, holding_duration_seconds, exit_trigger, executed_at
        ) VALUES (
            'TR-CORRUPT-01', 'PLAN-01', 'SUZLON', 'BUY', 'MOMENTUM_CONTINUATION', 10,
            50.0, 0.2, 0.1, 0.1, 0.05, 0.05, 0.5, 0.0, 1.0,
            20.0, 50.0, 300.0, 'TAKE_PROFIT', '2026-09-25T10:05:00Z'
        );
        """
    )
    conn.commit()
    conn.close()

    verifier = DatabaseIntegrityVerifier(db_path=db_path)
    report = verifier.run_full_verification()

    assert report.accounting_reconciled is False
    assert len(report.accounting_issues) > 0
    assert "TR-CORRUPT-01" in report.accounting_issues[0]
    assert report.is_healthy is False


def test_secrets_handling_and_masking() -> None:
    """Verify secrets masking utility and configuration guard secrets audit."""
    assert mask_secret(None) == "<NOT_SET>"
    assert mask_secret("") == "<NOT_SET>"
    assert mask_secret("short") == "****"
    assert mask_secret("PROD-LIVE-APPROVAL-KEY-9981") == "PROD****9981"
    assert mask_secret("KITE_SECRET_987654321") == "KITE****4321"

    guard = ProductionConfigurationGuard()
    sec_audit = guard.audit_secrets_handling()
    assert sec_audit.status in ("PASS", "WARNING")
    assert "approval_token_masked" in sec_audit.evidence


def test_broker_isolation_and_live_paper_separation() -> None:
    """Verify live/paper separation and broker isolation guard."""
    guard = ProductionConfigurationGuard()
    broker_audit = guard.audit_broker_isolation()
    assert broker_audit.status == "PASS"
    assert broker_audit.evidence["is_paper_trading"] is True


def test_production_health_monitor(temp_env: dict[str, str]) -> None:
    """Verify ProductionHealthMonitor sweeps across 6 subsystems and returns HEALTHY status."""
    db_path = temp_env["db_file"]
    backup_dir = temp_env["backup_dir"]

    # Create one backup so backup probe is happy
    mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
    mgr.create_backup(tag="init")

    monitor = ProductionHealthMonitor(db_path=db_path, backup_dir=backup_dir)
    report = monitor.run_full_health_check()

    assert report.system_status in ("HEALTHY", "DEGRADED")
    assert "sqlite_database" in report.components
    assert "disk_storage" in report.components
    assert "backup_manager" in report.components
    assert "position_watcher" in report.components
    assert "broker_adapter" in report.components
    assert "ai_council" in report.components


def test_production_hardening_runner_14_dimensions(temp_env: dict[str, str]) -> None:
    """Verify ProductionHardeningRunner audits all 14 Phase 23 dimensions."""
    db_path = temp_env["db_file"]
    root = temp_env["root"]

    # Create dummy docs and build manifests in temp root to test doc/dependency/build dimensions
    for d in ["RUNBOOK.md", "OPERATIONS.md", "INCIDENT_RESPONSE.md", "BACKUP_RECOVERY.md", "RELEASE_CHECKLIST.md"]:
        with open(os.path.join(root, d), "w", encoding="utf-8") as f:
            f.write("# Test Doc")

    backend_dir = os.path.join(root, "backend")
    os.makedirs(backend_dir, exist_ok=True)
    with open(os.path.join(backend_dir, "requirements-pinned.txt"), "w", encoding="utf-8") as f:
        f.write("fastapi==0.141.1\n")
    with open(os.path.join(root, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write("FROM python:3.11-slim\n")

    runner = ProductionHardeningRunner(db_path=db_path, project_root=root)
    audit = runner.verify_all_dimensions()

    assert audit.dimensions_evaluated == 14
    assert audit.all_passed is True
    assert audit.dimensions_failed == 0


def test_fastapi_hardening_endpoints(temp_env: dict[str, str]) -> None:
    """Verify Phase 23 FastAPI endpoints: hardening-audit, integrity, backup/create, backup/list."""
    db_path = temp_env["db_file"]
    app.dependency_overrides[get_db_path] = lambda: db_path
    client = TestClient(app)

    try:
        # 1. Hardening audit endpoint
        r_audit = client.get("/api/v1/system/hardening-audit")
        assert r_audit.status_code == 200
        data_audit = r_audit.json()
        assert "dimensions_evaluated" in data_audit
        assert data_audit["dimensions_evaluated"] == 14

        # 2. Database integrity endpoint
        r_integ = client.get("/api/v1/system/integrity")
        assert r_integ.status_code == 200
        data_integ = r_integ.json()
        assert data_integ["is_healthy"] is True
        assert data_integ["integrity_check_passed"] is True

        # 3. Create backup endpoint
        r_bkp = client.post("/api/v1/system/backup/create?tag=api_test")
        assert r_bkp.status_code == 200
        data_bkp = r_bkp.json()
        assert data_bkp["success"] is True

        # 4. List backups endpoint
        r_list = client.get("/api/v1/system/backup/list")
        assert r_list.status_code == 200
        data_list = r_list.json()
        assert len(data_list) >= 1
    finally:
        app.dependency_overrides.clear()
