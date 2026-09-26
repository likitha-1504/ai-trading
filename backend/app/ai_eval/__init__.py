"""Phase 28: AI Learning & Evaluation package."""

from app.ai_eval.evaluator import (
    AILearningEvaluator,
    DeterministicSafetyViolationError,
)
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

__all__ = [
    "AILatencyTimeoutMetrics",
    "AILearningEvaluationSummary",
    "AILearningEvaluator",
    "CouncilDisagreementMetrics",
    "DeepSeekR1ChallengeEvaluation",
    "DeterministicSafetyViolationError",
    "GateRejectionMetrics",
    "PromptConfigRegistry",
    "PromptVersionRecord",
    "Qwen3ThesisEvaluation",
    "get_prompt_registry",
]
