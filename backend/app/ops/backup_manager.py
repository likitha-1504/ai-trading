"""Production-grade automated SQLite backup, verification, rotation, and recovery manager.

Adheres to Phase 23 requirements:
- Online live WAL backup using SQLite native backup API (zero tear, non-blocking)
- SHA-256 cryptographic checksum calculation
- Automatic post-backup integrity validation (PRAGMA integrity_check)
- Retention rotation (keeps last N backups)
- Safe restore workflow with pre-restore safety snapshots
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BackupMetadata(BaseModel):
    """Metadata record for a verified database backup snapshot."""

    backup_id: str
    source_db: str
    backup_file: str
    size_bytes: int
    sha256_hash: str
    verified: bool
    integrity_status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tag: str = "auto"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackupVerificationError(RuntimeError):
    """Raised when a backup fails cryptographic checksum or SQLite integrity checks."""


class BackupManager:
    """Manages online SQLite backups, verification, and recovery for production operations."""

    def __init__(
        self,
        db_path: str = "trading_agent.db",
        backup_dir: str = "backups",
        max_retained_backups: int = 14,
    ) -> None:
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.max_retained_backups = max_retained_backups
        os.makedirs(self.backup_dir, exist_ok=True)

    def _compute_sha256(self, file_path: str) -> str:
        """Computes SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_backup(self, tag: str = "auto") -> BackupMetadata:
        """Performs a live, non-blocking online backup using SQLite's native backup API.

        Guarantees:
        - Atomic snapshot even during concurrent WAL operations
        - Immediate SHA-256 hashing
        - Immediate PRAGMA integrity_check on the generated snapshot
        - Automatic metadata file persistence
        - Rotation of stale backups
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Source database '{self.db_path}' does not exist.")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"trading_agent_backup_{timestamp_str}_{tag}.db"
        backup_filepath = os.path.join(self.backup_dir, backup_filename)
        backup_id = f"BKP-{timestamp_str}-{tag}"

        logger.info("Starting online database backup to %s...", backup_filepath)

        # 1. Execute SQLite online backup API
        src_conn = sqlite3.connect(self.db_path)
        dst_conn = sqlite3.connect(backup_filepath)
        try:
            with dst_conn:
                src_conn.backup(dst_conn, pages=100, sleep=0.001)
        finally:
            dst_conn.close()
            src_conn.close()

        # 2. Check file size and SHA-256 hash
        size_bytes = os.path.getsize(backup_filepath)
        sha256_hash = self._compute_sha256(backup_filepath)

        # 3. Verify snapshot integrity
        verified, integrity_msg = self.verify_backup_file(backup_filepath)
        if not verified:
            os.remove(backup_filepath)
            raise BackupVerificationError(
                f"Generated backup failed integrity check: {integrity_msg}"
            )

        metadata = BackupMetadata(
            backup_id=backup_id,
            source_db=self.db_path,
            backup_file=backup_filepath,
            size_bytes=size_bytes,
            sha256_hash=sha256_hash,
            verified=verified,
            integrity_status=integrity_msg,
            created_at=datetime.now(timezone.utc),
            tag=tag,
            metadata={"sqlite_version": sqlite3.sqlite_version},
        )

        # 4. Save metadata sidecar
        meta_filepath = backup_filepath + ".json"
        with open(meta_filepath, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.info(
            "Backup %s successfully created and verified (%d bytes, SHA256: %s...)",
            backup_id,
            size_bytes,
            sha256_hash[:12],
        )

        # 5. Apply retention policy rotation
        self._rotate_backups()

        return metadata

    def verify_backup_file(self, backup_filepath: str) -> tuple[bool, str]:
        """Runs PRAGMA integrity_check and foreign_key_check on a backup snapshot."""
        if not os.path.exists(backup_filepath):
            return False, f"File {backup_filepath} does not exist"

        try:
            conn = sqlite3.connect(backup_filepath)
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            integrity_row = cur.fetchone()
            integrity_result = integrity_row[0] if integrity_row else "UNKNOWN"

            cur.execute("PRAGMA foreign_key_check;")
            fk_violations = cur.fetchall()
            conn.close()

            if integrity_result.lower() != "ok":
                return False, f"Integrity check failed: {integrity_result}"

            if fk_violations:
                return False, f"Foreign key check violations: {len(fk_violations)}"

            return True, "PRAGMA integrity_check: ok, foreign_keys: ok"
        except (sqlite3.Error, OSError) as e:
            return False, f"SQLite verification error: {e}"

    def list_backups(self) -> list[BackupMetadata]:
        """Lists all available verified backups in reverse chronological order."""
        if not os.path.exists(self.backup_dir):
            return []

        backups: list[BackupMetadata] = []
        for fname in os.listdir(self.backup_dir):
            if fname.endswith(".db.json"):
                meta_path = os.path.join(self.backup_dir, fname)
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        backups.append(BackupMetadata(**data))
                except (OSError, ValueError, TypeError) as e:
                    logger.warning("Could not read backup metadata %s: %s", meta_path, e)

        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def restore_backup(
        self,
        backup_filepath: str,
        target_db_path: str | None = None,
        create_pre_restore_snapshot: bool = True,
    ) -> bool:
        """Safely restores database from a verified backup snapshot.

        Safety Mechanisms:
        1. Pre-validates backup snapshot integrity before taking any action.
        2. Creates a pre-restore backup of the target database so rollback is possible.
        3. Restores cleanly using SQLite online backup API.
        4. Verifies target database integrity post-restore.
        """
        target = target_db_path or self.db_path

        # 1. Pre-validation
        verified, msg = self.verify_backup_file(backup_filepath)
        if not verified:
            raise BackupVerificationError(
                f"Cannot restore from corrupt or invalid backup '{backup_filepath}': {msg}"
            )

        # 2. Pre-restore snapshot of current database
        if create_pre_restore_snapshot and os.path.exists(target):
            pre_restore_path = f"{target}.pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            logger.info("Creating pre-restore safety copy at %s", pre_restore_path)
            shutil.copy2(target, pre_restore_path)

        # 3. Perform restoration
        logger.info("Restoring database from %s to %s...", backup_filepath, target)
        src_conn = sqlite3.connect(backup_filepath)
        dst_conn = sqlite3.connect(target)
        try:
            with dst_conn:
                src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # 4. Post-restore verification
        post_verified, post_msg = self.verify_backup_file(target)
        if not post_verified:
            raise BackupVerificationError(
                f"Restored target database failed integrity validation: {post_msg}"
            )

        logger.info("Successfully restored and validated %s from %s", target, backup_filepath)
        return True

    def _rotate_backups(self) -> None:
        """Retains only the most recent N backups, pruning older files."""
        backups = self.list_backups()
        if len(backups) <= self.max_retained_backups:
            return

        excess = backups[self.max_retained_backups :]
        for b in excess:
            try:
                if os.path.exists(b.backup_file):
                    os.remove(b.backup_file)
                meta_file = b.backup_file + ".json"
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                logger.info("Pruned old backup snapshot: %s", b.backup_id)
            except OSError as e:
                logger.warning("Could not prune backup %s: %s", b.backup_file, e)
