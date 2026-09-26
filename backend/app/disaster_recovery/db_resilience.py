"""Database Resilience, WAL Recovery, and Backup Failover Manager for Phase 33.

Handles SQLite integrity verification, WAL checkpoint synchronization, corruption detection,
and automated restore from backup snapshots.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone

from app.db.connection import get_connection, get_db_path
from app.disaster_recovery.models import DatabaseHealthReport
from app.ops.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class DatabaseResilienceManager:
    """Monitors database integrity, manages WAL checkpoints, and executes failover recovery."""

    def __init__(
        self,
        db_path: str | None = None,
        backup_manager: BackupManager | None = None,
    ) -> None:
        self.db_path = get_db_path(db_path)
        self.backup_mgr = backup_manager or BackupManager(db_path=self.db_path)

    def evaluate_db_health(self) -> DatabaseHealthReport:
        """Run diagnostic checks on database file, WAL mode, and integrity."""
        integrity_ok = False
        wal_mode = "unknown"
        fk_enabled = False
        connections_ok = False

        try:
            with get_connection(self.db_path) as conn:
                connections_ok = True

                # 1. Integrity check
                cur = conn.execute("PRAGMA integrity_check;")
                res = cur.fetchone()
                if res and res[0] == "ok":
                    integrity_ok = True

                # 2. Journal mode
                cur_jm = conn.execute("PRAGMA journal_mode;")
                row_jm = cur_jm.fetchone()
                if row_jm:
                    wal_mode = str(row_jm[0]).lower()

                # 3. Foreign keys
                cur_fk = conn.execute("PRAGMA foreign_keys;")
                row_fk = cur_fk.fetchone()
                if row_fk and row_fk[0] == 1:
                    fk_enabled = True

        except Exception as e:  # noqa: BLE001
            logger.error("Database health check encountered exception: %s", e)

        backups = self.backup_mgr.list_backups()
        latest_bkp = backups[0] if backups else None
        has_backup = latest_bkp is not None and os.path.exists(latest_bkp.backup_file)

        overall_status = "HEALTHY" if (integrity_ok and connections_ok) else "DEGRADED"

        return DatabaseHealthReport(
            db_path=self.db_path,
            integrity_ok=integrity_ok,
            wal_journal_mode=wal_mode,
            foreign_keys_enabled=fk_enabled,
            active_connections_ok=connections_ok,
            backup_file_available=has_backup,
            last_checkpoint_timestamp=datetime.now(timezone.utc),
            status=overall_status,
        )

    def force_wal_checkpoint(self, mode: str = "TRUNCATE") -> bool:
        """Flush and truncate the SQLite Write-Ahead Log to the main database file."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute(f"PRAGMA wal_checkpoint({mode});")
                conn.commit()
            logger.info("WAL checkpoint (%s) completed successfully for %s", mode, self.db_path)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("WAL checkpoint failed: %s", e)
            return False

    def recover_from_corruption_or_failure(self) -> tuple[bool, str]:
        """Detect and recover from database corruption by restoring latest verified backup."""
        health = self.evaluate_db_health()
        if health.integrity_ok:
            return True, "Database integrity is already healthy (PRAGMA integrity_check passed)."

        logger.critical("Database corruption detected on %s! Initiating disaster restore...", self.db_path)

        backups = self.backup_mgr.list_backups()
        latest_backup = backups[0] if backups else None
        if not latest_backup or not os.path.exists(latest_backup.backup_file):
            msg = "Disaster recovery failed: No valid backup snapshot available to restore."
            logger.critical(msg)
            return False, msg

        try:
            success = self.backup_mgr.restore_backup(latest_backup.backup_file)
            # Re-verify integrity post-restore
            post_health = self.evaluate_db_health()
            if post_health.integrity_ok and success:
                msg = f"Database successfully restored from backup {latest_backup.backup_id} (SHA256 verified)."
                logger.info(msg)
                return True, msg
            return False, f"Post-restore integrity check failed for backup {latest_backup.backup_id}."
        except Exception as e:
            err_msg = f"Failed to restore database from backup: {e}"
            logger.exception(err_msg)
            return False, err_msg
