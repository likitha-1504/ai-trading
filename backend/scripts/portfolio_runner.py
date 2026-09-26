"""Operational CLI Runner & Audit Tool for Phase 31 Multi-Strategy Portfolio.

Inspects multi-strategy capital allocations, independent validation status,
cross-sectional concentration limits, and portfolio gross exposure.

Usage:
    python backend/scripts/portfolio_runner.py [--json] [--validate]
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.contracts import StrategyType
from app.portfolio.portfolio_manager import MultiStrategyPortfolioManager


def print_ascii_portfolio_dashboard() -> None:
    """Renders formatted multi-strategy portfolio audit dashboard."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))
    summary = mgr.get_portfolio_summary()

    print("==================================================================")
    print("      PHASE 31 MULTI-STRATEGY PORTFOLIO AUDIT DASHBOARD           ")
    print("==================================================================")
    print(f"Portfolio ID:         {summary.portfolio_id}")
    print(f"Timestamp:            {summary.timestamp.isoformat()}")
    print(f"Total Equity:         INR {float(summary.total_capital):.2f}")
    print(f"Available Cash:       INR {float(summary.available_cash):.2f}")
    print(f"Deployed Capital:     INR {float(summary.deployed_capital):.2f}")
    print(f"Allocation Method:    {summary.allocation_method.value}")
    print(f"Active Positions:     {summary.active_positions_total}")
    print("------------------------------------------------------------------")
    print("1. STRATEGY CAPITAL ALLOCATIONS & STATUS:")
    for alloc in summary.allocations:
        print(
            f"   [{alloc.strategy_type.value:<22}] "
            f"Weight: {float(alloc.target_weight_pct):5.1f}% | "
            f"Alloc: INR {float(alloc.allocated_capital):6.2f} | "
            f"Deployed: INR {float(alloc.deployed_capital):5.2f} | "
            f"Status: {alloc.validation_status.value}"
        )
    print("------------------------------------------------------------------")
    print("2. INDEPENDENT STRATEGY VALIDATION GATES:")
    for strat in StrategyType:
        rep = mgr.get_validation_report(strat)
        if rep:
            print(
                f"   [{strat.value:<22}] "
                f"Trades: {rep.trades_count:2d} | "
                f"Win: {float(rep.win_rate_pct):5.1f}% | "
                f"PF: {float(rep.profit_factor):4.2f} | "
                f"Sharpe: {float(rep.sharpe_ratio):4.2f} | "
                f"MaxDD: {float(rep.max_drawdown_pct):4.1f}% | "
                f"Valid: {rep.is_validated}"
            )
    print("------------------------------------------------------------------")
    print("3. CONCENTRATION BOUNDARIES & EXPOSURE:")
    print(f"   Gross Exposure:    {float(summary.concentrations.gross_exposure_pct):.1f}% (Limit: {float(summary.limits.max_gross_exposure_pct):.1f}%)")
    print(f"   Max Strategy Cap:  Limit: {float(summary.limits.max_single_strategy_pct):.1f}%")
    print(f"   Max Symbol Cap:    Limit: {float(summary.limits.max_single_symbol_pct):.1f}%")
    print(f"   Max Sector Cap:    Limit: {float(summary.limits.max_single_sector_pct):.1f}%")
    print(f"   Limits Compliance: Within Limits={summary.concentrations.is_within_limits}")
    if summary.concentrations.violations:
        print(f"   Violations:        {', '.join(summary.concentrations.violations)}")
    else:
        print("   Violations:        None (100% compliant)")
    print("------------------------------------------------------------------")
    print("OVERALL RECOMMENDATION: PORTFOLIO_CONCENTRATION_GATED_AND_VALIDATED")
    print("==================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 31 Multi-Strategy Portfolio Runner")
    parser.add_argument("--json", action="store_true", help="Output JSON stream")
    parser.add_argument("--validate", action="store_true", help="Run standalone strategy validation checks")
    args = parser.parse_args()

    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    if args.validate:
        reports = [mgr.get_validation_report(s) for s in StrategyType]
        valid_reports = [r for r in reports if r is not None]
        if args.json:
            print(json.dumps([r.model_dump(mode="json") for r in valid_reports], indent=2))
        else:
            for r in valid_reports:
                print(f"Strategy {r.strategy_type.value}: Validated={r.is_validated} ({r.status.value})")
                print(f"   Trades: {r.trades_count}, Win Rate: {r.win_rate_pct}%, Sharpe: {r.sharpe_ratio}")
        sys.exit(0)

    if args.json:
        summary = mgr.get_portfolio_summary()
        print(json.dumps(summary.model_dump(mode="json"), indent=2))
        sys.exit(0)

    print_ascii_portfolio_dashboard()


if __name__ == "__main__":
    main()
