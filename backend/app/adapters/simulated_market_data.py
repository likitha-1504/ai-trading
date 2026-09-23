"""Deterministic simulated market data adapter.

Generates realistic tick events for testing and paper trading,
supporting fault injection (disconnects, delays, stale data).
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.adapters.market_data_base import BaseMarketDataAdapter
from app.models.contracts import MarketSource, RawMarketTick

logger = logging.getLogger(__name__)


class SimulatedMarketDataAdapter(BaseMarketDataAdapter):
    """Simulated market data feed with deterministic pricing and fault injection."""

    def __init__(
        self,
        base_prices: dict[str, Decimal] | None = None,
        tick_interval_ms: int = 100,
        spread_bps: int = 5,
        stale_threshold_seconds: float = 15.0,
        max_reconnect_attempts: int = 5,
        reconnect_base_delay: float = 0.1,
    ) -> None:
        super().__init__(
            stale_threshold_seconds=stale_threshold_seconds,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnect_base_delay=reconnect_base_delay,
        )
        self.prices: dict[str, Decimal] = base_prices or {
            "RELIANCE": Decimal("2500.00"),
            "TCS": Decimal("3500.00"),
            "INFY": Decimal("1500.00"),
        }
        self.tick_interval_ms = tick_interval_ms
        self.spread_bps = spread_bps
        self._generator_task: asyncio.Task | None = None
        self._inject_disconnect: bool = False
        self._inject_stale_seconds: float = 0.0

    async def _do_connect(self) -> bool:
        if self._inject_disconnect:
            self._inject_disconnect = False
            return False

        if self._generator_task is None or self._generator_task.done():
            self._generator_task = asyncio.create_task(self._run_generator())
        return True

    async def _do_disconnect(self) -> None:
        if self._generator_task and not self._generator_task.done():
            self._generator_task.cancel()
            try:
                await self._generator_task
            except asyncio.CancelledError:
                pass
        self._generator_task = None

    async def _do_subscribe(self, symbols: list[str]) -> None:
        for s in symbols:
            if s not in self.prices:
                self.prices[s] = Decimal("100.00")

    async def _do_unsubscribe(self, symbols: list[str]) -> None:
        pass

    def inject_disconnect(self) -> None:
        """Inject a simulated connection loss."""
        self._is_connected = False
        if self._generator_task and not self._generator_task.done():
            self._generator_task.cancel()

    def set_stale_offset(self, seconds: float) -> None:
        """Inject a timestamp lag to simulate stale quotes."""
        self._inject_stale_seconds = seconds

    async def emit_tick(
        self,
        symbol: str,
        price: Decimal,
        volume: int = 100,
        bid_price: Decimal | None = None,
        ask_price: Decimal | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Directly emit a deterministic tick fixture."""
        ts = timestamp or datetime.now(timezone.utc)
        if self._inject_stale_seconds > 0:
            ts = datetime.fromtimestamp(
                ts.timestamp() - self._inject_stale_seconds, tz=timezone.utc
            )

        spread_offset = price * Decimal(str(self.spread_bps)) / Decimal(10000)
        bid = bid_price or (price - spread_offset)
        ask = ask_price or (price + spread_offset)

        raw = RawMarketTick(
            source=MarketSource.SIMULATED,
            symbol=symbol,
            timestamp=ts,
            last_price=price,
            volume=volume,
            bid_price=bid,
            ask_price=ask,
            bid_quantity=10,
            ask_quantity=10,
        )
        await self.dispatch_raw_tick(raw)

    async def _run_generator(self) -> None:
        """Continuously generate synthetic ticks for subscribed symbols."""
        step = 0
        try:
            while self._is_connected:
                for symbol in list(self._subscribed_symbols):
                    current_price = self.prices.get(symbol, Decimal("100.00"))
                    # Micro sinusoidal variation around price
                    variation = Decimal("0.05") if step % 2 == 0 else Decimal("-0.05")
                    new_price = max(Decimal("1.00"), current_price + variation)
                    self.prices[symbol] = new_price

                    await self.emit_tick(symbol=symbol, price=new_price, volume=50)
                step += 1
                await asyncio.sleep(self.tick_interval_ms / 1000.0)
        except asyncio.CancelledError:
            pass
