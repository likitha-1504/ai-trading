"""AI module for qualitative reasoning, candidate analysis, and challenger layers."""

from app.ai.challenger_client import DeepSeekR1ChallengerClient
from app.ai.challenger_config import DeepSeekR1Config
from app.ai.challenger_prompts import (
    DEEPSEEK_R1_SYSTEM_PROMPT,
    DeepSeekR1PromptBuilder,
)
from app.ai.challenger_validator import (
    DeepSeekR1OutputValidator,
    MalformedChallengerOutputError,
)
from app.ai.client import Qwen3AnalystClient
from app.ai.config import Qwen3Config
from app.ai.council_evaluator import CouncilVerdict, evaluate_council_signals
from app.ai.metrics import AIAnalystMetrics
from app.ai.prompts import QWEN3_SYSTEM_PROMPT, Qwen3PromptBuilder
from app.ai.validator import MalformedAIOutputError, Qwen3OutputValidator

__all__ = [
    "DEEPSEEK_R1_SYSTEM_PROMPT",
    "QWEN3_SYSTEM_PROMPT",
    "AIAnalystMetrics",
    "CouncilVerdict",
    "DeepSeekR1ChallengerClient",
    "DeepSeekR1Config",
    "DeepSeekR1OutputValidator",
    "DeepSeekR1PromptBuilder",
    "MalformedAIOutputError",
    "MalformedChallengerOutputError",
    "Qwen3AnalystClient",
    "Qwen3Config",
    "Qwen3OutputValidator",
    "Qwen3PromptBuilder",
    "evaluate_council_signals",
]
