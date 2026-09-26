"""Council Evolution Master Orchestrator for Phase 36.

Coordinates candidate model justification evaluations, deterministic safety
independence audits, and generates full Phase 36 compliance reports.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.council_evolution.admission_gate import ModelAdmissionGate
from app.council_evolution.independence_guard import CouncilIndependenceGuard
from app.council_evolution.models import (
    CouncilEvolutionReport,
    MeasurableHurdles,
)
from app.security.tamper_log import TamperEvidentAuditLogger


class CouncilEvolutionOrchestrator:
    """Master orchestrator for AI Council Evolution and safety decoupling verification."""

    def __init__(
        self,
        hurdles: MeasurableHurdles | None = None,
        audit_logger: TamperEvidentAuditLogger | None = None,
    ) -> None:
        self.audit_logger = audit_logger or TamperEvidentAuditLogger()
        self.admission_gate = ModelAdmissionGate(
            hurdles=hurdles,
            audit_logger=self.audit_logger,
        )
        self.independence_guard = CouncilIndependenceGuard()

    def run_council_evolution_audit(self) -> CouncilEvolutionReport:
        """Executes full Phase 36 compliance audit across model justification and gate independence."""
        audit_id = f"COUNCIL-EVO-{uuid.uuid4().hex[:8].upper()}"
        active_models = self.admission_gate.get_active_council()
        scorecards = self.admission_gate.list_candidate_scorecards()
        attestation = self.independence_guard.audit_complete_independence()

        overall_status = "AUDIT_VERIFIED"
        if not attestation.trade_gate_zero_llm_dependency or not attestation.position_watcher_zero_llm_dependency:
            overall_status = "SAFETY_INDEPENDENCE_BREACH"

        return CouncilEvolutionReport(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            active_council_models=active_models,
            candidate_scorecards=scorecards,
            independence_attestation=attestation,
            overall_status=overall_status,
        )
