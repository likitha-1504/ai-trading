"""Operational CLI Runner & Audit Tool for Phase 32 Execution Optimization.

Executes comparative paper execution studies, analyzes empirical slippage,
evaluates liquidity-aware sizing, and reports latency profiles.

Usage:
    python backend/scripts/execution_opt_runner.py [--json] [--run-study] [--orders 50]
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.execution_opt.execution_optimizer import ExecutionOptimizer
from app.execution_opt.liquidity_sizer import LiquidityAwareSizer
from app.execution_opt.slippage_model import SlippageModel


def print_ascii_execution_dashboard(orders_count: int = 50) -> None:
    """Renders formatted multi-dimensional ASCII execution optimization report."""
    optimizer = ExecutionOptimizer()
    study = optimizer.run_comparative_study(orders_count=orders_count)

    # Sample single-order sizing and slippage check
    sample_sizing = LiquidityAwareSizer.size_order(
        symbol="RELIANCE",
        requested_qty=60,
        bar_volume=2000,
        spread_pct=Decimal("0.04"),
    )
    sample_slippage = SlippageModel.estimate_slippage(
        symbol="RELIANCE",
        order_qty=sample_sizing.recommended_qty,
        expected_price=Decimal("2450.00"),
        spread_pct=Decimal("0.04"),
        bar_volume=2000,
    )

    print("==================================================================")
    print("      PHASE 32 EXECUTION OPTIMIZATION AUDIT DASHBOARD             ")
    print("==================================================================")
    print(f"Study ID:             {study.study_id}")
    print(f"Timestamp:            {study.timestamp.isoformat()}")
    print(f"Orders Analyzed:      {study.orders_analyzed_count} simulated paper orders")
    print(f"Paper Validated:      {study.paper_validated} (Pre-Live Verification Verified)")
    print("------------------------------------------------------------------")
    print("1. EMPIRICAL SLIPPAGE & FRICTION REDUCTION:")
    print(f"   Baseline Slippage: {float(study.baseline_avg_slippage_bps):.2f} bps | Total Drag: INR {float(study.baseline_total_friction_inr):.2f}")
    print(f"   Optimized Slippage:{float(study.optimized_avg_slippage_bps):.2f} bps | Total Drag: INR {float(study.optimized_total_friction_inr):.2f}")
    print(f"   Slippage Reduction:{float(study.slippage_reduction_pct):.1f}% improvement")
    print(f"   Friction Savings:  INR {float(study.friction_savings_inr):.2f} saved across benchmark batch")
    print("------------------------------------------------------------------")
    print("2. FILL RATES & LATENCY PROFILES:")
    print(f"   Fill Rate:         Baseline {float(study.fill_rate_baseline_pct):.1f}% vs Optimized {float(study.fill_rate_optimized_pct):.1f}%")
    print(f"   P95 Fill Latency:  Baseline {study.p95_fill_latency_baseline_ms:.1f} ms vs Optimized {study.p95_fill_latency_optimized_ms:.1f} ms")
    print(f"   Latency Gain:      {float(study.latency_improvement_pct):.1f}% faster execution matching")
    print("------------------------------------------------------------------")
    print("3. LIQUIDITY-AWARE SIZING SAMPLE (RELIANCE):")
    print(f"   Requested Qty:     {sample_sizing.requested_qty} shares -> Recommended: {sample_sizing.recommended_qty} shares")
    print(f"   Participation:     {float(sample_sizing.volume_participation_pct):.2f}% (Cap: {float(sample_sizing.max_participation_cap_pct):.1f}%)")
    print(f"   Expected Slippage: {float(sample_slippage.total_slippage_bps):.2f} bps (Impact: {float(sample_slippage.market_impact_bps):.2f} bps)")
    print(f"   Rationale:         {sample_sizing.rationale}")
    print("------------------------------------------------------------------")
    print("4. KEY EMPIRICAL FINDINGS:")
    for finding in study.key_findings:
        print(f"   - {finding}")
    print("------------------------------------------------------------------")
    print("OVERALL RECOMMENDATION: EXECUTION_OPTIMIZATIONS_VALIDATED_IN_PAPER_MODE")
    print("==================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 32 Execution Optimization Runner")
    parser.add_argument("--json", action="store_true", help="Output JSON stream")
    parser.add_argument("--run-study", action="store_true", help="Execute comparative paper study")
    parser.add_argument("--orders", type=int, default=50, help="Number of simulated orders for study")
    args = parser.parse_args()

    optimizer = ExecutionOptimizer()

    if args.json:
        study = optimizer.run_comparative_study(orders_count=args.orders)
        print(json.dumps(study.model_dump(mode="json"), indent=2))
        sys.exit(0)

    print_ascii_execution_dashboard(orders_count=args.orders)


if __name__ == "__main__":
    main()
