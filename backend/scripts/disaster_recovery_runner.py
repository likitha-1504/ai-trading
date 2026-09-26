"""Operational CLI Runner & Audit Tool for Phase 33 Disaster Recovery.

Provides command-line execution of multi-scenario disaster drills,
status evaluation, and structured JSON output.

Usage:
    python backend/scripts/disaster_recovery_runner.py [--run-drill] [--json] [--status]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.disaster_recovery.models import DisasterRecoveryAuditResult
from app.disaster_recovery.recovery_orchestrator import DisasterRecoveryOrchestrator


def print_ascii_dashboard(audit: DisasterRecoveryAuditResult) -> None:
    """Renders formatted operational dashboard for disaster recovery audit."""
    print("=" * 70)
    print("      PHASE 33 DISASTER RECOVERY & FAULT TOLERANCE AUDIT      ")
    print("=" * 70)
    print(f"Audit ID:             {audit.audit_id}")
    print(f"Timestamp:            {audit.timestamp.isoformat()}")
    print(f"Scenarios Tested:     {audit.scenarios_tested}")
    print(f"Scenarios Passed:     {audit.scenarios_passed}/{audit.scenarios_tested}")
    print(f"All Scenarios Passed: {audit.all_passed}")
    print(f"Overall System Status:{audit.system_status.value}")
    print("-" * 70)
    print("FAULT INJECTION & CONTINUITY SCENARIO BREAKDOWN:")
    print("-" * 70)

    for i, res in enumerate(audit.drill_results, start=1):
        status_tag = "[PASS]" if res.passed else "[FAIL]"
        print(f"{i}. {status_tag} {res.scenario.value} ({res.latency_ms:.1f}ms)")
        print(f"   Summary:  {res.description}")
        print(f"   Evidence: {res.verification_evidence}")
        print()

    print("-" * 70)
    if audit.attestation:
        print("SAFE RESUMPTION GOVERNANCE ATTESTATION:")
        print(f"   Attestation ID:      {audit.attestation.attestation_id}")
        print(f"   Operator Token:      {audit.attestation.operator_token}")
        print(f"   Resumption Approved: {audit.attestation.resumption_approved}")
        print(f"   Operational Mode:    {audit.attestation.operational_mode}")
        for note in audit.attestation.notes:
            print(f"     - {note}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 33 Disaster Recovery Audit Tool")
    parser.add_argument("--run-drill", action="store_true", help="Execute full multi-scenario fault injection drill")
    parser.add_argument("--status", action="store_true", help="Display current continuity status")
    parser.add_argument("--json", action="store_true", help="Output audit results as JSON")

    args = parser.parse_args()

    orchestrator = DisasterRecoveryOrchestrator()

    if args.status and not args.run_drill:
        db_health = orchestrator.db_resilience.evaluate_db_health()
        broker_online = orchestrator.broker_resilience.check_connection()
        status_payload = {
            "system_status": orchestrator.safe_resume.current_status.value,
            "database_integrity_ok": db_health.integrity_ok,
            "broker_connected": broker_online,
        }
        if args.json:
            print(json.dumps(status_payload, indent=2))
        else:
            print(f"Status: {status_payload['system_status']} | DB Ok: {status_payload['database_integrity_ok']} | Broker: {status_payload['broker_connected']}")
        sys.exit(0)

    # Default to running drill
    audit = orchestrator.run_comprehensive_disaster_drill()

    if args.json:
        print(json.dumps(audit.model_dump(), default=str, indent=2))
    else:
        print_ascii_dashboard(audit)

    sys.exit(0 if audit.all_passed else 1)


if __name__ == "__main__":
    main()
