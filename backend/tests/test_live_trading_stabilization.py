"""Comprehensive test suite for Phase 26: Live Trading Stabilization.

Verifies:
1. Capital invariant enforcement (rejection of automatic capital increases > INR 100).
2. Paper vs Live execution comparison (fill rates, latency SLAs).
3. Realized slippage distribution (ticks, bps, adverse vs favorable).
4. Statutory cost variance (modeled vs realized exchange/SEBI/STT/GST costs).
5. Rejected orders auditing and safety boundary enforcement.
6. Partial fills and order book depth absorption.
7. Broker vs SQLite WAL ledger state reconciliation.
8. Position Watcher sub-50ms deterministic SLA compliance.
9. Consolidated stabilization report generation.
10. FastAPI REST API endpoints (/api/v1/stabilization/*).
11. CLI stabilization runner execution.
"""

from __future__ import annotations

import os
import sys
import tempfile
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db.connection import init_db
from app.live.stabilization_engine import (
    CostVarianceAnalysis,
    ExecutionMetricComparison,
    LiveStabilizationEngine,
    PartialFillsAnalysis,
    PositionWatcherSurveillance,
    ReconciliationAudit,
    RejectedOrdersAnalysis,
    SlippageAnalysis,
    StabilizationSecurityError,
    StabilizationSummary,
)
from app.main import app

# Ensure scripts directory can be imported
_scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from stabilization_runner import main as stabilization_cli_main


@pytest.fixture
def temp_stabilization_db():
    """Create isolated SQLite database for stabilization testing."""
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


def test_stabilization_engine_initialization(temp_stabilization_db: str):
    """Verify stabilization engine initializes with strict Phase 26 invariant defaults."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    assert engine.initial_capital == Decimal("100.00")
    assert engine.autonomous_threshold == Decimal("300.00")
    assert engine.verify_capital_invariants() is True


def test_capital_invariant_prohibits_auto_increase(temp_stabilization_db: str):
    """Verify any attempt to automatically increase capital beyond INR 100 raises security error."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)

    # Valid check under/at ceiling
    assert engine.verify_capital_invariants(Decimal("100.00")) is True
    assert engine.verify_capital_invariants(Decimal("50.00")) is True

    # Attempted auto-scaling must fail deterministically
    with pytest.raises(StabilizationSecurityError) as exc_info:
        engine.verify_capital_invariants(Decimal("150.00"))
    assert "Automatic capital increase" in str(exc_info.value)
    assert "prohibited in Phase 26" in str(exc_info.value)


def test_compare_execution_metrics(temp_stabilization_db: str):
    """Verify execution comparison between paper trading baseline and live executions."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    metrics = engine.compare_execution_metrics()

    assert isinstance(metrics, ExecutionMetricComparison)
    assert metrics.paper_fill_rate_pct == 96.0
    assert metrics.live_fill_rate_pct == 80.0
    assert metrics.paper_avg_fill_latency_ms < 50.0
    assert metrics.live_avg_fill_latency_ms < 50.0
    assert metrics.fill_rate_pass is True
    assert metrics.latency_pass is True


def test_evaluate_slippage_distribution(temp_stabilization_db: str):
    """Verify slippage distribution metrics and boundary compliance (<25 bps)."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    slip = engine.evaluate_slippage()

    assert isinstance(slip, SlippageAnalysis)
    assert slip.total_fills == 4
    assert slip.zero_slippage_fills == 2
    assert slip.favorable_slippage_fills == 1
    assert slip.adverse_slippage_fills == 1
    assert slip.avg_slippage_bps == 2.1
    assert slip.max_adverse_slippage_bps < 25.0
    assert slip.is_acceptable is True


def test_evaluate_cost_variance(temp_stabilization_db: str):
    """Verify statutory cost variance between modeled fees and realized broker debits."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    cost = engine.evaluate_cost_variance()

    assert isinstance(cost, CostVarianceAnalysis)
    assert cost.total_turnover_inr == 385.20
    assert cost.cost_variance_pct < 5.0
    assert cost.fee_drag_pct_of_turnover < 0.5
    assert "brokerage" in cost.breakdown_verified
    assert "gst" in cost.breakdown_verified
    assert cost.is_accurate is True


def test_evaluate_rejected_orders(temp_stabilization_db: str):
    """Verify rejected orders audit ensures safety boundaries are enforced."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    rej = engine.evaluate_rejected_orders()

    assert isinstance(rej, RejectedOrdersAnalysis)
    assert rej.total_submissions == 5
    assert rej.total_rejections == 1
    assert rej.rejections_by_reason.get("EXCEEDS_100_CAP") == 1
    assert rej.safety_rejections_compliant is True


def test_evaluate_partial_fills(temp_stabilization_db: str):
    """Verify partial fills evaluation confirms liquidity adequacy."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    partial = engine.evaluate_partial_fills()

    assert isinstance(partial, PartialFillsAnalysis)
    assert partial.orders_with_partial_fills == 0
    assert partial.avg_chunks_per_order == 1.0
    assert partial.liquidity_adequate is True


def test_audit_reconciliation(temp_stabilization_db: str):
    """Verify broker state reconciles 100% with local SQLite WAL ledger."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    recon = engine.audit_reconciliation()

    assert isinstance(recon, ReconciliationAudit)
    assert recon.broker_active_positions_count == recon.database_open_positions_count
    assert recon.position_quantity_mismatch_count == 0
    assert recon.cash_discrepancy_inr == 0.0
    assert recon.is_in_parity is True


def test_audit_position_watcher_surveillance(temp_stabilization_db: str):
    """Verify Position Watcher SLA compliance (sub-50ms) and zero LLM in exit path."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    watcher = engine.audit_position_watcher_surveillance()

    assert isinstance(watcher, PositionWatcherSurveillance)
    assert watcher.sub_50ms_compliance_pct == 100.0
    assert watcher.realized_median_latency_us < 50_000  # < 50ms
    assert watcher.realized_p95_latency_us < 50_000
    assert watcher.zero_llm_dependency_verified is True
    assert watcher.sla_passed is True


def test_generate_stabilization_report(temp_stabilization_db: str):
    """Verify full stabilization synthesis report generation."""
    engine = LiveStabilizationEngine(db_path=temp_stabilization_db)
    summary = engine.generate_stabilization_report()

    assert isinstance(summary, StabilizationSummary)
    assert summary.phase_id == "PHASE-26-STABILIZATION"
    assert summary.stabilization_status == "STABLE"
    assert summary.capital_invariants_preserved is True
    assert summary.capital_increase_attempted is False
    assert summary.recommendation == "PROCEED_TO_STRATEGY_RESEARCH"


# --- REST API Tests ---

def test_api_stabilization_report():
    """Verify GET /api/v1/stabilization/report endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/report")
    assert response.status_code == 200
    data = response.json()
    assert data["phase_id"] == "PHASE-26-STABILIZATION"
    assert data["stabilization_status"] == "STABLE"
    assert data["capital_invariants_preserved"] is True
    assert data["recommendation"] == "PROCEED_TO_STRATEGY_RESEARCH"


def test_api_stabilization_comparison():
    """Verify GET /api/v1/stabilization/comparison endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/comparison")
    assert response.status_code == 200
    data = response.json()
    assert data["paper_fill_rate_pct"] == 96.0
    assert data["live_fill_rate_pct"] == 80.0
    assert data["fill_rate_pass"] is True
    assert data["latency_pass"] is True


def test_api_stabilization_slippage():
    """Verify GET /api/v1/stabilization/slippage endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/slippage")
    assert response.status_code == 200
    data = response.json()
    assert data["total_fills"] == 4
    assert data["is_acceptable"] is True


def test_api_stabilization_cost_variance():
    """Verify GET /api/v1/stabilization/cost-variance endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/cost-variance")
    assert response.status_code == 200
    data = response.json()
    assert data["is_accurate"] is True
    assert data["cost_variance_inr"] == 0.02


def test_api_stabilization_reconciliation():
    """Verify GET /api/v1/stabilization/reconciliation endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/reconciliation")
    assert response.status_code == 200
    data = response.json()
    assert data["is_in_parity"] is True
    assert data["cash_discrepancy_inr"] == 0.0


def test_api_stabilization_watcher_behavior():
    """Verify GET /api/v1/stabilization/watcher-behavior endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/stabilization/watcher-behavior")
    assert response.status_code == 200
    data = response.json()
    assert data["sla_passed"] is True
    assert data["zero_llm_dependency_verified"] is True
    assert data["sub_50ms_compliance_pct"] == 100.0


# --- CLI Runner Tests ---

def test_stabilization_cli_runner(monkeypatch, capsys):
    """Verify CLI stabilization runner execution in both ASCII and JSON mode."""
    # Test ASCII format
    monkeypatch.setattr(sys, "argv", ["stabilization_runner.py"])
    exit_code = stabilization_cli_main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "PHASE 26 LIVE TRADING STABILIZATION AUDIT REPORT" in captured.out
    assert "Stabilization Status: STABLE" in captured.out

    # Test JSON format
    monkeypatch.setattr(sys, "argv", ["stabilization_runner.py", "--json"])
    exit_code = stabilization_cli_main()
    assert exit_code == 0
    captured_json = capsys.readouterr()
    assert '"phase_id": "PHASE-26-STABILIZATION"' in captured_json.out
    assert '"recommendation": "PROCEED_TO_STRATEGY_RESEARCH"' in captured_json.out
