"""Market data normalizer and validator.

Transforms incoming RawMarketTick payloads into standard NormalizedMarketEvent
objects, enforcing monotonic timestamp progression and stale data detection.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.models.contracts import NormalizedMarketEvent, RawMarketTick

logger = logging.getLogger(__name__)


class MarketDataNormalizer:
    """Normalizes raw market ticks into verified, timestamped events."""

    def __init__(self, stale_threshold_seconds: float = 15.0) -> None:
        self.stale_threshold_seconds = stale_threshold_seconds
        self._last_timestamps: dict[str, datetime] = {}

    def normalize(
        self,
        raw: RawMarketTick,
        reference_time: datetime | None = None,
    ) -> NormalizedMarketEvent:
        """Normalize a raw tick into a standardized NormalizedMarketEvent.

        Args:
            raw: The raw tick payload from the market provider.
            reference_time: Optional reference time (default: current UTC) for stale checking.

        Returns:
            NormalizedMarketEvent with verified monotonic timestamps and spread metrics.
        """
        now = reference_time or datetime.now(timezone.utc)

        # Monotonic timestamp validation per symbol
        if raw.symbol in self._last_timestamps:
            prev_ts = self._last_timestamps[raw.symbol]
            if raw.timestamp < prev_ts:
                logger.warning(
                    "Non-monotonic timestamp detected for %s: current=%s < prev=%s",
                    raw.symbol,
                    raw.timestamp,
                    prev_ts,
                )

        self._last_timestamps[raw.symbol] = raw.timestamp

        # Fallback bid/ask prices if not provided in tick
        bid = raw.bid_price if raw.bid_price is not None else raw.last_price
        ask = raw.ask_price if raw.ask_price is not None else raw.last_price
        bid_qty = raw.bid_quantity if raw.bid_quantity is not None else 1
        ask_qty = raw.ask_quantity if raw.ask_quantity is not None else 1

        # Calculate spread percentage
        if raw.last_price > Decimal(0):
            spread_pct = max(Decimal(0), (ask - bid) / raw.last_price)
        else:
            spread_pct = Decimal(0)

        # Stale data detection
        time_delta = (now - raw.timestamp).total_seconds()
        is_stale = time_delta > self.stale_threshold_seconds

        if is_stale:
            logger.warning(
                "Stale tick detected for %s: age=%.2fs > threshold=%.2fs",
                raw.symbol,
                time_delta,
                self.stale_threshold_seconds,
            )

        return NormalizedMarketEvent(
            symbol=raw.symbol,
            source=raw.source,
            exchange_timestamp=raw.timestamp,
            ingest_timestamp=now,
            last_price=raw.last_price,
            volume=raw.volume,
            bid_price=bid,
            ask_price=ask,
            bid_quantity=bid_qty,
            ask_quantity=ask_qty,
            spread_pct=spread_pct,
            is_stale=is_stale,
        )
