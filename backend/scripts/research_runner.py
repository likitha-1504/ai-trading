#!/usr/bin/env python3
"""CLI Strategy Research & Optimization Runner for Phase 27.

Usage:
    python backend/scripts/research_runner.py [--summary] [--json] [--leakage-check]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.research.experiment_registry import get_experiment_registry
from app.research.leakage_auditor import LeakageAuditor
from app.research.research_engine import StrategyResearchEngine


def format_research_summary(summary_dict: dict) -> str:
    """Formats strategy research matrix into an ASCII terminal audit report."""
    matrix = summary_dict["comparison_matrix"]

    lines = [
        "==================================================================",
        "        PHASE 27 STRATEGY RESEARCH & OPTIMIZATION REPORT          ",
        "==================================================================",
        f"Phase ID:             {summary_dict['phase_id']}",
        f"Timestamp:            {summary_dict['timestamp']}",
        f"Active Production:    {summary_dict['promoted_version']}",
        f"Total Experiments:    {summary_dict['total_experiments']} (Candidates: {summary_dict['candidates_count']})",
        f"Governance Status:    {summary_dict['governance_status']}",
        "------------------------------------------------------------------",
        "STRATEGY COMPARATIVE MATRIX (REALISTIC COSTS & SLIPPAGE):",
        "------------------------------------------------------------------",
        f"{'Version':<26} | {'Status':<9} | {'OOS PnL':<8} | {'Sharpe':<6} | {'Win %':<6} | {'MaxDD':<5} | {'Robust'}",
        "------------------------------------------------------------------",
    ]

    for row in matrix:
        lines.append(
            f"{row['version_tag']:<26} | {row['status']:<9} | "
            f"INR {row['oos_pnl_inr']:>4.2f} | {row['oos_sharpe']:>6.2f} | "
            f"{row['oos_win_rate_pct']:>5.1f}% | {row['max_drawdown_pct']:>4.1f}% | {row['is_robust']}"
        )

    lines.extend([
        "------------------------------------------------------------------",
        "LEAKAGE & LOOK-AHEAD AUDIT:",
        f"   {summary_dict['leakage_audit_summary']}",
        "------------------------------------------------------------------",
        "WALK-FORWARD STATISTICAL VALIDATION:",
        f"   {summary_dict['walk_forward_summary']}",
        "------------------------------------------------------------------",
        f"OVERALL RECOMMENDATION: {summary_dict['recommendation']}",
        "==================================================================",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 27 Strategy Research & Optimization Runner")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--leakage-check", action="store_true", help="Run leakage audit check")
    args = parser.parse_args()

    registry = get_experiment_registry()
    engine = StrategyResearchEngine(registry=registry)

    if args.leakage_check:
        report = LeakageAuditor.audit_event_stream([])
        if args.json:
            print(json.dumps(report.model_dump(), default=str, indent=2))
        else:
            print(f"Leakage Audit Status: {'PASS' if report.is_leakage_free else 'FAIL'}")
            print(f"Details: {report.details}")
        return 0

    summary = engine.generate_research_summary()
    summary_dict = summary.model_dump()

    if args.json:
        print(json.dumps(summary_dict, default=str, indent=2))
    else:
        print(format_research_summary(summary_dict))

    return 0


if __name__ == "__main__":
    sys.exit(main())
