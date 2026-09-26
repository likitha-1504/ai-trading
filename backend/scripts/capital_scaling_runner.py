#!/usr/bin/env python3
"""CLI Controlled Capital Scaling Runner for Phase 29.

Usage:
    python backend/scripts/capital_scaling_runner.py [--json] [--eligibility]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.capital_scaling.scaling_manager import get_capital_scaling_manager


def format_scaling_report(data: dict) -> str:
    """Formats the Phase 29 capital scaling summary into an ASCII terminal audit report."""
    rec = data["latest_reconciliation"]
    elig = data["eligibility"]
    stages = data["configured_stages"]

    lines = [
        "==================================================================",
        "        PHASE 29 CONTROLLED CAPITAL SCALING AUDIT REPORT          ",
        "==================================================================",
        f"Phase ID:             {data['phase_id']}",
        f"Timestamp:            {data['timestamp']}",
        f"Active Stage:         {data['active_stage']} (Ceiling: INR {data['current_capital_ceiling_inr']:.2f})",
        f"Autonomous Limit:     INR {data['current_autonomous_limit_inr']:.2f}",
        f"Auto-Scaling Status:  Blocked={data['auto_scaling_blocked']} (Prohibited From Performance)",
        f"Rollback Capability:  Ready={data['rollback_ready']} (Atomic Reconciliation Enforced)",
        f"Total Transitions:    {data['transitions_count']}",
        "------------------------------------------------------------------",
        "1. RECONCILIATION INTEGRITY (BROKER vs LEDGER):",
        f"   Broker Cash:       INR {rec['broker_cash_inr']:.2f} | Ledger Cash: INR {rec['ledger_cash_inr']:.2f}",
        f"   Discrepancy:       INR {rec['discrepancy_inr']:.2f} | In Parity: {rec['is_in_parity']}",
        f"   Active Positions:  {rec['active_positions_count']}",
        f"   Details:           {rec['details']}",
        "------------------------------------------------------------------",
        "2. CONFIGURABLE CAPITAL STAGES:",
    ]

    for s in stages:
        lines.append(
            f"   [{s['stage']:<27}] Ceiling: INR {s['capital_ceiling_inr']:>6.2f} | "
            f"AutoLimit: INR {s['autonomous_limit_inr']:>7.2f} | "
            f"Prereq: {s['min_trade_count_prereq']:>3} trades, {s['min_win_rate_prereq']:>4.1f}% win"
        )

    lines.extend([
        "------------------------------------------------------------------",
        "3. SCALING ELIGIBILITY & GOVERNANCE:",
        f"   Current Stage:     {elig['current_stage']}",
        f"   Next Stage:        {elig['next_stage'] or 'None (Top Tier)'}",
        f"   Prerequisites Met: {elig['prerequisites_met']} (Trades: {elig['trades_completed']}, Win Rate: {elig['realized_win_rate_pct']:.1f}%)",
        f"   Auto-Scaling:      Permitted={elig['auto_scaling_permitted']} (Strictly Blocked)",
        f"   Operator Required: {elig['operator_action_required']} (Explicit Token Mandatory)",
        f"   Details:           {elig['details']}",
        "------------------------------------------------------------------",
        f"OVERALL RECOMMENDATION: {data['recommendation']}",
        "==================================================================",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 29 Controlled Capital Scaling Runner")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--eligibility", action="store_true", help="Display eligibility evaluation only")
    args = parser.parse_args()

    manager = get_capital_scaling_manager()

    if args.eligibility:
        elig = manager.evaluate_eligibility()
        if args.json:
            print(json.dumps(elig.model_dump(), default=str, indent=2))
        else:
            print("==================================================================")
            print("             CAPITAL SCALING ELIGIBILITY AUDIT                   ")
            print("==================================================================")
            print(f"Current Stage:     {elig.current_stage.value}")
            print(f"Next Target Stage: {elig.next_stage.value if elig.next_stage else 'None'}")
            print(f"Prerequisites Met: {elig.prerequisites_met}")
            print(f"Auto-Scaling:      Permitted={elig.auto_scaling_permitted} (Strictly Blocked)")
            print(f"Operator Required: {elig.operator_action_required} (Mandatory)")
            print(f"Details:           {elig.details}")
            print("==================================================================")
        return 0

    summary = manager.generate_scaling_summary()
    summary_dict = summary.model_dump(mode="json")

    if args.json:
        print(json.dumps(summary_dict, default=str, indent=2))
    else:
        print(format_scaling_report(summary_dict))

    return 0


if __name__ == "__main__":
    sys.exit(main())
