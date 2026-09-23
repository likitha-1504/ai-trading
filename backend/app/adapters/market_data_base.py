"""Base market data adapter interface and reconnection engine.

Provides an abstract, broker-neutral interface with built-in reconnect
loops, exponential backoff, rate limiting, and event streaming.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable

from app.adapters.normalizer import MarketDataNormalizer
from app.models.contracts import NormalizedMarketEvent, RawMarketTick

logger = logging.getLogger(__name__)


class BaseMarketDataAdapter(ABC):
    """Abstract broker-neutral market data provider adapter."""

    def __init__(
        self,
        stale_threshold_seconds: float = 15.0,
        max_reconnect_attempts: int = 5,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
    ) -> None:
        self.normalizer = MarketDataNormalizer(
            stale_threshold_seconds=stale_threshold_seconds
        )
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        self.reconnect_max_delay = reconnect_max_delay

        self._is_connected: bool = False
        self._subscribed_symbols: set[str] = set()
        self._latest_events: dict[str, NormalizedMarketEvent] = {}
        self._subscribers: list[Callable[[NormalizedMarketEvent], None]] = []
        self._reconnect_count: int = 0
        self._queue: asyncio.Queue[NormalizedMarketEvent] = asyncio.Queue()

    @property
    def is_connected(self) -> bool:
        """Return current connection state."""
        return self._is_connected

    @property
    def subscribed_symbols(self) -> set[str]:
        """Return set of actively subscribed symbols."""
        return set(self._subscribed_symbols)

    async def connect(self) -> bool:
        """Connect to the provider and initialize feed."""
        try:
            success = await self._do_connect()
            if success:
                self._is_connected = True
                self._reconnect_count = 0
                logger.info("Market data adapter connected successfully.")
                return True
            return False
        except Exception as e:  # noqa: BLE001 - Protect adapter from unexpected network driver failures
            logger.error("Failed to connect to market data provider: %s", e)
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect cleanly from provider."""
        self._is_connected = False
        await self._do_disconnect()
        logger.info("Market data adapter disconnected.")

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to quote streams for the specified symbols."""
        new_symbols = [s for s in symbols if s not in self._subscribed_symbols]
        if new_symbols:
            await self._do_subscribe(new_symbols)
            self._subscribed_symbols.update(new_symbols)
            logger.info("Subscribed to symbols: %s", new_symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from quote streams for the specified symbols."""
        remove_symbols = [s for s in symbols if s in self._subscribed_symbols]
        if remove_symbols:
            await self._do_unsubscribe(remove_symbols)
            self._subscribed_symbols.difference_update(remove_symbols)
            logger.info("Unsubscribed from symbols: %s", remove_symbols)

    def get_latest_event(self, symbol: str) -> NormalizedMarketEvent | None:
        """Return the latest normalized market event for a symbol."""
        return self._latest_events.get(symbol)

    def register_callback(
        self, callback: Callable[[NormalizedMarketEvent], None]
    ) -> None:
        """Register a downstream event callback."""
        self._subscribers.append(callback)

    async def dispatch_raw_tick(self, raw_tick: RawMarketTick) -> NormalizedMarketEvent:
        """Normalize an incoming raw tick and dispatch to subscribers and queue."""
        event = self.normalizer.normalize(raw_tick)
        self._latest_events[event.symbol] = event
        await self._queue.put(event)

        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:  # noqa: BLE001 - Prevent faulty subscriber callback from killing dispatcher
                logger.error(
                    "Callback error dispatching tick for %s: %s", event.symbol, e
                )

        return event

    async def stream_events(self) -> AsyncIterator[NormalizedMarketEvent]:
        """Async generator yielding normalized market events."""
        while self._is_connected or not self._queue.empty():
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield event
            except asyncio.TimeoutError:
                continue

    async def handle_connection_loss(self) -> bool:
        """Trigger exponential backoff reconnection loop."""
        self._is_connected = False
        logger.warning("Market data connection lost. Initiating reconnect loop...")

        while self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            delay = min(
                self.reconnect_base_delay * (2 ** (self._reconnect_count - 1)),
                self.reconnect_max_delay,
            )
            logger.info(
                "Reconnect attempt %d/%d in %.1fs...",
                self._reconnect_count,
                self.max_reconnect_attempts,
                delay,
            )
            await asyncio.sleep(delay)

            try:
                if await self.connect():
                    logger.info(
                        "Reconnection successful on attempt %d.", self._reconnect_count
                    )
                    # Re-subscribe to existing symbols
                    if self._subscribed_symbols:
                        await self._do_subscribe(list(self._subscribed_symbols))
                    return True
            except Exception as e:  # noqa: BLE001 - Catch reconnect failure to continue backoff loop
                logger.error(
                    "Reconnect attempt %d failed: %s", self._reconnect_count, e
                )

        logger.critical(
            "Maximum reconnect attempts reached. Market data provider offline."
        )
        return False

    @abstractmethod
    async def _do_connect(self) -> bool:
        """Subclass implementation of provider-specific connection."""

    @abstractmethod
    async def _do_disconnect(self) -> None:
        """Subclass implementation of provider-specific disconnection."""

    @abstractmethod
    async def _do_subscribe(self, symbols: list[str]) -> None:
        """Subclass implementation of provider-specific subscription."""

    @abstractmethod
    async def _do_unsubscribe(self, symbols: list[str]) -> None:
        """Subclass implementation of provider-specific unsubscription."""
