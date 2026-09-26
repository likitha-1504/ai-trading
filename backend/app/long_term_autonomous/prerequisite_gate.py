"""Multi-Phase Prerequisite Gate for Phase 37 Long-Term Autonomous System.

Rigidly validates that all earlier foundational phases (21 through 36) are verified,
active, and intact before permitting broader long-term autonomous operations:
- Phase 25: Operational Health & Database Integrity
- Phase 29: Controlled Capital Scaling & Hard Limits
- Phase 31: Multi-Strategy Portfolio & Concentration Engine
- Phase 33: Disaster Recovery & State Rehydration
- Phase 34: Security Hardening & Tamper-Evident Audit Logging
- Phase 35: Research Sandbox & Controlled Promotion Protocol
- Phase 36: AI Council Evolution & Deterministic Decoupling
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.capital.config import CapitalConfig, RiskLimitsConfig
from app.capital_scaling.scaling_manager import ControlledCapitalScalingManager
from app.core.config import settings
from app.council_evolution.independence_guard import CouncilIndependenceGuard
from app.db.connection import get_connection, get_db_path
from app.db.recovery import RestartRecoveryManager
from app.db.repository import DatabaseRepository
from app.long_term_autonomous.models import (
    PrerequisiteDimension,
    PrerequisiteNotMetError,
    PrerequisitePhaseAudit,
)
from app.portfolio.models import ConcentrationLimits
from app.sandbox.promotion_gate import ExplicitPromotionGate
from app.security.rbac import AccessControlManager
from app.security.tamper_log import TamperEvidentAuditLogger

logger = logging.getLogger(__name__)


class LongTermPrerequisiteGate:
    """Verifies that all earlier phases are certified prior to long-term automation."""

    def __init__(
        self,
        db_path: str | None = None,
        audit_logger: TamperEvidentAuditLogger | None = None,
    ) -> None:
        self.db_path = get_db_path(db_path)
        self.audit_logger = audit_logger or TamperEvidentAuditLogger(self.db_path)

    def audit_prerequisites(self, strict: bool = False) -> PrerequisitePhaseAudit:
        """Executes systematic multi-phase audit across all 7 prerequisite dimensions."""
        dimension_results: dict[PrerequisiteDimension, bool] = {}
        details: dict[str, str] = {}

        # 1. Dimension 1: Operational Health & WAL Mode (Phase 25)
        try:
            with get_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode;")
                journal_mode = cursor.fetchone()[0].upper()
                cursor.execute("PRAGMA integrity_check;")
                integrity = cursor.fetchone()[0].lower()
            dim_1_pass = (journal_mode == "WAL") and (integrity == "ok")
            dimension_results[PrerequisiteDimension.OPS_PREFLIGHT] = dim_1_pass
            details[PrerequisiteDimension.OPS_PREFLIGHT.value] = (
                f"Journal: {journal_mode}, Integrity: {integrity}"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.OPS_PREFLIGHT] = False
            details[PrerequisiteDimension.OPS_PREFLIGHT.value] = f"Error: {e}"

        # 2. Dimension 2: Capital Scaling Limits & Paper Trading Hard Lock (Phase 29)
        try:
            scaling_mgr = ControlledCapitalScalingManager(initial_cash_inr=100.0)
            cap_cfg = CapitalConfig()
            risk_cfg = RiskLimitsConfig()
            is_paper = getattr(settings, "IS_PAPER_TRADING", True)
            initial_cap_ok = cap_cfg.starting_capital <= Decimal("100.00")
            risk_ok = risk_cfg.max_loss_per_trade_pct <= Decimal("0.015")
            dim_2_pass = is_paper and initial_cap_ok and risk_ok and (scaling_mgr.active_stage is not None)
            dimension_results[PrerequisiteDimension.CAPITAL_LIMITS] = dim_2_pass
            details[PrerequisiteDimension.CAPITAL_LIMITS.value] = (
                f"Paper: {is_paper}, InitialCap: {cap_cfg.starting_capital} INR, Risk: {float(risk_cfg.max_loss_per_trade_pct) * 100}%"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.CAPITAL_LIMITS] = False
            details[PrerequisiteDimension.CAPITAL_LIMITS.value] = f"Error: {e}"

        # 3. Dimension 3: Multi-Strategy Portfolio & Concentration Engine (Phase 31)
        try:
            limits = ConcentrationLimits()
            limits_ok = (
                limits.max_gross_exposure_pct <= Decimal("100.00")
                and limits.max_single_strategy_pct <= Decimal("60.00")
                and limits.max_single_symbol_pct <= Decimal("40.00")
                and limits.max_single_sector_pct <= Decimal("50.00")
            )
            dimension_results[PrerequisiteDimension.PORTFOLIO_CONCENTRATION] = limits_ok
            details[PrerequisiteDimension.PORTFOLIO_CONCENTRATION.value] = (
                f"Gross: {limits.max_gross_exposure_pct}%, Strat: {limits.max_single_strategy_pct}%, "
                f"Sym: {limits.max_single_symbol_pct}%, Sec: {limits.max_single_sector_pct}%"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.PORTFOLIO_CONCENTRATION] = False
            details[PrerequisiteDimension.PORTFOLIO_CONCENTRATION.value] = f"Error: {e}"

        # 4. Dimension 4: Disaster Recovery & State Rehydration (Phase 33)
        try:
            repo = DatabaseRepository(self.db_path)
            rec_mgr = RestartRecoveryManager(repository=repo, db_path=self.db_path)
            rec_state = rec_mgr.recover_system_state()
            dim_4_pass = rec_state is not None and hasattr(rec_state, "recovered_positions")
            dimension_results[PrerequisiteDimension.DISASTER_RECOVERY] = dim_4_pass
            details[PrerequisiteDimension.DISASTER_RECOVERY.value] = (
                f"Rehydrated positions: {len(rec_state.recovered_positions)}, Capital: {rec_state.latest_equity} INR"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.DISASTER_RECOVERY] = False
            details[PrerequisiteDimension.DISASTER_RECOVERY.value] = f"Error: {e}"

        # 5. Dimension 5: Security Hardening & Tamper-Evident Ledger (Phase 34)
        try:
            rbac_finding = AccessControlManager.audit_rbac_matrix()
            ledger_verified, msg, count = self.audit_logger.verify_chain_integrity()
            dim_5_pass = rbac_finding.passed and ledger_verified
            dimension_results[PrerequisiteDimension.SECURITY_LEAST_PRIVILEGE] = dim_5_pass
            details[PrerequisiteDimension.SECURITY_LEAST_PRIVILEGE.value] = (
                f"RBAC valid: {rbac_finding.passed}, Ledger verified: {ledger_verified} ({count} entries)"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.SECURITY_LEAST_PRIVILEGE] = False
            details[PrerequisiteDimension.SECURITY_LEAST_PRIVILEGE.value] = f"Error: {e}"

        # 6. Dimension 6: Research Sandbox & Promotion Hurdles (Phase 35)
        try:
            promo_gate = ExplicitPromotionGate(audit_logger=self.audit_logger)
            hurdles = promo_gate.hurdles
            hurdles_ok = (
                hurdles.min_trades >= 20
                and hurdles.min_win_rate >= 0.50
                and hurdles.min_profit_factor >= 1.30
                and hurdles.min_sharpe_ratio >= 1.20
                and hurdles.max_drawdown_pct <= 5.00
            )
            dimension_results[PrerequisiteDimension.RESEARCH_SANDBOX] = hurdles_ok
            details[PrerequisiteDimension.RESEARCH_SANDBOX.value] = (
                f"MinTrades: {hurdles.min_trades}, MinWinRate: {hurdles.min_win_rate:.0%}, "
                f"MaxDD: {hurdles.max_drawdown_pct}%"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.RESEARCH_SANDBOX] = False
            details[PrerequisiteDimension.RESEARCH_SANDBOX.value] = f"Error: {e}"

        # 7. Dimension 7: AI Council Justification & Deterministic Decoupling (Phase 36)
        try:
            indep_guard = CouncilIndependenceGuard()
            attestation = indep_guard.audit_complete_independence()
            dim_7_pass = (
                attestation.trade_gate_zero_llm_dependency
                and attestation.position_watcher_zero_llm_dependency
                and attestation.models_offline_blackout_tested
                and attestation.unanimous_ai_buy_override_blocked
                and attestation.position_watcher_sub_50ms_sla
            )
            dimension_results[PrerequisiteDimension.AI_COUNCIL_DECOUPLING] = dim_7_pass
            details[PrerequisiteDimension.AI_COUNCIL_DECOUPLING.value] = (
                f"Decoupled: {dim_7_pass}, Latency: {attestation.realized_watcher_latency_us:.1f}us"
            )
        except Exception as e:  # noqa: BLE001
            dimension_results[PrerequisiteDimension.AI_COUNCIL_DECOUPLING] = False
            details[PrerequisiteDimension.AI_COUNCIL_DECOUPLING.value] = f"Error: {e}"

        # Evaluate complete pass
        is_all_passed = all(dimension_results.values())
        audit = PrerequisitePhaseAudit(
            audit_id=f"PRE-AUDIT-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            is_all_passed=is_all_passed,
            dimension_results=dimension_results,
            details=details,
        )

        # Log audit entry into tamper-evident ledger
        self.audit_logger.log_event(
            event_type="PREREQUISITE_PHASE_AUDIT",
            operator_id="SYSTEM_ORCHESTRATOR",
            role="ADMIN",
            action="AUDIT_PREREQUISITES",
            resource="PHASE_37_LONG_TERM_SYSTEM",
            details={
                "audit_id": audit.audit_id,
                "is_all_passed": is_all_passed,
                "dimension_results": {k.value: v for k, v in dimension_results.items()},
            },
        )

        if strict and not is_all_passed:
            failed_dims = [k.value for k, v in dimension_results.items() if not v]
            raise PrerequisiteNotMetError(
                f"Cannot proceed with Long-Term Autonomous System: Failed prerequisite dimensions: {failed_dims}"
            )

        return audit
