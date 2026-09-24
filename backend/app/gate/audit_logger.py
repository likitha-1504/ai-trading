"""Comprehensive Audit Logger for Deterministic Trade Gate decision pipeline."""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TradeGateAuditRecord:
    """Immutable audit entry capturing a pipeline stage transition."""

    record_id: str
    timestamp: datetime
    stage: str
    candidate_id: str
    decision: str  # e.g. "PASSED", "REJECTED", "CAUTION", "AUTONOMOUS", "MANUAL_PENDING", "TRANSFERRED"
    reason: str
    plan_id: str | None = None
    order_id: str | None = None
    position_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TradeGateAuditLogger:
    """Maintains an auditable, queryable event log for all Trade Gate actions and decisions."""

    def __init__(self) -> None:
        self._records: list[TradeGateAuditRecord] = []

    def record_stage(
        self,
        stage: str,
        candidate_id: str,
        decision: str,
        reason: str,
        plan_id: str | None = None,
        order_id: str | None = None,
        position_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TradeGateAuditRecord:
        """Log a pipeline stage event to audit storage and standard logger."""
        now = datetime.now(timezone.utc)
        record_id = f"audit-{len(self._records) + 1:06d}"
        meta = metadata or {}

        record = TradeGateAuditRecord(
            record_id=record_id,
            timestamp=now,
            stage=stage,
            candidate_id=candidate_id,
            decision=decision,
            reason=reason,
            plan_id=plan_id,
            order_id=order_id,
            position_id=position_id,
            metadata=meta,
        )
        self._records.append(record)

        log_msg = (
            f"[TradeGate Audit] [{stage}] Candidate={candidate_id} Decision={decision} "
            f"Reason='{reason}' Plan={plan_id} Order={order_id} Pos={position_id}"
        )
        if decision in ("REJECTED", "VETO"):
            logger.warning(log_msg)
        elif decision in ("PASSED", "AUTONOMOUS", "TRANSFERRED"):
            logger.info(log_msg)
        else:
            logger.debug(log_msg)

        return record

    def get_history(
        self,
        candidate_id: str | None = None,
        plan_id: str | None = None,
        stage: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query audit records with optional filters."""
        results = self._records
        if candidate_id:
            results = [r for r in results if r.candidate_id == candidate_id]
        if plan_id:
            results = [r for r in results if r.plan_id == plan_id]
        if stage:
            results = [r for r in results if r.stage.upper() == stage.upper()]

        return [asdict(r) for r in results]

    def clear(self) -> None:
        """Clear audit history (used primarily in test setups)."""
        self._records.clear()
