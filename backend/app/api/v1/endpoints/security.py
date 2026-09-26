"""FastAPI Endpoints for Phase 34 Security Hardening and Cryptographic Governance."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.security.models import (
    ConfigIntegrityReport,
    SecurityFinding,
    SecurityHardeningReport,
    UserRole,
)
from app.security.security_auditor import SecurityHardeningAuditor

router = APIRouter(prefix="/security", tags=["Security Hardening"])

_auditor = SecurityHardeningAuditor()


@router.get("/audit", response_model=SecurityHardeningReport)
def run_security_hardening_audit() -> SecurityHardeningReport:
    """Executes on-demand audit across all 8 mandatory security hardening dimensions."""
    return _auditor.run_security_audit()


@router.post("/verify-tamper-log", response_model=dict[str, Any])
def verify_tamper_evident_audit_log() -> dict[str, Any]:
    """Cryptographically verifies every entry in the SHA-256 hash-chained security audit log."""
    valid, message, count = _auditor.tamper_logger.verify_chain_integrity()
    return {
        "chain_valid": valid,
        "message": message,
        "verified_entries_count": count,
    }


@router.post("/scan-secrets", response_model=list[SecurityFinding])
def scan_project_for_secrets() -> list[SecurityFinding]:
    """Scans repository source code and .gitignore to verify zero hardcoded secrets."""
    return _auditor.secrets_scanner.run_full_secrets_audit()


@router.post("/issue-token", response_model=dict[str, Any])
def issue_operator_token(
    operator_id: str = Query("OPERATOR_01", description="Operator identity"),
    role: UserRole = Query(UserRole.OPERATOR, description="Requested access role tier"),
    ttl_seconds: int = Query(3600, ge=60, le=86400, description="Token lifetime in seconds"),
) -> dict[str, Any]:
    """Generates an HMAC-SHA256 authenticated bearer token for authorized operations."""
    token = _auditor.auth_manager.generate_token(
        operator_id=operator_id,
        role=role,
        ttl_seconds=ttl_seconds,
    )
    return {
        "operator_id": operator_id,
        "role": role.value,
        "token": token,
        "expires_in_seconds": ttl_seconds,
    }


@router.get("/config-integrity", response_model=ConfigIntegrityReport)
def check_configuration_integrity() -> ConfigIntegrityReport:
    """Evaluates system configuration parameters against immutable safety caps."""
    return _auditor.config_validator.evaluate_config_integrity()
