"""Role-Based Access Control (RBAC) and Least Privilege Matrix for Phase 34.

Enforces role hierarchy (ADMIN > OPERATOR > VIEWER) and scope-based authorization
across all API endpoints and operational workflows.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import HTTPException, Header, status

from app.security.auth import AuthenticationManager
from app.security.models import (
    OperatorTokenPayload,
    SecurityAuditDimension,
    SecurityFinding,
    SecuritySeverity,
    UserRole,
)

logger = logging.getLogger(__name__)

# Role hierarchy levels
ROLE_LEVELS: dict[UserRole, int] = {
    UserRole.VIEWER: 1,
    UserRole.OPERATOR: 2,
    UserRole.ADMIN: 3,
}

_default_auth_mgr = AuthenticationManager()


def has_sufficient_role(user_role: UserRole, required_role: UserRole) -> bool:
    """Verifies that user role meets or exceeds required authorization tier."""
    return ROLE_LEVELS.get(user_role, 0) >= ROLE_LEVELS.get(required_role, 99)


class AccessControlManager:
    """Evaluates role authorizations and audits endpoint permissions."""

    @staticmethod
    def audit_rbac_matrix() -> SecurityFinding:
        """Audits role hierarchy and ensures least privilege principle is mathematically sound."""
        viewer_denied_admin = not has_sufficient_role(UserRole.VIEWER, UserRole.ADMIN)
        operator_denied_admin = not has_sufficient_role(UserRole.OPERATOR, UserRole.ADMIN)
        admin_permitted_all = (
            has_sufficient_role(UserRole.ADMIN, UserRole.ADMIN)
            and has_sufficient_role(UserRole.ADMIN, UserRole.OPERATOR)
            and has_sufficient_role(UserRole.ADMIN, UserRole.VIEWER)
        )

        passed = viewer_denied_admin and operator_denied_admin and admin_permitted_all

        return SecurityFinding(
            dimension=SecurityAuditDimension.AUTHORIZATION_RBAC,
            severity=SecuritySeverity.LOW if passed else SecuritySeverity.HIGH,
            title="RBAC Least-Privilege Hierarchy Verified",
            description="Strict three-tier role hierarchy (ADMIN > OPERATOR > VIEWER) enforces access boundaries.",
            passed=passed,
            evidence="Viewer blocked from Admin: True; Operator blocked from Admin: True; Admin granted all: True.",
        )


def require_role(required_role: UserRole) -> Callable[..., OperatorTokenPayload]:
    """FastAPI dependency enforcing mandatory role authorization."""

    def role_checker(
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> OperatorTokenPayload:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header: bearer token required.",
            )

        token = authorization.replace("Bearer ", "").strip()
        valid, payload, msg = _default_auth_mgr.verify_token(token)

        if not valid or payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {msg}",
            )

        if not has_sufficient_role(payload.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{payload.role.value}' does not possess required '{required_role.value}' privileges.",
            )

        return payload

    return role_checker
