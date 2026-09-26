"""Unified Master Security Auditor for Phase 34 Security Hardening.

Orchestrates automated evaluation across all 8 mandatory security dimensions:
1. Secrets Sanitization
2. Authentication (HMAC-SHA256)
3. Authorization & RBAC
4. Dependency Supply Chain
5. Network Exposure & Security Headers
6. Tamper-Evident Audit Logging
7. Configuration Integrity
8. Broker Permissions & Scope Isolation
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.broker_base import BrokerAdapter
from app.adapters.paper_adapter import PaperAdapter
from app.security.auth import AuthenticationManager
from app.security.broker_scope import BrokerScopeAuditor
from app.security.config_integrity import ConfigIntegrityValidator
from app.security.dependency_auditor import DependencyAuditor
from app.security.models import (
    SecurityFinding,
    SecurityHardeningReport,
)
from app.security.network_guard import NetworkSecurityAuditor
from app.security.rbac import AccessControlManager
from app.security.secrets_scanner import SecretsScanner
from app.security.tamper_log import TamperEvidentAuditLogger

logger = logging.getLogger(__name__)


class SecurityHardeningAuditor:
    """Master orchestrator executing complete 8-dimension security hardening audit."""

    def __init__(
        self,
        project_root: str | None = None,
        db_path: str | None = None,
        broker_adapter: BrokerAdapter | None = None,
    ) -> None:
        self.root_dir = Path(project_root or ".").resolve()
        self.db_path = db_path
        self.broker = broker_adapter or PaperAdapter()

        # Initialize sub-auditors
        self.secrets_scanner = SecretsScanner(root_dir=str(self.root_dir))
        self.auth_manager = AuthenticationManager()
        self.access_control = AccessControlManager()
        self.dependency_auditor = DependencyAuditor(root_dir=str(self.root_dir))
        self.network_auditor = NetworkSecurityAuditor()
        self.tamper_logger = TamperEvidentAuditLogger(db_path=self.db_path)
        self.config_validator = ConfigIntegrityValidator()
        self.broker_auditor = BrokerScopeAuditor()

        self._last_report: SecurityHardeningReport | None = None

    def run_security_audit(self) -> SecurityHardeningReport:
        """Executes automated audit across all 8 security dimensions."""
        now = datetime.now(timezone.utc)
        audit_id = f"SEC-AUDIT-{uuid.uuid4().hex[:8].upper()}"
        findings: list[SecurityFinding] = []

        logger.info("Initiating Phase 34 Security Hardening Audit %s...", audit_id)

        # 1. Secrets Sanitization
        findings.extend(self.secrets_scanner.run_full_secrets_audit())

        # 2. Authentication
        findings.append(self.auth_manager.audit_authentication())

        # 3. Authorization & RBAC
        findings.append(self.access_control.audit_rbac_matrix())

        # 4. Dependency Vulnerabilities & Pinning
        findings.append(self.dependency_auditor.audit_dependencies())

        # 5. Network Exposure & Security Headers
        findings.append(self.network_auditor.audit_security_headers())
        findings.append(self.network_auditor.audit_network_exposure())

        # 6. Tamper-Evident Audit Logging
        findings.append(self.tamper_logger.audit_tamper_log())

        # 7. Configuration Integrity
        findings.append(self.config_validator.audit_configuration())

        # 8. Broker Permissions & Scope Isolation
        findings.append(self.broker_auditor.audit_broker_permissions(broker_adapter=self.broker))

        # Evaluate overall results
        all_passed = all(f.passed for f in findings)
        unique_dims = {f.dimension for f in findings}
        passed_dims = sum(1 for d in unique_dims if all(f.passed for f in findings if f.dimension == d))

        chain_ok = any(f.dimension.value == "AUDIT_LOG_TAMPER_EVIDENT" and f.passed for f in findings)
        cfg_ok = any(f.dimension.value == "CONFIGURATION_INTEGRITY" and f.passed for f in findings)
        secrets_ok = all(f.passed for f in findings if f.dimension.value == "SECRETS_SANITIZATION")
        broker_ok = any(f.dimension.value == "BROKER_PERMISSIONS" and f.passed for f in findings)

        report = SecurityHardeningReport(
            audit_id=audit_id,
            timestamp=now,
            total_dimensions=len(unique_dims),
            passed_dimensions=passed_dims,
            all_passed=all_passed,
            findings=findings,
            tamper_log_chain_valid=chain_ok,
            config_integrity_valid=cfg_ok,
            secrets_clean=secrets_ok,
            broker_scopes_least_privilege=broker_ok,
            overall_status="HARDENED_AND_VERIFIED" if all_passed else "REMEDIATION_REQUIRED",
        )

        self._last_report = report

        # Log completion to tamper-evident audit ledger
        self.tamper_logger.log_event(
            event_type="SECURITY_AUDIT_COMPLETED",
            operator_id="SECURITY_AUDITOR",
            role="ADMIN",
            action="RUN_SECURITY_AUDIT",
            resource=audit_id,
            details={
                "all_passed": all_passed,
                "passed_dimensions": passed_dims,
                "total_dimensions": len(unique_dims),
            },
        )

        return report

    def get_latest_report(self) -> SecurityHardeningReport:
        """Returns the most recent report or runs on demand."""
        if self._last_report is None:
            return self.run_security_audit()
        return self._last_report
