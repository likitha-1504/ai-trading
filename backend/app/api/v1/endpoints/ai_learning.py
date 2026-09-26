"""FastAPI REST API endpoints for Phase 28: AI Learning & Evaluation.

Provides routes for:
1. Consolidated AI learning and evaluation telemetry report.
2. Qwen3 thesis quality calibration.
3. DeepSeek-R1 adversarial critique and veto precision telemetry.
4. Council disagreement and arbitration analysis.
5. Deterministic Trade Gate rejection metrics and safety override verification.
6. Latency, timeout, and fallback tracking.
7. Prompt and model configuration registry.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

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
    get_prompt_registry,
)

router = APIRouter()


def get_ai_evaluator(
    prompt_registry: PromptConfigRegistry = Depends(get_prompt_registry),
) -> AILearningEvaluator:
    """Dependency provider for AI learning evaluator."""
    return AILearningEvaluator(prompt_registry=prompt_registry)


@router.get(
    "/summary",
    response_model=AILearningEvaluationSummary,
    summary="Phase 28 Consolidated AI Learning Evaluation Summary",
    description="Returns multi-dimensional evaluation across Qwen3, DeepSeek-R1, disagreement rates, and safety inviolability.",
)
def get_evaluation_summary(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> AILearningEvaluationSummary:
    return evaluator.generate_evaluation_summary()


@router.get(
    "/qwen-quality",
    response_model=Qwen3ThesisEvaluation,
    summary="Qwen3 Thesis Quality & Accuracy",
    description="Returns directional thesis accuracy, confidence calibration, and win rates.",
)
def get_qwen_quality(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> Qwen3ThesisEvaluation:
    return evaluator.evaluate_qwen3_quality()


@router.get(
    "/deepseek-challenge",
    response_model=DeepSeekR1ChallengeEvaluation,
    summary="DeepSeek-R1 Challenge & Veto Telemetry",
    description="Returns adversarial challenge frequency, severity distribution, veto precision, and capital saved.",
)
def get_deepseek_challenge(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> DeepSeekR1ChallengeEvaluation:
    return evaluator.evaluate_deepseek_challenge()


@router.get(
    "/disagreement",
    response_model=CouncilDisagreementMetrics,
    summary="Council Disagreement & Arbitration Telemetry",
    description="Returns consensus vs disagreement rates and quantitative arbitration breakdown.",
)
def get_council_disagreement(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> CouncilDisagreementMetrics:
    return evaluator.evaluate_council_disagreement()


@router.get(
    "/gate-rejections",
    response_model=GateRejectionMetrics,
    summary="Deterministic Safety Gate Rejections",
    description="Verifies deterministic safety gate overrides AI consensus when risk/spread/capital limits are breached.",
)
def get_gate_rejections(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> GateRejectionMetrics:
    return evaluator.evaluate_gate_rejections()


@router.get(
    "/latencies",
    response_model=AILatencyTimeoutMetrics,
    summary="AI Latencies, Timeouts & Fallback Routes",
    description="Returns P95 latency distributions, timeout counts, and fallback trigger frequencies.",
)
def get_latency_metrics(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> AILatencyTimeoutMetrics:
    return evaluator.evaluate_latencies_and_timeouts()


@router.get(
    "/prompts",
    response_model=List[PromptVersionRecord],
    summary="List Versioned Prompts and Configurations",
    description="Returns immutable prompt lineage, system prompt hashes, and active configurations.",
)
def list_prompts(
    registry: PromptConfigRegistry = Depends(get_prompt_registry),
) -> List[PromptVersionRecord]:
    return registry.list_prompts()


@router.post(
    "/verify-safety-override",
    summary="Verify Safety Gate Overrides AI Signals",
    description="Asserts that 100% confidence AI signals are blocked when hard boundaries are violated.",
)
def verify_safety_override(
    evaluator: AILearningEvaluator = Depends(get_ai_evaluator),
) -> dict:
    is_safe = evaluator.verify_safety_override_immunity()
    return {
        "safety_inviolability_verified": is_safe,
        "details": "Deterministic trade gate maintains absolute decision authority over AI opinions.",
    }
