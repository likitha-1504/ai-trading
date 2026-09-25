"""CLI tool for automated or manual SQLite database backup."""

from __future__ import annotations

import argparse
import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001, S110
        pass

from app.ops.backup_manager import BackupManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a verified online SQLite backup snapshot.")
    parser.add_argument("--db-path", default="trading_agent.db", help="Path to source SQLite database.")
    parser.add_argument("--backup-dir", default="backups", help="Directory where backup files are saved.")
    parser.add_argument("--tag", default="manual", help="Tag for backup snapshot (e.g. pre_deploy, daily).")
    args = parser.parse_args()

    # Determine paths
    root = ".." if os.path.exists(os.path.join("..", "TASKS.md")) else "."
    db_path = os.path.join(root, args.db_path) if not os.path.isabs(args.db_path) else args.db_path
    backup_dir = os.path.join(root, args.backup_dir) if not os.path.isabs(args.backup_dir) else args.backup_dir

    if not os.path.exists(db_path):
        print(f"ERROR: Source database not found at {db_path}", file=sys.stderr)
        return 1

    mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
    try:
        meta = mgr.create_backup(tag=args.tag)
        print("==================================================================")
        print("DATABASE BACKUP CREATED AND VERIFIED")
        print(f"Backup ID:    {meta.backup_id}")
        print(f"Backup File:  {meta.backup_file}")
        print(f"Size:         {meta.size_bytes} bytes")
        print(f"SHA-256:      {meta.sha256_hash}")
        print(f"Status:       {meta.integrity_status}")
        print(f"Timestamp:    {meta.created_at.isoformat()}")
        print("==================================================================")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Backup creation failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
