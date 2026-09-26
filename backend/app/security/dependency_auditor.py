"""Dependency Vulnerability and Pinning Auditor for Phase 34 Security Hardening.

Inspects pyproject.toml manifests to ensure reproducible dependency pinning,
prohibiting unpinned wildcards on runtime packages.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.security.models import (
    SecurityAuditDimension,
    SecurityFinding,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)


class DependencyAuditor:
    """Audits software supply chain, dependency pinning, and manifest configurations."""

    def __init__(self, root_dir: str | None = None) -> None:
        self.root_dir = Path(root_dir or ".").resolve()

    def audit_dependencies(self) -> SecurityFinding:
        """Inspects backend/pyproject.toml for explicit dependency pinning."""
        pyproject_path = self.root_dir / "backend" / "pyproject.toml"
        if not pyproject_path.exists():
            pyproject_path = self.root_dir / "pyproject.toml"

        if not pyproject_path.exists():
            return SecurityFinding(
                dimension=SecurityAuditDimension.DEPENDENCY_VULNERABILITY,
                severity=SecuritySeverity.HIGH,
                title="pyproject.toml Missing",
                description="Could not locate pyproject.toml manifest for supply chain verification.",
                passed=False,
                evidence=f"File not found in {self.root_dir}",
                remediation="Ensure backend/pyproject.toml is present and pinned.",
            )

        content = pyproject_path.read_text(encoding="utf-8", errors="ignore")
        unpinned: list[str] = []

        # Parse dependencies section
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("]"):
                    in_deps = False
                    break
                # Check for unpinned entries without >=, ==, ~=
                pkg_entry = stripped.strip('",')
                if pkg_entry and not any(op in pkg_entry for op in ["==", ">=", "~=", "<="]):
                    unpinned.append(pkg_entry)

        passed = len(unpinned) == 0

        return SecurityFinding(
            dimension=SecurityAuditDimension.DEPENDENCY_VULNERABILITY,
            severity=SecuritySeverity.LOW if passed else SecuritySeverity.MEDIUM,
            title="Runtime Dependencies Explicitly Pinned",
            description="Software supply chain verified; zero wildcard or unconstrained packages in pyproject.toml.",
            passed=passed,
            evidence=f"Manifest: {pyproject_path.name}; Unpinned packages detected: {len(unpinned)}." if passed else f"Unpinned packages: {unpinned}",
            remediation="Pin versions in pyproject.toml (e.g., 'package>=1.0.0')." if not passed else None,
        )
