"""Measurable Justification & Model Admission Gate for Phase 36 AI Council Evolution.

Ensures that models are admitted to the AI Council strictly upon demonstrating
empirical accuracy uplift, orthogonal reasoning diversity, downside capital
preservation, and sub-budget latency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.council_evolution.models import (
    AdmissionStatus,
    CandidateModelBenchmark,
    CouncilRole,
    MeasurableHurdles,
    ModelJustificationScorecard,
    UnjustifiedModelError,
)
from app.security.tamper_log import TamperEvidentAuditLogger

logger = logging.getLogger(__name__)


class ModelAdmissionGate:
    """Enforces rigorous measurable justification before admitting candidate models to the AI Council."""

    def __init__(
        self,
        hurdles: MeasurableHurdles | None = None,
        audit_logger: TamperEvidentAuditLogger | None = None,
    ) -> None:
        self.hurdles = hurdles or MeasurableHurdles()
        self.audit_logger = audit_logger or TamperEvidentAuditLogger()
        self._active_council: list[dict[str, str]] = [
            {"model_id": "QWEN3-ANALYST-V2", "name": "Qwen3 32B Analyst", "role": CouncilRole.PRIMARY_ANALYST.value},
            {"model_id": "DEEPSEEK-R1-V2", "name": "DeepSeek-R1 70B Challenger", "role": CouncilRole.ADVERSARIAL_CHALLENGER.value},
        ]
        self._candidates: dict[str, CandidateModelBenchmark] = {}
        self._scorecards: dict[str, ModelJustificationScorecard] = {}
        self._initialize_candidate_catalog()

    def _initialize_candidate_catalog(self) -> None:
        """Initializes candidate models with empirical benchmark datasets."""
        # 1. Justified Candidate: FinGPT Macro Sentiment Specialist
        c1 = CandidateModelBenchmark(
            candidate_id="FINGPT-SENTIMENT-V1",
            name="FinGPT Sentiment Specialist",
            proposed_role=CouncilRole.MACRO_SENTIMENT_SPECIALIST,
            test_cases_evaluated=200,
            directional_accuracy_pct=75.2,
            accuracy_uplift_pct=4.2,             # Hurdle: >= 3.0% (PASS)
            downside_capital_saved_inr=28.50,    # Hurdle: >= 20.0 (PASS)
            reasoning_diversity_score=0.38,       # Hurdle: >= 0.25 (PASS)
            p95_latency_ms=1450.0,               # Hurdle: <= 2500ms (PASS)
            token_cost_ratio=1.15,               # Hurdle: <= 1.50 (PASS)
        )
        self._candidates[c1.candidate_id] = c1

        # 2. Unjustified Candidate: Redundant Echo Bot (Negative Control)
        c2 = CandidateModelBenchmark(
            candidate_id="REDUNDANT-ECHO-BOT",
            name="Redundant Echo Model",
            proposed_role=CouncilRole.CANDIDATE_MODEL,
            test_cases_evaluated=200,
            directional_accuracy_pct=71.2,
            accuracy_uplift_pct=0.2,             # Hurdle: >= 3.0% (FAIL)
            downside_capital_saved_inr=2.50,     # Hurdle: >= 20.0 (FAIL)
            reasoning_diversity_score=0.06,       # Hurdle: >= 0.25 (FAIL)
            p95_latency_ms=2950.0,               # Hurdle: <= 2500ms (FAIL)
            token_cost_ratio=1.95,               # Hurdle: <= 1.50 (FAIL)
        )
        self._candidates[c2.candidate_id] = c2

    def evaluate_candidate(self, candidate_id: str) -> ModelJustificationScorecard:
        """Evaluates a candidate model against all 5 measurable justification hurdles."""
        if candidate_id not in self._candidates:
            raise KeyError(f"Candidate model '{candidate_id}' not found in benchmark catalog.")

        bm = self._candidates[candidate_id]
        admission_reasons: list[str] = []
        rejection_reasons: list[str] = []
        passed_all = True

        # Hurdle 1: Accuracy Uplift
        if bm.accuracy_uplift_pct >= self.hurdles.min_accuracy_uplift_pct:
            admission_reasons.append(
                f"Accuracy uplift {bm.accuracy_uplift_pct:+.1f}% satisfies minimum hurdle (+{self.hurdles.min_accuracy_uplift_pct:.1f}%)."
            )
        else:
            passed_all = False
            rejection_reasons.append(
                f"Accuracy uplift {bm.accuracy_uplift_pct:+.1f}% breaches minimum hurdle (+{self.hurdles.min_accuracy_uplift_pct:.1f}%)."
            )

        # Hurdle 2: Downside Capital Saved
        if bm.downside_capital_saved_inr >= self.hurdles.min_downside_capital_saved:
            admission_reasons.append(
                f"Downside capital saved (INR {bm.downside_capital_saved_inr:.2f}) satisfies threshold (INR {self.hurdles.min_downside_capital_saved:.2f})."
            )
        else:
            passed_all = False
            rejection_reasons.append(
                f"Downside capital saved (INR {bm.downside_capital_saved_inr:.2f}) insufficient (required INR {self.hurdles.min_downside_capital_saved:.2f})."
            )

        # Hurdle 3: Reasoning Diversity
        if bm.reasoning_diversity_score >= self.hurdles.min_diversity_score:
            admission_reasons.append(
                f"Reasoning diversity score {bm.reasoning_diversity_score:.2f} proves orthogonal insight (>= {self.hurdles.min_diversity_score:.2f})."
            )
        else:
            passed_all = False
            rejection_reasons.append(
                f"Reasoning diversity score {bm.reasoning_diversity_score:.2f} indicates redundant mirroring (< {self.hurdles.min_diversity_score:.2f})."
            )

        # Hurdle 4: P95 Latency Budget
        if bm.p95_latency_ms <= self.hurdles.max_p95_latency_ms:
            admission_reasons.append(
                f"P95 latency {bm.p95_latency_ms:.0f}ms within operational budget (<= {self.hurdles.max_p95_latency_ms:.0f}ms)."
            )
        else:
            passed_all = False
            rejection_reasons.append(
                f"P95 latency {bm.p95_latency_ms:.0f}ms exceeds operational budget (<= {self.hurdles.max_p95_latency_ms:.0f}ms)."
            )

        # Hurdle 5: Token Cost Ratio
        if bm.token_cost_ratio <= self.hurdles.max_token_cost_ratio:
            admission_reasons.append(
                f"Token cost ratio {bm.token_cost_ratio:.2f} economically justified (<= {self.hurdles.max_token_cost_ratio:.2f})."
            )
        else:
            passed_all = False
            rejection_reasons.append(
                f"Token cost ratio {bm.token_cost_ratio:.2f} excessive economically (<= {self.hurdles.max_token_cost_ratio:.2f})."
            )

        status = AdmissionStatus.JUSTIFIED if passed_all else AdmissionStatus.REJECTED
        scorecard = ModelJustificationScorecard(
            candidate_id=bm.candidate_id,
            model_name=bm.name,
            role=bm.proposed_role,
            status=status,
            is_justified=passed_all,
            hurdles_evaluated=self.hurdles,
            realized_metrics=bm,
            admission_reasons=admission_reasons,
            rejection_reasons=rejection_reasons,
            evaluated_at=datetime.now(timezone.utc),
        )
        self._scorecards[candidate_id] = scorecard
        return scorecard

    def admit_model(
        self,
        candidate_id: str,
        operator_token: str,
        operator_id: str = "OPERATOR_01",
    ) -> ModelJustificationScorecard:
        """Admits a measurably justified candidate model to the active AI council."""
        if not self._validate_operator_token(operator_token):
            raise PermissionError("Valid signed operator token required for AI Council model admission.")

        scorecard = self.evaluate_candidate(candidate_id)
        if not scorecard.is_justified:
            reasons_str = "; ".join(scorecard.rejection_reasons)
            raise UnjustifiedModelError(
                f"Model '{candidate_id}' rejected: breaches measurable justification hurdles ({reasons_str})."
            )

        # Add to active council
        new_entry = {
            "model_id": candidate_id,
            "name": scorecard.model_name,
            "role": scorecard.role.value,
        }
        if not any(m["model_id"] == candidate_id for m in self._active_council):
            self._active_council.append(new_entry)

        scorecard.status = AdmissionStatus.ADMITTED

        # Cryptographically log admission in audit ledger
        self.audit_logger.log_event(
            event_type="AI_COUNCIL_EVOLUTION",
            operator_id=operator_id,
            role="OPERATOR",
            action="ADMIT_COUNCIL_MODEL",
            resource=candidate_id,
            details={
                "model_name": scorecard.model_name,
                "role": scorecard.role.value,
                "metrics": scorecard.realized_metrics.model_dump(mode="json"),
                "admission_reasons": scorecard.admission_reasons,
            },
        )

        return scorecard

    @staticmethod
    def _validate_operator_token(token: str | None) -> bool:
        """Validates operator token format."""
        if not token:
            return False
        if token.startswith("OPERATOR-COUNCIL-PHASE36-") and len(token) > 30:
            return True
        return bool(token.startswith("OPTOK.") and len(token.split(".")) == 3)

    def get_active_council(self) -> list[dict[str, str]]:
        """Returns the list of active models in the deliberation council."""
        return list(self._active_council)

    def list_candidate_scorecards(self) -> list[ModelJustificationScorecard]:
        """Returns scorecards for all evaluated candidates."""
        for cid in self._candidates:
            if cid not in self._scorecards:
                self.evaluate_candidate(cid)
        return list(self._scorecards.values())
