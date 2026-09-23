"""Point-in-time candlestick bar aggregator.

Aggregates incoming NormalizedMarketEvents into timestamp-aligned
OHLCV bars without look-ahead leakage.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.models.contracts import NormalizedMarketEvent


@dataclass(slots=True)
class Bar:
    """Timestamp-aligned OHLCV candle bar."""

    symbol: str
    timestamp: datetime
    timeframe_seconds: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    typical_price_volume_sum: Decimal
    volume_sum: int
    vwap: Decimal
    last_spread_pct: Decimal
    ticks_count: int

    @property
    def typical_price(self) -> Decimal:
        """Typical price (High + Low + Close) / 3."""
        return (self.high + self.low + self.close) / Decimal(3)


class BarAggregator:
    """Aggregates streaming ticks into OHLCV bars strictly point-in-time."""

    def __init__(self, timeframe_seconds: int = 60) -> None:
        self.timeframe_seconds = timeframe_seconds
        self._current_bars: dict[str, Bar] = {}
        self._completed_bars: dict[str, list[Bar]] = {}

    def get_bar_start_time(self, timestamp: datetime) -> datetime:
        """Calculate bucket start timestamp for a given tick time."""
        epoch = timestamp.timestamp()
        bucket_epoch = (
            math.floor(epoch / self.timeframe_seconds) * self.timeframe_seconds
        )
        return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)

    def process_tick(self, event: NormalizedMarketEvent) -> Bar | None:
        """Ingest a normalized tick event.

        Returns:
            Completed Bar if the tick crossed into a new time bucket, else None.
        """
        bar_start = self.get_bar_start_time(event.exchange_timestamp)
        symbol = event.symbol
        completed_bar: Bar | None = None

        current = self._current_bars.get(symbol)

        if current is not None and current.timestamp < bar_start:
            # Bar completed! Archive it
            completed_bar = current
            if symbol not in self._completed_bars:
                self._completed_bars[symbol] = []
            self._completed_bars[symbol].append(completed_bar)
            current = None

        if current is None:
            # Initialize new bar
            price = event.last_price
            vol = max(0, event.volume)
            tp_vol = price * Decimal(vol)
            current = Bar(
                symbol=symbol,
                timestamp=bar_start,
                timeframe_seconds=self.timeframe_seconds,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=vol,
                typical_price_volume_sum=tp_vol,
                volume_sum=vol,
                vwap=price,
                last_spread_pct=event.spread_pct,
                ticks_count=1,
            )
        else:
            # Update existing bar in-place
            price = event.last_price
            vol = max(0, event.volume)
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            current.volume += vol
            current.typical_price_volume_sum += price * Decimal(vol)
            current.volume_sum += vol
            if current.volume_sum > 0:
                current.vwap = current.typical_price_volume_sum / Decimal(
                    current.volume_sum
                )
            current.last_spread_pct = event.spread_pct
            current.ticks_count += 1

        self._current_bars[symbol] = current
        return completed_bar

    def get_current_in_progress_bar(self, symbol: str) -> Bar | None:
        """Return the current active in-progress bar for a symbol."""
        return self._current_bars.get(symbol)

    def get_completed_bars(self, symbol: str) -> list[Bar]:
        """Return historical completed bars for a symbol."""
        return list(self._completed_bars.get(symbol, []))
