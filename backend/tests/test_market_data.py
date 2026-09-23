"""Unit and integration tests for Market Data & Normalization (Phase 03)."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.adapters.normalizer import MarketDataNormalizer
from app.adapters.simulated_market_data import SimulatedMarketDataAdapter
from app.models.contracts import MarketSource, RawMarketTick


def test_normalizer_valid_tick():
    """Verify normalizer produces valid event with correct spread."""
    normalizer = MarketDataNormalizer(stale_threshold_seconds=10.0)
    now = datetime.now(timezone.utc)

    raw = RawMarketTick(
        source=MarketSource.SIMULATED,
        symbol="TATASTEEL",
        timestamp=now,
        last_price=Decimal("150.00"),
        volume=500,
        bid_price=Decimal("149.95"),
        ask_price=Decimal("150.05"),
        bid_quantity=100,
        ask_quantity=120,
    )

    event = normalizer.normalize(raw, reference_time=now)
    assert event.symbol == "TATASTEEL"
    assert event.last_price == Decimal("150.00")
    assert event.spread_pct == Decimal("0.10") / Decimal("150.00")
    assert not event.is_stale


def test_normalizer_stale_detection():
    """Verify ticks older than threshold are marked is_stale."""
    normalizer = MarketDataNormalizer(stale_threshold_seconds=10.0)
    tick_time = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)
    reference_time = datetime(2026, 9, 23, 10, 0, 20, tzinfo=timezone.utc)  # 20s later

    raw = RawMarketTick(
        source=MarketSource.SIMULATED,
        symbol="SBIN",
        timestamp=tick_time,
        last_price=Decimal("780.00"),
        volume=300,
    )

    event = normalizer.normalize(raw, reference_time=reference_time)
    assert event.is_stale is True


@pytest.mark.asyncio
async def test_simulated_adapter_connection_and_subscription():
    """Verify adapter connects, subscribes, and receives ticks."""
    adapter = SimulatedMarketDataAdapter(tick_interval_ms=50)
    connected = await adapter.connect()
    assert connected is True
    assert adapter.is_connected is True

    await adapter.subscribe(["RELIANCE", "INFY"])
    assert "RELIANCE" in adapter.subscribed_symbols
    assert "INFY" in adapter.subscribed_symbols

    # Wait for generator to emit at least 1 tick
    await asyncio.sleep(0.15)

    rel_event = adapter.get_latest_event("RELIANCE")
    assert rel_event is not None
    assert rel_event.symbol == "RELIANCE"
    assert rel_event.last_price > Decimal(0)

    await adapter.disconnect()
    assert adapter.is_connected is False


@pytest.mark.asyncio
async def test_simulated_adapter_callback_dispatch():
    """Verify registered callbacks receive dispatched events."""
    adapter = SimulatedMarketDataAdapter(tick_interval_ms=100)
    await adapter.connect()

    received_events = []
    adapter.register_callback(lambda e: received_events.append(e))

    await adapter.emit_tick(symbol="HDFCBANK", price=Decimal("1650.00"), volume=250)

    assert len(received_events) == 1
    assert received_events[0].symbol == "HDFCBANK"
    assert received_events[0].last_price == Decimal("1650.00")

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_simulated_adapter_injected_stale_data():
    """Verify injected stale offset marks output events stale."""
    adapter = SimulatedMarketDataAdapter(stale_threshold_seconds=5.0)
    await adapter.connect()

    # Inject 10s lag
    adapter.set_stale_offset(10.0)

    await adapter.emit_tick(symbol="WIPRO", price=Decimal("450.00"), volume=100)
    event = adapter.get_latest_event("WIPRO")

    assert event is not None
    assert event.is_stale is True

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_simulated_adapter_reconnect_loop():
    """Verify exponential backoff reconnects after simulated drop."""
    adapter = SimulatedMarketDataAdapter(
        max_reconnect_attempts=3,
        reconnect_base_delay=0.05,
    )
    await adapter.connect()
    await adapter.subscribe(["TCS"])

    # Simulate disconnect
    adapter.inject_disconnect()
    assert adapter.is_connected is False

    # Trigger reconnect handler
    reconnected = await adapter.handle_connection_loss()
    assert reconnected is True
    assert adapter.is_connected is True
    assert "TCS" in adapter.subscribed_symbols

    await adapter.disconnect()
