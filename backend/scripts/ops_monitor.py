#!/usr/bin/env python3
"""CLI Production Operations and Telemetry Monitor for Phase 25.

Usage:
    python backend/scripts/ops_monitor.py [--db-path PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ops.production_operations import ProductionOperationsMonitor


def format_report(report_dict: dict) -> str:
    """Formats the Production Operations report into an operator-friendly ASCII dashboard."""
    feed = report_dict["data_feed"]
    broker = report_dict["broker_connectivity"]
    db = report_dict["database"]
    lat = report_dict["latency_errors"]
    bkp = report_dict["backups"]

    lines = [
        "==================================================================",
        "          PHASE 25 PRODUCTION OPERATIONS & TELEMETRY MONITOR       ",
        "==================================================================",
        f"Timestamp:    {report_dict['timestamp']}",
        f"System Status: {report_dict['system_status']}",
        f"Environment:   {report_dict['environment']} | Mode: {'PAPER' if report_dict['is_paper_trading'] else 'LIVE'}",
        f"Uptime:        {report_dict['uptime_seconds']} seconds | Version: {report_dict['version']}",
        "------------------------------------------------------------------",
        "1. DATA FEED HEALTH:",
        f"   Status:         [{feed['status']}]",
        f"   Feed Adapter:   {feed['feed_adapter']}",
        f"   Last Tick Age:  {feed['age_seconds']}s (Stale Threshold: {feed['stale_threshold_seconds']}s)",
        f"   Spread Bps:     {feed['spread_bps']} bps (Compliant: {feed['spread_compliant']})",
        f"   Details:        {feed['details']}",
        "------------------------------------------------------------------",
        "2. BROKER CONNECTIVITY:",
        f"   Status:         [{broker['status']}]",
        f"   Adapter:        {broker['adapter_name']}",
        f"   Heartbeat:      {broker['heartbeat_latency_ms']} ms",
        f"   Reconnects:     {broker['reconnect_attempts']} / {broker['max_reconnect_attempts']}",
        f"   Circuit Breaker: Armed={broker['circuit_breaker_armed']}, Tripped={broker['circuit_breaker_tripped']}",
        f"   Details:        {broker['details']}",
        "------------------------------------------------------------------",
        "3. DATABASE STORAGE & WAL HEALTH:",
        f"   Status:         [{db['status']}]",
        f"   Journal Mode:   {db['journal_mode']} | Sync: {db['synchronous']}",
        f"   Integrity:      {'OK' if db['integrity_ok'] else 'FAIL'}",
        f"   DB Size:        {db['db_size_bytes']} bytes | WAL Size: {db['wal_size_bytes']} bytes",
        f"   Write Latency:  {db['write_latency_ms']} ms",
        f"   Open Positions: {db['open_positions']} | Total Orders: {db['total_orders']}",
        "------------------------------------------------------------------",
        "4. LATENCY & ERROR MONITORING:",
        f"   Watcher SLA:    Target <{lat['watcher_sla_target_ms']}ms | Realized Median: {lat['watcher_realized_median_us']} us",
        f"   SLA Compliance: {lat['watcher_compliance_pct']}%",
        f"   Feature Calc:   {lat['feature_compute_avg_ms']} ms",
        f"   DB Commit:      {lat['db_commit_avg_ms']} ms",
        f"   AI Council:     {lat['ai_council_avg_seconds']} s",
        f"   Error Rate:     {lat['error_rate_pct']}% (Errors: {lat['total_errors']}/{lat['total_requests']})",
        "------------------------------------------------------------------",
        "5. HOT BACKUP OPERATIONS:",
        f"   Status:         [{bkp['status']}]",
        f"   Total Backups:  {bkp['total_backups']}",
        f"   Latest Backup:  {bkp['latest_backup_id'] or 'None'}",
        f"   Age:            {bkp['latest_backup_age_hours']} hours (Verified: {bkp['latest_backup_verified']})",
        "==================================================================",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 25 Production Operations Monitor")
    parser.add_argument("--db-path", default="trading_agent.db", help="Path to SQLite database")
    parser.add_argument("--json", action="store_true", help="Output JSON telemetry")
    args = parser.parse_args()

    monitor = ProductionOperationsMonitor(db_path=args.db_path)
    report = monitor.generate_operations_report()
    report_dict = report.model_dump()

    if args.json:
        print(json.dumps(report_dict, indent=2, default=str))
    else:
        print(format_report(report_dict))

    return 0 if report.system_status in ("HEALTHY", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
