"""CLI tool for safe SQLite database recovery from verified backup snapshot."""

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
    parser = argparse.ArgumentParser(description="Restore SQLite database from verified backup snapshot.")
    parser.add_argument("backup_file", help="Path to verified backup snapshot .db file.")
    parser.add_argument("--target-db", default="trading_agent.db", help="Path to target database to overwrite.")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation flag required to proceed.")
    args = parser.parse_args()

    if not args.confirm:
        print("ERROR: Safety interlock: --confirm flag is required to restore database.", file=sys.stderr)
        return 1

    if not os.path.exists(args.backup_file):
        print(f"ERROR: Backup file '{args.backup_file}' does not exist.", file=sys.stderr)
        return 2

    root = ".." if os.path.exists(os.path.join("..", "TASKS.md")) else "."
    target_db = os.path.join(root, args.target_db) if not os.path.isabs(args.target_db) else args.target_db

    mgr = BackupManager(db_path=target_db)
    try:
        mgr.restore_backup(
            backup_filepath=args.backup_file,
            target_db_path=target_db,
            create_pre_restore_snapshot=True,
        )
        print("==================================================================")
        print("DATABASE RESTORE SUCCESSFUL")
        print(f"Restored from: {args.backup_file}")
        print(f"Restored to:   {target_db}")
        print("Pre-restore snapshot preserved.")
        print("Integrity check passed.")
        print("==================================================================")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Database restoration failed: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
