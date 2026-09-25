"""Runner script to execute Phase 19 Live Readiness Audit and output summary."""

import os
import sys
from decimal import Decimal

# Ensure backend root is on sys.path when runner is called directly
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.adapters.live_broker_adapter import LiveBrokerAdapter
from app.live.readiness_audit import LiveReadinessAuditor


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass

    print("=" * 70)
    print("PHASE 19: CONTROLLED ₹100 LIVE READINESS GATE AUDIT")
    print("=" * 70)

    adapter = LiveBrokerAdapter(
        broker_name="ZERODHA",
        api_key="KITE_API_KEY_LIVE_9981",
        api_secret="KITE_API_SECRET_LIVE_4412",
        access_token="KITE_ACCESS_TOKEN_LIVE_7700",
        account_id="ACC_MICRO_100",
        is_sandbox=True,
        initial_cash=Decimal("100.00"),
    )

    auditor = LiveReadinessAuditor(broker_adapter=adapter)
    result = auditor.run_full_audit()

    print(f"\nOverall Readiness Status: {result.overall_status}")
    print(f"Passed Checks: {result.passed_checks} / {result.total_checks}")
    print("-" * 70)

    for chk in result.preflight_checks:
        status_tag = "[PASS]" if chk.passed else "[FAIL]"
        print(f"{status_tag} {chk.check_id} [{chk.category}]: {chk.description}")
        print(f"       Details: {chk.details}")

    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f" - {rec}")
    print("=" * 70)

    return 0 if result.overall_status == "READY_FOR_APPROVAL" else 1


if __name__ == "__main__":
    sys.exit(main())
