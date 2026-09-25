"""Database integrity and financial accounting verification engine for Phase 23."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CORE_REQUIRED_TABLES = [
    "capital_state",
    "positions",
    "orders",
    "trades",
    "candidates",
    "features",
    "ai_analyses",
    "trade_plans",
    "risk_events",
    "strategy_versions",
    "model_calls",
    "execution_metrics",
    "system_events",
    "strategy_proposals",
]


class TableIntegrityStats(BaseModel):
    """Integrity and row count statistics for a database table."""

    table_name: str
    exists: bool
    row_count: int
    has_indices: bool


class IntegrityReport(BaseModel):
    """Consolidated database and financial integrity audit report."""

    db_path: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_healthy: bool
    journal_mode: str
    synchronous: str
    integrity_check_passed: bool
    integrity_check_output: str
    foreign_keys_passed: bool
    foreign_key_violations: list[str] = Field(default_factory=list)
    missing_tables: list[str] = Field(default_factory=list)
    tables: list[TableIntegrityStats] = Field(default_factory=list)
    accounting_reconciled: bool
    accounting_issues: list[str] = Field(default_factory=list)
    capital_invariants_passed: bool
    capital_issues: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class DatabaseIntegrityVerifier:
    """Verifies SQLite storage integrity, WAL journaling, and financial accounting consistency."""

    def __init__(self, db_path: str = "trading_agent.db") -> None:
        self.db_path = db_path

    def run_full_verification(self) -> IntegrityReport:
        """Executes full diagnostic suite over SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            # 1. PRAGMA integrity_check
            cur.execute("PRAGMA integrity_check;")
            row = cur.fetchone()
            integrity_str = row[0] if row else "UNKNOWN"
            integrity_passed = integrity_str.lower() == "ok"

            # 2. PRAGMA journal_mode & synchronous
            cur.execute("PRAGMA journal_mode;")
            journal_mode = str(cur.fetchone()[0]).upper()

            cur.execute("PRAGMA synchronous;")
            sync_val = str(cur.fetchone()[0])
            sync_map = {"0": "OFF", "1": "NORMAL", "2": "FULL", "3": "EXTRA"}
            synchronous_str = sync_map.get(sync_val, sync_val)

            # 3. PRAGMA foreign_key_check
            cur.execute("PRAGMA foreign_key_check;")
            fk_violations_raw = cur.fetchall()
            foreign_keys_passed = len(fk_violations_raw) == 0
            fk_violations = [
                f"Table {r[0]} rowid {r[1]} references {r[2]} (fkid {r[3]})"
                for r in fk_violations_raw
            ]

            # 4. Check core tables and indices
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            existing_tables = {r[0] for r in cur.fetchall()}

            missing_tables = [t for t in CORE_REQUIRED_TABLES if t not in existing_tables]
            table_stats: list[TableIntegrityStats] = []

            for t in existing_tables:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                count = cur.fetchone()[0]
                cur.execute(f"PRAGMA index_list({t});")
                indices = cur.fetchall()
                table_stats.append(
                    TableIntegrityStats(
                        table_name=t,
                        exists=True,
                        row_count=count,
                        has_indices=len(indices) > 0,
                    )
                )

            # 5. Financial Accounting Consistency Check
            accounting_issues: list[str] = []
            if "trades" in existing_tables:
                cur.execute("PRAGMA table_info(trades);")
                trade_cols = {col["name"] for col in cur.fetchall()}
                id_col = "id" if "id" in trade_cols else ("trade_id" if "trade_id" in trade_cols else None)
                gross_col = "gross_pnl" if "gross_pnl" in trade_cols else None
                net_col = "net_pnl" if "net_pnl" in trade_cols else None
                friction_col = "total_friction" if "total_friction" in trade_cols else ("friction" if "friction" in trade_cols else None)

                if id_col and gross_col and net_col and friction_col:
                    cur.execute(
                        f"SELECT {id_col} AS tid, {gross_col} AS gross, {net_col} AS net, {friction_col} AS friction FROM trades;"
                    )
                    for tr in cur.fetchall():
                        tid = tr["tid"]
                        try:
                            gross = Decimal(str(tr["gross"]))
                            net = Decimal(str(tr["net"]))
                            # Friction is stored as JSON or string or Decimal or numeric
                            import json
                            f_data = tr["friction"]
                            if isinstance(f_data, str) and f_data.startswith("{"):
                                f_dict = json.loads(f_data)
                                f_total = Decimal(str(f_dict.get("total_friction", "0.00")))
                            else:
                                f_total = Decimal(str(f_data or "0.00"))

                            expected_net = gross - f_total
                            # Check rounding tolerance (within 2 paise)
                            diff = abs(net - expected_net)
                            if diff > Decimal("0.02"):
                                accounting_issues.append(
                                    f"Trade {tid} math discrepancy: gross {gross} - friction {f_total} = {expected_net}, but net_pnl is {net} (diff: {diff})"
                                )
                        except (ValueError, TypeError, json.JSONDecodeError) as e:
                            accounting_issues.append(f"Trade {tid} invalid numeric data: {e}")

            accounting_reconciled = len(accounting_issues) == 0

            # 6. Capital Invariants Check
            capital_issues: list[str] = []
            if "capital_state" in existing_tables:
                cur.execute("PRAGMA table_info(capital_state);")
                cap_cols = {col["name"] for col in cur.fetchall()}
                equity_col = "total_capital" if "total_capital" in cap_cols else ("total_equity" if "total_equity" in cap_cols else None)
                avail_col = "available_capital" if "available_capital" in cap_cols else None

                if equity_col and avail_col:
                    cur.execute(
                        f"SELECT {equity_col} AS equity, {avail_col} AS avail FROM capital_state ORDER BY id DESC LIMIT 1;"
                    )
                    cap_row = cur.fetchone()
                    if cap_row:
                        try:
                            equity = Decimal(str(cap_row["equity"]))
                            avail = Decimal(str(cap_row["avail"]))
                            if equity < Decimal("0.00"):
                                capital_issues.append(f"Negative total equity: {equity}")
                            if avail > equity:
                                capital_issues.append(
                                    f"Available capital ({avail}) exceeds total equity ({equity})"
                                )
                        except (ValueError, TypeError) as e:
                            capital_issues.append(f"Invalid capital row values: {e}")

            capital_invariants_passed = len(capital_issues) == 0

            # Overall Health Determination
            is_healthy = (
                integrity_passed
                and foreign_keys_passed
                and len(missing_tables) == 0
                and accounting_reconciled
                and capital_invariants_passed
                and journal_mode in ("WAL", "MEMORY")
            )

            return IntegrityReport(
                db_path=self.db_path,
                is_healthy=is_healthy,
                journal_mode=journal_mode,
                synchronous=synchronous_str,
                integrity_check_passed=integrity_passed,
                integrity_check_output=integrity_str,
                foreign_keys_passed=foreign_keys_passed,
                foreign_key_violations=fk_violations,
                missing_tables=missing_tables,
                tables=table_stats,
                accounting_reconciled=accounting_reconciled,
                accounting_issues=accounting_issues,
                capital_invariants_passed=capital_invariants_passed,
                capital_issues=capital_issues,
                diagnostics={
                    "sqlite_version": sqlite3.sqlite_version,
                    "tables_verified_count": len(table_stats),
                },
            )
        finally:
            conn.close()
