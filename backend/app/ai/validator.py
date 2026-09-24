"""Deterministic validation and parsing of Qwen3 model outputs."""

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.contracts import MarketThesis, MarketThesisAction

logger = logging.getLogger(__name__)


class MalformedAIOutputError(ValueError):
    """Raised when the AI output cannot be parsed into a valid MarketThesis."""


class Qwen3OutputValidator:
    """Validates raw Qwen3 output strings against strict JSON schema and deterministic rules."""

    @classmethod
    def clean_json_text(cls, raw_text: str) -> str:
        """Strip markdown fences and auxiliary text to isolate JSON payload."""
        text = raw_text.strip()

        # Handle ```json ... ``` or ``` ... ```
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()

        # If still surrounded by other characters, extract outer curly brackets
        if not (text.startswith("{") and text.endswith("}")):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1].strip()

        return text

    @classmethod
    def validate_and_parse(
        cls,
        raw_output: str,
        candidate_id: str,
        latency_ms: int,
        model_name: str,
        model_version: str,
        prompt_version: str,
        token_count: int | None = None,
    ) -> MarketThesis:
        """Parse and strictly validate raw model output into a typed MarketThesis.

        Raises:
            MalformedAIOutputError: If JSON is invalid or schema contracts are violated.
        """
        cleaned = cls.clean_json_text(raw_output)
        try:
            payload: dict[str, Any] = json.loads(cleaned)
        except Exception as e:
            raise MalformedAIOutputError(
                f"Failed to parse JSON from model output: {e}. Raw content: {raw_output[:200]}"
            ) from e

        if not isinstance(payload, dict):
            raise MalformedAIOutputError("Model output JSON is not a dictionary")

        # 1. Thesis Summary
        thesis_summary = payload.get("thesis_summary")
        if not thesis_summary or not isinstance(thesis_summary, str) or not thesis_summary.strip():
            raise MalformedAIOutputError("Missing or invalid 'thesis_summary' string")

        # 2. Catalyst Identified (optional)
        catalyst = payload.get("catalyst_identified")
        if catalyst is not None and not isinstance(catalyst, str):
            catalyst = str(catalyst)

        # 3. Evidence, Invalidation, Risks lists
        evidence = payload.get("bullish_evidence")
        if not isinstance(evidence, list):
            raise MalformedAIOutputError("'bullish_evidence' must be a list of strings")
        evidence = [str(item) for item in evidence if item]

        invalidation = payload.get("invalidation_conditions")
        if not isinstance(invalidation, list):
            raise MalformedAIOutputError("'invalidation_conditions' must be a list of strings")
        invalidation = [str(item) for item in invalidation if item]

        risks = payload.get("perceived_risks")
        if not isinstance(risks, list):
            raise MalformedAIOutputError("'perceived_risks' must be a list of strings")
        risks = [str(item) for item in risks if item]

        # 4. Confidence Score bounded [0.0, 1.0]
        conf_raw = payload.get("confidence_score")
        if conf_raw is None:
            raise MalformedAIOutputError("Missing 'confidence_score'")
        try:
            confidence = Decimal(str(conf_raw))
        except (InvalidOperation, TypeError) as e:
            raise MalformedAIOutputError(f"Invalid confidence_score format: {conf_raw}") from e

        if not (Decimal("0.0") <= confidence <= Decimal("1.0")):
            raise MalformedAIOutputError(
                f"confidence_score {confidence} out of valid range [0.0, 1.0]"
            )

        # 5. Context Summary (optional)
        context_summary = payload.get("context_summary")
        if context_summary is not None and not isinstance(context_summary, str):
            context_summary = str(context_summary)

        # 6. Suggested Action (PROCEED / CAUTION / REJECT)
        action_raw = payload.get("suggested_action")
        if not action_raw or not isinstance(action_raw, str):
            raise MalformedAIOutputError("Missing or invalid 'suggested_action'")

        action_clean = action_raw.strip().upper()
        try:
            action = MarketThesisAction(action_clean)
        except ValueError as e:
            raise MalformedAIOutputError(
                f"Invalid suggested_action '{action_clean}'. Must be one of: {[a.value for a in MarketThesisAction]}"
            ) from e

        return MarketThesis(
            candidate_id=candidate_id,
            model_name=model_name,
            model_version=model_version,
            prompt_version=prompt_version,
            thesis_summary=thesis_summary.strip(),
            catalyst_identified=catalyst.strip() if catalyst else None,
            bullish_evidence=evidence,
            invalidation_conditions=invalidation,
            perceived_risks=risks,
            confidence_score=confidence,
            context_summary=context_summary.strip() if context_summary else None,
            suggested_action=action,
            latency_ms=latency_ms,
            token_count=token_count,
            is_fallback=False,
            raw_response=raw_output,
        )

    @classmethod
    def create_fallback_thesis(
        cls,
        candidate_id: str,
        reason: str,
        latency_ms: int,
        model_name: str,
        model_version: str,
        prompt_version: str,
        raw_output: str | None = None,
    ) -> MarketThesis:
        """Create a safe, deterministic fallback MarketThesis when AI fails or times out.

        Crucial safety invariant: Fallback output has confidence 0.0 and cannot authorize
        trade execution or bypass risk controls.
        """
        logger.warning(
            "Generating fallback MarketThesis for candidate %s. Reason: %s (latency: %dms)",
            candidate_id,
            reason,
            latency_ms,
        )
        return MarketThesis(
            candidate_id=candidate_id,
            model_name=model_name,
            model_version=model_version,
            prompt_version=prompt_version,
            thesis_summary=f"Deterministic Fallback: {reason}",
            catalyst_identified=None,
            bullish_evidence=[],
            invalidation_conditions=["AI inference failure or timeout"],
            perceived_risks=["AI unresponsiveness; fallback safety engaged"],
            confidence_score=Decimal("0.0"),
            context_summary="Fallback generated to ensure deterministic safety without LLM dependence.",
            suggested_action=MarketThesisAction.CAUTION,
            latency_ms=latency_ms,
            token_count=0,
            is_fallback=True,
            raw_response=raw_output,
        )
