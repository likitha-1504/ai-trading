"""CLI Management Utility for Phase 37 Long-Term Autonomous System.

Provides operator commands for:
- System status inspection and real-time state reporting
- Multi-phase prerequisite verification audit
- Executing complete autonomous session lifecycle workflows
- Dynamic portfolio rebalancing under release gate governance
- Release gate token verification and evaluation
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.long_term_autonomous.lifecycle_orchestrator import LongTermAutonomousOrchestrator
from app.long_term_autonomous.models import (
    ReleaseGateRequest,
    ReleaseGateType,
)
from app.models.contracts import (
    MarketSource,
    NormalizedMarketEvent,
    TradeSide,
)


def run_status(orch: LongTermAutonomousOrchestrator, as_json: bool) -> None:
    status = orch.get_system_status()
    if as_json:
        print(json.dumps(status, indent=2, default=str))
        return

    print("=" * 65)
    print("PHASE 37: LONG-TERM AUTONOMOUS SYSTEM STATUS")
    print("=" * 65)
    print(f"State:                   {status['state']}")
    print(f"Session ID:              {status['session_id'] or 'None'}")
    print(f"Current Capital:         INR {status['capital']:.2f}")
    print(f"Initial Session Capital: INR {status['initial_capital_session']:.2f}")
    print(f"Circuit Breaker Tripped: {status['circuit_breaker_tripped']}")
    print(f"Square-off Completed:    {status['square_off_completed']}")
    print(f"Trades Executed:         {status['executed_trades']} (Wins: {status['winning_trades']}, Losses: {status['losing_trades']})")
    print(f"Consecutive Losses:      {status['consecutive_losses']}")
    print(f"Active Positions:        {status['active_positions_count']}")

    print("\n--- Strategy Portfolio ---")
    port = status["portfolio"]
    print(f"Active Strategies:       {port['active_strategy_count']}")
    for name, strat in port["strategies"].items():
        print(
            f"  - [{strat['lifecycle_stage']}] {name}: Weight {strat['target_weight_pct']}%, "
            f"Win Rate: {strat['rolling_win_rate_pct']}%, Sharpe: {strat['rolling_sharpe']}, "
            f"Trades: {strat['total_trades']}"
        )
    print("=" * 65)


def run_prerequisites(orch: LongTermAutonomousOrchestrator, as_json: bool) -> None:
    audit = orch.execute_pre_market_audit()
    if as_json:
        print(json.dumps(audit.model_dump(mode="json"), indent=2))
        return

    print("=" * 65)
    print("PHASE 37: MULTI-PHASE PREREQUISITE VERIFICATION AUDIT")
    print("=" * 65)
    print(f"Audit ID:       {audit.audit_id}")
    print(f"Overall Status: {'PASSED' if audit.is_all_passed else 'FAILED'}")
    print("-" * 65)
    for dim, passed in audit.dimension_results.items():
        status_str = "[PASS]" if passed else "[FAIL]"
        detail = audit.details.get(dim.value, "")
        print(f"{status_str:7} {dim.value:<26} : {detail}")
    print("=" * 65)


def run_session_lifecycle(orch: LongTermAutonomousOrchestrator, token: str, as_json: bool) -> None:
    print("Step 1: Running Pre-Market Audit...")
    audit = orch.execute_pre_market_audit()
    if not audit.is_all_passed:
        print("ERROR: Prerequisite audit failed! Cannot start session.")
        return

    print("Step 2: Activating Autonomous Session with Release Token...")
    session_id = orch.start_session(operator_id="OPERATOR_CLI", operator_token=token)
    print(f"  -> Session {session_id} ACTIVE.")

    print("Step 3: Processing Intraday Market Events & Simulated Trades...")
    now = datetime.now(timezone.utc)
    # Simulate a market tick
    tick = NormalizedMarketEvent(
        symbol="RELIANCE",
        source=MarketSource.PAPER,
        exchange_timestamp=now,
        last_price=Decimal("2500.00"),
        volume=1000,
        bid_price=Decimal("2499.50"),
        ask_price=Decimal("2500.50"),
        bid_quantity=100,
        ask_quantity=100,
        spread_pct=Decimal("0.04"),
    )
    orch.process_market_tick(tick)

    # Record two simulated trades
    orch.record_trade_completion(
        strategy_name="MOMENTUM_CONTINUATION",
        symbol="RELIANCE",
        side=TradeSide.BUY,
        pnl=Decimal("1.50"),
    )
    orch.record_trade_completion(
        strategy_name="EARLY_MOVE_DETECTION",
        symbol="INFY",
        side=TradeSide.BUY,
        pnl=Decimal("0.80"),
    )
    print(f"  -> Processed 2 trades. Current Capital: INR {orch.capital:.2f}")

    print("Step 4: Triggering Mandatory 15:15 IST Intraday Cutoff Auto-Square-Off...")
    squared_off = orch.trigger_intraday_cutoff()
    print(f"  -> Intraday Cutoff: {squared_off} positions squared off.")

    print("Step 5: Executing Post-Market Reconciliation & Cryptographic Archival...")
    summary = orch.execute_post_market_reconciliation()
    print(f"  -> Session {summary.session_id} ARCHIVED.")
    print(f"  -> Net PnL: INR {summary.realized_pnl:.2f}, Ledger Hash: {summary.reconciliation_hash[:16]}...")

    if as_json:
        print(json.dumps(summary.model_dump(mode="json"), indent=2))


def run_rebalance(orch: LongTermAutonomousOrchestrator, token: str, as_json: bool) -> None:
    print("Generating Sharpe-Weighted Rebalance Proposal...")
    proposal = orch.portfolio_governor.generate_rebalance_proposal(method="SHARPE_WEIGHTED")
    print(f"Proposed Weights: {proposal.proposed_weights}")

    print("Applying Rebalance Proposal with Operator Release Token...")
    applied = orch.portfolio_governor.apply_rebalance_proposal(
        proposal=proposal,
        operator_token=token,
        operator_id="OPERATOR_CLI",
    )
    print(f"Successfully Applied Dynamic Weights: {applied}")
    if as_json:
        print(json.dumps({k: float(v) for k, v in applied.items()}, indent=2))


def run_verify_release(orch: LongTermAutonomousOrchestrator, release_type_str: str, token: str, as_json: bool) -> None:
    rel_type = ReleaseGateType(release_type_str)
    req = ReleaseGateRequest(
        release_type=rel_type,
        operator_id="OPERATOR_CLI",
        operator_token=token,
        target_identifier="TEST_TARGET",
    )
    decision = orch.release_gate.evaluate_release(req)
    if as_json:
        print(json.dumps(decision.model_dump(mode="json"), indent=2))
        return

    print("=" * 65)
    print("RELEASE GATE EVALUATION")
    print("=" * 65)
    print(f"Decision ID: {decision.decision_id}")
    print(f"Approved:    {decision.is_approved}")
    print(f"Reason:      {decision.reason}")
    print(f"Audit Hash:  {decision.audit_hash or 'None'}")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 37 Long-Term Autonomous System CLI Runner")
    parser.add_argument("--status", action="store_true", help="Print overall system status")
    parser.add_argument("--check-prerequisites", action="store_true", help="Run multi-phase prerequisite audit")
    parser.add_argument("--run-session", action="store_true", help="Run full autonomous session lifecycle")
    parser.add_argument("--rebalance", action="store_true", help="Generate and apply dynamic portfolio rebalance")
    parser.add_argument("--verify-release", type=str, help="Verify release gate token for release type")
    parser.add_argument("--token", type=str, default="RELEASE-AUTONOMOUS-SESSION-VALID-2026-TOKEN", help="Operator release token")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    orch = LongTermAutonomousOrchestrator()

    if args.status:
        run_status(orch, args.json)
    elif args.check_prerequisites:
        run_prerequisites(orch, args.json)
    elif args.run_session:
        run_session_lifecycle(orch, args.token, args.json)
    elif args.rebalance:
        token = args.token if "REBALANCE" in args.token else "RELEASE-PORTFOLIO-REBALANCE-VALID-2026"
        run_rebalance(orch, token, args.json)
    elif args.verify_release:
        run_verify_release(orch, args.verify_release, args.token, args.json)
    else:
        run_status(orch, False)


if __name__ == "__main__":
    main()
