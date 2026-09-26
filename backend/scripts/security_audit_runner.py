"""Operational CLI Runner & Audit Tool for Phase 34 Security Hardening.

Provides command-line execution of full 8-dimension security audit,
tamper-evident audit log verification, token issuance, and structured JSON output.

Usage:
    python backend/scripts/security_audit_runner.py [--audit] [--verify-tamper-log] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.security.models import SecurityHardeningReport, UserRole
from app.security.security_auditor import SecurityHardeningAuditor


def print_ascii_dashboard(report: SecurityHardeningReport) -> None:
    """Renders formatted operational dashboard for security hardening audit."""
    print("=" * 72)
    print("         PHASE 34 COMPREHENSIVE SECURITY HARDENING AUDIT         ")
    print("=" * 72)
    print(f"Audit ID:                {report.audit_id}")
    print(f"Timestamp:               {report.timestamp.isoformat()}")
    print(f"Dimensions Evaluated:    {report.total_dimensions}")
    print(f"Dimensions Passed:       {report.passed_dimensions}/{report.total_dimensions}")
    print(f"All Dimensions Passed:   {report.all_passed}")
    print(f"Tamper Log Chain Valid:  {report.tamper_log_chain_valid}")
    print(f"Config Integrity Valid:  {report.config_integrity_valid}")
    print(f"Secrets Sanitized Clean: {report.secrets_clean}")
    print(f"Broker Scopes Enforced:  {report.broker_scopes_least_privilege}")
    print(f"Overall Security Status: {report.overall_status}")
    print("-" * 72)
    print("MANDATORY 8-DIMENSION SECURITY AUDIT BREAKDOWN:")
    print("-" * 72)

    for i, finding in enumerate(report.findings, start=1):
        status_tag = "[PASS]" if finding.passed else "[FAIL]"
        print(f"{i:02d}. {status_tag} [{finding.severity.value:8s}] {finding.dimension.value}")
        print(f"    Title:    {finding.title}")
        print(f"    Evidence: {finding.evidence}")
        if not finding.passed and finding.remediation:
            print(f"    Remedy:   {finding.remediation}")
        print()

    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 34 Security Hardening Audit Tool")
    parser.add_argument("--audit", action="store_true", help="Execute complete 8-dimension security audit")
    parser.add_argument("--verify-tamper-log", action="store_true", help="Verify cryptographic hash chain of audit log")
    parser.add_argument("--issue-token", action="store_true", help="Issue an HMAC-SHA256 operator token")
    parser.add_argument("--role", type=str, default="OPERATOR", choices=["VIEWER", "OPERATOR", "ADMIN"])
    parser.add_argument("--operator-id", type=str, default="CLI_OPERATOR")
    parser.add_argument("--json", action="store_true", help="Output audit results as JSON")

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    auditor = SecurityHardeningAuditor(project_root=str(project_root))

    if args.verify_tamper_log:
        valid, msg, count = auditor.tamper_logger.verify_chain_integrity()
        payload = {"chain_valid": valid, "message": msg, "verified_entries_count": count}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Tamper Log Chain Valid: {valid} ({count} entries verified). Status: {msg}")
        sys.exit(0 if valid else 1)

    if args.issue_token:
        role_enum = UserRole(args.role)
        token = auditor.auth_manager.generate_token(operator_id=args.operator_id, role=role_enum)
        payload = {"operator_id": args.operator_id, "role": role_enum.value, "token": token}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Issued Token for {args.operator_id} ({role_enum.value}):\n{token}")
        sys.exit(0)

    # Default to running comprehensive security audit
    report = auditor.run_security_audit()

    if args.json:
        print(json.dumps(report.model_dump(), default=str, indent=2))
    else:
        print_ascii_dashboard(report)

    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
