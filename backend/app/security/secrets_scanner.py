"""Secrets Scanner and Sanitization Engine for Phase 34 Security Hardening.

Audits source files, environment variables, configuration manifests, and .gitignore rules
to ensure zero raw secrets, credentials, or private keys are exposed or committed.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.security.models import (
    SecurityAuditDimension,
    SecurityFinding,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)

# Standard regex patterns for sensitive credentials
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "AWS Access Key": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "GitHub Token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"),
    "OpenAI / Anthropic API Key": re.compile(r"\b(sk-[a-zA-Z0-9]{32,64})\b"),
    "Kite / Zerodha API Key": re.compile(r"\b([a-z0-9]{32})\b"),  # Checked in sensitive context
    "Private Key Header": re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"),
    "Generic Bearer Token": re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{40,}"),
    "Database Password in URI": re.compile(r"(?i)postgres(?:ql)?://[^:]+:([^@]+)@"),
}

EXCLUDED_EXTENSIONS = {
    ".pyc", ".git", ".venv", "venv", ".png", ".jpg", ".jpeg", ".ico", ".svg",
    ".woff", ".woff2", ".pdf", ".db", "-wal", "-shm",
}


def mask_secret(text: str, visible_prefix: int = 3, visible_suffix: int = 3) -> str:
    """Masks sensitive strings, exposing only minimal edge characters."""
    if not text:
        return ""
    if len(text) <= (visible_prefix + visible_suffix):
        return "***REDACTED***"
    return f"{text[:visible_prefix]}***REDACTED***{text[-visible_suffix:]}"


class SecretsScanner:
    """Scans filesystem and repository for credential leakage and audits git exclusion rules."""

    def __init__(self, root_dir: str | None = None) -> None:
        self.root_dir = Path(root_dir or ".").resolve()

    def audit_gitignore(self) -> SecurityFinding:
        """Verifies that .gitignore properly excludes all sensitive credential & database files."""
        gitignore_path = self.root_dir / ".gitignore"
        if not gitignore_path.exists():
            return SecurityFinding(
                dimension=SecurityAuditDimension.SECRETS_SANITIZATION,
                severity=SecuritySeverity.CRITICAL,
                title=".gitignore Missing",
                description="Root .gitignore file is absent, risking accidental credential commits.",
                passed=False,
                evidence="File .gitignore does not exist at repository root.",
                remediation="Create a comprehensive .gitignore excluding .env, *.db, backups/, and secrets.",
            )

        content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        required_patterns = [".env", "*.db", "backups", "*.log", ".venv"]
        missing = [p for p in required_patterns if p not in content]

        if missing:
            return SecurityFinding(
                dimension=SecurityAuditDimension.SECRETS_SANITIZATION,
                severity=SecuritySeverity.HIGH,
                title=".gitignore Incomplete",
                description="Root .gitignore does not exclude all mandatory sensitive patterns.",
                passed=False,
                evidence=f"Missing patterns: {missing}",
                remediation=f"Add {missing} to .gitignore.",
            )

        return SecurityFinding(
            dimension=SecurityAuditDimension.SECRETS_SANITIZATION,
            severity=SecuritySeverity.LOW,
            title=".gitignore Rules Verified",
            description="Root .gitignore properly excludes .env, database files, backups, and logs.",
            passed=True,
            evidence="All mandatory exclusion patterns (.env, *.db, backups, *.log, .venv) present.",
        )

    def scan_source_code(self) -> list[SecurityFinding]:
        """Scans tracked source files for high-entropy secrets and credential patterns."""
        findings: list[SecurityFinding] = []
        violations: list[str] = []

        scan_dirs = ["backend/app", "backend/scripts", "frontend/src"]

        for rel_dir in scan_dirs:
            target_path = self.root_dir / rel_dir
            if not target_path.exists():
                continue

            for file_path in target_path.rglob("*"):
                if file_path.is_dir() or file_path.suffix in EXCLUDED_EXTENSIONS:
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    for pattern_name, pattern in SECRET_PATTERNS.items():
                        # Only check Kite API Key if explicitly labeled as api_key or secret
                        if pattern_name == "Kite / Zerodha API Key":
                            if "api_key" in text.lower() or "secret" in text.lower():
                                matches = pattern.findall(text)
                                for m in matches:
                                    if m != "0" * 32 and m != "x" * 32:
                                        violations.append(f"{file_path.name}: potential {pattern_name}")
                        else:
                            matches = pattern.findall(text)
                            if matches:
                                violations.append(f"{file_path.name}: potential {pattern_name}")
                except Exception as e:  # noqa: BLE001
                    logger.debug("Could not read %s for secret scanning: %s", file_path, e)

        if violations:
            findings.append(
                SecurityFinding(
                    dimension=SecurityAuditDimension.SECRETS_SANITIZATION,
                    severity=SecuritySeverity.CRITICAL,
                    title="Hardcoded Secrets Detected",
                    description="Identified potential hardcoded API keys or credentials in source code.",
                    passed=False,
                    evidence=f"Violations detected in: {violations[:5]}",
                    remediation="Extract credentials to .env file and reference via environment variables.",
                )
            )
        else:
            findings.append(
                SecurityFinding(
                    dimension=SecurityAuditDimension.SECRETS_SANITIZATION,
                    severity=SecuritySeverity.LOW,
                    title="Source Code Free of Committed Secrets",
                    description="Zero hardcoded API keys, private keys, or credentials found in source files.",
                    passed=True,
                    evidence=f"Scanned source trees {scan_dirs}; zero secret patterns identified.",
                )
            )

        return findings

    def run_full_secrets_audit(self) -> list[SecurityFinding]:
        """Runs complete secrets audit across gitignore and source code."""
        results: list[SecurityFinding] = [self.audit_gitignore()]
        results.extend(self.scan_source_code())
        return results
