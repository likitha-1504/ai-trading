#!/usr/bin/env python3
"""CLI Live Trading Stabilization Runner & Audit Tool for Phase 26.

Usage:
    python backend/scripts/stabilization_runner.py [--db-path PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.live.stabilization_engine import LiveStabilizationEngine


def format_report(data: dict) -> str:
    """Formats the stabilization summary into an ASCII terminal audit report."""
    cmp = data["execution_comparison"]
    slip = data["slippage"]
    cost = data["cost_variance"]
    rej = data["rejected_orders"]
    part = data["partial_fills"]
    recon = data["reconciliation"]
    wat = data["watcher_surveillance"]

    lines = [
        "==================================================================",
        "        PHASE 26 LIVE TRADING STABILIZATION AUDIT REPORT          ",
        "==================================================================",
        f"Phase ID:             {data['phase_id']}",
        f"Timestamp:            {data['timestamp']}",
        f"Stabilization Status: {data['stabilization_status']}",
        f"Capital Ceiling:      INR {data['initial_capital_inr']:.2f} (Autonomous Cap: INR {data['autonomous_threshold_inr']:.2f})",
        f"Current Capital:      INR {data['current_capital_inr']:.2f} (Invariants Preserved: {data['capital_invariants_preserved']})",
        f"Capital Auto-Scaled:  {data['capital_increase_attempted']} (Prohibited)",
        "------------------------------------------------------------------",
        "1. EXECUTION QUALITY COMPARISON (PAPER vs LIVE):",
        f"   Paper Fill Rate:   {cmp['paper_fill_rate_pct']:.1f}% ({cmp['paper_orders_filled']}/{cmp['paper_orders_submitted']}) | Avg Latency: {cmp['paper_avg_fill_latency_ms']:.2f} ms",
        f"   Live Fill Rate:    {cmp['live_fill_rate_pct']:.1f}% ({cmp['live_orders_filled']}/{cmp['live_orders_submitted']}) | Avg Latency: {cmp['live_avg_fill_latency_ms']:.2f} ms",
        f"   Fill Rate Pass:    {cmp['fill_rate_pass']} | Latency Pass: {cmp['latency_pass']}",
        f"   Details:           {cmp['details']}",
        "------------------------------------------------------------------",
        "2. SLIPPAGE DISTRIBUTION:",
        f"   Total Fills:       {slip['total_fills']} (Zero Slip: {slip['zero_slippage_fills']}, Fav: {slip['favorable_slippage_fills']}, Adv: {slip['adverse_slippage_fills']})",
        f"   Average Slippage:  {slip['avg_slippage_bps']:.1f} bps | P95 Slippage: {slip['p95_slippage_bps']:.1f} bps (Max: {slip['max_adverse_slippage_bps']:.1f} bps)",
        f"   Acceptable (<25):  {slip['is_acceptable']}",
        f"   Details:           {slip['details']}",
        "------------------------------------------------------------------",
        "3. STATUTORY COST VARIANCE (MODELED vs REALIZED):",
        f"   Turnover:          INR {cost['total_turnover_inr']:.2f}",
        f"   Modeled Fees:      INR {cost['modeled_fees_inr']:.2f} | Realized Fees: INR {cost['actual_realized_fees_inr']:.2f}",
        f"   Variance:          INR {cost['cost_variance_inr']:.2f} ({cost['cost_variance_pct']:.2f}%)",
        f"   Fee Drag:          {cost['fee_drag_pct_of_turnover']:.3f}% of turnover",
        f"   Accurate:          {cost['is_accurate']}",
        f"   Details:           {cost['details']}",
        "------------------------------------------------------------------",
        "4. REJECTED ORDERS & SAFETY BOUNDARIES:",
        f"   Total Submissions: {rej['total_submissions']} | Total Rejections: {rej['total_rejections']}",
        f"   Rejection Reasons: {rej['rejections_by_reason']}",
        f"   Safety Compliant:  {rej['safety_rejections_compliant']}",
        f"   Details:           {rej['details']}",
        "------------------------------------------------------------------",
        "5. PARTIAL FILLS & LIQUIDITY ABSORPTION:",
        f"   Partial Fills:     {part['orders_with_partial_fills']} | Total Chunks: {part['total_fill_chunks']}",
        f"   Liquidity OK:      {part['liquidity_adequate']}",
        f"   Details:           {part['details']}",
        "------------------------------------------------------------------",
        "6. BROKER vs DATABASE STATE RECONCILIATION:",
        f"   Broker Positions:  {recon['broker_active_positions_count']} | Database Open Positions: {recon['database_open_positions_count']}",
        f"   Discrepancies:     INR {recon['cash_discrepancy_inr']:.2f} | In Parity: {recon['is_in_parity']}",
        f"   Details:           {recon['details']}",
        "------------------------------------------------------------------",
        "7. POSITION WATCHER LIVE SLA & TRIGGER BEHAVIOR:",
        f"   Evaluations:       {wat['total_evaluations']} | Sub-50ms SLA Compliance: {wat['sub_50ms_compliance_pct']:.1f}%",
        f"   Median Latency:    {wat['realized_median_latency_us']:.2f} us | P95 Latency: {wat['realized_p95_latency_us']:.2f} us (Max: {wat['max_latency_us']:.2f} us)",
        f"   Exits Triggered:   {wat['exits_triggered']} (Triggers: {wat['trigger_breakdown']})",
        f"   Zero LLM In Exit:  {wat['zero_llm_dependency_verified']} (Passed: {wat['sla_passed']})",
        f"   Details:           {wat['details']}",
        "------------------------------------------------------------------",
        f"OVERALL RECOMMENDATION: {data['recommendation']}",
        "==================================================================",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 26 Live Trading Stabilization Runner")
    parser.add_argument("--db-path", default="live_experiment.db", help="Path to database")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    engine = LiveStabilizationEngine(db_path=args.db_path)
    summary = engine.generate_stabilization_report()
    summary_dict = summary.model_dump()

    if args.json:
        print(json.dumps(summary_dict, indent=2, default=str))
    else:
        print(format_report(summary_dict))

    return 0 if summary.stabilization_status == "STABLE" else 1


if __name__ == "__main__":
    sys.exit(main())
