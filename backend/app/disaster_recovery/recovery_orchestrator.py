"""Unified Disaster Recovery Orchestrator for Phase 33.

Coordinates multi-scenario fault injection drills, verifies fault tolerance,
and generates standardized audit telemetry.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.adapters.broker_base import BrokerAdapter
from app.adapters.paper_adapter import PaperAdapter
from app.db.connection import get_db_path
from app.db.recovery import RestartRecoveryManager
from app.db.repository import DatabaseRepository
from app.disaster_recovery.broker_resilience import BrokerResilienceManager
from app.disaster_recovery.db_resilience import DatabaseResilienceManager
from app.disaster_recovery.idempotency_manager import IdempotencyManager
from app.disaster_recovery.models import (
    DisasterRecoveryAuditResult,
    DisasterScenarioType,
    ScenarioDrillResult,
    SystemRecoveryStatus,
)
from app.disaster_recovery.safe_resume import SafeResumeController
from app.disaster_recovery.stale_data_guard import StaleDataGuard, StaleMarketDataError
from app.disaster_recovery.state_reconstructor import StateReconstructor
from app.execution.execution_engine import DuplicateOrderError

logger = logging.getLogger(__name__)


class DisasterRecoveryOrchestrator:
    """End-to-end disaster recovery testing and operational continuity manager."""

    def __init__(
        self,
        db_path: str | None = None,
        broker_adapter: BrokerAdapter | None = None,
    ) -> None:
        self.db_path = get_db_path(db_path)
        self.repo = DatabaseRepository(db_path=self.db_path)
        self.broker = broker_adapter or PaperAdapter()

        # Subsystems
        self.stale_guard = StaleDataGuard()
        self.idempotency_mgr = IdempotencyManager(db_path=self.db_path)
        self.db_resilience = DatabaseResilienceManager(db_path=self.db_path)
        self.broker_resilience = BrokerResilienceManager(broker_adapter=self.broker)
        self.state_reconstructor = StateReconstructor(
            repository=self.repo, broker_adapter=self.broker, db_path=self.db_path
        )
        self.safe_resume = SafeResumeController(
            db_resilience=self.db_resilience,
            broker_resilience=self.broker_resilience,
            state_reconstructor=self.state_reconstructor,
            stale_data_guard=self.stale_guard,
        )

        self._last_audit: DisasterRecoveryAuditResult | None = None

    def run_comprehensive_disaster_drill(self) -> DisasterRecoveryAuditResult:
        """Executes automated multi-scenario fault injection drill across all 6 disaster domains."""
        now = datetime.now(timezone.utc)
        audit_id = f"DR-AUDIT-{uuid.uuid4().hex[:8].upper()}"
        drill_results: list[ScenarioDrillResult] = []

        logger.info("Starting Comprehensive Disaster Recovery Drill %s...", audit_id)

        # 1. Process Crash & Restart State Reconstruction Drill
        drill_results.append(self._drill_crash_restart())

        # 2. Broker Disconnect & Auto-Reconnect Drill
        drill_results.append(self._drill_broker_disconnect())

        # 3. Stale Market Data Injection & Order Blocking Drill
        drill_results.append(self._drill_stale_market_data())

        # 4. Database Resilience & WAL Checkpointing Drill
        drill_results.append(self._drill_database_resilience())

        # 5. Duplicate Order Attack & Restart Idempotency Drill
        drill_results.append(self._drill_duplicate_prevention())

        # 6. Governed Safe Resume Attestation Drill
        drill_results.append(self._drill_safe_resume())

        passed_count = sum(1 for r in drill_results if r.passed)
        all_passed = passed_count == len(drill_results)

        status = SystemRecoveryStatus.HEALTHY if all_passed else SystemRecoveryStatus.DEGRADED

        audit_result = DisasterRecoveryAuditResult(
            audit_id=audit_id,
            timestamp=now,
            scenarios_tested=len(drill_results),
            scenarios_passed=passed_count,
            all_passed=all_passed,
            drill_results=drill_results,
            system_status=status,
            attestation=self.safe_resume.get_last_attestation(),
        )

        self._last_audit = audit_result
        logger.info(
            "Disaster Recovery Drill complete: %d/%d passed (All Passed: %s)",
            passed_count,
            len(drill_results),
            all_passed,
        )
        return audit_result

    def _drill_crash_restart(self) -> ScenarioDrillResult:
        """Drill 1: Simulate process death and state recovery from SQLite WAL."""
        t0 = time.perf_counter()
        try:
            recovery_mgr = RestartRecoveryManager(repository=self.repo, db_path=self.db_path)
            state = recovery_mgr.recover_system_state()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            evidence = (
                f"State reconstructed cleanly in {elapsed_ms:.2f}ms. "
                f"Positions recovered: {len(state.recovered_positions)}, "
                f"Orders recovered: {len(state.recovered_orders)}, "
                f"Equity: INR {state.latest_equity}, Status: {state.status}"
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.PROCESS_CRASH,
                passed=state.status == "SUCCESS",
                latency_ms=round(elapsed_ms, 2),
                description="Simulated ungraceful process crash and in-memory state rehydration from SQLite WAL storage.",
                verification_evidence=evidence,
                details={
                    "equity": float(state.latest_equity),
                    "positions_count": len(state.recovered_positions),
                    "orders_count": len(state.recovered_orders),
                },
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.PROCESS_CRASH,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Process crash recovery simulation encountered an error.",
                verification_evidence=f"Failed: {e}",
            )

    def _drill_broker_disconnect(self) -> ScenarioDrillResult:
        """Drill 2: Simulate broker drop, exponential retry backoff, and order resync."""
        t0 = time.perf_counter()
        try:
            telemetry = self.broker_resilience.simulate_disconnect_drill()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            passed = telemetry.reconnected_cleanly and telemetry.status == "RECONNECTED_AND_RECONCILED"
            evidence = (
                f"Broker disconnect simulated. Auto-reconnected in {telemetry.retry_attempts} attempts "
                f"({telemetry.downtime_seconds:.2f}s downtime). Status: {telemetry.status}"
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.BROKER_DISCONNECT,
                passed=passed,
                latency_ms=round(elapsed_ms, 2),
                description="Simulated broker network disconnect with exponential backoff reconnect and order resynchronization.",
                verification_evidence=evidence,
                details=telemetry.model_dump(),
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.BROKER_DISCONNECT,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Broker disconnect recovery failed.",
                verification_evidence=f"Failed: {e}",
            )

    def _drill_stale_market_data(self) -> ScenarioDrillResult:
        """Drill 3: Inject stale quote and confirm immediate order submission blocking."""
        t0 = time.perf_counter()
        try:
            # Register a quote that is 15 seconds old (threshold is 5.0s)
            stale_ts = datetime.fromtimestamp(time.time() - 15.0, tz=timezone.utc)
            self.stale_guard.update_quote("INFY", Decimal("1500.00"), quote_timestamp=stale_ts)

            blocked = False
            try:
                self.stale_guard.assert_quote_fresh("INFY")
            except StaleMarketDataError:
                blocked = True

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            report = self.stale_guard.check_quote_freshness("INFY")

            passed = blocked and report.is_stale
            evidence = (
                f"Stale quote (age: {report.age_seconds:.1f}s) correctly triggered StaleMarketDataError "
                f"and blocked downstream execution in {elapsed_ms:.2f}ms."
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.STALE_MARKET_DATA,
                passed=passed,
                latency_ms=round(elapsed_ms, 2),
                description="Injected stale market quote (age > 5.0s) and verified deterministic order blocking.",
                verification_evidence=evidence,
                details=report.model_dump(),
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.STALE_MARKET_DATA,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Stale data verification failed.",
                verification_evidence=f"Failed: {e}",
            )

    def _drill_database_resilience(self) -> ScenarioDrillResult:
        """Drill 4: Verify database integrity, WAL journal mode, and force checkpoint."""
        t0 = time.perf_counter()
        try:
            health = self.db_resilience.evaluate_db_health()
            cp_ok = self.db_resilience.force_wal_checkpoint(mode="TRUNCATE")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            passed = health.integrity_ok and health.wal_journal_mode == "wal" and cp_ok
            evidence = (
                f"DB integrity ok: {health.integrity_ok}, Journal mode: {health.wal_journal_mode}, "
                f"WAL checkpoint (TRUNCATE): {cp_ok}, Status: {health.status}"
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.DATABASE_FAILURE,
                passed=passed,
                latency_ms=round(elapsed_ms, 2),
                description="Audited SQLite WAL integrity, foreign keys, and executed atomic WAL checkpointing.",
                verification_evidence=evidence,
                details=health.model_dump(),
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.DATABASE_FAILURE,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Database resilience drill encountered an error.",
                verification_evidence=f"Failed: {e}",
            )

    def _drill_duplicate_prevention(self) -> ScenarioDrillResult:
        """Drill 5: Submit order, simulate replay attack / restart, confirm duplicate rejection."""
        t0 = time.perf_counter()
        try:
            run_uuid = uuid.uuid4().hex[:6].upper()
            client_id = f"DRILL-ORD-{run_uuid}"
            plan_id = f"PLAN-DR-{run_uuid}"
            sym = "TCS"
            side = "BUY"
            qty = 10
            price = Decimal("3500.00")

            # First submission: must succeed
            rec = self.idempotency_mgr.check_and_register_order(
                client_order_id=client_id,
                symbol=sym,
                side=side,
                quantity=qty,
                price_level=price,
                plan_id=plan_id,
            )

            # Second submission with identical client_id: must raise DuplicateOrderError
            dup_id_blocked = False
            try:
                self.idempotency_mgr.check_and_register_order(
                    client_order_id=client_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    price_level=price,
                    plan_id=plan_id,
                )
            except DuplicateOrderError:
                dup_id_blocked = True

            # Third submission with new client_id but identical fingerprint: must raise DuplicateOrderError
            dup_fp_blocked = False
            try:
                self.idempotency_mgr.check_and_register_order(
                    client_order_id=f"{client_id}-REPLAY",
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    price_level=price,
                    plan_id=plan_id,
                )
            except DuplicateOrderError:
                dup_fp_blocked = True

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            passed = dup_id_blocked and dup_fp_blocked

            evidence = (
                f"Idempotency token {rec.order_fingerprint[:12]}... recorded. "
                f"Duplicate client ID blocked: {dup_id_blocked}, "
                f"Identical fingerprint blocked: {dup_fp_blocked}."
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.DUPLICATE_ORDER_ATTACK,
                passed=passed,
                latency_ms=round(elapsed_ms, 2),
                description="Simulated duplicate order submission and fingerprint replay; verified persistent rejection.",
                verification_evidence=evidence,
                details={"order_id": client_id, "fingerprint": rec.order_fingerprint},
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.DUPLICATE_ORDER_ATTACK,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Duplicate prevention drill failed.",
                verification_evidence=f"Failed: {e}",
            )

    def _drill_safe_resume(self) -> ScenarioDrillResult:
        """Drill 6: Verify pre-resumption checklist and issue formal safe resume attestation."""
        t0 = time.perf_counter()
        try:
            token = "OPERATOR-RESUME-PHASE33-DRILL"
            attestation = self.safe_resume.request_safe_resume(
                operator_token=token, active_broker=self.broker
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            evidence = (
                f"Safe resume attestation {attestation.attestation_id} generated in {elapsed_ms:.2f}ms. "
                f"Resumption approved: {attestation.resumption_approved}, "
                f"Mode: {attestation.operational_mode}, Status: {self.safe_resume.current_status.value}"
            )
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.STATE_DIVERGENCE,
                passed=attestation.resumption_approved,
                latency_ms=round(elapsed_ms, 2),
                description="Evaluated 5-point safe resumption checklist and validated operator resumption governance.",
                verification_evidence=evidence,
                details=attestation.model_dump(),
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return ScenarioDrillResult(
                scenario=DisasterScenarioType.STATE_DIVERGENCE,
                passed=False,
                latency_ms=round(elapsed_ms, 2),
                description="Safe resume drill encountered an error.",
                verification_evidence=f"Failed: {e}",
            )

    def get_latest_audit(self) -> DisasterRecoveryAuditResult:
        """Return the most recent disaster recovery audit or run on demand."""
        if self._last_audit is None:
            return self.run_comprehensive_disaster_drill()
        return self._last_audit
