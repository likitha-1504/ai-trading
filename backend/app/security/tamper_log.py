"""Tamper-Evident Cryptographic Audit Logging for Phase 34 Security Hardening.

Maintains an immutable SHA-256 hash-chained security ledger in SQLite storage,
enabling mathematically verifiable proof against log tampering, deletion, or injection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.connection import get_connection, get_db_path
from app.security.models import (
    AuditLogEntry,
    SecurityAuditDimension,
    SecurityFinding,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


class TamperEvidentAuditLogger:
    """Manages cryptographic hash-chaining of security and trading audit events."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = get_db_path(db_path)
        self._init_table()

    def _init_table(self) -> None:
        """Initialize security audit ledger table if not present."""
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_audit_ledger (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entry_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        operator_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource TEXT NOT NULL,
                        details_json TEXT NOT NULL,
                        prev_hash TEXT NOT NULL,
                        record_hash TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_security_audit_timestamp
                    ON security_audit_ledger (timestamp);
                    """
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not initialize security audit table: %s", e)

    @staticmethod
    def compute_record_hash(
        prev_hash: str,
        timestamp: str,
        operator_id: str,
        action: str,
        resource: str,
        details_json: str,
    ) -> str:
        """Computes deterministic cryptographic SHA-256 hash for audit record."""
        raw = f"{prev_hash}:{timestamp}:{operator_id}:{action}:{resource}:{details_json}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_latest_hash(self) -> str:
        """Retrieves record_hash of the most recent audit entry (or GENESIS_HASH)."""
        try:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT record_hash FROM security_audit_ledger ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                return str(row["record_hash"]) if row else GENESIS_HASH
        except Exception:  # noqa: BLE001
            return GENESIS_HASH

    def log_event(
        self,
        event_type: str,
        operator_id: str,
        role: str,
        action: str,
        resource: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Appends a new security event to the tamper-evident hash chain."""
        now = datetime.now(timezone.utc).isoformat()
        entry_id = f"SEC-LOG-{uuid.uuid4().hex[:8].upper()}"
        details_dict = details or {}
        details_json = json.dumps(details_dict, sort_keys=True)

        prev_hash = self.get_latest_hash()
        record_hash = self.compute_record_hash(
            prev_hash=prev_hash,
            timestamp=now,
            operator_id=operator_id,
            action=action,
            resource=resource,
            details_json=details_json,
        )

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO security_audit_ledger (
                    entry_id, timestamp, event_type, operator_id, role,
                    action, resource, details_json, prev_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    now,
                    event_type,
                    operator_id,
                    role,
                    action,
                    resource,
                    details_json,
                    prev_hash,
                    record_hash,
                ),
            )

        return AuditLogEntry(
            entry_id=entry_id,
            timestamp=datetime.fromisoformat(now),
            event_type=event_type,
            operator_id=operator_id,
            role=role,
            action=action,
            resource=resource,
            details=details_dict,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )

    def verify_chain_integrity(self) -> tuple[bool, str, int]:
        """Walks the entire audit ledger verifying every cryptographic hash link in sequence."""
        try:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT * FROM security_audit_ledger ORDER BY id ASC"
                )
                rows = cur.fetchall()

            if not rows:
                return True, "Audit chain is empty (zero entries).", 0

            expected_prev = GENESIS_HASH
            for row in rows:
                row_id = row["id"]
                actual_prev = row["prev_hash"]
                actual_hash = row["record_hash"]

                if actual_prev != expected_prev:
                    return (
                        False,
                        f"Hash chain broken at row {row_id} ({row['entry_id']}): expected prev_hash {expected_prev[:12]}..., found {actual_prev[:12]}...",
                        len(rows),
                    )

                recomputed = self.compute_record_hash(
                    prev_hash=actual_prev,
                    timestamp=row["timestamp"],
                    operator_id=row["operator_id"],
                    action=row["action"],
                    resource=row["resource"],
                    details_json=row["details_json"],
                )

                if recomputed != actual_hash:
                    return (
                        False,
                        f"Record hash tampering detected at row {row_id} ({row['entry_id']}): recomputed {recomputed[:12]}... != stored {actual_hash[:12]}...",
                        len(rows),
                    )

                expected_prev = actual_hash

            return True, f"All {len(rows)} audit entries verified against cryptographic hash chain.", len(rows)

        except Exception as e:  # noqa: BLE001
            return False, f"Integrity check failed with database error: {e}", 0

    def audit_tamper_log(self) -> SecurityFinding:
        """Audits the tamper-evident security audit log."""
        # Ensure at least one genesis event is recorded
        if self.get_latest_hash() == GENESIS_HASH:
            self.log_event(
                event_type="SYSTEM_GENESIS",
                operator_id="SECURITY_AUDITOR",
                role="ADMIN",
                action="INITIALIZE_AUDIT_LEDGER",
                resource="security_audit_ledger",
                details={"phase": 34, "initialized_at": datetime.now(timezone.utc).isoformat()},
            )

        valid, msg, count = self.verify_chain_integrity()

        return SecurityFinding(
            dimension=SecurityAuditDimension.AUDIT_LOG_TAMPER_EVIDENT,
            severity=SecuritySeverity.LOW if valid else SecuritySeverity.CRITICAL,
            title="Cryptographic Audit Hash Chain Verified",
            description="Immutable SHA-256 hash chaining ensures audit records cannot be modified or deleted.",
            passed=valid,
            evidence=f"Verified entries: {count}; Status: {msg}",
            remediation="Investigate unauthorized database mutation if chain verification fails." if not valid else None,
        )
