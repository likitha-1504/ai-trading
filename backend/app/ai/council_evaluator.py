"""Deterministic AI Council evaluation rules resolving Qwen3 and DeepSeek-R1 signals."""

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.contracts import (
    Candidate,
    ChallengerCritique,
    ChallengerRecommendation,
    ChallengerSeverity,
    MarketThesis,
    MarketThesisAction,
)

logger = logging.getLogger(__name__)


@dataclass
class CouncilVerdict:
    """Outcome of deterministic council evaluation between Qwen3 thesis and DeepSeek-R1 critique."""

    action: MarketThesisAction
    passed_filter: bool
    decision_reason: str
    risk_audit_notes: list[str] = field(default_factory=list)
    confidence: Decimal = Decimal("0.0")


def evaluate_council_signals(
    candidate: Candidate,
    thesis: MarketThesis,
    critique: ChallengerCritique,
    min_qwen_confidence: Decimal = Decimal("0.60"),
    max_tolerable_spread_pct: Decimal = Decimal("0.0015"),
    min_tolerable_liquidity: Decimal = Decimal("70.0"),
) -> CouncilVerdict:
    """Deterministically arbitrate Qwen3 analyst thesis and DeepSeek-R1 critique.

    Safety Invariant:
    Never implements simple majority voting or probabilistic resolution.
    Deterministic quantitative facts (spread, liquidity, stop-risk, fatal veto conditions)
    retain absolute decision authority over conflicting AI opinions.
    """
    fs = candidate.feature_snapshot
    risk_notes: list[str] = []

    # 1. Fallback Safety Gating: If either model failed, autonomous clearance is blocked
    if thesis.is_fallback or critique.is_fallback:
        reasons = []
        if thesis.is_fallback:
            reasons.append("Qwen3 primary analyst offline or fallback")
        if critique.is_fallback:
            reasons.append("DeepSeek-R1 challenger offline or fallback")
        logger.warning(
            "Deterministic Council Gate: Fallback engaged for %s (%s)",
            candidate.candidate_id,
            ", ".join(reasons),
        )
        return CouncilVerdict(
            action=MarketThesisAction.CAUTION,
            passed_filter=False,
            decision_reason=f"Deterministic Rule: AI Council fallback active ({'; '.join(reasons)})",
            risk_audit_notes=reasons,
            confidence=Decimal("0.0"),
        )

    # 2. Qwen3 Primary Filter: Rejection or sub-threshold confidence terminates immediately
    if thesis.suggested_action == MarketThesisAction.REJECT:
        return CouncilVerdict(
            action=MarketThesisAction.REJECT,
            passed_filter=False,
            decision_reason=f"Deterministic Rule: Qwen3 thesis rejected candidate ({thesis.thesis_summary})",
            risk_audit_notes=thesis.perceived_risks,
            confidence=thesis.confidence_score,
        )

    if thesis.confidence_score < min_qwen_confidence:
        return CouncilVerdict(
            action=MarketThesisAction.REJECT,
            passed_filter=False,
            decision_reason=(
                f"Deterministic Rule: Qwen3 confidence {thesis.confidence_score} "
                f"below minimum hurdle {min_qwen_confidence}"
            ),
            risk_audit_notes=thesis.perceived_risks,
            confidence=thesis.confidence_score,
        )

    # 3. DeepSeek-R1 Fatal Flaw Veto: Severe downside with VETO_CANDIDATE blocks trade
    if (
        critique.recommendation_flag == ChallengerRecommendation.VETO_CANDIDATE
        and critique.downside_severity == ChallengerSeverity.SEVERE
    ):
        return CouncilVerdict(
            action=MarketThesisAction.REJECT,
            passed_filter=False,
            decision_reason=(
                f"Deterministic Rule: DeepSeek-R1 vetoed candidate on severe risk: {critique.worst_case_scenario}"
            ),
            risk_audit_notes=critique.identified_vulnerabilities + critique.contradictory_signals,
            confidence=thesis.confidence_score,
        )

    # 4. Dispute Resolution (Qwen3 Bullish vs DeepSeek-R1 Contesting):
    # Deterministic quantitative facts arbitrate the dispute
    if critique.recommendation_flag in (
        ChallengerRecommendation.CONTEST,
        ChallengerRecommendation.VETO_CANDIDATE,
    ):
        risk_notes.extend(critique.identified_vulnerabilities)
        risk_notes.extend(critique.contradictory_signals)

        # Empirical Check A: Spread friction check
        if fs is not None and fs.spread_pct > max_tolerable_spread_pct:
            return CouncilVerdict(
                action=MarketThesisAction.REJECT,
                passed_filter=False,
                decision_reason=(
                    f"Deterministic Rule: DeepSeek-R1 risk confirmed by empirical spread "
                    f"{fs.spread_pct} > threshold {max_tolerable_spread_pct}"
                ),
                risk_audit_notes=risk_notes,
                confidence=thesis.confidence_score,
            )

        # Empirical Check B: Liquidity support check
        if fs is not None and fs.liquidity_score < min_tolerable_liquidity:
            return CouncilVerdict(
                action=MarketThesisAction.REJECT,
                passed_filter=False,
                decision_reason=(
                    f"Deterministic Rule: DeepSeek-R1 risk confirmed by deficient liquidity score "
                    f"{fs.liquidity_score} < threshold {min_tolerable_liquidity}"
                ),
                risk_audit_notes=risk_notes,
                confidence=thesis.confidence_score,
            )

        # Empirical Check C: Stop risk validity
        if candidate.initial_stop_price >= candidate.trigger_price:
            return CouncilVerdict(
                action=MarketThesisAction.REJECT,
                passed_filter=False,
                decision_reason="Deterministic Rule: Invalid stop-loss orientation relative to trigger price",
                risk_audit_notes=risk_notes,
                confidence=thesis.confidence_score,
            )

        # If empirical checks pass, the trade is cleared with CAUTION status and audited risk notes
        return CouncilVerdict(
            action=MarketThesisAction.CAUTION,
            passed_filter=True,
            decision_reason=(
                "Deterministic Rule: Qwen3 thesis accepted with caution. "
                "DeepSeek-R1 contested signals logged, but empirical metrics satisfy risk hurdle."
            ),
            risk_audit_notes=risk_notes,
            confidence=thesis.confidence_score,
        )

    # 5. Full Agreement (Qwen3 PROCEED + DeepSeek-R1 CONFIRM)
    return CouncilVerdict(
        action=MarketThesisAction.PROCEED,
        passed_filter=True,
        decision_reason="Deterministic Rule: Qwen3 thesis corroborated by DeepSeek-R1 stress test",
        risk_audit_notes=thesis.perceived_risks,
        confidence=thesis.confidence_score,
    )
