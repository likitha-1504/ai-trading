"""CLI Runner for Phase 18 Paper Trading Validation."""

import os
import sys
from decimal import Decimal

# Ensure backend root is on sys.path when runner is called directly
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.paper.paper_validator import PaperTradingValidator, PaperValidationConfig


def main() -> int:
    """Execute Phase 18 Paper Trading Validation, generate markdown report, and log summary."""
    print("=" * 80)
    print("AI MICRO-TRADING AGENT: PHASE 18 PAPER TRADING VALIDATION RUNNER")
    print("=" * 80)

    db_path = "paper_validation.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            if os.path.exists(f"{db_path}-wal"):
                os.remove(f"{db_path}-wal")
            if os.path.exists(f"{db_path}-shm"):
                os.remove(f"{db_path}-shm")
        except OSError as e:
            print(f"Warning: Could not remove old db files: {e}")

    cfg = PaperValidationConfig(
        initial_capital=Decimal("100.00"),
        autonomous_threshold=Decimal("300.00"),
        slippage_ticks=1,
        tick_size=Decimal("0.05"),
        num_sessions=5,
        db_path=db_path,
        enable_crash_recovery_test=True,
    )

    validator = PaperTradingValidator(config=cfg)
    result = validator.run_validation()

    # Write report markdown to root
    report_path = "PAPER_TRADING_VALIDATION_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result.report_markdown)

    print(f"\n[+] Validation Report generated successfully at: {report_path}")
    print("\n--- SUMMARY METRICS ---")
    print(f"Run ID:             {result.run_id}")
    print(f"Initial Capital:    INR {result.initial_capital:.2f}")
    print(f"Final Equity:       INR {result.final_equity:.2f}")
    print(f"Net Realized P/L:   INR {result.net_pnl:.2f}")
    print(f"Win Rate:           {result.win_rate_pct:.1f}%")
    print(f"Profit Factor:      {result.profit_factor:.2f}")
    print(f"Max Drawdown:       {result.max_drawdown_pct:.2f}% (INR {result.max_drawdown_amount:.2f})")
    print(f"Watcher Latency:    {result.watcher_behavior.median_latency_us:.1f} us (Median)")
    print(f"Sub-50ms Compliant: {result.watcher_behavior.sub_50ms_compliance_rate_pct:.1f}%")
    print(f"Crash Recovery:     {'VERIFIED' if result.recovery_behavior.position_integrity_verified else 'FAILED'}")
    print(f"Reproducibility:    {'100% REPRODUCIBLE' if result.is_fully_reproducible else 'INCOMPLETE'}")
    print("\n[!] GATE RECOMMENDATION:")
    print(f"    {result.gate_recommendation}\n")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
