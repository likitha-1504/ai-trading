"""Comprehensive test suite for Phase 20 Controlled ₹100 Live Experiment."""

import os
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_path
from app.db.connection import init_db
from app.live.experiment_engine import (
    LiveExperimentConfig,
    LiveExperimentEngine,
    LiveExperimentResult,
    LiveExperimentSecurityError,
)
from app.live.experiment_runner import main as runner_main
from app.main import app


@pytest.fixture
def clean_experiment_db(tmp_path: str) -> str:
    """Provide isolated SQLite database path for live experiment tests."""
    return os.path.join(str(tmp_path), "test_live_experiment.db")


def test_live_experiment_config_validation() -> None:
    """Verify LiveExperimentConfig enforces ₹100 capital and ₹300 autonomy ceilings."""
    # Valid config
    valid_cfg = LiveExperimentConfig(
        initial_capital=Decimal("100.00"),
        autonomous_threshold=Decimal("300.00"),
    )
    valid_cfg.validate()

    # Invalid: Initial capital > ₹100
    with pytest.raises(LiveExperimentSecurityError, match="exceeds Phase 20 limit of ₹100.00"):
        bad_cap_cfg = LiveExperimentConfig(initial_capital=Decimal("150.00"))
        bad_cap_cfg.validate()

    # Invalid: Autonomous threshold > ₹300
    with pytest.raises(LiveExperimentSecurityError, match="exceeds ₹300.00"):
        bad_auto_cfg = LiveExperimentConfig(autonomous_threshold=Decimal("500.00"))
        bad_auto_cfg.validate()


def test_capital_increase_rejection_without_token(clean_experiment_db: str) -> None:
    """Verify capital increase above ₹100 is strictly prohibited without human authorization."""
    cfg = LiveExperimentConfig(db_path=clean_experiment_db)
    engine = LiveExperimentEngine(config=cfg)

    # Attempting to increase without token
    with pytest.raises(LiveExperimentSecurityError, match="Strictly prohibited"):
        engine.request_capital_increase(new_capital=Decimal("200.00"), human_auth_token=None)

    # Attempting to increase with invalid token
    with pytest.raises(LiveExperimentSecurityError, match="Strictly prohibited"):
        engine.request_capital_increase(
            new_capital=Decimal("200.00"), human_auth_token="INVALID_TOKEN_123"
        )


def test_strategy_version_mutation_audit(clean_experiment_db: str) -> None:
    """Verify strategy parameter changes require documented reasons and are logged."""
    cfg = LiveExperimentConfig(db_path=clean_experiment_db)
    engine = LiveExperimentEngine(config=cfg)

    # Attempting mutation without documented reason
    with pytest.raises(LiveExperimentSecurityError, match="without documenting explicit reason"):
        engine.record_strategy_version(
            version="v1.0.1",
            reason="",
            parameters={"rvol_threshold": 2.2},
        )

    # Valid mutation with reason
    audit = engine.record_strategy_version(
        version="v1.0.1",
        reason="Tightening RVOL threshold from 1.8 to 2.2 based on morning spread compression",
        parameters={"rvol_threshold": 2.2},
    )
    assert audit.version == "v1.0.1"
    assert "Tightening RVOL threshold" in audit.reason
    assert audit.is_active is True

    # Verify persisted in SQLite
    saved_v = engine.repo.get_active_strategy_version("LIVE_EXPERIMENT_CORE")
    assert saved_v is not None
    assert saved_v["version"] == "v1.0.1"


def test_controlled_live_experiment_execution(clean_experiment_db: str) -> None:
    """Verify end-to-end execution of Phase 20 controlled live experiment across 9 dimensions."""
    cfg = LiveExperimentConfig(db_path=clean_experiment_db, num_sessions=5)
    engine = LiveExperimentEngine(config=cfg)

    result = engine.run_controlled_experiment()
    assert isinstance(result, LiveExperimentResult)
    assert result.initial_capital == Decimal("100.00")
    assert result.final_equity > Decimal("0.00")
    assert result.gate_checkpoint_reached is True

    # Dimension 1: Net P/L After Costs
    assert result.net_pnl_metrics.total_friction > Decimal("0.00")
    assert result.net_pnl_metrics.total_brokerage > Decimal("0.00")
    assert result.net_pnl_metrics.total_stt > Decimal("0.00")
    assert result.net_pnl_metrics.total_gst > Decimal("0.00")
    assert result.net_pnl_metrics.total_net_pnl == (
        result.net_pnl_metrics.total_gross_pnl - result.net_pnl_metrics.total_friction
    )

    # Dimension 2: Execution Quality
    assert result.execution_quality.orders_submitted == 5
    assert result.execution_quality.orders_filled == 4
    assert result.execution_quality.fill_rate_pct == 80.0  # 4/5 (1 rejected by ₹100 cap)
    assert result.execution_quality.avg_fill_latency_ms > 0.0

    # Dimension 3: Slippage
    assert result.slippage_metrics.max_slippage_bps >= 0.0
    assert len(result.slippage_metrics.tick_slippage_distribution) > 0

    # Dimension 4: Rejected Orders
    assert result.rejected_orders.total_rejections == 1
    assert result.rejected_orders.capital_cap_rejections == 1
    assert "EXCEEDS_100_CAP" in result.rejected_orders.rejections_by_reason

    # Dimension 5: Watcher Response
    assert result.watcher_response.total_evaluations > 0
    assert result.watcher_response.sub_50ms_compliance_pct == 100.0
    assert result.watcher_response.llm_independence_verified is True
    assert result.watcher_response.exits_triggered == 4

    # Dimension 6: Model Latency
    assert result.model_latency.qwen3_calls == 5
    assert result.model_latency.deepseek_r1_calls == 5
    assert result.model_latency.qwen3_avg_latency_ms > 0.0
    assert result.model_latency.deepseek_r1_avg_latency_ms > 0.0

    # Dimension 7: Model Disagreement
    assert result.model_disagreement.total_council_evaluations == 5
    assert result.model_disagreement.disagreements == 2
    assert result.model_disagreement.arbitrations_approved == 2

    # Dimension 8: Trade Frequency & Velocity
    assert result.trade_frequency.total_trades == 4
    assert result.trade_frequency.trades_per_session == 0.8
    assert result.trade_frequency.avg_holding_duration_seconds > 0.0

    # Dimension 9: Failure Events
    assert result.failure_events.unhandled_exceptions == 0


def test_experiment_report_cautionary_warning(clean_experiment_db: str) -> None:
    """Verify generated report includes explicit cautionary warnings on short-term profit."""
    cfg = LiveExperimentConfig(db_path=clean_experiment_db)
    engine = LiveExperimentEngine(config=cfg)
    result = engine.run_controlled_experiment()

    report = result.report_markdown
    assert "NEVER INTERPRET SHORT-TERM PROFIT AS PROOF OF A ROBUST STRATEGY" in report
    assert "Phase 20 Gate Checkpoint" in report
    assert "Micro-Capital Statutory Friction" in report
    assert "**Autonomous Threshold**: ₹300.00" in report


def test_experiment_runner_cli() -> None:
    """Verify Phase 20 CLI runner script executes successfully."""
    exit_code = runner_main()
    assert exit_code == 0


def test_live_experiment_api_endpoints() -> None:
    """Verify FastAPI endpoints for Phase 20 live experiment."""
    client = TestClient(app)

    # 1. Status endpoint
    res = client.get("/api/v1/live/experiment/status")
    assert res.status_code == 200
    data = res.json()
    assert data["experiment_id"] == "EXP-PHASE20-LIVE-100"
    assert data["initial_capital"] == 100.0
    assert data["gate_status"] == "PHASE_20_GATE_CHECKPOINT_AWAITING_APPROVAL"
    assert "net_pnl_metrics" in data["metrics"]
    assert "watcher_response" in data["metrics"]

    # 2. Report endpoint
    res = client.get("/api/v1/live/experiment/report")
    assert res.status_code == 200
    rep_data = res.json()
    assert "NEVER INTERPRET SHORT-TERM PROFIT" in rep_data["report_markdown"]

    # 3. Strategy mutation endpoint
    res = client.post(
        "/api/v1/live/experiment/strategy-version",
        json={
            "version": "v1.0.2",
            "reason": "Adjusting profit target multiplier from 2.5 to 2.2 for tighter intraday exits",
            "parameters": {"profit_target_multiplier": 2.2},
        },
    )
    assert res.status_code == 200
    assert res.json()["version"] == "v1.0.2"

    # 4. Capital increase rejection endpoint
    res = client.post(
        "/api/v1/live/experiment/capital-request",
        json={
            "requested_capital": 250.0,
            "authorization_token": "UNAUTHORIZED_TOKEN",
        },
    )
    assert res.status_code == 403


def test_live_experiment_halt_guard(clean_experiment_db: str) -> None:
    """Verify live experiment iteration is blocked if system state is HALTED."""
    init_db(clean_experiment_db)
    app.dependency_overrides[get_db_path] = lambda: clean_experiment_db
    client = TestClient(app)
    try:
        # Trigger kill switch to halt system
        ks_res = client.post(
            "/api/v1/system/kill-switch",
            json={"confirm": True, "reason": "Safety Test Halt"},
        )
        assert ks_res.status_code == 200

        # Attempt live experiment run while halted
        res = client.post("/api/v1/live/experiment/run")
        assert res.status_code == 400
        assert "HALTED" in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db_path, None)
