"""Persistent Idempotency and Duplicate Order Prevention Manager for Phase 33.

Ensures that repeated signal triggers, network retries, or process crash/restarts
never result in duplicate order dispatches to the broker or execution engine.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.db.connection import get_connection
from app.disaster_recovery.models import IdempotencyRecord
from app.execution.execution_engine import DuplicateOrderError

logger = logging.getLogger(__name__)


class IdempotencyManager:
    """Manages persistent and in-memory order fingerprints to prevent duplicate dispatches."""

    def __init__(
        self,
        db_path: str | None = None,
        dedup_window_seconds: float = 60.0,
    ) -> None:
        self.db_path = db_path
        self.dedup_window_seconds = dedup_window_seconds
        self._memory_cache: dict[str, IdempotencyRecord] = {}
        self._fingerprint_cache: dict[str, IdempotencyRecord] = {}
        self._init_table()

    def _init_table(self) -> None:
        """Create idempotency storage table if not exists."""
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS order_idempotency_ledger (
                        client_order_id TEXT PRIMARY KEY,
                        order_fingerprint TEXT NOT NULL,
                        plan_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price_level REAL,
                        created_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_order_idempotency_fingerprint
                    ON order_idempotency_ledger (order_fingerprint, created_at);
                    """
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not initialize idempotency table (falling back to memory): %s", e)

    @staticmethod
    def compute_fingerprint(
        symbol: str,
        side: str,
        quantity: int,
        price_level: Decimal | None,
        plan_id: str,
        time_bucket_seconds: int = 60,
        as_of: datetime | None = None,
    ) -> str:
        """Generates deterministic cryptographic order fingerprint for time bucket."""
        now = as_of or datetime.now(timezone.utc)
        bucket = int(now.timestamp()) // time_bucket_seconds
        price_str = f"{price_level:.2f}" if price_level is not None else "MARKET"
        raw_key = f"{symbol.upper()}:{side.upper()}:{quantity}:{price_str}:{plan_id}:{bucket}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def check_and_register_order(
        self,
        client_order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price_level: Decimal | None,
        plan_id: str,
        as_of: datetime | None = None,
    ) -> IdempotencyRecord:
        """Validates that order is not a duplicate and registers it.

        Raises DuplicateOrderError if client_order_id exists or identical fingerprint
        was submitted within the deduplication window.
        """
        now = as_of or datetime.now(timezone.utc)
        fingerprint = self.compute_fingerprint(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price_level=price_level,
            plan_id=plan_id,
            as_of=now,
        )

        # 1. Check in-memory caches
        if client_order_id in self._memory_cache:
            prev = self._memory_cache[client_order_id]
            elapsed = (now - prev.created_at).total_seconds()
            if elapsed <= self.dedup_window_seconds:
                raise DuplicateOrderError(
                    f"Duplicate order {client_order_id} detected in memory (submitted {elapsed:.1f}s ago)"
                )

        if fingerprint in self._fingerprint_cache:
            prev_fp = self._fingerprint_cache[fingerprint]
            elapsed_fp = (now - prev_fp.created_at).total_seconds()
            if elapsed_fp <= self.dedup_window_seconds:
                raise DuplicateOrderError(
                    f"Duplicate order fingerprint detected for {symbol} {side} (matched order {prev_fp.client_order_id}, {elapsed_fp:.1f}s ago)"
                )

        # 2. Check persistent database store
        self._check_db_duplicates(client_order_id, fingerprint, now)

        # 3. Register record
        record = IdempotencyRecord(
            client_order_id=client_order_id,
            order_fingerprint=fingerprint,
            plan_id=plan_id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            price_level=price_level,
            created_at=now,
            status="RECORDED",
        )

        self._memory_cache[client_order_id] = record
        self._fingerprint_cache[fingerprint] = record
        self._save_to_db(record)
        return record

    def _check_db_duplicates(
        self, client_order_id: str, fingerprint: str, now: datetime
    ) -> None:
        """Query persistent database to detect duplicates across process restarts."""
        try:
            with get_connection(self.db_path) as conn:
                # Check client_order_id
                cur = conn.execute(
                    "SELECT client_order_id, created_at FROM order_idempotency_ledger WHERE client_order_id = ?",
                    (client_order_id,),
                )
                row = cur.fetchone()
                if row:
                    prev_ts = datetime.fromisoformat(row["created_at"])
                    elapsed = (now - prev_ts).total_seconds()
                    if elapsed <= self.dedup_window_seconds:
                        raise DuplicateOrderError(
                            f"Duplicate client_order_id {client_order_id} found in persistent storage (submitted {elapsed:.1f}s ago)"
                        )

                # Check fingerprint
                cur_fp = conn.execute(
                    "SELECT client_order_id, created_at FROM order_idempotency_ledger WHERE order_fingerprint = ?",
                    (fingerprint,),
                )
                row_fp = cur_fp.fetchone()
                if row_fp:
                    prev_ts = datetime.fromisoformat(row_fp["created_at"])
                    elapsed_fp = (now - prev_ts).total_seconds()
                    if elapsed_fp <= self.dedup_window_seconds:
                        raise DuplicateOrderError(
                            f"Duplicate order fingerprint matched in persistent storage (order {row_fp['client_order_id']}, {elapsed_fp:.1f}s ago)"
                        )
        except DuplicateOrderError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.debug("Idempotency DB lookup error: %s", e)

    def _save_to_db(self, record: IdempotencyRecord) -> None:
        """Persist idempotency record to SQLite table."""
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO order_idempotency_ledger (
                        client_order_id, order_fingerprint, plan_id, symbol,
                        side, quantity, price_level, created_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.client_order_id,
                        record.order_fingerprint,
                        record.plan_id,
                        record.symbol,
                        record.side,
                        record.quantity,
                        float(record.price_level) if record.price_level is not None else None,
                        record.created_at.isoformat(),
                        record.status,
                    ),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not persist idempotency record to SQLite: %s", e)

    def count_records(self) -> int:
        """Returns total recorded orders."""
        try:
            with get_connection(self.db_path) as conn:
                cur = conn.execute("SELECT COUNT(*) AS total FROM order_idempotency_ledger")
                row = cur.fetchone()
                return int(row["total"]) if row else len(self._memory_cache)
        except Exception:  # noqa: BLE001
            return len(self._memory_cache)
