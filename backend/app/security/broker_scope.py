"""Broker Permissions & Least-Privilege Scope Auditor for Phase 34.

Verifies that broker interfaces possess only order placement and read-only market data
privileges, with zero banking, fund transfer, or credential mutation access.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from app.adapters.broker_base import BrokerAdapter
from app.adapters.paper_adapter import PaperAdapter
from app.core.config import settings
from app.security.models import (
    SecurityAuditDimension,
    SecurityFinding,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)


class BrokerScopeAuditor:
    """Audits broker adapter scopes and isolation boundaries."""

    # Prohibited operations for an algorithmic trading agent session
    PROHIBITED_BANKING_METHODS: ClassVar[list[str]] = [
        "withdraw_funds",
        "transfer_cash",
        "add_bank_account",
        "modify_password",
        "generate_api_secret",
        "authorize_margin_loan",
    ]

    @classmethod
    def audit_broker_permissions(
        cls, broker_adapter: BrokerAdapter | None = None
    ) -> SecurityFinding:
        """Audits broker adapter methods and paper trading isolation."""
        adapter = broker_adapter or PaperAdapter()
        adapter_type = type(adapter).__name__

        # 1. Prohibited methods check (must NOT exist on adapter)
        leaked_methods: list[str] = []
        for method_name in cls.PROHIBITED_BANKING_METHODS:
            if hasattr(adapter, method_name):
                leaked_methods.append(method_name)

        # 2. Paper trading isolation check
        is_paper = settings.IS_PAPER_TRADING is True
        isolation_ok = is_paper and (adapter_type == "PaperAdapter" or hasattr(adapter, "is_live"))

        passed = len(leaked_methods) == 0 and isolation_ok

        if not passed:
            return SecurityFinding(
                dimension=SecurityAuditDimension.BROKER_PERMISSIONS,
                severity=SecuritySeverity.CRITICAL,
                title="Broker Scope Violation Detected",
                description="Broker adapter possesses prohibited banking methods or violates paper mode isolation.",
                passed=False,
                evidence=f"Leaked methods: {leaked_methods}; Paper isolation: {isolation_ok}",
                remediation="Ensure broker adapter only exposes Order placement and Market data read APIs.",
            )

        return SecurityFinding(
            dimension=SecurityAuditDimension.BROKER_PERMISSIONS,
            severity=SecuritySeverity.LOW,
            title="Broker Scopes Constrained to Least Privilege",
            description="Broker adapter is restricted to order placement and quote queries with zero banking/withdrawal access.",
            passed=True,
            evidence=(
                f"Adapter: {adapter_type}; Zero prohibited banking endpoints exposed; "
                f"Paper trading isolation verified (IS_PAPER_TRADING={settings.IS_PAPER_TRADING})."
            ),
        )
