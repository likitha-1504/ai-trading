"""Operational CLI Runner & Governance Tool for Phase 35 Research Sandbox.

Enables command-line simulation of research experiments, exact reproducibility
verification, dataset integrity auditing, and explicit operator promotion.

Usage:
    python backend/scripts/sandbox_runner.py [--status] [--list] [--run EXP_ID]
                                            [--verify EXP_ID] [--promote EXP_ID]
                                            [--token TOKEN] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.sandbox.dataset_registry import ReproducibleDatasetRegistry
from app.sandbox.isolation_guard import SandboxIsolationGuard
from app.sandbox.models import PromotionRequest, SandboxExecutionResult
from app.sandbox.promotion_gate import ExplicitPromotionGate
from app.sandbox.sandbox_engine import ResearchSandboxEngine
from app.sandbox.versioned_config import VersionedConfigManager


def print_ascii_dashboard(result: SandboxExecutionResult) -> None:
    """Renders formatted operational dashboard for a sandbox experiment execution."""
    m = result.metrics
    print("=" * 72)
    print("               PHASE 35 RESEARCH SANDBOX SIMULATION              ")
    print("=" * 72)
    print(f"Run ID:                  {result.run_id}")
    print(f"Experiment ID:           {result.experiment_id}")
    print(f"Dataset ID:              {result.dataset_id}")
    print(f"Dataset Hash:            {result.dataset_hash[:20]}...")
    print(f"Config Hash:             {result.config_hash[:20]}...")
    print(f"Execution Hash:          {result.execution_hash[:20]}...")
    print(f"Isolation Verified:      {result.isolation_verified}")
    print(f"Reproducibility Checked: {result.reproducibility_verified}")
    print("-" * 72)
    print("SIMULATED PERFORMANCE METRICS (REALISTIC FRICTION & TAXES):")
    print("-" * 72)
    print(f"Total Trades Executed:   {m.total_trades}")
    print(f"Win Rate:                {m.win_rate:.2%} ({m.winning_trades}W / {m.losing_trades}L)")
    print(f"Profit Factor:           {m.profit_factor:.2f}")
    print(f"Annualized Sharpe Ratio: {m.sharpe_ratio:.2f}")
    print(f"Max Drawdown:            {m.max_drawdown_pct:.2f}%")
    print(f"Net PnL (Post-Friction): INR {m.net_pnl:+.2f}")
    print(f"Gross PnL:               INR {m.gross_pnl:+.2f}")
    print(f"Total Fees & Slippage:   INR {m.total_fees_slippage:.2f}")
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 35 Research Sandbox Runner")
    parser.add_argument("--status", action="store_true", help="Display sandbox quarantine and isolation status")
    parser.add_argument("--list", action="store_true", help="List registered datasets and experiment configs")
    parser.add_argument("--run", type=str, metavar="EXP_ID", help="Execute simulation for an experiment ID")
    parser.add_argument("--dataset", type=str, metavar="DS_ID", help="Optional dataset override for simulation")
    parser.add_argument("--verify", type=str, metavar="EXP_ID", help="Verify exact mathematical reproducibility")
    parser.add_argument("--promote", type=str, metavar="EXP_ID", help="Submit experiment for promotion")
    parser.add_argument("--token", type=str, help="Operator authorization token for promotion")
    parser.add_argument("--rationale", type=str, default="Meets research criteria", help="Rationale for promotion")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    datasets = ReproducibleDatasetRegistry()
    configs = VersionedConfigManager()
    isolation = SandboxIsolationGuard()
    engine = ResearchSandboxEngine(
        dataset_registry=datasets,
        config_manager=configs,
        isolation_guard=isolation,
    )
    promotion_gate = ExplicitPromotionGate(engine=engine)

    # 1. Status probe
    if args.status:
        audit = isolation.audit_isolation()
        audit["registered_datasets_count"] = len(datasets.list_datasets())
        audit["registered_configs_count"] = len(configs.list_configs())
        if args.json:
            print(json.dumps(audit, indent=2))
        else:
            print("=" * 72)
            print("                 SANDBOX QUARANTINE STATUS REPORT                ")
            print("=" * 72)
            for k, v in audit.items():
                print(f"{k:28s}: {v}")
            print("=" * 72)
        sys.exit(0)

    # 2. List datasets and configs
    if args.list:
        ds_list = [
            {
                "dataset_id": ds.dataset_id,
                "name": ds.name,
                "record_count": ds.record_count,
                "sha256_hash": ds.sha256_hash[:16] + "...",
                "seed": ds.seed,
            }
            for ds in datasets.list_datasets()
        ]
        cfg_list = [
            {
                "experiment_id": c.experiment_id,
                "strategy": c.strategy_name,
                "dataset_id": c.dataset_id,
                "config_hash": c.config_hash[:16] + "...",
            }
            for c in configs.list_configs()
        ]
        if args.json:
            print(json.dumps({"datasets": ds_list, "configs": cfg_list}, indent=2))
        else:
            print("=" * 72)
            print("REGISTERED REPRODUCIBLE DATASETS:")
            print("-" * 72)
            for d in ds_list:
                print(f"- {d['dataset_id']:32s} | {d['name']:30s} | {d['record_count']} bars | Seed: {d['seed']}")
            print("\nREGISTERED EXPERIMENT CONFIGURATIONS:")
            print("-" * 72)
            for c in cfg_list:
                print(f"- {c['experiment_id']:26s} | {c['strategy']:18s} | Bound: {c['dataset_id']}")
            print("=" * 72)
        sys.exit(0)

    # 3. Verify reproducibility
    if args.verify:
        valid, result, msg = engine.verify_reproducibility(args.verify, args.dataset)
        if args.json:
            print(json.dumps({"reproducibility_verified": valid, "message": msg, "hash": result.execution_hash}, indent=2))
        else:
            print(f"[REPRODUCIBILITY CHECK] Result: {valid} | Status: {msg}")
            print_ascii_dashboard(result)
        sys.exit(0 if valid else 1)

    # 4. Promote
    if args.promote:
        if not args.token:
            print("Error: --token is required for explicit promotion.", file=sys.stderr)
            sys.exit(1)
        req = PromotionRequest(
            experiment_id=args.promote,
            target_environment="PAPER_CANDIDATE",
            operator_token=args.token,
            rationale=args.rationale,
        )
        res = promotion_gate.process_promotion_request(req)
        if args.json:
            print(json.dumps(res.model_dump(), default=str, indent=2))
        else:
            print("=" * 72)
            print("                    PROMOTION GATE DECISION                     ")
            print("=" * 72)
            print(f"Success:                 {res.success}")
            print(f"Experiment ID:           {res.experiment_id}")
            print(f"Stage:                   {res.stage.value}")
            print(f"Audit Ledger ID:         {res.audit_ledger_id}")
            print(f"Message:                 {res.message}")
            print("=" * 72)
        sys.exit(0 if res.success else 1)

    # 5. Run simulation (default or specified)
    target_exp = args.run or "EXP-SANDBOX-EMA-V1"
    result = engine.run_simulation(target_exp, args.dataset)
    if args.json:
        print(json.dumps(result.model_dump(), default=str, indent=2))
    else:
        print_ascii_dashboard(result)


if __name__ == "__main__":
    main()
