"""Comprehensive test suite for Phase 29: Controlled Capital Scaling.

Verifies:
1. Configurable discrete capital stages and prerequisite parameters.
2. Absolute anti-auto-scaling enforcement: scaling from performance is strictly prohibited.
3. Pre- and post-scaling accounting reconciliation.
4. Atomic defensive rollback capabilities.
5. FastAPI REST API endpoints (/api/v1/capital-scaling/*).
6. Operational CLI runner execution.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

from app.capital_scaling.models import (
    CapitalScalingSummary,
    CapitalStage,
    ScalingEligibility,
    UnauthorizedCapitalEscalationError,
)
from app.capital_scaling.scaling_manager import (
    ControlledCapitalScalingManager,
)
from app.main import app

# Ensure scripts directory can be imported
_scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from capital_scaling_runner import main as capital_scaling_cli_main


# --- Scaling Manager Core Tests ---

def test_scaling_manager_initialization():
    """Verify scaling manager starts at STAGE_1_MICRO with strict INR 100 ceiling."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)
    assert manager.active_stage == CapitalStage.STAGE_1_MICRO

    stage_def = manager.get_stage_definition(CapitalStage.STAGE_1_MICRO)
    assert stage_def.capital_ceiling_inr == 100.0
    assert stage_def.autonomous_limit_inr == 300.0
    assert stage_def.max_risk_pct == 1.5

    all_stages = manager.list_stage_definitions()
    assert len(all_stages) == 4


def test_anti_auto_scaling_blocks_unauthorized_transition():
    """Inviolable: Any attempt to scale capital without explicit operator token is rejected."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)

    # Missing token
    with pytest.raises(UnauthorizedCapitalEscalationError) as exc_info:
        manager.transition_stage(
            target_stage=CapitalStage.STAGE_2_EXPLORATORY,
            operator_authorization_token="",
            rationale="Automatic performance scaling",
        )
    assert "automatic scaling from recent performance is strictly prohibited" in str(exc_info.value)

    # Invalid token (e.g. attempting to claim recent performance as authorization)
    with pytest.raises(UnauthorizedCapitalEscalationError) as exc_info:
        manager.transition_stage(
            target_stage=CapitalStage.STAGE_2_EXPLORATORY,
            operator_authorization_token="RECENT-WIN-STREAK-TOKEN",
            rationale="Auto-scaling after 5 wins",
        )
    assert "Mandatory operator authorization token" in str(exc_info.value)


def test_authorized_stage_transition_with_reconciliation():
    """Verify stage transition succeeds when authorized with valid operator token."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)

    record = manager.transition_stage(
        target_stage=CapitalStage.STAGE_2_EXPLORATORY,
        operator_authorization_token="OPERATOR-STAGE-TRANSITION-AUTH-2026",
        rationale="Approved by operator after statistical validation.",
    )

    assert manager.active_stage == CapitalStage.STAGE_2_EXPLORATORY
    assert record.from_stage == CapitalStage.STAGE_1_MICRO
    assert record.to_stage == CapitalStage.STAGE_2_EXPLORATORY
    assert record.status == "COMPLETED"
    assert record.pre_reconciliation.is_in_parity is True
    assert record.post_reconciliation.is_in_parity is True
    assert record.pre_reconciliation.discrepancy_inr == 0.0


def test_atomic_rollback_with_reconciliation():
    """Verify atomic rollback restores prior capital stage with full reconciliation."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)

    # First escalate
    manager.transition_stage(
        target_stage=CapitalStage.STAGE_2_EXPLORATORY,
        operator_authorization_token="OPERATOR-STAGE-TRANSITION-VALID-01",
        rationale="Escalation test",
    )
    assert manager.active_stage == CapitalStage.STAGE_2_EXPLORATORY

    # Unauthenticated rollback attempt must fail
    with pytest.raises(UnauthorizedCapitalEscalationError):
        manager.rollback_to_stage(
            target_stage=CapitalStage.STAGE_1_MICRO,
            operator_authorization_token="INVALID-TOKEN",
        )

    # Authorized rollback
    rollback_record = manager.rollback_to_stage(
        target_stage=CapitalStage.STAGE_1_MICRO,
        operator_authorization_token="OPERATOR-STAGE-ROLLBACK-CONFIRM-99",
        reason="Defensive market volatility rollback",
    )

    assert manager.active_stage == CapitalStage.STAGE_1_MICRO
    assert rollback_record.status == "ROLLED_BACK"
    assert rollback_record.to_stage == CapitalStage.STAGE_1_MICRO
    assert rollback_record.post_reconciliation.is_in_parity is True


def test_scaling_eligibility_auditing():
    """Verify eligibility assessment confirms prerequisites while asserting auto_scaling_permitted=False."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)
    elig = manager.evaluate_eligibility()

    assert isinstance(elig, ScalingEligibility)
    assert elig.current_stage == CapitalStage.STAGE_1_MICRO
    assert elig.next_stage == CapitalStage.STAGE_2_EXPLORATORY
    assert elig.auto_scaling_permitted is False
    assert elig.operator_action_required is True


def test_generate_scaling_summary():
    """Verify summary compilation includes all configured stages, ceiling, and reconciliation."""
    manager = ControlledCapitalScalingManager(initial_cash_inr=98.42)
    summary = manager.generate_scaling_summary()

    assert isinstance(summary, CapitalScalingSummary)
    assert summary.phase_id == "PHASE-29-CAPITAL-SCALING"
    assert summary.auto_scaling_blocked is True
    assert summary.rollback_ready is True
    assert summary.current_capital_ceiling_inr == 100.0
    assert len(summary.configured_stages) == 4


# --- REST API Tests ---

def test_api_capital_scaling_summary():
    """Verify GET /api/v1/capital-scaling/summary endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/capital-scaling/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["phase_id"] == "PHASE-29-CAPITAL-SCALING"
    assert data["auto_scaling_blocked"] is True
    assert data["rollback_ready"] is True


def test_api_capital_scaling_stages():
    """Verify GET /api/v1/capital-scaling/stages endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/capital-scaling/stages")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4


def test_api_capital_scaling_eligibility():
    """Verify GET /api/v1/capital-scaling/eligibility endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/capital-scaling/eligibility")
    assert response.status_code == 200
    data = response.json()
    assert data["auto_scaling_permitted"] is False
    assert data["operator_action_required"] is True


def test_api_capital_scaling_history():
    """Verify GET /api/v1/capital-scaling/history endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/capital-scaling/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_capital_scaling_transition_and_rollback():
    """Verify transition and rollback endpoints enforce authorization tokens."""
    client = TestClient(app)

    # 1. Unauthorized transition attempt (403 Forbidden)
    bad_payload = {
        "target_stage": "STAGE_2_EXPLORATORY",
        "operator_authorization_token": "UNAUTHORIZED-AUTO-SCALE",
        "rationale": "Auto scaling attempt",
    }
    res_bad = client.post("/api/v1/capital-scaling/transition", json=bad_payload)
    assert res_bad.status_code == 403
    assert "automatic scaling from recent performance is strictly prohibited" in res_bad.json()["detail"]

    # 2. Authorized transition (200 OK)
    auth_payload = {
        "target_stage": "STAGE_2_EXPLORATORY",
        "operator_authorization_token": "OPERATOR-STAGE-TRANSITION-TOKEN-88",
        "rationale": "Operator approved scaling to INR 300 exploratory stage.",
    }
    res_ok = client.post("/api/v1/capital-scaling/transition", json=auth_payload)
    assert res_ok.status_code == 200
    assert res_ok.json()["to_stage"] == "STAGE_2_EXPLORATORY"

    # 3. Authorized rollback (200 OK)
    rollback_payload = {
        "target_stage": "STAGE_1_MICRO",
        "operator_authorization_token": "OPERATOR-STAGE-ROLLBACK-TOKEN-44",
        "reason": "Defensive capital retreat to micro baseline.",
    }
    res_rbk = client.post("/api/v1/capital-scaling/rollback", json=rollback_payload)
    assert res_rbk.status_code == 200
    assert res_rbk.json()["to_stage"] == "STAGE_1_MICRO"


# --- CLI Runner Tests ---

def test_capital_scaling_cli_runner(monkeypatch, capsys):
    """Verify CLI capital scaling runner execution in ASCII, JSON, and eligibility modes."""
    # Test ASCII format
    monkeypatch.setattr(sys, "argv", ["capital_scaling_runner.py"])
    exit_code = capital_scaling_cli_main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "PHASE 29 CONTROLLED CAPITAL SCALING AUDIT REPORT" in captured.out
    assert "Auto-Scaling Status:  Blocked=True" in captured.out

    # Test JSON format
    monkeypatch.setattr(sys, "argv", ["capital_scaling_runner.py", "--json"])
    exit_code = capital_scaling_cli_main()
    assert exit_code == 0
    captured_json = capsys.readouterr()
    assert '"phase_id": "PHASE-29-CAPITAL-SCALING"' in captured_json.out

    # Test eligibility format
    monkeypatch.setattr(sys, "argv", ["capital_scaling_runner.py", "--eligibility"])
    exit_code = capital_scaling_cli_main()
    assert exit_code == 0
    captured_elig = capsys.readouterr()
    assert "CAPITAL SCALING ELIGIBILITY AUDIT" in captured_elig.out
    assert "Auto-Scaling:      Permitted=False" in captured_elig.out
