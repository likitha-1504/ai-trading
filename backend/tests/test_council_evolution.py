"""Comprehensive Test Suite for Phase 36 AI Council Evolution & Safety Decoupling.

Tests:
- Measurable Model Justification Scorecards & Hurdle Evaluations
- Rejection of Unjustified & Redundant Candidate Models
- Governed Model Admission with Operator Authorization Tokens
- Tamper-Evident Audit Logging of Council Mutations
- Trade Gate Survival during Complete AI Blackouts
- Position Watcher Sub-50ms SLA and Decoupling from AI Inference
- AI Consensus Override Immunity (AI Cannot Override Deterministic Risk)
- FastAPI REST Endpoints for Council Evolution
- Operational CLI Runner Subprocess Execution
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.council_evolution.admission_gate import ModelAdmissionGate
from app.council_evolution.evolution_orchestrator import CouncilEvolutionOrchestrator
from app.council_evolution.independence_guard import CouncilIndependenceGuard
from app.council_evolution.models import (
    AdmissionStatus,
    CouncilRole,
    MeasurableHurdles,
    UnjustifiedModelError,
)
from app.db.connection import init_db
from app.main import app
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
# 1. Measurable Justification Scorecard Tests
# =========================================================================

def test_candidate_justification_evaluation() -> None:
    gate = ModelAdmissionGate()

    # 1. Test Justified Candidate (FinGPT Sentiment)
    sc_justified = gate.evaluate_candidate("FINGPT-SENTIMENT-V1")
    assert sc_justified.candidate_id == "FINGPT-SENTIMENT-V1"
    assert sc_justified.is_justified is True
    assert sc_justified.status == AdmissionStatus.JUSTIFIED
    assert sc_justified.role == CouncilRole.MACRO_SENTIMENT_SPECIALIST
    assert len(sc_justified.admission_reasons) == 5
    assert len(sc_justified.rejection_reasons) == 0

    # 2. Test Unjustified Candidate (Redundant Echo Bot)
    sc_unjustified = gate.evaluate_candidate("REDUNDANT-ECHO-BOT")
    assert sc_unjustified.candidate_id == "REDUNDANT-ECHO-BOT"
    assert sc_unjustified.is_justified is False
    assert sc_unjustified.status == AdmissionStatus.REJECTED
    assert len(sc_unjustified.rejection_reasons) == 5


def test_candidate_custom_hurdles() -> None:
    # Stricter hurdles demanding 10% accuracy uplift
    strict_hurdles = MeasurableHurdles(min_accuracy_uplift_pct=10.0)
    gate = ModelAdmissionGate(hurdles=strict_hurdles)

    sc = gate.evaluate_candidate("FINGPT-SENTIMENT-V1")
    assert sc.is_justified is False
    assert any("Accuracy uplift" in r for r in sc.rejection_reasons)


# =========================================================================
# 2. Model Admission Gate Tests
# =========================================================================

def test_unjustified_model_admission_blocked() -> None:
    gate = ModelAdmissionGate()
    valid_token = "OPERATOR-COUNCIL-PHASE36-VERIFIED-AUTH-TOKEN-12345"

    with pytest.raises(UnjustifiedModelError) as exc_info:
        gate.admit_model("REDUNDANT-ECHO-BOT", operator_token=valid_token)

    assert "breaches measurable justification hurdles" in str(exc_info.value)


def test_model_admission_token_validation() -> None:
    gate = ModelAdmissionGate()

    # Missing token
    with pytest.raises(PermissionError):
        gate.admit_model("FINGPT-SENTIMENT-V1", operator_token="")

    # Invalid token format
    with pytest.raises(PermissionError):
        gate.admit_model("FINGPT-SENTIMENT-V1", operator_token="INVALID_TOKEN")


def test_justified_model_admission_and_audit_logging(temp_db: str) -> None:
    logger = TamperEvidentAuditLogger(db_path=temp_db)
    gate = ModelAdmissionGate(audit_logger=logger)
    valid_token = "OPERATOR-COUNCIL-PHASE36-VERIFIED-AUTH-TOKEN-99999"

    sc = gate.admit_model("FINGPT-SENTIMENT-V1", operator_token=valid_token)
    assert sc.status == AdmissionStatus.ADMITTED

    # Verify model is now in active council
    active_ids = [m["model_id"] for m in gate.get_active_council()]
    assert "FINGPT-SENTIMENT-V1" in active_ids

    # Verify audit ledger has recorded the admission
    chain_valid, _, count = logger.verify_chain_integrity()
    assert chain_valid is True
    assert count >= 1


# =========================================================================
# 3. Deterministic Safety Decoupling & Independence Tests
# =========================================================================

def test_trade_gate_blackout_resilience() -> None:
    guard = CouncilIndependenceGuard()
    ok, details = guard._verify_trade_gate_outage_resilience()

    assert ok is True
    assert details["prescreen_gate_rejected"] is True
    assert details["zero_llm_calls_made"] is True
    assert details["evaluation_duration_ms"] < 50.0


def test_position_watcher_independence_and_sla() -> None:
    guard = CouncilIndependenceGuard()
    ok, p95_us, details = guard._verify_position_watcher_independence()

    assert ok is True
    assert details["sla_met_sub_50ms"] is True
    assert details["hard_stop_triggered"] is True
    assert details["zero_ai_dependency"] is True
    assert p95_us < 50000.0


def test_ai_unanimous_override_immunity() -> None:
    guard = CouncilIndependenceGuard()
    blocked, details = guard._verify_ai_override_immunity()

    assert blocked is True
    assert details["override_prevented"] is True
    assert details["risk_engine_blocked"] is True
    assert any("Insufficient capital or risk budget" in r for r in details["reasons"])


def test_complete_independence_attestation() -> None:
    guard = CouncilIndependenceGuard()
    att = guard.audit_complete_independence()

    assert att.trade_gate_zero_llm_dependency is True
    assert att.position_watcher_zero_llm_dependency is True
    assert att.models_offline_blackout_tested is True
    assert att.unanimous_ai_buy_override_blocked is True
    assert att.position_watcher_sub_50ms_sla is True
    assert len(att.attestation_hash) == 64


# =========================================================================
# 4. Master Orchestrator Audit Test
# =========================================================================

def test_council_evolution_orchestrator(temp_db: str) -> None:
    logger = TamperEvidentAuditLogger(db_path=temp_db)
    orchestrator = CouncilEvolutionOrchestrator(audit_logger=logger)
    report = orchestrator.run_council_evolution_audit()

    assert report.overall_status == "AUDIT_VERIFIED"
    assert len(report.active_council_models) >= 2
    assert len(report.candidate_scorecards) >= 2
    assert report.independence_attestation.unanimous_ai_buy_override_blocked is True


# =========================================================================
# 5. FastAPI REST Endpoints Tests
# =========================================================================

def test_fastapi_council_evolution_endpoints(client: TestClient) -> None:
    # 1. GET /status
    res_status = client.get("/api/v1/council-evolution/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["active_models_count"] >= 2
    assert data_status["candidates_evaluated_count"] >= 2

    # 2. GET /candidates
    res_cands = client.get("/api/v1/council-evolution/candidates")
    assert res_cands.status_code == 200
    assert len(res_cands.json()) >= 2

    # 3. POST /evaluate-candidate
    res_eval = client.post(
        "/api/v1/council-evolution/evaluate-candidate?candidate_id=FINGPT-SENTIMENT-V1"
    )
    assert res_eval.status_code == 200
    assert res_eval.json()["is_justified"] is True

    # 4. POST /audit-independence
    res_ind = client.post("/api/v1/council-evolution/audit-independence")
    assert res_ind.status_code == 200
    assert res_ind.json()["unanimous_ai_buy_override_blocked"] is True

    # 5. GET /audit
    res_audit = client.get("/api/v1/council-evolution/audit")
    assert res_audit.status_code == 200
    assert res_audit.json()["overall_status"] == "AUDIT_VERIFIED"

    # 6. POST /admit-model (unjustified candidate rejected: 422)
    res_admit_fail = client.post(
        "/api/v1/council-evolution/admit-model?candidate_id=REDUNDANT-ECHO-BOT&operator_token=OPERATOR-COUNCIL-PHASE36-VERIFIED-AUTH-TOKEN-12345"
    )
    assert res_admit_fail.status_code == 422

    # 7. POST /admit-model (invalid token rejected: 403)
    res_admit_unauth = client.post(
        "/api/v1/council-evolution/admit-model?candidate_id=FINGPT-SENTIMENT-V1&operator_token=BAD_TOKEN"
    )
    assert res_admit_unauth.status_code == 403


# =========================================================================
# 6. Operational CLI Runner Subprocess Tests
# =========================================================================

def test_cli_council_evolution_subprocesses() -> None:
    # 1. Status probe
    r_status = subprocess.run(
        [sys.executable, "backend/scripts/council_evolution_runner.py", "--status"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert r_status.returncode == 0
    assert "AI COUNCIL ACTIVE COMPOSITION" in r_status.stdout

    # 2. Candidates list
    r_cands = subprocess.run(
        [sys.executable, "backend/scripts/council_evolution_runner.py", "--candidates"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert r_cands.returncode == 0
    assert "CANDIDATE: FINGPT-SENTIMENT-V1" in r_cands.stdout

    # 3. Independence audit drill
    r_ind = subprocess.run(
        [sys.executable, "backend/scripts/council_evolution_runner.py", "--audit-independence"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert r_ind.returncode == 0
    assert "SAFETY SYSTEMS DECOUPLING & INDEPENDENCE ATTESTATION" in r_ind.stdout
