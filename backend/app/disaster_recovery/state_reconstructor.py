"""Cross-Ledger State Reconstruction and Reconciliation Engine for Phase 33.

Reconstructs consistent state across local SQLite WAL storage and broker gateway
after system crashes or network disruptions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.adapters.broker_base import BrokerAdapter
from app.db.repository import DatabaseRepository
from app.disaster_recovery.models import StateReconstructionReport
from app.models.contracts import (
    ReconciliationReport,
)

logger = logging.getLogger(__name__)


class StateReconstructor:
    """Audits and reconciles in-flight trading state between database and broker."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        broker_adapter: BrokerAdapter | None = None,
        db_path: str | None = None,
    ) -> None:
        self.repo = repository or DatabaseRepository(db_path=db_path)
        self.broker = broker_adapter

    def reconstruct_and_reconcile(
        self,
        broker: BrokerAdapter | None = None,
    ) -> StateReconstructionReport:
        """Execute full cross-ledger audit between database state and broker state."""
        active_broker = broker or self.broker
        now = datetime.now(timezone.utc)

        # 1. Fetch Local DB State
        db_positions = self.repo.get_open_positions()
        latest_cap = self.repo.get_latest_capital_state()
        db_equity = (
            Decimal(str(latest_cap["total_capital"]))
            if latest_cap
            else Decimal("100.00")
        )

        db_pos_by_symbol = {p.symbol.upper(): p for p in db_positions}

        # If broker adapter not provided or offline, return DB baseline with warning
        if active_broker is None or not active_broker.is_connected:
            return StateReconstructionReport(
                reconstructed_at=now,
                db_positions_count=len(db_positions),
                broker_positions_count=0,
                matched_positions_count=0,
                orphaned_positions=[],
                phantom_positions=[p.symbol for p in db_positions],
                reconciled_equity=db_equity,
                broker_cash_balance=Decimal("0.00"),
                cash_divergence=db_equity,
                is_divergent=True,
                reconstruction_action="OPERATOR_INTERVENTION_REQUIRED_BROKER_OFFLINE",
            )

        # 2. Fetch Broker State
        broker_positions = active_broker.get_positions()
        broker_balance = active_broker.get_account_balance()
        broker_cash = broker_balance.cash_balance

        broker_pos_by_symbol = {p.symbol.upper(): p for p in broker_positions}

        # 3. Match Positions and Identify Divergences
        matched_symbols: list[str] = []
        orphaned_symbols: list[str] = []  # In broker, missing in DB
        phantom_symbols: list[str] = []   # In DB, missing in broker

        for sym, b_pos in broker_pos_by_symbol.items():
            if sym in db_pos_by_symbol:
                db_p = db_pos_by_symbol[sym]
                if db_p.quantity == b_pos.quantity:
                    matched_symbols.append(sym)
                else:
                    orphaned_symbols.append(f"{sym} (Qty mismatch: DB {db_p.quantity} vs Broker {b_pos.quantity})")
            else:
                orphaned_symbols.append(f"{sym} (Broker qty {b_pos.quantity}, DB missing)")

        for sym, db_p in db_pos_by_symbol.items():
            if sym not in broker_pos_by_symbol:
                phantom_symbols.append(f"{sym} (DB qty {db_p.quantity}, Broker missing)")

        # 4. Check Cash / Equity Divergence
        cash_div = abs(db_equity - broker_cash)
        is_cash_divergent = cash_div > Decimal("0.05")

        is_divergent = bool(orphaned_symbols or phantom_symbols or is_cash_divergent)

        if not is_divergent:
            action = "NO_ACTION_REQUIRED"
        elif not orphaned_symbols and not phantom_symbols and not is_cash_divergent:
            action = "STATE_FULLY_CONSISTENT"
        else:
            action = "OPERATOR_INTERVENTION_REQUIRED"

        # 5. Use Broker's built-in reconciliation if available
        recon_report: ReconciliationReport | None = None
        try:
            recon_report = active_broker.reconcile(db_positions)
        except Exception as e:  # noqa: BLE001
            logger.debug("Broker reconciliation helper error: %s", e)

        report = StateReconstructionReport(
            reconstructed_at=now,
            db_positions_count=len(db_positions),
            broker_positions_count=len(broker_positions),
            matched_positions_count=len(matched_symbols),
            orphaned_positions=orphaned_symbols,
            phantom_positions=phantom_symbols,
            reconciled_equity=db_equity,
            broker_cash_balance=broker_cash,
            cash_divergence=cash_div,
            is_divergent=is_divergent,
            reconstruction_action=action,
            reconciliation_details=recon_report,
        )

        logger.info(
            "State reconstruction complete: %d matched, %d orphans, %d phantoms, cash divergence INR %s",
            len(matched_symbols),
            len(orphaned_symbols),
            len(phantom_symbols),
            cash_div,
        )
        return report
