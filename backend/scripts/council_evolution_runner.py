"""Operational CLI Runner & Governance Tool for Phase 36 AI Council Evolution.

Enables command-line evaluation of candidate model justification scorecards,
deterministic Trade Gate & Position Watcher decoupling audits, and governed
model admission.

Usage:
    python backend/scripts/council_evolution_runner.py [--status] [--candidates]
                                                       [--benchmark CANDIDATE_ID]
                                                       [--audit-independence]
                                                       [--admit CANDIDATE_ID --token TOKEN]
                                                       [--audit] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.council_evolution.evolution_orchestrator import CouncilEvolutionOrchestrator
from app.council_evolution.models import (
    CouncilIndependenceAttestation,
    ModelJustificationScorecard,
)


def print_ascii_scorecard(sc: ModelJustificationScorecard) -> None:
    """Renders formatted ASCII scorecard for a candidate model."""
    m = sc.realized_metrics
    h = sc.hurdles_evaluated
    print("-" * 72)
    print(f"CANDIDATE: {sc.candidate_id:24s} | {sc.model_name}")
    print(f"Proposed Role: {sc.role.value:20s} | Status: {sc.status.value} (Justified: {sc.is_justified})")
    print("-" * 72)
    print(f"1. Directional Accuracy Uplift: {m.accuracy_uplift_pct:+.1f}% (Hurdle: >= +{h.min_accuracy_uplift_pct:.1f}%)")
    print(f"2. Downside Capital Preserved:  INR {m.downside_capital_saved_inr:.2f} (Hurdle: >= INR {h.min_downside_capital_saved:.2f})")
    print(f"3. Reasoning Diversity Index:   {m.reasoning_diversity_score:.2f} (Hurdle: >= {h.min_diversity_score:.2f})")
    print(f"4. P95 Inference Latency:       {m.p95_latency_ms:.0f} ms (Budget: <= {h.max_p95_latency_ms:.0f} ms)")
    print(f"5. Token Economic Cost Ratio:   {m.token_cost_ratio:.2f}x (Budget: <= {h.max_token_cost_ratio:.2f}x)")
    print("-" * 72)
    if sc.is_justified:
        print("[PASS] Measurable Justification Verified across all 5 criteria.")
        for r in sc.admission_reasons:
            print(f"  + {r}")
    else:
        print("[REJECT] Breached Measurable Justification Hurdles:")
        for r in sc.rejection_reasons:
            print(f"  - {r}")
    print()


def print_ascii_attestation(att: CouncilIndependenceAttestation) -> None:
    """Renders formatted ASCII attestation of safety decoupling from AI availability."""
    print("=" * 72)
    print("         SAFETY SYSTEMS DECOUPLING & INDEPENDENCE ATTESTATION    ")
    print("=" * 72)
    print(f"Attestation Hash:            {att.attestation_hash}")
    print(f"Trade Gate Zero-LLM Dep:     {att.trade_gate_zero_llm_dependency} (Deterministic fallback verified)")
    print(f"Position Watcher Zero-LLM:   {att.position_watcher_zero_llm_dependency} (Dedicated sub-50ms tick loop)")
    print(f"Total AI Blackout Tested:    {att.models_offline_blackout_tested} (Survival during 100% LLM outage)")
    print(f"AI Override Immunity:        {att.unanimous_ai_buy_override_blocked} (100% AI BUY cannot breach risk caps)")
    print(f"Watcher Sub-50ms SLA Met:    {att.position_watcher_sub_50ms_sla} (Realized: {att.realized_watcher_latency_us:.1f} µs)")
    print("-" * 72)
    print("DRILL EVIDENCE SUMMARY:")
    for k, v in att.evidence_details.items():
        print(f"  [{k}]: {v}")
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 36 AI Council Evolution Runner")
    parser.add_argument("--status", action="store_true", help="Display active council composition and summary")
    parser.add_argument("--candidates", action="store_true", help="List all candidate scorecards")
    parser.add_argument("--benchmark", type=str, metavar="CANDIDATE_ID", help="Benchmark candidate for measurable justification")
    parser.add_argument("--audit-independence", action="store_true", help="Audit Trade Gate & Position Watcher decoupling from AI")
    parser.add_argument("--admit", type=str, metavar="CANDIDATE_ID", help="Attempt candidate model admission")
    parser.add_argument("--token", type=str, help="Operator authorization token for model admission")
    parser.add_argument("--audit", action="store_true", help="Run comprehensive Phase 36 audit")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    orchestrator = CouncilEvolutionOrchestrator()

    # 1. Status
    if args.status:
        active = orchestrator.admission_gate.get_active_council()
        candidates = orchestrator.admission_gate.list_candidate_scorecards()
        payload = {
            "active_council_models": active,
            "candidates_count": len(candidates),
            "justified_count": sum(1 for c in candidates if c.is_justified),
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("=" * 72)
            print("                 AI COUNCIL ACTIVE COMPOSITION                  ")
            print("=" * 72)
            for m in active:
                print(f"- {m['model_id']:24s} | {m['name']:28s} | Role: {m['role']}")
            print("-" * 72)
            print(f"Evaluated Candidates: {len(candidates)} ({payload['justified_count']} justified)")
            print("=" * 72)
        sys.exit(0)

    # 2. Candidates
    if args.candidates:
        scorecards = orchestrator.admission_gate.list_candidate_scorecards()
        if args.json:
            print(json.dumps([s.model_dump() for s in scorecards], default=str, indent=2))
        else:
            print("=" * 72)
            print("         AI COUNCIL CANDIDATE MODEL JUSTIFICATION SCORECARDS    ")
            print("=" * 72)
            for s in scorecards:
                print_ascii_scorecard(s)
        sys.exit(0)

    # 3. Benchmark
    if args.benchmark:
        scorecard = orchestrator.admission_gate.evaluate_candidate(args.benchmark)
        if args.json:
            print(json.dumps(scorecard.model_dump(), default=str, indent=2))
        else:
            print_ascii_scorecard(scorecard)
        sys.exit(0 if scorecard.is_justified else 1)

    # 4. Independence Audit
    if args.audit_independence:
        att = orchestrator.independence_guard.audit_complete_independence()
        if args.json:
            print(json.dumps(att.model_dump(), default=str, indent=2))
        else:
            print_ascii_attestation(att)
        sys.exit(0)

    # 5. Admit Model
    if args.admit:
        if not args.token:
            print("Error: --token is required for model admission.", file=sys.stderr)
            sys.exit(1)
        res = orchestrator.admission_gate.admit_model(args.admit, operator_token=args.token)
        if args.json:
            print(json.dumps(res.model_dump(), default=str, indent=2))
        else:
            print(f"Model '{args.admit}' successfully admitted to the active AI council.")
            print_ascii_scorecard(res)
        sys.exit(0)

    # 6. Comprehensive Audit (default)
    report = orchestrator.run_council_evolution_audit()
    if args.json:
        print(json.dumps(report.model_dump(), default=str, indent=2))
    else:
        print("=" * 72)
        print("            PHASE 36 COMPREHENSIVE AI COUNCIL EVOLUTION AUDIT   ")
        print("=" * 72)
        print(f"Audit ID:                {report.audit_id}")
        print(f"Timestamp:               {report.timestamp.isoformat()}")
        print(f"Active Models Count:     {len(report.active_council_models)}")
        print(f"Overall Status:          {report.overall_status}")
        print_ascii_attestation(report.independence_attestation)
        print("CANDIDATE SCORECARDS EVALUATED:")
        for sc in report.candidate_scorecards:
            print_ascii_scorecard(sc)

    sys.exit(0 if report.overall_status == "AUDIT_VERIFIED" else 1)


if __name__ == "__main__":
    main()
