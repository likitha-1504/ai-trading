"""Comprehensive test suite for Phase 28: AI Learning & Evaluation.

Verifies:
1. Qwen3 thesis quality: accuracy, confidence calibration, win rate separation.
2. DeepSeek-R1 adversarial challenge: veto precision (78.6%) and downside capital saved.
3. Council disagreement rate and quantitative deterministic arbitration.
4. Absolute safety gate inviolability: AI CANNOT override deterministic safety controls.
5. Model latency, timeouts, and graceful deterministic fallback routing.
6. Prompt configuration versioning and SHA-256 fingerprinting.
7. FastAPI REST API endpoints (/api/v1/ai-learning/*).
8. Operational CLI runner execution.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

from app.ai_eval.evaluator import AILearningEvaluator
from app.ai_eval.models import (
    AILatencyTimeoutMetrics,
    AILearningEvaluationSummary,
    CouncilDisagreementMetrics,
    DeepSeekR1ChallengeEvaluation,
    GateRejectionMetrics,
    PromptVersionRecord,
    Qwen3ThesisEvaluation,
)
from app.ai_eval.prompt_registry import (
    PromptConfigRegistry,
)
from app.main import app

# Ensure scripts directory can be imported
_scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from ai_eval_runner import main as ai_eval_cli_main


# --- Evaluator Core Tests ---

def test_qwen3_thesis_quality_metrics():
    """Verify Qwen3 thesis directional accuracy and confidence win rate calibration."""
    evaluator = AILearningEvaluator()
    qwen = evaluator.evaluate_qwen3_quality()

    assert isinstance(qwen, Qwen3ThesisEvaluation)
    assert qwen.total_theses == 150
    assert qwen.thesis_direction_accuracy_pct > 65.0
    assert qwen.high_confidence_win_rate_pct > qwen.low_confidence_win_rate_pct
    assert qwen.average_confidence >= 0.70


def test_deepseek_challenge_metrics():
    """Verify DeepSeek-R1 critique frequency, veto precision, and capital saved."""
    evaluator = AILearningEvaluator()
    ds = evaluator.evaluate_deepseek_challenge()

    assert isinstance(ds, DeepSeekR1ChallengeEvaluation)
    assert ds.total_critiques == 150
    assert ds.challenges_raised == 42
    assert ds.vetoes_enforced == 14
    assert ds.precision_pct >= 75.0
    assert ds.capital_saved_inr > 30.0


def test_council_disagreement_metrics():
    """Verify council consensus vs disagreement tracking and quantitative arbitration."""
    evaluator = AILearningEvaluator()
    dis = evaluator.evaluate_council_disagreement()

    assert isinstance(dis, CouncilDisagreementMetrics)
    assert dis.total_evaluations == 150
    assert dis.full_consensus_count + dis.disagreement_count == dis.total_evaluations
    assert dis.disagreement_rate_pct == 28.0
    assert dis.deterministic_arbitration_count == 42


def test_deterministic_safety_gate_rejections():
    """Verify deterministic safety gate rejects AI-approved trades violating hard bounds."""
    evaluator = AILearningEvaluator()
    gate = evaluator.evaluate_gate_rejections()

    assert isinstance(gate, GateRejectionMetrics)
    assert gate.deterministic_gate_rejected > 0
    assert gate.ai_override_attempts_prevented == gate.deterministic_gate_rejected
    assert gate.safety_inviolability_verified is True
    assert "SPREAD_EXCEEDS_15_BPS" in gate.rejections_by_rule
    assert "CAPITAL_EXCEEDS_100_CAP" in gate.rejections_by_rule


def test_ai_cannot_override_deterministic_safety():
    """Explicit invariant test: AI unanimity (100% confidence) CANNOT override safety limits."""
    evaluator = AILearningEvaluator()

    # Case 1: Excessive Risk (2.5% > 1.5% max)
    assert evaluator.verify_safety_override_immunity(
        simulated_ai_confidence=1.0, simulated_risk_pct=2.5, simulated_spread_bps=10.0, simulated_capital_inr=90.0
    ) is True

    # Case 2: Excessive Spread (25 bps > 15 bps max)
    assert evaluator.verify_safety_override_immunity(
        simulated_ai_confidence=1.0, simulated_risk_pct=1.0, simulated_spread_bps=25.0, simulated_capital_inr=90.0
    ) is True

    # Case 3: Excessive Capital (INR 150 > INR 100 max)
    assert evaluator.verify_safety_override_immunity(
        simulated_ai_confidence=1.0, simulated_risk_pct=1.0, simulated_spread_bps=10.0, simulated_capital_inr=150.0
    ) is True


def test_latencies_and_timeout_metrics():
    """Verify latency distributions and fallback routing telemetry."""
    evaluator = AILearningEvaluator()
    lat = evaluator.evaluate_latencies_and_timeouts()

    assert isinstance(lat, AILatencyTimeoutMetrics)
    assert lat.qwen3_avg_latency_ms < 5000.0
    assert lat.deepseek_r1_avg_latency_ms < 5000.0
    assert lat.fallback_rate_pct < 10.0
    assert lat.circuit_breaker_triggered is False


# --- Prompt Registry Tests ---

def test_prompt_registry_seeding_and_immutability():
    """Verify prompt registry seeds baseline and active prompt versions."""
    registry = PromptConfigRegistry()
    prompts = registry.list_prompts()

    assert len(prompts) >= 4
    active = registry.get_active_prompts()
    assert len(active) >= 2

    # Prevent duplicate prompt ID
    p_dup = PromptVersionRecord(
        prompt_id="PRM-QWEN3-V1",
        model_name="qwen2.5:3b",
        version_tag="v1.0.0-duplicate",
        system_prompt_hash="12345678abcdef01",
    )
    with pytest.raises(ValueError) as exc_info:
        registry.register_prompt_version(p_dup)
    assert "already exists" in str(exc_info.value)


# --- Consolidated Summary Test ---

def test_generate_evaluation_summary():
    """Verify comprehensive summary generation."""
    evaluator = AILearningEvaluator()
    summary = evaluator.generate_evaluation_summary()

    assert isinstance(summary, AILearningEvaluationSummary)
    assert summary.phase_id == "PHASE-28-AI-LEARNING"
    assert summary.safety_controls_uncompromised is True
    assert len(summary.active_prompts) >= 2
    assert "MAINTAIN_COUNCIL_CONFIG" in summary.recommendation


# --- REST API Tests ---

def test_api_ai_learning_summary():
    """Verify GET /api/v1/ai-learning/summary endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["phase_id"] == "PHASE-28-AI-LEARNING"
    assert data["safety_controls_uncompromised"] is True


def test_api_ai_learning_qwen_quality():
    """Verify GET /api/v1/ai-learning/qwen-quality endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/qwen-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["total_theses"] == 150
    assert data["thesis_direction_accuracy_pct"] == 71.0


def test_api_ai_learning_deepseek_challenge():
    """Verify GET /api/v1/ai-learning/deepseek-challenge endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/deepseek-challenge")
    assert response.status_code == 200
    data = response.json()
    assert data["precision_pct"] == 78.6
    assert data["capital_saved_inr"] == 38.50


def test_api_ai_learning_disagreement():
    """Verify GET /api/v1/ai-learning/disagreement endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/disagreement")
    assert response.status_code == 200
    data = response.json()
    assert data["disagreement_rate_pct"] == 28.0


def test_api_ai_learning_gate_rejections():
    """Verify GET /api/v1/ai-learning/gate-rejections endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/gate-rejections")
    assert response.status_code == 200
    data = response.json()
    assert data["safety_inviolability_verified"] is True
    assert data["ai_override_attempts_prevented"] == 38


def test_api_ai_learning_latencies():
    """Verify GET /api/v1/ai-learning/latencies endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/latencies")
    assert response.status_code == 200
    data = response.json()
    assert data["circuit_breaker_triggered"] is False


def test_api_ai_learning_prompts():
    """Verify GET /api/v1/ai-learning/prompts endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai-learning/prompts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4


def test_api_ai_learning_verify_safety_override():
    """Verify POST /api/v1/ai-learning/verify-safety-override endpoint."""
    client = TestClient(app)
    response = client.post("/api/v1/ai-learning/verify-safety-override")
    assert response.status_code == 200
    data = response.json()
    assert data["safety_inviolability_verified"] is True


# --- CLI Runner Tests ---

def test_ai_eval_cli_runner(monkeypatch, capsys):
    """Verify CLI ai_eval runner execution in ASCII, JSON, and safety verify modes."""
    # Test ASCII format
    monkeypatch.setattr(sys, "argv", ["ai_eval_runner.py"])
    exit_code = ai_eval_cli_main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "PHASE 28 AI LEARNING & EVALUATION AUDIT REPORT" in captured.out
    assert "Safety Inviolability: True" in captured.out

    # Test JSON format
    monkeypatch.setattr(sys, "argv", ["ai_eval_runner.py", "--json"])
    exit_code = ai_eval_cli_main()
    assert exit_code == 0
    captured_json = capsys.readouterr()
    assert '"phase_id": "PHASE-28-AI-LEARNING"' in captured_json.out

    # Test safety verify mode
    monkeypatch.setattr(sys, "argv", ["ai_eval_runner.py", "--verify-safety"])
    exit_code = ai_eval_cli_main()
    assert exit_code == 0
    captured_safety = capsys.readouterr()
    assert "Safety Override Verification: PASS" in captured_safety.out
