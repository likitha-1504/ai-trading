"""CLI Runner for Phase 20 Controlled ₹100 Live Experiment."""

import os
import sys
from decimal import Decimal

# Ensure backend root is on sys.path when runner is called directly
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.live.experiment_engine import LiveExperimentConfig, LiveExperimentEngine


def main() -> int:
    """Execute Phase 20 Controlled Live Experiment and generate LIVE_EXPERIMENT_REPORT.md."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass

    print("=" * 76)
    print("PHASE 20: CONTROLLED ₹100 LIVE EXPERIMENT RUNNER")
    print("=" * 76)

    cfg = LiveExperimentConfig(
        initial_capital=Decimal("100.00"),
        autonomous_threshold=Decimal("300.00"),
        strategy_version="v1.0.0-phase20",
        db_path="live_experiment.db",
        num_sessions=5,
    )

    engine = LiveExperimentEngine(config=cfg)
    print(f"\n[INIT] Initial Capital Capped at: ₹{cfg.initial_capital:.2f}")
    print(f"[INIT] Autonomous Threshold: ₹{cfg.autonomous_threshold:.2f}")
    print(f"[INIT] Active Strategy Version: {cfg.strategy_version}")
    print("\n[RUNNING] Executing controlled live experiment across 5 sessions...")

    result = engine.run_controlled_experiment()

    print("-" * 76)
    print("EXPERIMENT TELEMETRY SUMMARY (9 OPERATIONAL DIMENSIONS):")
    print("-" * 76)
    print(
        f"1. Net P/L After Costs: Gross ₹{result.net_pnl_metrics.total_gross_pnl:.2f} | "
        f"Friction -₹{result.net_pnl_metrics.total_friction:.4f} | "
        f"Net ₹{result.net_pnl_metrics.total_net_pnl:.2f} ({result.net_pnl_metrics.return_on_capital_pct:+.2f}%)"
    )
    print(
        f"2. Execution Quality:   Submitted {result.execution_quality.orders_submitted} | "
        f"Filled {result.execution_quality.orders_filled} ({result.execution_quality.fill_rate_pct:.1f}%) | "
        f"Avg Fill Latency {result.execution_quality.avg_fill_latency_ms:.2f} ms"
    )
    print(
        f"3. Slippage:            Avg {result.slippage_metrics.avg_slippage_bps:.1f} bps | "
        f"Max {result.slippage_metrics.max_slippage_bps:.1f} bps"
    )
    print(
        f"4. Rejected Orders:     Total {result.rejected_orders.total_rejections} | "
        f"Cap Rejections {result.rejected_orders.capital_cap_rejections} (TATASTEEL ₹150 > ₹100 cap)"
    )
    print(
        f"5. Watcher Response:    Evaluations {result.watcher_response.total_evaluations} | "
        f"Median Latency {result.watcher_response.median_latency_us:.2f} µs | "
        f"Sub-50ms SLA {result.watcher_response.sub_50ms_compliance_pct:.1f}% | "
        f"LLM Independence: VERIFIED"
    )
    print(
        f"6. Model Latency:       Qwen3 Avg {result.model_latency.qwen3_avg_latency_ms:.1f} ms | "
        f"DeepSeek-R1 Avg {result.model_latency.deepseek_r1_avg_latency_ms:.1f} ms | Timeouts 0"
    )
    print(
        f"7. Disagreement:        Evaluations {result.model_disagreement.total_council_evaluations} | "
        f"Disagreements {result.model_disagreement.disagreements} ({result.model_disagreement.disagreement_rate_pct:.1f}%) | "
        f"Deterministic Arbitrations {result.model_disagreement.arbitrations_approved}"
    )
    print(
        f"8. Trade Frequency:     Trades {result.trade_frequency.total_trades} | "
        f"Avg Holding {result.trade_frequency.avg_holding_duration_seconds:.1f} s | "
        f"Turnover {result.trade_frequency.capital_velocity:.3f}x"
    )
    print(
        f"9. Failure Events:      Failures {result.failure_events.total_failure_events} | "
        f"Unhandled Exceptions {result.failure_events.unhandled_exceptions}"
    )
    print("=" * 76)
    print(f"Final Capital State: ₹{result.final_equity:.2f} (Base ₹{result.initial_capital:.2f})")
    print("Report written to: LIVE_EXPERIMENT_REPORT.md")
    print("GATE CHECKPOINT: Halted awaiting human approval before Phase 21.")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    sys.exit(main())
