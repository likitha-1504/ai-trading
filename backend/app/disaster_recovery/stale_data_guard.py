"""Stale Market Data Guard for Phase 33 Disaster Recovery.

Prevents trading decisions and order routing based on delayed, frozen, or dropped
market quotes and feed outages.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.disaster_recovery.models import QuoteFreshnessReport, StaleDataThresholds

logger = logging.getLogger(__name__)


class StaleMarketDataError(RuntimeError):
    """Raised when an operation is attempted with stale or missing market data."""


class StaleDataGuard:
    """Monitors quote freshness and feed heartbeats to prevent trading on stale data."""

    def __init__(self, thresholds: StaleDataThresholds | None = None) -> None:
        self.thresholds = thresholds or StaleDataThresholds()
        self._last_quote_times: dict[str, datetime] = {}
        self._last_prices: dict[str, Decimal] = {}
        self._feed_heartbeats: dict[str, datetime] = {}

    def update_quote(
        self,
        symbol: str,
        price: Decimal,
        quote_timestamp: datetime | None = None,
    ) -> None:
        """Register arrival of a new market quote for a symbol."""
        ts = quote_timestamp or datetime.now(timezone.utc)
        self._last_quote_times[symbol.upper()] = ts
        self._last_prices[symbol.upper()] = price

    def record_feed_heartbeat(
        self,
        feed_id: str = "PRIMARY_MARKET_FEED",
        heartbeat_timestamp: datetime | None = None,
    ) -> None:
        """Record heartbeat from the market feed transport."""
        ts = heartbeat_timestamp or datetime.now(timezone.utc)
        self._feed_heartbeats[feed_id] = ts

    def is_feed_alive(
        self,
        feed_id: str = "PRIMARY_MARKET_FEED",
        as_of: datetime | None = None,
    ) -> bool:
        """Check if market feed transport heartbeat is within tolerance."""
        now = as_of or datetime.now(timezone.utc)
        last_hb = self._feed_heartbeats.get(feed_id)
        if last_hb is None:
            return False
        gap = (now - last_hb).total_seconds()
        return gap <= self.thresholds.max_feed_gap_seconds

    def check_quote_freshness(
        self,
        symbol: str,
        as_of: datetime | None = None,
    ) -> QuoteFreshnessReport:
        """Evaluate quote freshness for a specific symbol against thresholds."""
        now = as_of or datetime.now(timezone.utc)
        sym = symbol.upper()
        quote_ts = self._last_quote_times.get(sym)

        if quote_ts is None:
            return QuoteFreshnessReport(
                symbol=sym,
                quote_timestamp=now,
                current_timestamp=now,
                age_seconds=999999.0,
                is_stale=True,
                status="NO_DATA",
                message=f"No quotes recorded for symbol {sym}",
            )

        age = (now - quote_ts).total_seconds()
        is_stale = age > self.thresholds.max_quote_age_seconds

        status = "STALE" if is_stale else "FRESH"
        msg = (
            f"Quote age {age:.2f}s exceeds {self.thresholds.max_quote_age_seconds}s threshold"
            if is_stale
            else f"Quote age {age:.2f}s is within acceptable threshold"
        )

        return QuoteFreshnessReport(
            symbol=sym,
            quote_timestamp=quote_ts,
            current_timestamp=now,
            age_seconds=round(age, 3),
            is_stale=is_stale,
            status=status,
            message=msg,
        )

    def assert_quote_fresh(
        self,
        symbol: str,
        as_of: datetime | None = None,
    ) -> QuoteFreshnessReport:
        """Assert that symbol quote is strictly fresh; raises StaleMarketDataError if stale."""
        report = self.check_quote_freshness(symbol=symbol, as_of=as_of)
        if report.is_stale:
            logger.error("STALE DATA VIOLATION: %s for %s", report.message, symbol)
            raise StaleMarketDataError(
                f"Market data for {symbol} is stale: {report.message} (age: {report.age_seconds:.2f}s)"
            )
        return report

    def clear(self) -> None:
        """Reset all tracked quotes and heartbeats."""
        self._last_quote_times.clear()
        self._last_prices.clear()
        self._feed_heartbeats.clear()
