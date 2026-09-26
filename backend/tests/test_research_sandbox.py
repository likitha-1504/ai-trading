"""Comprehensive Test Suite for Phase 35 Research Sandbox.

Tests:
- Production Isolation & Quarantine Enforcement
- Reproducible Datasets & Cryptographic SHA-256 Fingerprinting
- Versioned Code & Configuration Management
- Deterministic Sandbox Simulation & Reproducibility Verification
- Explicit Promotion Gate & Anti-Silent Promotion Guard
- Tamper-Evident Audit Logging of Promotion Decisions
- FastAPI REST Endpoints
- Operational CLI Runner Execution
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.connection import init_db
from app.main import app
from app.sandbox.dataset_registry import (
    ReproducibleDatasetRegistry,
    compute_bars_sha256,
)
from app.sandbox.isolation_guard import (
    SandboxIsolationGuard,
    SandboxIsolationState,
)
from app.sandbox.models import (
    ProductionIsolationError,
    PromotionRequest,
    PromotionStage,
    SandboxExecutionMetrics,
    SandboxExecutionResult,
    SilentPromotionError,
)
from app.sandbox.promotion_gate import ExplicitPromotionGate
from app.sandbox.sandbox_engine import (
    ResearchSandboxEngine,
    compute_execution_hash,
)
from app.sandbox.versioned_config import (
    VersionedConfigManager,
    compute_config_hash,
)
from app.security.tamper_log import TamperEvidentAuditLogger


@pytest.fixture
def temp_db():
    """Provides an isolated SQLite database for audit log testing."""
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
# 1. Isolation & Quarantine Tests
# =========================================================================

def test_production_db_isolation_guard() -> None:
    guard = SandboxIsolationGuard(prod_db_path=settings.DATABASE_PATH)
    assert guard.state == SandboxIsolationState.QUARANTINED

    # Attempting to access production DB must raise ProductionIsolationError
    with pytest.raises(ProductionIsolationError):
        guard.validate_database_isolation(settings.DATABASE_PATH)

    assert guard.state == SandboxIsolationState.VIOLATION_DETECTED

    # Safe isolated path must pass
    guard_safe = SandboxIsolationGuard()
    guard_safe.validate_database_isolation("C:/Users/likit/Desktop/project/sandbox_isolated.db")
    assert guard_safe.state == SandboxIsolationState.QUARANTINED


def test_broker_isolation_guard() -> None:
    guard = SandboxIsolationGuard()

    class MockLiveBroker:
        is_live = True

    with pytest.raises(ProductionIsolationError):
        guard.validate_broker_isolation(MockLiveBroker())


def test_sandbox_scope_context() -> None:
    assert SandboxIsolationGuard.is_in_sandbox() is False
    with SandboxIsolationGuard.isolated_sandbox_scope():
        assert SandboxIsolationGuard.is_in_sandbox() is True
    assert SandboxIsolationGuard.is_in_sandbox() is False


# =========================================================================
# 2. Reproducible Dataset & SHA-256 Tests
# =========================================================================

def test_synthetic_bars_determinism() -> None:
    bars1 = ReproducibleDatasetRegistry.generate_synthetic_bars(seed=42, count=50)
    bars2 = ReproducibleDatasetRegistry.generate_synthetic_bars(seed=42, count=50)
    bars3 = ReproducibleDatasetRegistry.generate_synthetic_bars(seed=99, count=50)

    hash1 = compute_bars_sha256(bars1, seed=42)
    hash2 = compute_bars_sha256(bars2, seed=42)
    hash3 = compute_bars_sha256(bars3, seed=99)

    assert hash1 == hash2
    assert hash1 != hash3


def test_dataset_registry_integrity_and_immutability() -> None:
    reg = ReproducibleDatasetRegistry()
    ds = reg.get_dataset("DATASET-NIFTY-MICRO-2026-TRAIN")
    assert ds is not None
    assert ds.record_count == 100

    # Integrity verification
    valid, msg = reg.verify_integrity("DATASET-NIFTY-MICRO-2026-TRAIN")
    assert valid is True
    assert "verified" in msg

    # Duplicate registration prevention
    with pytest.raises(ValueError):
        reg.register_dataset(ds)


# =========================================================================
# 3. Versioned Code & Configuration Tests
# =========================================================================

def test_versioned_config_manager() -> None:
    mgr = VersionedConfigManager()
    cfg = mgr.get_config("EXP-SANDBOX-EMA-V1")
    assert cfg.strategy_name == "EMA_PULLBACK"
    assert cfg.version == "1.0.0-sandbox"

    # Verify config hash
    expected = compute_config_hash(
        strategy_name=cfg.strategy_name,
        parameters=cfg.parameters,
        risk_limits=cfg.risk_limits,
        code_hash=cfg.code_hash,
        dataset_hash=cfg.dataset_hash,
    )
    assert cfg.config_hash == expected


# =========================================================================
# 4. Simulation Engine & Exact Reproducibility Tests
# =========================================================================

def test_sandbox_simulation_execution() -> None:
    engine = ResearchSandboxEngine()
    result = engine.run_simulation("EXP-SANDBOX-EMA-V1")

    assert result.experiment_id == "EXP-SANDBOX-EMA-V1"
    assert result.isolation_verified is True
    assert result.metrics.total_trades > 0
    assert result.metrics.total_fees_slippage > 0.0


def test_sandbox_exact_reproducibility() -> None:
    engine = ResearchSandboxEngine()
    valid, result, msg = engine.verify_reproducibility("EXP-SANDBOX-EMA-V1")

    assert valid is True
    assert result.reproducibility_verified is True
    assert "Exact mathematical reproducibility verified" in msg


# =========================================================================
# 5. Promotion Gate & Anti-Silent Promotion Tests
# =========================================================================

def test_anti_silent_promotion_guard() -> None:
    gate = ExplicitPromotionGate()
    req = PromotionRequest(
        experiment_id="EXP-SANDBOX-EMA-V1",
        target_environment="PAPER_CANDIDATE",
        operator_token="",  # Empty token -> must be rejected
        rationale="Testing silent promotion block",
    )

    with pytest.raises(SilentPromotionError) as exc_info:
        gate.process_promotion_request(req)

    assert "Silent promotion prohibited" in str(exc_info.value)


def test_promotion_gate_evaluation_and_audit_logging(temp_db: str) -> None:
    logger = TamperEvidentAuditLogger(db_path=temp_db)
    engine = ResearchSandboxEngine()
    gate = ExplicitPromotionGate(engine=engine, audit_logger=logger)

    # Fabricate a passing execution result meeting all strict hurdles
    passing_metrics = SandboxExecutionMetrics(
        total_trades=25,
        winning_trades=18,
        losing_trades=7,
        win_rate=0.72,
        profit_factor=2.45,
        sharpe_ratio=1.85,
        max_drawdown_pct=1.40,
        net_pnl=14.50,
        gross_pnl=18.25,
        total_fees_slippage=3.75,
    )
    exec_hash = compute_execution_hash("dummy_ds_h", "dummy_cfg_h", passing_metrics)
    passing_result = SandboxExecutionResult(
        run_id="RUN-TEST-PASS-01",
        experiment_id="EXP-TEST-PROMO",
        dataset_id="DATASET-NIFTY-MICRO-2026-TRAIN",
        dataset_hash="dummy_ds_h",
        config_hash="dummy_cfg_h",
        executed_at=datetime.now(timezone.utc),
        metrics=passing_metrics,
        execution_hash=exec_hash,
        isolation_verified=True,
        reproducibility_verified=True,
    )

    valid_token = "OPERATOR-PROMOTION-PHASE35-VERIFIED-AUTH-KEY-999"
    req = PromotionRequest(
        experiment_id="EXP-TEST-PROMO",
        target_environment="PAPER_CANDIDATE",
        operator_token=valid_token,
        rationale="Validated alpha on micro-Nifty with sub-1.5% DD",
    )

    promo_result = gate.process_promotion_request(req, execution_result=passing_result)
    assert promo_result.success is True
    assert promo_result.stage == PromotionStage.APPROVED_CANDIDATE
    assert promo_result.audit_ledger_id is not None

    # Verify that the audit ledger has recorded the promotion
    chain_valid, chain_msg, count = logger.verify_chain_integrity()
    assert chain_valid is True
    assert count >= 1


# =========================================================================
# 6. FastAPI REST Endpoints Tests
# =========================================================================

def test_fastapi_sandbox_endpoints(client: TestClient) -> None:
    # 1. GET /status
    res_status = client.get("/api/v1/sandbox/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["isolation_state"] == "QUARANTINED"
    assert data_status["quarantine_active"] is True

    # 2. GET /datasets
    res_ds = client.get("/api/v1/sandbox/datasets")
    assert res_ds.status_code == 200
    datasets = res_ds.json()
    assert len(datasets) >= 2

    # 3. GET /datasets/{id}/verify
    res_verify_ds = client.get(
        "/api/v1/sandbox/datasets/DATASET-NIFTY-MICRO-2026-TRAIN/verify"
    )
    assert res_verify_ds.status_code == 200
    assert res_verify_ds.json()["integrity_valid"] is True

    # 4. GET /experiments
    res_exp = client.get("/api/v1/sandbox/experiments")
    assert res_exp.status_code == 200
    assert len(res_exp.json()) >= 2

    # 5. POST /experiments/run
    res_run = client.post(
        "/api/v1/sandbox/experiments/run?experiment_id=EXP-SANDBOX-EMA-V1"
    )
    assert res_run.status_code == 200
    assert res_run.json()["isolation_verified"] is True

    # 6. POST /experiments/verify-reproducibility
    res_repro = client.post(
        "/api/v1/sandbox/experiments/verify-reproducibility?experiment_id=EXP-SANDBOX-EMA-V1"
    )
    assert res_repro.status_code == 200
    assert res_repro.json()["reproducibility_verified"] is True

    # 7. POST /promote (silent rejection check)
    res_promo_silent = client.post(
        "/api/v1/sandbox/promote",
        json={
            "experiment_id": "EXP-SANDBOX-EMA-V1",
            "target_environment": "PAPER_CANDIDATE",
            "operator_token": "INVALID_TOKEN",
            "rationale": "Testing silent rejection",
        },
    )
    assert res_promo_silent.status_code == 403


# =========================================================================
# 7. Operational CLI Runner Subprocess Tests
# =========================================================================

def test_cli_sandbox_runner_subprocesses() -> None:
    # 1. Probe status
    cmd_status = [sys.executable, "backend/scripts/sandbox_runner.py", "--status"]
    r_status = subprocess.run(cmd_status, capture_output=True, text=True, timeout=20, check=False)
    assert r_status.returncode == 0
    assert "SANDBOX QUARANTINE STATUS REPORT" in r_status.stdout

    # 2. List datasets and configs
    cmd_list = [sys.executable, "backend/scripts/sandbox_runner.py", "--list"]
    r_list = subprocess.run(cmd_list, capture_output=True, text=True, timeout=20, check=False)
    assert r_list.returncode == 0
    assert "REGISTERED REPRODUCIBLE DATASETS" in r_list.stdout

    # 3. Verify reproducibility
    cmd_verify = [
        sys.executable,
        "backend/scripts/sandbox_runner.py",
        "--verify",
        "EXP-SANDBOX-EMA-V1",
    ]
    r_verify = subprocess.run(cmd_verify, capture_output=True, text=True, timeout=20, check=False)
    assert r_verify.returncode == 0
    assert "Exact mathematical reproducibility verified" in r_verify.stdout


# =========================================================================
# 8. Additional Edge Cases & Hurdles Rejection Tests
# =========================================================================

def test_promotion_gate_statistical_hurdles_rejection() -> None:
    gate = ExplicitPromotionGate()

    # Metrics breaching min_trades and win_rate
    failing_metrics = SandboxExecutionMetrics(
        total_trades=10,  # Required >= 20
        winning_trades=3,
        losing_trades=7,
        win_rate=0.30,   # Required >= 0.50
        profit_factor=0.85,  # Required >= 1.30
        sharpe_ratio=0.45,   # Required >= 1.20
        max_drawdown_pct=5.50,  # Required <= 2.50%
        net_pnl=-5.50,
        gross_pnl=-4.00,
        total_fees_slippage=1.50,
    )
    exec_hash = compute_execution_hash("ds_h", "cfg_h", failing_metrics)
    failing_result = SandboxExecutionResult(
        run_id="RUN-FAIL-01",
        experiment_id="EXP-FAIL",
        dataset_id="DATASET-NIFTY-MICRO-2026-TRAIN",
        dataset_hash="ds_h",
        config_hash="cfg_h",
        executed_at=datetime.now(timezone.utc),
        metrics=failing_metrics,
        execution_hash=exec_hash,
        isolation_verified=True,
        reproducibility_verified=True,
    )

    evaluation = gate.evaluate_candidate(
        failing_result,
        operator_token="OPERATOR-PROMOTION-PHASE35-VALID-TOKEN-KEY-12345",
    )
    assert evaluation.passed_statistical_hurdles is False
    assert evaluation.target_stage == PromotionStage.REJECTED
    assert len(evaluation.rejection_reasons) >= 3


def test_dataset_tamper_detection() -> None:
    reg = ReproducibleDatasetRegistry()
    ds = reg.get_dataset("DATASET-NIFTY-MICRO-2026-TRAIN")

    # Manually tamper with a bar's close price
    original_close = ds.bars[0].close
    try:
        ds.bars[0].close += 100.0  # Malicious tamper
        valid, msg = reg.verify_integrity("DATASET-NIFTY-MICRO-2026-TRAIN")
        assert valid is False
        assert "Integrity compromised" in msg
    finally:
        ds.bars[0].close = original_close  # Restore


def test_operator_token_validation_matrix() -> None:
    assert ExplicitPromotionGate._validate_operator_token(None) is False
    assert ExplicitPromotionGate._validate_operator_token("") is False
    assert ExplicitPromotionGate._validate_operator_token("short") is False
    assert ExplicitPromotionGate._validate_operator_token("RANDOM-TOKEN") is False

    # Valid Phase 35 token
    assert (
        ExplicitPromotionGate._validate_operator_token(
            "OPERATOR-PROMOTION-PHASE35-VERIFIED-AUTH-KEY-12345"
        )
        is True
    )

    # Valid OPTOK HMAC token
    assert ExplicitPromotionGate._validate_operator_token("OPTOK.payload.hmac") is True

