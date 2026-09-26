"""Security Hardening, Cryptographic Audit Ledger & Least-Privilege Governance Package."""

from app.security.auth import AuthenticationManager
from app.security.broker_scope import BrokerScopeAuditor
from app.security.config_integrity import (
    ConfigIntegrityValidator,
    ConfigurationTamperError,
)
from app.security.dependency_auditor import DependencyAuditor
from app.security.models import (
    AuditLogEntry,
    ConfigIntegrityReport,
    OperatorTokenPayload,
    SecurityAuditDimension,
    SecurityFinding,
    SecurityHardeningReport,
    SecuritySeverity,
    UserRole,
)
from app.security.network_guard import (
    NetworkSecurityAuditor,
    SecurityHeadersMiddleware,
)
from app.security.rbac import (
    AccessControlManager,
    has_sufficient_role,
    require_role,
)
from app.security.secrets_scanner import SecretsScanner, mask_secret
from app.security.security_auditor import SecurityHardeningAuditor
from app.security.tamper_log import TamperEvidentAuditLogger

__all__ = [
    "AccessControlManager",
    "AuditLogEntry",
    "AuthenticationManager",
    "BrokerScopeAuditor",
    "ConfigIntegrityReport",
    "ConfigIntegrityValidator",
    "ConfigurationTamperError",
    "DependencyAuditor",
    "NetworkSecurityAuditor",
    "OperatorTokenPayload",
    "SecretsScanner",
    "SecurityAuditDimension",
    "SecurityFinding",
    "SecurityHardeningAuditor",
    "SecurityHardeningReport",
    "SecurityHeadersMiddleware",
    "SecuritySeverity",
    "TamperEvidentAuditLogger",
    "UserRole",
    "has_sufficient_role",
    "mask_secret",
    "require_role",
]
