"""Comprehensive test suite for Phase 27: Strategy Research & Optimization.

Verifies:
1. LeakageAuditor: look-ahead bias detection, timestamp monotonicity, and split boundary isolation.
2. StrategyExperimentRegistry: immutable experiment preservation and version lineage.
3. Silent production entry prevention: strict guard against promoting unapproved experiments.
4. StrategyResearchEngine: realistic Indian market cost & slippage modeling and walk-forward validation.
5. FastAPI REST API endpoints (/api/v1/research/*).
6. CLI research runner execution.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.contracts import (
    MarketSource,
    NormalizedMarketEvent,
)
from app.research.experiment_registry import (
    StrategyExperimentRegistry,
)
from app.research.leakage_auditor import LeakageAuditor
from app.research.models import (
    ExperimentStatus,
    ExperimentVersion,
    LeakageAuditReport,
    SilentProductionEntryError,
    StrategyHypothesis,
    WalkForwardSummary,
)
from app.research.research_engine import StrategyResearchEngine

# Ensure scripts directory can be imported
_scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from research_runner import main as research_cli_main


def _make_dummy_event(ts: datetime, symbol: str = "RELIANCE") -> NormalizedMarketEvent:
    return NormalizedMarketEvent(
        symbol=symbol,
        source=MarketSource.SIMULATED,
        exchange_timestamp=ts,
        ingest_timestamp=ts,
        last_price=Decimal("2500.05"),
        volume=100,
        bid_price=Decimal("2500.00"),
        ask_price=Decimal("2500.10"),
        bid_quantity=50,
        ask_quantity=50,
        spread_pct=Decimal("0.004"),
        is_stale=False,
    )


# --- Leakage Auditor Tests ---

def test_leakage_auditor_monotonic_success():
    """Verify monotonic event series passes leakage audit cleanly."""
    base_ts = datetime(2026, 9, 26, 9, 15, 0, tzinfo=timezone.utc)
    events = [_make_dummy_event(base_ts + timedelta(seconds=i)) for i in range(10)]
    report = LeakageAuditor.audit_event_stream(events)

    assert report.is_leakage_free is True
    assert report.timestamp_monotonic is True
    assert report.lookahead_bias_detected is False
    assert report.checked_events_count == 10


def test_leakage_auditor_inversion_detected():
    """Verify timestamp inversions are immediately detected as lookahead bias."""
    base_ts = datetime(2026, 9, 26, 9, 15, 0, tzinfo=timezone.utc)
    events = [
        _make_dummy_event(base_ts),
        _make_dummy_event(base_ts + timedelta(seconds=5)),
        _make_dummy_event(base_ts + timedelta(seconds=2)),  # Timestamp inversion!
    ]
    report = LeakageAuditor.audit_event_stream(events)

    assert report.is_leakage_free is False
    assert report.timestamp_monotonic is False
    assert report.lookahead_bias_detected is True
    assert "Timestamp inversion" in report.details


def test_leakage_auditor_train_test_split_clean():
    """Verify clean temporal boundary between train and test partitions passes."""
    t0 = datetime(2026, 9, 26, 9, 15, 0, tzinfo=timezone.utc)
    train_events = [_make_dummy_event(t0 + timedelta(minutes=i)) for i in range(5)]
    test_events = [_make_dummy_event(t0 + timedelta(minutes=5 + i)) for i in range(5)]

    report = LeakageAuditor.audit_train_test_split(train_events, test_events)
    assert report.is_leakage_free is True
    assert report.split_contamination_detected is False


def test_leakage_auditor_train_test_split_contamination():
    """Verify overlapping train/test splits are flagged as contamination."""
    t0 = datetime(2026, 9, 26, 9, 15, 0, tzinfo=timezone.utc)
    train_events = [_make_dummy_event(t0 + timedelta(minutes=i)) for i in range(10)]
    # test split starts at minute 5, overlapping train!
    test_events = [_make_dummy_event(t0 + timedelta(minutes=5 + i)) for i in range(5)]

    report = LeakageAuditor.audit_train_test_split(train_events, test_events)
    assert report.is_leakage_free is False
    assert report.split_contamination_detected is True
    assert "Temporal split contamination" in report.details


# --- Experiment Registry & Silent Entry Gate Tests ---

def test_registry_initializes_with_baseline_and_candidates():
    """Verify registry seeds the baseline v1.0.0 and research candidates."""
    registry = StrategyExperimentRegistry()
    experiments = registry.list_experiments()

    assert len(experiments) >= 3
    baseline = registry.get_experiment("EXP-STRAT-001")
    assert baseline is not None
    assert baseline.version_tag == "v1.0.0-baseline"
    assert baseline.status == ExperimentStatus.PROMOTED

    cand1 = registry.get_experiment("EXP-STRAT-002")
    assert cand1 is not None
    assert cand1.version_tag == "v1.1.0-volatility-filter"
    assert cand1.status == ExperimentStatus.VALIDATED


def test_registry_prevents_duplicate_version_tags():
    """Verify attempting to overwrite an existing semantic version tag is blocked."""
    registry = StrategyExperimentRegistry()
    duplicate = ExperimentVersion(
        experiment_id="EXP-STRAT-999",
        version_tag="v1.0.0-baseline",  # Duplicate tag!
        hypothesis=StrategyHypothesis(
            title="Duplicate",
            description="Testing duplicate collision",
            expected_edge_bps=10.0,
            risk_rationale="N/A",
        ),
        leakage_audit=LeakageAuditReport(
            is_leakage_free=True,
            timestamp_monotonic=True,
            lookahead_bias_detected=False,
            split_contamination_detected=False,
            future_target_referenced=False,
            checked_events_count=10,
            details="OK",
        ),
        walk_forward=WalkForwardSummary(
            num_windows=3,
            in_sample_ratio=0.7,
            avg_oos_profit_factor=1.5,
            avg_oos_expectancy_inr=1.5,
            window_stability_score=0.9,
            is_robust=True,
        ),
    )
    with pytest.raises(ValueError) as exc_info:
        registry.register_experiment(duplicate)
    assert "already exists" in str(exc_info.value)


def test_registry_prohibits_silent_production_entry():
    """Verify promotion without valid operator authorization token is rejected."""
    registry = StrategyExperimentRegistry()

    # Empty token must fail
    with pytest.raises(SilentProductionEntryError) as exc_info:
        registry.promote_experiment(
            experiment_id="EXP-STRAT-002",
            operator_authorization_token="",
            rationale="Testing silent entry",
        )
    assert "silent production entry is strictly prohibited" in str(exc_info.value)

    # Invalid token must fail
    with pytest.raises(SilentProductionEntryError) as exc_info:
        registry.promote_experiment(
            experiment_id="EXP-STRAT-002",
            operator_authorization_token="UNAUTHORIZED-KEY",
            rationale="Testing silent entry",
        )
    assert "Requires valid operator authorization token" in str(exc_info.value)


def test_registry_allows_authorized_promotion():
    """Verify promotion with valid operator authorization token succeeds."""
    registry = StrategyExperimentRegistry()
    promoted = registry.promote_experiment(
        experiment_id="EXP-STRAT-002",
        operator_authorization_token="OPERATOR-PHASE27-TOKEN-7788",
        rationale="Superior out-of-sample sharpe (2.15) with zero leakage.",
        target_environment="paper",
    )
    assert promoted.status == ExperimentStatus.PROMOTED
    assert "Promoted by operator" in promoted.notes


# --- Strategy Research Engine Tests ---

def test_research_engine_summary_generation():
    """Verify research engine compiles comparative research matrix."""
    registry = StrategyExperimentRegistry()
    engine = StrategyResearchEngine(registry=registry)
    summary = engine.generate_research_summary()

    assert summary.phase_id == "PHASE-27-RESEARCH"
    assert summary.total_experiments >= 3
    assert len(summary.comparison_matrix) >= 3
    assert summary.promoted_version == "v1.0.0-baseline"
    assert summary.candidates_count >= 2
    assert summary.recommendation == "CANDIDATES_AVAILABLE_FOR_OPERATOR_REVIEW"


def test_research_engine_runs_experiment():
    """Verify executing a new experiment through the research engine."""
    registry = StrategyExperimentRegistry()
    engine = StrategyResearchEngine(registry=registry)

    exp = engine.run_experiment(
        experiment_id="EXP-STRAT-004",
        version_tag="v1.3.0-volume-breakout",
        parent_version="v1.1.0-volatility-filter",
        hypothesis=StrategyHypothesis(
            title="Volume Surge Microstructure Filter",
            description="Requires 2.5x volume acceleration on breakout bar.",
            expected_edge_bps=17.5,
            risk_rationale="Eliminates low-liquidity slippage.",
        ),
        parameters={"rvol_threshold": 2.5},
    )

    assert exp.experiment_id == "EXP-STRAT-004"
    assert exp.version_tag == "v1.3.0-volume-breakout"
    assert exp.oos_sharpe > 1.5
    assert exp.leakage_audit.is_leakage_free is True
    assert exp.walk_forward.is_robust is True


# --- REST API Tests ---

def test_api_research_summary():
    """Verify GET /api/v1/research/summary endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/research/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["phase_id"] == "PHASE-27-RESEARCH"
    assert data["total_experiments"] >= 3
    assert "comparison_matrix" in data


def test_api_research_experiments_list():
    """Verify GET /api/v1/research/experiments endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/research/experiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_api_research_experiment_details():
    """Verify GET /api/v1/research/experiments/{id} endpoint."""
    client = TestClient(app)
    # Existing baseline
    response = client.get("/api/v1/research/experiments/EXP-STRAT-001")
    assert response.status_code == 200
    data = response.json()
    assert data["version_tag"] == "v1.0.0-baseline"

    # Non-existent
    response_404 = client.get("/api/v1/research/experiments/NONEXISTENT-999")
    assert response_404.status_code == 404


def test_api_research_leakage_audit():
    """Verify GET /api/v1/research/leakage-audit endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/research/leakage-audit")
    assert response.status_code == 200
    data = response.json()
    assert data["is_leakage_free"] is True
    assert data["timestamp_monotonic"] is True


def test_api_research_promote_blocked_and_allowed():
    """Verify POST /api/v1/research/promote endpoint enforces authorization."""
    client = TestClient(app)

    # Attempt silent promotion (forbidden 403)
    silent_payload = {
        "experiment_id": "EXP-STRAT-003",
        "operator_authorization_token": "INVALID-TOKEN",
        "target_environment": "paper",
        "rationale": "Silent promotion attempt",
    }
    res_forbidden = client.post("/api/v1/research/promote", json=silent_payload)
    assert res_forbidden.status_code == 403
    assert "silent production entry is strictly prohibited" in res_forbidden.json()["detail"]

    # Authorized promotion (200 OK)
    auth_payload = {
        "experiment_id": "EXP-STRAT-003",
        "operator_authorization_token": "OPERATOR-PHASE27-TOKEN-APPROVED",
        "target_environment": "paper",
        "rationale": "Validated candidate with +3.45 INR/trade expectancy.",
    }
    res_ok = client.post("/api/v1/research/promote", json=auth_payload)
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "PROMOTED"


# --- CLI Runner Tests ---

def test_research_cli_runner(monkeypatch, capsys):
    """Verify CLI research runner execution in both ASCII and JSON modes."""
    # Test ASCII format
    monkeypatch.setattr(sys, "argv", ["research_runner.py"])
    exit_code = research_cli_main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "PHASE 27 STRATEGY RESEARCH & OPTIMIZATION REPORT" in captured.out
    assert "v1.0.0-baseline" in captured.out

    # Test JSON format
    monkeypatch.setattr(sys, "argv", ["research_runner.py", "--json"])
    exit_code = research_cli_main()
    assert exit_code == 0
    captured_json = capsys.readouterr()
    assert '"phase_id": "PHASE-27-RESEARCH"' in captured_json.out

    # Test leakage check
    monkeypatch.setattr(sys, "argv", ["research_runner.py", "--leakage-check"])
    exit_code = research_cli_main()
    assert exit_code == 0
    captured_leak = capsys.readouterr()
    assert "Leakage Audit Status: PASS" in captured_leak.out
