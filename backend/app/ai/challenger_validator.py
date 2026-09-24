"""Deterministic validation and parsing of DeepSeek-R1 challenger outputs."""

import json
import logging
import re
from typing import Any

from app.models.contracts import (
    ChallengerCritique,
    ChallengerRecommendation,
    ChallengerSeverity,
)

logger = logging.getLogger(__name__)


class MalformedChallengerOutputError(ValueError):
    """Raised when the DeepSeek-R1 output cannot be parsed into a valid ChallengerCritique."""


class DeepSeekR1OutputValidator:
    """Validates raw DeepSeek-R1 output strings against strict JSON schema and deterministic rules."""

    @classmethod
    def clean_json_text(cls, raw_text: str) -> str:
        """Strip <think> blocks, markdown fences, and auxiliary text to isolate JSON payload."""
        text = raw_text.strip()

        # 1. Strip DeepSeek-R1 reasoning <think>...</think> blocks
        if "<think>" in text:
            text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

        # 2. Handle markdown codeblocks ```json ... ``` or ``` ... ```
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()

        # 3. Extract outer curly brackets if extra preamble/postscript text exists
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
    ) -> ChallengerCritique:
        """Parse and strictly validate raw model output into a typed ChallengerCritique.

        Raises:
            MalformedChallengerOutputError: If JSON is invalid or schema contracts are violated.
        """
        cleaned = cls.clean_json_text(raw_output)
        try:
            payload: dict[str, Any] = json.loads(cleaned)
        except Exception as e:
            raise MalformedChallengerOutputError(
                f"Failed to parse JSON from challenger output: {e}. Raw content: {raw_output[:200]}"
            ) from e

        if not isinstance(payload, dict):
            raise MalformedChallengerOutputError("Challenger output JSON is not a dictionary")

        # 1. Critique Summary
        summary = payload.get("critique_summary")
        if not summary or not isinstance(summary, str) or not summary.strip():
            raise MalformedChallengerOutputError("Missing or invalid 'critique_summary' string")

        # 2. Identified Vulnerabilities list
        vulnerabilities = payload.get("identified_vulnerabilities")
        if not isinstance(vulnerabilities, list):
            raise MalformedChallengerOutputError("'identified_vulnerabilities' must be a list of strings")
        vulnerabilities = [str(item).strip() for item in vulnerabilities if str(item).strip()]

        # 3. Contradictory Signals list
        signals = payload.get("contradictory_signals")
        if not isinstance(signals, list):
            raise MalformedChallengerOutputError("'contradictory_signals' must be a list of strings")
        signals = [str(item).strip() for item in signals if str(item).strip()]

        # 4. Missing Evidence list (optional in output, defaults to empty list)
        missing = payload.get("missing_evidence", [])
        if not isinstance(missing, list):
            raise MalformedChallengerOutputError("'missing_evidence' must be a list of strings")
        missing = [str(item).strip() for item in missing if str(item).strip()]

        # 5. Invalidation Conditions list (optional in output, defaults to empty list)
        invalidation = payload.get("invalidation_conditions", [])
        if not isinstance(invalidation, list):
            raise MalformedChallengerOutputError("'invalidation_conditions' must be a list of strings")
        invalidation = [str(item).strip() for item in invalidation if str(item).strip()]

        # 6. Worst Case Scenario
        worst_case = payload.get("worst_case_scenario")
        if not worst_case or not isinstance(worst_case, str) or not worst_case.strip():
            raise MalformedChallengerOutputError("Missing or invalid 'worst_case_scenario' string")

        # 7. Downside Severity (LOW / MEDIUM / SEVERE)
        sev_raw = payload.get("downside_severity")
        if not sev_raw or not isinstance(sev_raw, str):
            raise MalformedChallengerOutputError("Missing or invalid 'downside_severity'")

        sev_clean = sev_raw.strip().upper()
        try:
            severity = ChallengerSeverity(sev_clean)
        except ValueError as e:
            raise MalformedChallengerOutputError(
                f"Invalid downside_severity '{sev_clean}'. Must be one of: {[s.value for s in ChallengerSeverity]}"
            ) from e

        # 8. Recommendation Flag (CONFIRM / CONTEST / VETO_CANDIDATE)
        rec_raw = payload.get("recommendation_flag")
        if not rec_raw or not isinstance(rec_raw, str):
            raise MalformedChallengerOutputError("Missing or invalid 'recommendation_flag'")

        rec_clean = rec_raw.strip().upper()
        try:
            recommendation = ChallengerRecommendation(rec_clean)
        except ValueError as e:
            raise MalformedChallengerOutputError(
                f"Invalid recommendation_flag '{rec_clean}'. Must be one of: {[r.value for r in ChallengerRecommendation]}"
            ) from e

        return ChallengerCritique(
            candidate_id=candidate_id,
            model_name=model_name,
            model_version=model_version,
            prompt_version=prompt_version,
            critique_summary=summary.strip(),
            identified_vulnerabilities=vulnerabilities,
            contradictory_signals=signals,
            missing_evidence=missing,
            invalidation_conditions=invalidation,
            worst_case_scenario=worst_case.strip(),
            downside_severity=severity,
            recommendation_flag=recommendation,
            latency_ms=latency_ms,
            token_count=token_count,
            is_fallback=False,
            raw_response=raw_output,
        )

    @classmethod
    def create_fallback_critique(
        cls,
        candidate_id: str,
        reason: str,
        latency_ms: int,
        model_name: str,
        model_version: str,
        prompt_version: str,
        raw_output: str | None = None,
    ) -> ChallengerCritique:
        """Create a safe, deterministic fallback ChallengerCritique when challenger fails or times out.

        Crucial safety invariant: Fallback critique has recommendation CONTEST and severity MEDIUM,
        mandating strict quantitative verification without blind endorsement.
        """
        logger.warning(
            "Generating fallback ChallengerCritique for candidate %s. Reason: %s (latency: %dms)",
            candidate_id,
            reason,
            latency_ms,
        )
        return ChallengerCritique(
            candidate_id=candidate_id,
            model_name=model_name,
            model_version=model_version,
            prompt_version=prompt_version,
            critique_summary=f"Deterministic Fallback: {reason}",
            identified_vulnerabilities=["Challenger inference unresponsiveness or timeout"],
            contradictory_signals=["Unverified risk profile due to challenger failure"],
            missing_evidence=["Challenger adversarial stress-testing incomplete"],
            invalidation_conditions=["Challenger communication failure"],
            worst_case_scenario="Unchecked market risk due to offline challenger layer; fallback safety engaged.",
            downside_severity=ChallengerSeverity.MEDIUM,
            recommendation_flag=ChallengerRecommendation.CONTEST,
            latency_ms=latency_ms,
            token_count=0,
            is_fallback=True,
            raw_response=raw_output,
        )
