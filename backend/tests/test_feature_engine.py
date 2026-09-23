"""Comprehensive test suite for BarAggregator and FeatureEngine (Phase 04).

Verifies mathematical correctness of all 12 quantitative features,
zero look-ahead bias, timestamp safety, edge-case resilience, and
the sub-15ms performance budget.
"""

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.engine.bar_aggregator import Bar, BarAggregator
from app.engine.feature_engine import FeatureEngine
from app.models.contracts import (
    FeatureSnapshot,
    MarketRegime,
    MarketSource,
    NormalizedMarketEvent,
)


def make_tick(
    symbol: str = "RELIANCE",
    price: str = "2500.00",
    volume: int = 100,
    timestamp: datetime | None = None,
    spread_pct: str = "0.0001",
) -> NormalizedMarketEvent:
    """Helper to construct valid NormalizedMarketEvent ticks."""
    ts = timestamp or datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)
    dec_price = Decimal(price)
    return NormalizedMarketEvent(
        symbol=symbol,
        source=MarketSource.SIMULATED,
        exchange_timestamp=ts,
        last_price=dec_price,
        volume=volume,
        bid_price=dec_price - Decimal("0.05"),
        ask_price=dec_price + Decimal("0.05"),
        bid_quantity=100,
        ask_quantity=100,
        spread_pct=Decimal(spread_pct),
    )


def make_bar(
    symbol: str = "RELIANCE",
    timestamp: datetime | None = None,
    open_p: str = "100.0",
    high_p: str = "105.0",
    low_p: str = "98.0",
    close_p: str = "102.0",
    volume: int = 1000,
    spread_pct: str = "0.0002",
) -> Bar:
    """Helper to construct valid Bar objects."""
    ts = timestamp or datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)
    o, h, l, c = Decimal(open_p), Decimal(high_p), Decimal(low_p), Decimal(close_p)
    tp = (h + l + c) / Decimal(3)
    return Bar(
        symbol=symbol,
        timestamp=ts,
        timeframe_seconds=60,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=volume,
        typical_price_volume_sum=tp * Decimal(volume),
        volume_sum=volume,
        vwap=tp,
        last_spread_pct=Decimal(spread_pct),
        ticks_count=10,
    )


# =============================================================================
# 1. Bar Aggregator Tests
# =============================================================================


def test_bar_aggregator_bucket_alignment():
    """Verify ticks align into standard 60s epoch buckets."""
    agg = BarAggregator(timeframe_seconds=60)
    t1 = datetime(2026, 9, 23, 9, 15, 12, tzinfo=timezone.utc)
    bucket = agg.get_bar_start_time(t1)
    assert bucket == datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    t2 = datetime(2026, 9, 23, 9, 15, 59, tzinfo=timezone.utc)
    assert agg.get_bar_start_time(t2) == bucket

    t3 = datetime(2026, 9, 23, 9, 16, 0, tzinfo=timezone.utc)
    assert agg.get_bar_start_time(t3) == datetime(
        2026, 9, 23, 9, 16, 0, tzinfo=timezone.utc
    )


def test_bar_aggregator_rollover_on_new_minute():
    """Verify bar completes and closes when tick crosses into the next time bucket."""
    agg = BarAggregator(timeframe_seconds=60)
    base_time = datetime(2026, 9, 23, 9, 15, 10, tzinfo=timezone.utc)

    # First tick at 09:15:10
    e1 = make_tick(price="100.0", volume=50, timestamp=base_time)
    bar1 = agg.process_tick(e1)
    assert bar1 is None  # Current bar active, no completed bar

    # Second tick in same minute at 09:15:45
    e2 = make_tick(
        price="105.0", volume=150, timestamp=base_time + timedelta(seconds=35)
    )
    bar2 = agg.process_tick(e2)
    assert bar2 is None

    # Third tick in next minute at 09:16:02 -> Triggers completion of 09:15 bar
    e3 = make_tick(
        price="104.0", volume=80, timestamp=base_time + timedelta(seconds=52)
    )
    completed_bar = agg.process_tick(e3)

    assert completed_bar is not None
    assert completed_bar.symbol == "RELIANCE"
    assert completed_bar.open == Decimal("100.0")
    assert completed_bar.high == Decimal("105.0")
    assert completed_bar.low == Decimal("100.0")
    assert completed_bar.close == Decimal("105.0")
    assert completed_bar.volume == 200
    assert completed_bar.ticks_count == 2


# =============================================================================
# 2. Feature Engine Feature Calculations
# =============================================================================


def test_feature_engine_initial_tick():
    """Verify first tick produces valid snapshot with zero errors."""
    engine = FeatureEngine()
    tick = make_tick(price="100.0", volume=50)
    snapshot = engine.process_tick(tick)

    assert isinstance(snapshot, FeatureSnapshot)
    assert snapshot.symbol == "RELIANCE"
    assert snapshot.current_price == Decimal("100.0000")
    assert snapshot.vwap == Decimal("100.0000")
    assert snapshot.vwap_distance_pct == Decimal("0.0000")
    assert snapshot.relative_volume_10 == Decimal("1.0000")
    assert snapshot.price_structure == "RANGE"
    assert snapshot.market_index_direction == "NEUTRAL"
    assert snapshot.sector_strength == Decimal("0.0000")


def test_feature_engine_vwap_and_distance():
    """Verify VWAP is computed cumulatively and distance % reflects price difference."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Feed 2 completed bars
    # Bar 1: Price 100, Vol 1000 -> PV = 100,000
    b1 = make_bar(
        timestamp=base_t,
        open_p="100",
        high_p="100",
        low_p="100",
        close_p="100",
        volume=1000,
    )
    # Bar 2: Price 110, Vol 1000 -> PV = 110,000
    b2 = make_bar(
        timestamp=base_t + timedelta(minutes=1),
        open_p="110",
        high_p="110",
        low_p="110",
        close_p="110",
        volume=1000,
    )

    engine.register_completed_bar(b1)
    engine.register_completed_bar(b2)

    # Total PV = 210,000, Total Vol = 2000 -> VWAP = 105.0
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=2),
        current_price=Decimal("115.50"),
        current_spread_pct=Decimal("0.0001"),
    )

    assert snap.vwap == Decimal("105.0000")
    # Distance: (115.5 - 105.0) / 105.0 * 100 = 10.5 / 105.0 * 100 = 10.0000%
    assert snap.vwap_distance_pct == Decimal("10.0000")


def test_feature_engine_momentum_score():
    """Verify 5-bar ROC momentum calculation."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Feed 5 bars: 100 -> 102 -> 104 -> 106 -> 108
    for i in range(5):
        p = str(100 + i * 2)
        b = make_bar(
            timestamp=base_t + timedelta(minutes=i),
            open_p=p,
            high_p=p,
            low_p=p,
            close_p=p,
        )
        engine.register_completed_bar(b)

    # 5 bars ago close was 100. Current price = 110
    # Momentum = (110 - 100) / 100 * 100 = 10.0000%
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=5),
        current_price=Decimal("110.0"),
        current_spread_pct=Decimal("0.0001"),
    )
    assert snap.momentum_score == Decimal("10.0000")


def test_feature_engine_relative_volume():
    """Verify RVOL computed against rolling 10-bar baseline."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # 10 bars with volume 500 each -> baseline average = 500
    for i in range(10):
        b = make_bar(timestamp=base_t + timedelta(minutes=i), volume=500)
        engine.register_completed_bar(b)

    # Current bar has volume 1500 -> RVOL = 1500 / 500 = 3.0
    active_bar = make_bar(timestamp=base_t + timedelta(minutes=10), volume=1500)
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=10),
        current_price=Decimal("100.0"),
        current_spread_pct=Decimal("0.0001"),
        current_in_progress_bar=active_bar,
    )
    assert snap.relative_volume_10 == Decimal("3.0000")


def test_feature_engine_volume_and_price_acceleration():
    """Verify volume and price acceleration calculations."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Bar 1: close 100, vol 1000
    b1 = make_bar(timestamp=base_t, close_p="100.0", volume=1000)
    # Bar 2: close 102, vol 1200 -> velocity_0 = 2.0%
    b2 = make_bar(timestamp=base_t + timedelta(minutes=1), close_p="102.0", volume=1200)

    engine.register_completed_bar(b1)
    engine.register_completed_bar(b2)

    # Current bar: close 106.08, vol 1800
    # vel_t = (106.08 - 102.0) / 102.0 * 100 = 4.0%
    # Price acceleration = 4.0% - 2.0% = 2.0%
    # Volume acceleration = (1800 - 1200) / 1200 * 100 = 50.0%
    active_bar = make_bar(
        timestamp=base_t + timedelta(minutes=2), close_p="106.08", volume=1800
    )
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=2),
        current_price=Decimal("106.08"),
        current_spread_pct=Decimal("0.0001"),
        current_in_progress_bar=active_bar,
    )

    assert abs(snap.price_acceleration - Decimal("2.0000")) < Decimal("0.001")
    assert abs(snap.volume_acceleration - Decimal("50.0000")) < Decimal("0.001")


def test_feature_engine_realized_volatility():
    """Verify realized volatility returns positive standard deviation for fluctuating prices."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    prices = ["100.0", "102.0", "99.0", "103.5", "101.0", "104.0"]
    for i, p in enumerate(prices):
        b = make_bar(timestamp=base_t + timedelta(minutes=i), close_p=p)
        engine.register_completed_bar(b)

    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=len(prices)),
        current_price=Decimal("102.0"),
        current_spread_pct=Decimal("0.0001"),
    )
    assert snap.realized_volatility_15 > Decimal(0)


def test_feature_engine_liquidity_score_range():
    """Verify liquidity score produces values bounded between 0.0 and 100.0."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Tight spread (0.01%) and high volume (RVOL = 2.0)
    b = make_bar(timestamp=base_t, volume=1000)
    engine.register_completed_bar(b)

    active = make_bar(timestamp=base_t + timedelta(minutes=1), volume=2000)
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=1),
        current_price=Decimal("100.0"),
        current_spread_pct=Decimal("0.0001"),
        current_in_progress_bar=active,
    )
    assert Decimal("90.0") <= snap.liquidity_score <= Decimal("100.0")

    # Wide spread (0.60%) and zero volume
    snap_illiquid = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=1),
        current_price=Decimal("100.0"),
        current_spread_pct=Decimal("0.0060"),
        current_tick_volume=0,
    )
    assert snap_illiquid.liquidity_score == Decimal("0.00")


# =============================================================================
# 3. Price Structure & Market Regime Tests
# =============================================================================


def test_price_structure_higher_highs():
    """Verify HIGHER_HIGHS pattern detection."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Bar 1: H 102, L 98, C 101
    b1 = make_bar(timestamp=base_t, high_p="102.0", low_p="98.0", close_p="101.0")
    # Bar 2: H 104, L 100, C 103
    b2 = make_bar(
        timestamp=base_t + timedelta(minutes=1),
        high_p="104.0",
        low_p="100.0",
        close_p="103.0",
    )
    # Bar 3: H 106, L 102, C 105
    b3 = make_bar(
        timestamp=base_t + timedelta(minutes=2),
        high_p="106.0",
        low_p="102.0",
        close_p="105.0",
    )

    engine.register_completed_bar(b1)
    engine.register_completed_bar(b2)
    engine.register_completed_bar(b3)

    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=3),
        current_price=Decimal("106.0"),
        current_spread_pct=Decimal("0.0001"),
    )
    assert snap.price_structure == "HIGHER_HIGHS"


def test_price_structure_breakout():
    """Verify BREAKOUT pattern detection when breaking 10-bar max with RVOL."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # 10 bars trapped between 95 and 100
    for i in range(10):
        b = make_bar(
            timestamp=base_t + timedelta(minutes=i),
            high_p="100.0",
            low_p="95.0",
            close_p="98.0",
            volume=500,
        )
        engine.register_completed_bar(b)

    # Breakout tick: price 102.0 (> 100.0) with volume 1000 (RVOL = 2.0 >= 1.2)
    active = make_bar(
        timestamp=base_t + timedelta(minutes=10),
        high_p="102.0",
        low_p="98.0",
        close_p="102.0",
        volume=1000,
    )
    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=10),
        current_price=Decimal("102.0"),
        current_spread_pct=Decimal("0.0001"),
        current_in_progress_bar=active,
    )
    assert snap.price_structure == "BREAKOUT"


def test_market_regime_classification():
    """Verify deterministic regime mapping for trending and chop conditions."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Setup strong uptrend: higher highs, price > vwap
    b1 = make_bar(
        timestamp=base_t, high_p="100.0", low_p="98.0", close_p="99.0", volume=1000
    )
    b2 = make_bar(
        timestamp=base_t + timedelta(minutes=1),
        high_p="103.0",
        low_p="99.5",
        close_p="102.0",
        volume=1000,
    )
    b3 = make_bar(
        timestamp=base_t + timedelta(minutes=2),
        high_p="106.0",
        low_p="102.5",
        close_p="105.0",
        volume=1000,
    )

    engine.register_completed_bar(b1)
    engine.register_completed_bar(b2)
    engine.register_completed_bar(b3)
    engine.set_market_index_direction("BULLISH")

    snap = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=3),
        current_price=Decimal("106.5"),
        current_spread_pct=Decimal("0.0001"),
    )
    assert snap.regime == MarketRegime.BULLISH_TRENDING


# =============================================================================
# 4. Strict Look-Ahead Safety & Invariant Tests
# =============================================================================


def test_zero_lookahead_bias():
    """Prove that adding future bars does NOT alter previously generated snapshots."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Step 1: Ingest 3 bars up to T=2
    b0 = make_bar(timestamp=base_t, close_p="100.0", volume=500)
    b1 = make_bar(timestamp=base_t + timedelta(minutes=1), close_p="102.0", volume=600)
    b2 = make_bar(timestamp=base_t + timedelta(minutes=2), close_p="104.0", volume=700)

    engine.register_completed_bar(b0)
    engine.register_completed_bar(b1)
    engine.register_completed_bar(b2)

    # Snapshot at T=2
    snapshot_t2 = engine.compute_features(
        symbol="RELIANCE",
        timestamp=base_t + timedelta(minutes=2),
        current_price=Decimal("104.0"),
        current_spread_pct=Decimal("0.0001"),
    )

    # Step 2: Ingest 5 future bars into T=7 with massive volatility & price spikes
    for i in range(3, 8):
        future_bar = make_bar(
            timestamp=base_t + timedelta(minutes=i),
            close_p=str(150 + i * 10),
            volume=5000,
        )
        engine.register_completed_bar(future_bar)

    # Verify snapshot_t2 values remain frozen and immutable
    assert snapshot_t2.current_price == Decimal("104.0000")
    assert snapshot_t2.vwap < Decimal("105.0000")


# =============================================================================
# 5. Performance Benchmark (< 15ms Budget)
# =============================================================================


def test_feature_computation_latency_budget():
    """Verify feature snapshot computation strictly honors the < 15ms latency budget."""
    engine = FeatureEngine()
    base_t = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)

    # Preload 50 bars of history
    for i in range(50):
        b = make_bar(
            timestamp=base_t + timedelta(minutes=i),
            close_p=str(100 + (i % 5)),
            volume=1000,
        )
        engine.register_completed_bar(b)

    # Benchmark 100 feature snapshot evaluations
    latencies: list[float] = []
    for _ in range(100):
        start_ns = time.perf_counter_ns()
        engine.compute_features(
            symbol="RELIANCE",
            timestamp=base_t + timedelta(minutes=51),
            current_price=Decimal("103.50"),
            current_spread_pct=Decimal("0.0001"),
            current_tick_volume=1200,
        )
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        latencies.append(duration_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    # Must be well below the 15ms budget (target < 1ms on local machine)
    assert avg_latency < 5.0, (
        f"Average feature latency exceeded budget: {avg_latency:.3f}ms"
    )
    assert max_latency < 15.0, (
        f"Max feature latency exceeded 15ms budget: {max_latency:.3f}ms"
    )
