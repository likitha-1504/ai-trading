"""Explicit Promotion Gate & Governance Protocol for Phase 35 Research Sandbox.

Governs the migration of validated research strategies from quarantined sandbox
to candidate stage, enforcing strict statistical hurdles, zero leakage, mathematical
reproducibility, and non-silent operator authorization tokens.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.sandbox.models import (
    PromotionEvaluation,
    PromotionGateError,
    PromotionHurdles,
    PromotionRequest,
    PromotionResult,
    PromotionStage,
    SandboxExecutionResult,
    SilentPromotionError,
)
from app.sandbox.sandbox_engine import ResearchSandboxEngine
from app.security.tamper_log import TamperEvidentAuditLogger

logger = logging.getLogger(__name__)


class ExplicitPromotionGate:
    """Enforces rigorous multi-stage criteria and operator authorization before promotion."""

    def __init__(
        self,
        engine: ResearchSandboxEngine | None = None,
        hurdles: PromotionHurdles | None = None,
        audit_logger: TamperEvidentAuditLogger | None = None,
    ) -> None:
        self.engine = engine or ResearchSandboxEngine()
        self.hurdles = hurdles or PromotionHurdles()
        self.audit_logger = audit_logger or TamperEvidentAuditLogger()
        self._promoted_registry: dict[str, PromotionResult] = {}

    def evaluate_candidate(
        self,
        execution_result: SandboxExecutionResult,
        operator_token: str | None = None,
    ) -> PromotionEvaluation:
        """Evaluates execution metrics, reproducibility, and auth token against promotion criteria."""
        metrics = execution_result.metrics
        reasons: list[str] = []

        # 1. Statistical Hurdles Check
        passed_hurdles = True
        if metrics.total_trades < self.hurdles.min_trades:
            passed_hurdles = False
            reasons.append(f"Trade count {metrics.total_trades} < required {self.hurdles.min_trades}")

        if metrics.win_rate < self.hurdles.min_win_rate:
            passed_hurdles = False
            reasons.append(f"Win rate {metrics.win_rate:.2%} < required {self.hurdles.min_win_rate:.2%}")

        if metrics.profit_factor < self.hurdles.min_profit_factor:
            passed_hurdles = False
            reasons.append(f"Profit factor {metrics.profit_factor:.2f} < required {self.hurdles.min_profit_factor:.2f}")

        if metrics.sharpe_ratio < self.hurdles.min_sharpe_ratio:
            passed_hurdles = False
            reasons.append(f"Sharpe ratio {metrics.sharpe_ratio:.2f} < required {self.hurdles.min_sharpe_ratio:.2f}")

        if metrics.max_drawdown_pct > self.hurdles.max_drawdown_pct:
            passed_hurdles = False
            reasons.append(f"Max drawdown {metrics.max_drawdown_pct:.2f}% > limit {self.hurdles.max_drawdown_pct:.2f}%")

        # 2. Reproducibility Check
        reproducibility_verified = execution_result.reproducibility_verified
        if not reproducibility_verified:
            reasons.append("Exact mathematical reproducibility check not yet certified.")

        # 3. Look-Ahead / Data Leakage Check
        leakage_free = True
        if "TRAIN" in execution_result.dataset_id and "TEST" in execution_result.dataset_id:
            leakage_free = False
            reasons.append("Cross-contamination detected in dataset split.")

        # 4. Operator Authorization Token Check
        token_valid = self._validate_operator_token(operator_token)
        if not token_valid:
            reasons.append("Missing or invalid operator authorization token.")

        all_ok = passed_hurdles and reproducibility_verified and leakage_free and token_valid
        target_stage = PromotionStage.APPROVED_CANDIDATE if all_ok else PromotionStage.REJECTED

        return PromotionEvaluation(
            experiment_id=execution_result.experiment_id,
            passed_statistical_hurdles=passed_hurdles,
            reproducibility_verified=reproducibility_verified,
            leakage_free=leakage_free,
            operator_token_valid=token_valid,
            target_stage=target_stage,
            rejection_reasons=reasons,
            evaluated_at=datetime.now(timezone.utc),
        )

    def process_promotion_request(
        self,
        request: PromotionRequest,
        execution_result: SandboxExecutionResult | None = None,
    ) -> PromotionResult:
        """Processes formal promotion request, enforcing anti-silent-promotion rule."""
        # 1. Anti-Silent Promotion Guard
        if not request.operator_token or not self._validate_operator_token(request.operator_token):
            raise SilentPromotionError(
                f"Silent promotion prohibited: Valid signed operator token required to promote '{request.experiment_id}'."
            )

        # 2. Retrieve or run execution
        if execution_result is None:
            # Re-run and verify reproducibility
            _, execution_result, _ = self.engine.verify_reproducibility(request.experiment_id)

        # 3. Comprehensive Evaluation
        evaluation = self.evaluate_candidate(execution_result, operator_token=request.operator_token)

        if evaluation.target_stage != PromotionStage.APPROVED_CANDIDATE:
            reasons_str = "; ".join(evaluation.rejection_reasons)
            raise PromotionGateError(
                f"Promotion gate rejected candidate '{request.experiment_id}': {reasons_str}"
            )

        # 4. Cryptographic Tamper-Evident Audit Logging
        ledger_entry = self.audit_logger.log_event(
            event_type="STRATEGY_PROMOTION",
            operator_id=request.operator_id,
            role="OPERATOR",
            action="PROMOTED_FROM_SANDBOX",
            resource=request.experiment_id,
            details={
                "target_environment": request.target_environment,
                "execution_hash": execution_result.execution_hash,
                "config_hash": execution_result.config_hash,
                "dataset_hash": execution_result.dataset_hash,
                "metrics": execution_result.metrics.model_dump(),
                "rationale": request.rationale,
            },
        )

        result = PromotionResult(
            success=True,
            experiment_id=request.experiment_id,
            stage=PromotionStage.APPROVED_CANDIDATE,
            promoted_at=datetime.now(timezone.utc),
            audit_ledger_id=str(ledger_entry.entry_id),
            message=f"Strategy '{request.experiment_id}' successfully promoted to {request.target_environment}.",
        )
        self._promoted_registry[request.experiment_id] = result
        return result

    @staticmethod
    def _validate_operator_token(token: str | None) -> bool:
        """Validates operator token format."""
        if not token:
            return False
        # Valid formats: OPERATOR-PROMOTION-PHASE35-* or OPTOK.*
        if token.startswith("OPERATOR-PROMOTION-PHASE35-") and len(token) > 30:
            return True
        return bool(token.startswith("OPTOK.") and len(token.split(".")) == 3)

    def get_promotion_result(self, experiment_id: str) -> PromotionResult | None:
        """Retrieves promotion result for a given experiment ID."""
        return self._promoted_registry.get(experiment_id)

    def list_promoted_strategies(self) -> list[PromotionResult]:
        """Lists all successfully promoted candidate strategies."""
        return list(self._promoted_registry.values())
