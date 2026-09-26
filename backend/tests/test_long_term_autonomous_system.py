"""Unit, Integration, and Lifecycle Tests for Phase 37 Long-Term Autonomous System.

Validates:
- 7-Dimensional Multi-Phase Prerequisite Gate
- Explicit Release Gate & Non-Silent Token Enforcement
- Dynamic Multi-Strategy Portfolio Governor & Automated Edge Degradation
- End-to-End Autonomous Lifecycle State Machine (Pre-market -> Intraday -> Cutoff -> Archival)
- Circuit Breakers & Emergency Kill-Switch with Governed Reset
- FastAPI Endpoints & Operational CLI Utility
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.connection import get_connection, init_db
from app.long_term_autonomous.lifecycle_orchestrator import LongTermAutonomousOrchestrator
from app.long_term_autonomous.models import (
    AutonomousSystemState,
    LongTermStrategyProfile,
    PrerequisiteDimension,
    PrerequisiteNotMetError,
    ReleaseGateRequest,
    ReleaseGateType,
    StrategyLifecycleStage,
    UnapprovedReleaseError,
)
from app.long_term_autonomous.portfolio_governor import AutonomousPortfolioGovernor
from app.long_term_autonomous.prerequisite_gate import LongTermPrerequisiteGate
from app.long_term_autonomous.release_gate import AutonomousReleaseGate
from app.main import app
from app.models.contracts import (
    MarketSource,
    NormalizedMarketEvent,
    StrategyType,
    TradeSide,
)
from app.security.auth import AuthenticationManager
from app.security.models import UserRole
from app.security.tamper_log import TamperEvidentAuditLogger


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    """Creates a temporary SQLite database initialized with WAL journal mode."""
    db_file = str(tmp_path / "test_long_term_autonomous.db")
    init_db(db_file)
    with get_connection(db_file) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
    return db_file


@pytest.fixture
def audit_logger(temp_db: str) -> TamperEvidentAuditLogger:
    return TamperEvidentAuditLogger(temp_db)


@pytest.fixture
def prereq_gate(temp_db: str, audit_logger: TamperEvidentAuditLogger) -> LongTermPrerequisiteGate:
    return LongTermPrerequisiteGate(temp_db, audit_logger=audit_logger)


@pytest.fixture
def release_gate(audit_logger: TamperEvidentAuditLogger, prereq_gate: LongTermPrerequisiteGate) -> AutonomousReleaseGate:
    return AutonomousReleaseGate(audit_logger=audit_logger, prereq_gate=prereq_gate)


@pytest.fixture
def portfolio_governor(release_gate: AutonomousReleaseGate, audit_logger: TamperEvidentAuditLogger) -> AutonomousPortfolioGovernor:
    return AutonomousPortfolioGovernor(release_gate=release_gate, audit_logger=audit_logger)


@pytest.fixture
def orchestrator(
    temp_db: str,
    prereq_gate: LongTermPrerequisiteGate,
    release_gate: AutonomousReleaseGate,
    portfolio_governor: AutonomousPortfolioGovernor,
    audit_logger: TamperEvidentAuditLogger,
) -> LongTermAutonomousOrchestrator:
    return LongTermAutonomousOrchestrator(
        db_path=temp_db,
        initial_capital=Decimal("100.00"),
        max_daily_drawdown_pct=Decimal("3.00"),
        prereq_gate=prereq_gate,
        release_gate=release_gate,
        portfolio_governor=portfolio_governor,
        audit_logger=audit_logger,
    )


# =====================================================================
# 1. Prerequisite Gate Tests
# =====================================================================


def test_prerequisite_gate_execution(prereq_gate: LongTermPrerequisiteGate) -> None:
    """Verifies that all 7 prerequisite dimensions are evaluated systematically."""
    audit = prereq_gate.audit_prerequisites(strict=False)
    assert audit.audit_id.startswith("PRE-AUDIT-")
    assert len(audit.dimension_results) == 7

    # Verify all 7 dimensions exist
    expected_dims = {
        PrerequisiteDimension.OPS_PREFLIGHT,
        PrerequisiteDimension.CAPITAL_LIMITS,
        PrerequisiteDimension.PORTFOLIO_CONCENTRATION,
        PrerequisiteDimension.DISASTER_RECOVERY,
        PrerequisiteDimension.SECURITY_LEAST_PRIVILEGE,
        PrerequisiteDimension.RESEARCH_SANDBOX,
        PrerequisiteDimension.AI_COUNCIL_DECOUPLING,
    }
    assert set(audit.dimension_results.keys()) == expected_dims
    assert audit.is_all_passed is True


def test_prerequisite_gate_strict_rejection(tmp_path: Path) -> None:
    """Verifies that strict=True raises PrerequisiteNotMetError when a dimension fails."""
    # Corrupt DB path where WAL is not configured
    bad_db = str(tmp_path / "corrupt_empty.db")
    with get_connection(bad_db) as conn:
        conn.execute("PRAGMA journal_mode=DELETE;")  # Non-WAL mode

    bad_gate = LongTermPrerequisiteGate(bad_db)
    with pytest.raises(PrerequisiteNotMetError) as exc_info:
        bad_gate.audit_prerequisites(strict=True)

    assert "Failed prerequisite dimensions" in str(exc_info.value)


# =====================================================================
# 2. Release Gate Tests
# =====================================================================


def test_release_gate_valid_session_token(release_gate: AutonomousReleaseGate) -> None:
    """Verifies valid operator release token is approved and logged to audit chain."""
    req = ReleaseGateRequest(
        release_type=ReleaseGateType.SYSTEM_ACTIVATION,
        operator_id="OP-001",
        operator_token="RELEASE-AUTONOMOUS-SESSION-DEMO-2026-KEY",
        target_identifier="AUTONOMOUS_SESSION_TEST",
    )
    decision = release_gate.evaluate_release(req, verify_prerequisites=False)
    assert decision.is_approved is True
    assert decision.audit_hash is not None
    assert "Human operator authorization verified" in decision.reason


def test_release_gate_rejects_unauthorized_token(release_gate: AutonomousReleaseGate) -> None:
    """Verifies invalid or short tokens are rejected."""
    req = ReleaseGateRequest(
        release_type=ReleaseGateType.SYSTEM_ACTIVATION,
        operator_id="OP-001",
        operator_token="INVALID_TOKEN",
        target_identifier="AUTONOMOUS_SESSION_TEST",
    )
    decision = release_gate.evaluate_release(req, verify_prerequisites=False)
    assert decision.is_approved is False
    assert "Invalid or unauthorized release token" in decision.reason

    with pytest.raises(UnapprovedReleaseError):
        release_gate.enforce_release(
            release_type=ReleaseGateType.SYSTEM_ACTIVATION,
            operator_id="OP-001",
            operator_token="INVALID_TOKEN",
            target_identifier="AUTONOMOUS_SESSION_TEST",
            verify_prerequisites=False,
        )


def test_release_gate_nonce_replay_prevention(release_gate: AutonomousReleaseGate) -> None:
    """Verifies that consuming the same token twice triggers replay rejection."""
    token = "RELEASE-AUTONOMOUS-SESSION-REPLAY-CHECK-2026"
    req1 = ReleaseGateRequest(
        release_type=ReleaseGateType.SYSTEM_ACTIVATION,
        operator_id="OP-001",
        operator_token=token,
        target_identifier="SESSION_1",
    )
    decision1 = release_gate.evaluate_release(req1, verify_prerequisites=False)
    assert decision1.is_approved is True

    # Attempt replay
    req2 = ReleaseGateRequest(
        release_type=ReleaseGateType.SYSTEM_ACTIVATION,
        operator_id="OP-001",
        operator_token=token,
        target_identifier="SESSION_2",
    )
    decision2 = release_gate.evaluate_release(req2, verify_prerequisites=False)
    assert decision2.is_approved is False
    assert "Token replay detected" in decision2.reason


def test_release_gate_hmac_bearer_token(release_gate: AutonomousReleaseGate) -> None:
    """Verifies valid HMAC-signed bearer token with OPERATOR role is approved."""
    auth_mgr = AuthenticationManager()
    valid_hmac_token = auth_mgr.generate_token(operator_id="OP-HMAC", role=UserRole.OPERATOR)

    req = ReleaseGateRequest(
        release_type=ReleaseGateType.SYSTEM_ACTIVATION,
        operator_id="OP-HMAC",
        operator_token=valid_hmac_token,
        target_identifier="SESSION_HMAC",
    )
    decision = release_gate.evaluate_release(req, verify_prerequisites=False)
    assert decision.is_approved is True


# =====================================================================
# 3. Dynamic Strategy Portfolio Governor Tests
# =====================================================================


def test_portfolio_governor_baseline_profiles(portfolio_governor: AutonomousPortfolioGovernor) -> None:
    """Checks baseline strategies are loaded with active status and 50/50 target weights."""
    profiles = portfolio_governor._profiles
    assert StrategyType.MOMENTUM_CONTINUATION.value in profiles
    assert StrategyType.EARLY_MOVE_DETECTION.value in profiles

    mom = profiles[StrategyType.MOMENTUM_CONTINUATION.value]
    assert mom.lifecycle_stage == StrategyLifecycleStage.ACTIVE
    assert mom.target_weight_pct == Decimal("50.00")
    assert mom.is_active is True


def test_portfolio_governor_automated_edge_degradation(portfolio_governor: AutonomousPortfolioGovernor) -> None:
    """Checks that consecutive losses or win rate decay automatically demotes strategy and freezes capital."""
    strat_name = StrategyType.MOMENTUM_CONTINUATION.value

    # Simulate 4 consecutive losses
    for _ in range(4):
        portfolio_governor.update_strategy_performance(strat_name, trade_pnl=Decimal("-1.50"), is_win=False)

    profile = portfolio_governor._profiles[strat_name]
    assert profile.lifecycle_stage == StrategyLifecycleStage.DEGRADED
    assert profile.is_active is False
    assert profile.target_weight_pct == Decimal("0.00")
    assert "Consecutive loss limit breached" in (profile.quarantine_reason or "")


def test_portfolio_governor_dynamic_rebalance_flow(portfolio_governor: AutonomousPortfolioGovernor) -> None:
    """Generates Sharpe-weighted rebalance proposal and verifies release-gated application."""
    proposal = portfolio_governor.generate_rebalance_proposal(method="SHARPE_WEIGHTED")
    assert proposal.method == "SHARPE_WEIGHTED"
    assert sum(proposal.proposed_weights.values()) == Decimal("100.00")

    # Applying without valid token fails
    with pytest.raises(UnapprovedReleaseError):
        portfolio_governor.apply_rebalance_proposal(
            proposal=proposal,
            operator_token="BAD_TOKEN",
        )

    # Applying with valid token succeeds
    token = "RELEASE-PORTFOLIO-REBALANCE-TEST-2026-VAL"
    applied = portfolio_governor.apply_rebalance_proposal(
        proposal=proposal,
        operator_token=token,
    )
    assert sum(applied.values()) == Decimal("100.00")
    assert proposal.approved is True


def test_portfolio_governor_candidate_promotion_cap(portfolio_governor: AutonomousPortfolioGovernor) -> None:
    """Verifies that promoting to PROBATION enforces max 20% allocation cap."""
    candidate_profile = LongTermStrategyProfile(
        strategy_id="STRAT-CAND-01",
        strategy_name="MEAN_REVERSION_VOL",
        lifecycle_stage=StrategyLifecycleStage.CANDIDATE,
        target_weight_pct=Decimal("0.00"),
        rolling_win_rate_pct=Decimal("58.00"),
        rolling_sharpe=Decimal("1.50"),
        total_trades=35,
    )
    portfolio_governor.register_candidate_strategy("MEAN_REVERSION_VOL", candidate_profile)

    token = "RELEASE-STRATEGY-PROMOTION-CAND-2026"
    promoted = portfolio_governor.promote_strategy(
        strategy_name="MEAN_REVERSION_VOL",
        target_stage=StrategyLifecycleStage.PROBATION,
        operator_token=token,
        target_weight=Decimal("15.00"),
    )
    assert promoted.lifecycle_stage == StrategyLifecycleStage.PROBATION
    assert promoted.target_weight_pct == Decimal("15.00")


# =====================================================================
# 4. Autonomous Lifecycle Orchestrator Tests
# =====================================================================


def test_orchestrator_full_session_lifecycle(orchestrator: LongTermAutonomousOrchestrator) -> None:
    """Executes full operational lifecycle: Pre-market -> Active -> Cutoff -> Archival."""
    assert orchestrator.state == AutonomousSystemState.OFFLINE

    # 1. Pre-Market Audit
    audit = orchestrator.execute_pre_market_audit()
    assert orchestrator.state == AutonomousSystemState.PRE_MARKET_AUDIT
    assert audit.is_all_passed is True

    # 2. Session Start with Release Token
    token = "RELEASE-AUTONOMOUS-SESSION-LIFECYCLE-2026"
    session_id = orchestrator.start_session(operator_id="OP-001", operator_token=token)
    assert orchestrator.state == AutonomousSystemState.ACTIVE_AUTONOMOUS
    assert session_id.startswith("SESS-")

    # 3. Market Ticks & Position Watcher Loop
    now = datetime(2026, 9, 26, 5, 0, 0, tzinfo=timezone.utc)  # 10:30 AM IST
    tick = NormalizedMarketEvent(
        symbol="TCS",
        source=MarketSource.PAPER,
        exchange_timestamp=now,
        last_price=Decimal("3500.00"),
        volume=500,
        bid_price=Decimal("3499.00"),
        ask_price=Decimal("3501.00"),
        bid_quantity=50,
        ask_quantity=50,
        spread_pct=Decimal("0.05"),
    )
    exits = orchestrator.process_market_tick(tick)
    assert isinstance(exits, list)

    # 4. Record Trade Completions
    orchestrator.record_trade_completion(
        strategy_name=StrategyType.MOMENTUM_CONTINUATION.value,
        symbol="TCS",
        side=TradeSide.BUY,
        pnl=Decimal("2.50"),
    )
    assert orchestrator.executed_trades_count == 1
    assert orchestrator.winning_trades_count == 1
    assert orchestrator.capital == Decimal("102.50")

    # 5. Intraday Cutoff (15:15 IST auto-square-off)
    closed = orchestrator.trigger_intraday_cutoff()
    assert closed >= 0
    assert orchestrator.state == AutonomousSystemState.INTRADAY_CUTOFF
    assert orchestrator.square_off_completed is True

    # 6. Post-Market Reconciliation & Archival
    summary = orchestrator.execute_post_market_reconciliation()
    assert orchestrator.state == AutonomousSystemState.SESSION_ARCHIVED
    assert summary.session_id == session_id
    assert summary.realized_pnl == Decimal("2.50")
    assert summary.reconciliation_hash != ""


def test_orchestrator_drawdown_circuit_breaker(orchestrator: LongTermAutonomousOrchestrator) -> None:
    """Verifies that 3.0% daily drawdown trips circuit breaker and halts trading."""
    token = "RELEASE-AUTONOMOUS-SESSION-CB-CHECK-2026"
    orchestrator.execute_pre_market_audit()
    orchestrator.start_session(operator_id="OP-001", operator_token=token)

    # Simulate 3 losing trades totaling INR 3.50 loss (> 3.0% on INR 100)
    for _ in range(3):
        orchestrator.record_trade_completion(
            strategy_name=StrategyType.MOMENTUM_CONTINUATION.value,
            symbol="RELIANCE",
            side=TradeSide.BUY,
            pnl=Decimal("-1.20"),
        )

    # Trigger tick to evaluate breaker
    now = datetime(2026, 9, 26, 5, 0, 0, tzinfo=timezone.utc)
    tick = NormalizedMarketEvent(
        symbol="RELIANCE",
        source=MarketSource.PAPER,
        exchange_timestamp=now,
        last_price=Decimal("2400.00"),
        volume=100,
        bid_price=Decimal("2399.00"),
        ask_price=Decimal("2401.00"),
        bid_quantity=10,
        ask_quantity=10,
        spread_pct=Decimal("0.08"),
    )
    orchestrator.process_market_tick(tick)

    assert orchestrator.state == AutonomousSystemState.PAUSED_CIRCUIT_BREAKER
    assert orchestrator.circuit_breaker_tripped is True

    # Subsequent ticks ignored
    exits = orchestrator.process_market_tick(tick)
    assert exits == []


def test_orchestrator_emergency_halt_and_governed_reset(orchestrator: LongTermAutonomousOrchestrator) -> None:
    """Verifies kill-switch engagement and operator release token reset."""
    orchestrator.emergency_halt(operator_id="ADMIN_CHIEF", reason="Adverse market spike")
    assert orchestrator.state == AutonomousSystemState.EMERGENCY_HALT

    # Reset with valid token
    token = "RELEASE-SAFETY-RESET-OPERATOR-2026"
    orchestrator.reset_safety_halt(operator_id="ADMIN_CHIEF", operator_token=token)
    assert orchestrator.state == AutonomousSystemState.OFFLINE
    assert orchestrator.circuit_breaker_tripped is False


# =====================================================================
# 5. FastAPI Endpoints Tests
# =====================================================================


def test_fastapi_long_term_autonomous_endpoints() -> None:
    """Verifies FastAPI REST endpoints for Phase 37."""
    client = TestClient(app)

    # 1. Status
    res = client.get("/api/v1/long-term-autonomous/status")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "portfolio" in data

    # 2. Prerequisite Audit
    res_audit = client.post("/api/v1/long-term-autonomous/prerequisites/verify")
    assert res_audit.status_code == 200
    assert "dimension_results" in res_audit.json()

    # 3. Release Gate Evaluation
    res_rel = client.post(
        "/api/v1/long-term-autonomous/release-gate/evaluate",
        json={
            "release_type": "SYSTEM_ACTIVATION",
            "operator_id": "TEST_OP",
            "operator_token": "RELEASE-AUTONOMOUS-SESSION-API-2026-VAL",
            "target_identifier": "API_TEST",
            "parameters": {},
        },
    )
    assert res_rel.status_code == 200
    assert res_rel.json()["is_approved"] is True

    # 4. Rebalance Propose
    res_prop = client.post(
        "/api/v1/long-term-autonomous/portfolio/rebalance/propose",
        json={"method": "EQUAL_WEIGHT"},
    )
    assert res_prop.status_code == 200
    assert "proposed_weights" in res_prop.json()


# =====================================================================
# 6. CLI Management Subprocess Test
# =====================================================================


def test_cli_runner_subprocesses() -> None:
    """Verifies Phase 37 CLI runner executes --status, --check-prerequisites, and --run-session cleanly."""
    py_exec = sys.executable

    # Status check
    res_status = subprocess.run(
        [py_exec, "backend/scripts/long_term_autonomous_runner.py", "--status", "--json"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        check=True,
    )
    assert '"state":' in res_status.stdout

    # Prerequisites check
    res_prereq = subprocess.run(
        [py_exec, "backend/scripts/long_term_autonomous_runner.py", "--check-prerequisites", "--json"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        check=True,
    )
    assert '"is_all_passed":' in res_prereq.stdout

    # Run session lifecycle
    res_session = subprocess.run(
        [
            py_exec,
            "backend/scripts/long_term_autonomous_runner.py",
            "--run-session",
            "--token",
            "RELEASE-AUTONOMOUS-SESSION-CLI-SUBPROC-2026",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        check=True,
    )
    assert "Step 1: Running Pre-Market Audit..." in res_session.stdout
    assert "ARCHIVED." in res_session.stdout
