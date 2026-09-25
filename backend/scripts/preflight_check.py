"""Production preflight hardening verification runner for startup and release gating."""

from __future__ import annotations

import sys
import os

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

from app.ops.hardening_runner import ProductionHardeningRunner


def main() -> int:
    root = ".." if os.path.exists(os.path.join("..", "TASKS.md")) else "."
    db_path = os.path.join(root, "trading_agent.db")

    runner = ProductionHardeningRunner(db_path=db_path, project_root=root)
    audit = runner.verify_all_dimensions()

    print("==================================================================")
    print("PHASE 23 PRODUCTION HARDENING PREFLIGHT AUDIT")
    print(f"Audit ID:     {audit.audit_id}")
    print(f"Timestamp:    {audit.timestamp.isoformat()}")
    print(f"Status:       {'ALL PASSED' if audit.all_passed else 'ACTION REQUIRED'}")
    print(f"Passed:       {audit.dimensions_passed}/{audit.dimensions_evaluated}")
    print(f"Warnings:     {audit.dimensions_warning}")
    print(f"Failures:     {audit.dimensions_failed}")
    print("==================================================================")

    for r in audit.results:
        print(f"[{r.status:7s}] Dim {r.dimension_number:02d}: {r.dimension_name}")
        print(f"          Summary: {r.summary}")

    print("==================================================================")
    return 0 if audit.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
