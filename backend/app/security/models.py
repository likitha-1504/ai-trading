"""Security Hardening Data Models, Enums, and Telemetry Schemas for Phase 34.

Covers:
- Secrets Sanitization & Detection
- HMAC Authentication & Tokens
- Role-Based Access Control (RBAC)
- Dependency Vulnerabilities
- Network Exposure & HTTP Security Headers
- Cryptographic Tamper-Evident Audit Logging
- Configuration Integrity & Hard Cap Enforcement
- Broker Permissions & Scope Auditing
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Access control tiers following principle of least privilege."""

    VIEWER = "VIEWER"        # Read-only access to telemetry, dashboard, logs
    OPERATOR = "OPERATOR"    # Scans, paper trades, backtests, models
    ADMIN = "ADMIN"          # Emergency halt, safe resume, secret rotation, config changes


class SecurityAuditDimension(str, Enum):
    """The 8 mandatory security audit dimensions for Phase 34."""

    SECRETS_SANITIZATION = "SECRETS_SANITIZATION"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION_RBAC = "AUTHORIZATION_RBAC"
    DEPENDENCY_VULNERABILITY = "DEPENDENCY_VULNERABILITY"
    NETWORK_EXPOSURE = "NETWORK_EXPOSURE"
    AUDIT_LOG_TAMPER_EVIDENT = "AUDIT_LOG_TAMPER_EVIDENT"
    CONFIGURATION_INTEGRITY = "CONFIGURATION_INTEGRITY"
    BROKER_PERMISSIONS = "BROKER_PERMISSIONS"


class SecuritySeverity(str, Enum):
    """Severity ratings for security findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityFinding(BaseModel):
    """Individual security evaluation finding."""

    dimension: SecurityAuditDimension
    severity: SecuritySeverity
    title: str
    description: str
    passed: bool
    evidence: str
    remediation: str | None = None


class OperatorTokenPayload(BaseModel):
    """Cryptographically signed operator authorization token payload."""

    operator_id: str
    role: UserRole
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)
    nonce: str


class AuditLogEntry(BaseModel):
    """Immutable, tamper-evident security audit record in cryptographic hash chain."""

    entry_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    operator_id: str
    role: str
    action: str
    resource: str
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    record_hash: str


class ConfigIntegrityReport(BaseModel):
    """Telemetry report assessing configuration integrity against hard immutable caps."""

    config_checksum: str
    initial_capital_capped: bool
    autonomous_capital_capped: bool
    risk_limit_capped: bool
    drawdown_limit_capped: bool
    paper_trading_locked: bool
    is_tamper_free: bool
    violations: list[str] = Field(default_factory=list)


class SecurityHardeningReport(BaseModel):
    """Comprehensive summary of all Phase 34 security hardening audits."""

    audit_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_dimensions: int = 8
    passed_dimensions: int
    all_passed: bool
    findings: list[SecurityFinding] = Field(default_factory=list)
    tamper_log_chain_valid: bool
    config_integrity_valid: bool
    secrets_clean: bool
    broker_scopes_least_privilege: bool
    overall_status: str
