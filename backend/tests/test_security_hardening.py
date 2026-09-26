"""Comprehensive Test Suite for Phase 34 Security Hardening and Cryptographic Governance.

Tests:
- Secrets Sanitization, Masking, and .gitignore Rules
- HMAC-SHA256 Token Authentication, Expiration, and Revocation
- Role-Based Access Control (RBAC) Least Privilege Hierarchy
- Cryptographic Tamper-Evident Audit Logging & Hash Chain Integrity
- Configuration Integrity & Inviolable Hard Caps Enforcement
- Dependency Pinning & Supply Chain Auditing
- Network Exposure & OWASP Security Headers
- Broker Scope & Least Privilege Isolation
- FastAPI Security REST Endpoints
- Operational CLI Security Runner Execution
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.paper_adapter import PaperAdapter
from app.core.config import settings
from app.db.connection import init_db
from app.main import app
from app.security.auth import AuthenticationManager
from app.security.broker_scope import BrokerScopeAuditor
from app.security.config_integrity import (
    ConfigIntegrityValidator,
    ConfigurationTamperError,
)
from app.security.dependency_auditor import DependencyAuditor
from app.security.models import (
    SecurityAuditDimension,
    UserRole,
)
from app.security.network_guard import NetworkSecurityAuditor
from app.security.rbac import AccessControlManager, has_sufficient_role
from app.security.secrets_scanner import SecretsScanner, mask_secret
from app.security.security_auditor import SecurityHardeningAuditor
from app.security.tamper_log import TamperEvidentAuditLogger


@pytest.fixture
def temp_db():
    """Provides an isolated SQLite database for security audit logging tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    for ext in ["", "-wal", "-shm"]:
        p = f"{path}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# =========================================================================
# 1. Secrets Sanitization & Masking Tests
# =========================================================================

def test_mask_secret_utility() -> None:
    assert mask_secret("sk-1234567890abcdef1234567890abcdef") == "sk-***REDACTED***def"
    assert mask_secret("short") == "***REDACTED***"
    assert mask_secret("") == ""


def test_secrets_scanner_gitignore_audit() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    scanner = SecretsScanner(root_dir=str(project_root))
    finding = scanner.audit_gitignore()
    assert finding.passed is True
    assert finding.dimension == SecurityAuditDimension.SECRETS_SANITIZATION


def test_secrets_scanner_source_scan() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    scanner = SecretsScanner(root_dir=str(project_root))
    findings = scanner.scan_source_code()
    assert len(findings) >= 1
    assert all(f.passed for f in findings)


# =========================================================================
# 2. HMAC Authentication Tests
# =========================================================================

def test_auth_manager_token_issuance_and_verification() -> None:
    mgr = AuthenticationManager()
    token = mgr.generate_token(operator_id="OP_TEST", role=UserRole.OPERATOR, ttl_seconds=300)
    assert token.startswith("OPTOK.")

    valid, payload, _msg = mgr.verify_token(token)
    assert valid is True
    assert payload is not None
    assert payload.operator_id == "OP_TEST"
    assert payload.role == UserRole.OPERATOR


def test_auth_manager_tampered_signature_rejected() -> None:
    mgr = AuthenticationManager()
    token = mgr.generate_token(operator_id="OP_TEST", role=UserRole.ADMIN, ttl_seconds=300)
    parts = token.split(".")
    tampered_sig = parts[2][:-4] + ("0000" if parts[2][-4:] != "0000" else "1111")
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    valid, payload, msg = mgr.verify_token(tampered_token)
    assert valid is False
    assert payload is None
    assert "Invalid cryptographic HMAC signature" in msg


def test_auth_manager_token_revocation() -> None:
    mgr = AuthenticationManager()
    token = mgr.generate_token(operator_id="OP_REVOKE", role=UserRole.VIEWER)
    valid, _, _ = mgr.verify_token(token)
    assert valid is True

    mgr.revoke_token(token)
    valid_after, _, msg = mgr.verify_token(token)
    assert valid_after is False
    assert "revoked" in msg


def test_auth_manager_expired_token() -> None:
    mgr = AuthenticationManager()
    # Issue token with negative TTL
    token = mgr.generate_token(operator_id="OP_EXP", role=UserRole.VIEWER, ttl_seconds=-60)
    valid, _, msg = mgr.verify_token(token)
    assert valid is False
    assert "expired" in msg


# =========================================================================
# 3. RBAC Hierarchy Tests
# =========================================================================

def test_rbac_hierarchy_rules() -> None:
    # Admin has all privileges
    assert has_sufficient_role(UserRole.ADMIN, UserRole.ADMIN) is True
    assert has_sufficient_role(UserRole.ADMIN, UserRole.OPERATOR) is True
    assert has_sufficient_role(UserRole.ADMIN, UserRole.VIEWER) is True

    # Operator has operator and viewer privileges
    assert has_sufficient_role(UserRole.OPERATOR, UserRole.ADMIN) is False
    assert has_sufficient_role(UserRole.OPERATOR, UserRole.OPERATOR) is True
    assert has_sufficient_role(UserRole.OPERATOR, UserRole.VIEWER) is True

    # Viewer only has viewer privileges
    assert has_sufficient_role(UserRole.VIEWER, UserRole.ADMIN) is False
    assert has_sufficient_role(UserRole.VIEWER, UserRole.OPERATOR) is False
    assert has_sufficient_role(UserRole.VIEWER, UserRole.VIEWER) is True


def test_rbac_audit_matrix() -> None:
    finding = AccessControlManager.audit_rbac_matrix()
    assert finding.passed is True
    assert finding.dimension == SecurityAuditDimension.AUTHORIZATION_RBAC


# =========================================================================
# 4. Tamper-Evident Audit Logging Tests
# =========================================================================

def test_tamper_log_append_and_verify(temp_db: str) -> None:
    logger = TamperEvidentAuditLogger(db_path=temp_db)

    # Append 3 sequential entries
    logger.log_event(
        event_type="AUTH_LOGIN",
        operator_id="OP_01",
        role="OPERATOR",
        action="LOGIN",
        resource="system",
        details={"ip": "127.0.0.1"},
    )
    logger.log_event(
        event_type="ORDER_SUBMIT",
        operator_id="OP_01",
        role="OPERATOR",
        action="SUBMIT_ORDER",
        resource="RELIANCE",
        details={"qty": 10},
    )
    logger.log_event(
        event_type="KILL_SWITCH",
        operator_id="ADMIN_01",
        role="ADMIN",
        action="TRIGGER_KILL_SWITCH",
        resource="system",
        details={"reason": "audit"},
    )

    valid, msg, count = logger.verify_chain_integrity()
    assert valid is True
    assert count == 3
    assert "verified" in msg


def test_tamper_log_detects_mutation(temp_db: str) -> None:
    import sqlite3

    logger = TamperEvidentAuditLogger(db_path=temp_db)
    logger.log_event(
        event_type="TEST_1",
        operator_id="OP_A",
        role="VIEWER",
        action="VIEW",
        resource="dashboard",
    )
    logger.log_event(
        event_type="TEST_2",
        operator_id="OP_B",
        role="OPERATOR",
        action="MODIFY",
        resource="strategy",
    )

    # Malicious direct modification of SQLite table
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "UPDATE security_audit_ledger SET action = 'MALICIOUS_TAMPER' WHERE id = 2"
    )
    conn.commit()
    conn.close()

    # Re-verify: must fail and detect tampering
    valid, msg, _ = logger.verify_chain_integrity()
    assert valid is False
    assert "tampering detected" in msg or "broken" in msg


# =========================================================================
# 5. Configuration Integrity & Hard Caps Tests
# =========================================================================

def test_config_integrity_valid_settings() -> None:
    report = ConfigIntegrityValidator.evaluate_config_integrity()
    assert report.is_tamper_free is True
    assert report.initial_capital_capped is True
    assert report.autonomous_capital_capped is True
    assert report.paper_trading_locked is True
    assert len(report.violations) == 0


def test_config_integrity_detects_tamper(monkeypatch) -> None:
    # Temporarily monkeypatch settings to violate initial capital
    monkeypatch.setattr(settings, "INITIAL_CAPITAL", 50000.0)

    report = ConfigIntegrityValidator.evaluate_config_integrity()
    assert report.is_tamper_free is False
    assert report.initial_capital_capped is False
    assert any("exceeds immutable cap" in v for v in report.violations)

    with pytest.raises(ConfigurationTamperError):
        ConfigIntegrityValidator.assert_config_integrity()


# =========================================================================
# 6. Dependency & Network Security Tests
# =========================================================================

def test_dependency_auditor() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    auditor = DependencyAuditor(root_dir=str(project_root))
    finding = auditor.audit_dependencies()
    assert finding.passed is True
    assert finding.dimension == SecurityAuditDimension.DEPENDENCY_VULNERABILITY


def test_network_security_headers() -> None:
    finding = NetworkSecurityAuditor.audit_security_headers()
    assert finding.passed is True
    assert finding.dimension == SecurityAuditDimension.NETWORK_EXPOSURE


def test_broker_scope_auditor() -> None:
    broker = PaperAdapter()
    finding = BrokerScopeAuditor.audit_broker_permissions(broker_adapter=broker)
    assert finding.passed is True
    assert finding.dimension == SecurityAuditDimension.BROKER_PERMISSIONS


# =========================================================================
# 7. Master Security Auditor Full Drill Test
# =========================================================================

def test_security_auditor_full_run(temp_db: str) -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    broker = PaperAdapter()
    auditor = SecurityHardeningAuditor(
        project_root=str(project_root),
        db_path=temp_db,
        broker_adapter=broker,
    )
    report = auditor.run_security_audit()

    assert report.total_dimensions == 8
    assert report.passed_dimensions == 8
    assert report.all_passed is True
    assert report.overall_status == "HARDENED_AND_VERIFIED"
    assert report.tamper_log_chain_valid is True
    assert report.config_integrity_valid is True
    assert report.secrets_clean is True
    assert report.broker_scopes_least_privilege is True


# =========================================================================
# 8. FastAPI REST Endpoints Tests
# =========================================================================

def test_fastapi_security_endpoints(client: TestClient) -> None:
    # 1. GET /audit
    res_audit = client.get("/api/v1/security/audit")
    assert res_audit.status_code == 200
    data_audit = res_audit.json()
    assert data_audit["all_passed"] is True
    assert data_audit["passed_dimensions"] == 8

    # 2. POST /verify-tamper-log
    res_verify = client.post("/api/v1/security/verify-tamper-log")
    assert res_verify.status_code == 200
    data_verify = res_verify.json()
    assert data_verify["chain_valid"] is True

    # 3. POST /scan-secrets
    res_scan = client.post("/api/v1/security/scan-secrets")
    assert res_scan.status_code == 200
    data_scan = res_scan.json()
    assert len(data_scan) >= 1

    # 4. POST /issue-token
    res_token = client.post(
        "/api/v1/security/issue-token?operator_id=TEST_API_OP&role=ADMIN"
    )
    assert res_token.status_code == 200
    data_token = res_token.json()
    assert "token" in data_token
    assert data_token["token"].startswith("OPTOK.")

    # 5. GET /config-integrity
    res_cfg = client.get("/api/v1/security/config-integrity")
    assert res_cfg.status_code == 200
    data_cfg = res_cfg.json()
    assert data_cfg["is_tamper_free"] is True


def test_owasp_security_headers_middleware(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert "default-src 'self'" in res.headers.get("content-security-policy", "")
    assert "strict-origin-when-cross-origin" in res.headers.get("referrer-policy", "")


# =========================================================================
# 9. CLI Runner Subprocess Test
# =========================================================================

def test_cli_runner_security_audit() -> None:
    cmd = [sys.executable, "backend/scripts/security_audit_runner.py", "--audit"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0
    assert "PHASE 34 COMPREHENSIVE SECURITY HARDENING AUDIT" in result.stdout
    assert "All Dimensions Passed:   True" in result.stdout
