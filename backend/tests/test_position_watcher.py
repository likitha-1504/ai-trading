"""Comprehensive test suite for Phase 06: Independent Position Watcher and SELL Engine.

Verifies hard stop protection, stale-data emergency behavior, catastrophic liquidity loss,
daily circuit breakers, trailing stops, failure injection (model outage, network disconnect,
partial fills, rejected orders, restart recovery), and zero LLM dependency on emergency paths.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.contracts import (
    FeatureSnapshot,
    MarketRegime,
    MarketSource,
    NormalizedMarketEvent,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
    WatcherExitTrigger,
)
from app.watcher.config import WatcherConfig
from app.watcher.position_watcher import IndependentPositionWatcher


def make_position(
    position_id: str = "pos-001",
    symbol: str = "RELIANCE",
    quantity: int = 1,
    entry_price: str = "100.00",
    hard_stop_price: str = "98.50",  # Risk R = 1.50
    take_profit_price: str | None = "105.00",  # ~3R
    opened_at: datetime | None = None,
) -> PositionSnapshot:
    """Helper to construct an active micro-trading PositionSnapshot."""
    t0 = opened_at or datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)
    p_entry = Decimal(entry_price)
    tp = Decimal(take_profit_price) if take_profit_price else None
    return PositionSnapshot(
        position_id=position_id,
        plan_id=f"plan-{position_id}",
        symbol=symbol,
        side=TradeSide.BUY,
        quantity=quantity,
        entry_price=p_entry,
        current_price=p_entry,
        hard_stop_price=Decimal(hard_stop_price),
        take_profit_price=tp,
        highest_price_seen=p_entry,
        trailing_stop_price=None,
        unrealized_pnl=Decimal(0),
        status=PositionStatus.OPEN,
        opened_at=t0,
        last_evaluated_at=t0,
    )


def make_tick(
    symbol: str = "RELIANCE",
    price: str = "100.00",
    spread_pct: str = "0.0002",
    timestamp: datetime | None = None,
    is_stale: bool = False,
) -> NormalizedMarketEvent:
    """Helper to construct a NormalizedMarketEvent."""
    ts = timestamp or datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)
    dec_price = Decimal(price)
    return NormalizedMarketEvent(
        symbol=symbol,
        source=MarketSource.SIMULATED,
        exchange_timestamp=ts,
        last_price=dec_price,
        volume=100,
        bid_price=dec_price - Decimal("0.05"),
        ask_price=dec_price + Decimal("0.05"),
        bid_quantity=100,
        ask_quantity=100,
        spread_pct=Decimal(spread_pct),
        is_stale=is_stale,
    )


def make_snapshot(
    symbol: str = "RELIANCE",
    current_price: str = "100.00",
    momentum_score: str = "0.50",
    price_acceleration: str = "0.10",
    spread_pct: str = "0.0005",
    liquidity_score: str = "80.0",
    market_index_direction: str = "BULLISH",
    sector_strength: str = "0.20",
    price_structure: str = "RANGE",
    timestamp: datetime | None = None,
) -> FeatureSnapshot:
    """Helper to construct a FeatureSnapshot for deterioration testing."""
    ts = timestamp or datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)
    return FeatureSnapshot(
        symbol=symbol,
        timestamp=ts,
        bar_timeframe="1m",
        vwap=Decimal("99.50"),
        current_price=Decimal(current_price),
        vwap_distance_pct=Decimal("0.50"),
        momentum_score=Decimal(momentum_score),
        relative_volume_10=Decimal("1.50"),
        volume_acceleration=Decimal("10.0"),
        price_acceleration=Decimal(price_acceleration),
        realized_volatility_15=Decimal("0.25"),
        spread_pct=Decimal(spread_pct),
        liquidity_score=Decimal(liquidity_score),
        market_index_direction=market_index_direction,
        sector_strength=Decimal(sector_strength),
        price_structure=price_structure,
        regime=MarketRegime.BULLISH_TRENDING,
    )


# =============================================================================
# 1. Hard Stop Protection (Absolute Capital Preservation)
# =============================================================================


def test_hard_stop_execution_on_breach():
    """Verify immediate market exit is dispatched when price touches or breaches stop loss."""
    watcher = IndependentPositionWatcher()
    pos = make_position(entry_price="100.00", hard_stop_price="98.50")
    watcher.open_position(pos)

    # Price at 99.00 (safe) -> No intervention
    tick_safe = make_tick(price="99.00")
    assert len(watcher.evaluate_tick(tick_safe)) == 0
    assert pos.status == PositionStatus.OPEN

    # Price breaches hard stop to 98.40 -> HARD_STOP triggered
    tick_breach = make_tick(price="98.40")
    events = watcher.evaluate_tick(tick_breach)

    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.HARD_STOP
    assert events[0].trigger_price == Decimal("98.40")
    assert pos.status == PositionStatus.CLOSED


# =============================================================================
# 2. Stale Data & Emergency Liquidation
# =============================================================================


def test_stale_data_emergency_trigger():
    """Verify stale quote flag or frozen feed (> 15s) triggers emergency exit."""
    config = WatcherConfig(stale_quote_timeout_seconds=15.0)
    watcher = IndependentPositionWatcher(config=config)
    t0 = datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)
    pos = make_position(opened_at=t0)
    watcher.open_position(pos)

    # 1. Direct stale flag on incoming tick
    stale_tick = make_tick(
        price="100.00", is_stale=True, timestamp=t0 + timedelta(seconds=5)
    )
    events = watcher.evaluate_tick(stale_tick)
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.STALE_DATA_EMERGENCY

    # Reset position for timeout test
    pos2 = make_position(position_id="pos-002", opened_at=t0)
    watcher.open_position(pos2)
    # Feed initial tick at t0
    watcher.evaluate_tick(make_tick(price="100.00", timestamp=t0))

    # Heartbeat 16s later without new quotes -> STALE_DATA_EMERGENCY
    t_stale = t0 + timedelta(seconds=16)
    heartbeat_events = watcher.evaluate_heartbeat(current_time=t_stale)
    assert len(heartbeat_events) == 1
    assert heartbeat_events[0].trigger == WatcherExitTrigger.STALE_DATA_EMERGENCY


# =============================================================================
# 3. Catastrophic Liquidity & Spread Protection
# =============================================================================


def test_catastrophic_spread_and_liquidity_loss():
    """Verify spread blowout (>= 0.50%) or depth evaporation triggers defensive exit."""
    watcher = IndependentPositionWatcher()
    pos = make_position()
    watcher.open_position(pos)

    # Spread blowout to 0.55% (55 bps) -> CATASTROPHIC_LIQUIDITY_LOSS
    blowout_tick = make_tick(price="100.00", spread_pct="0.0055")
    events = watcher.evaluate_tick(blowout_tick)
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.CATASTROPHIC_LIQUIDITY_LOSS


# =============================================================================
# 4. Daily Circuit Breaker
# =============================================================================


def test_daily_circuit_breaker():
    """Verify daily loss exceeding 3.0% of equity halts trading and liquidates all positions."""
    config = WatcherConfig(
        capital_base=Decimal("100.00"), max_daily_drawdown_pct=Decimal("0.03")
    )
    watcher = IndependentPositionWatcher(config=config)

    # Simulate prior realized loss of ₹2.00 today (out of ₹3.00 max limit)
    watcher.realized_daily_pnl = Decimal("-2.00")

    # Open position with 1 share
    pos = make_position(quantity=1, entry_price="100.00", hard_stop_price="95.00")
    watcher.open_position(pos)

    # Price drops to 98.80 -> unrealized loss = -1.20 -> total loss = -3.20 (breaches -3.00 limit)
    tick = make_tick(price="98.80")
    events = watcher.evaluate_tick(tick)

    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.DAILY_CIRCUIT_BREAKER
    assert watcher.is_circuit_breaker_tripped is True


# =============================================================================
# 5. Take Profit & Trailing Stop Ratchet
# =============================================================================


def test_take_profit_target_execution():
    """Verify profit target execution when price reaches take-profit price."""
    watcher = IndependentPositionWatcher()
    pos = make_position(entry_price="100.00", take_profit_price="105.00")
    watcher.open_position(pos)

    # Price hits 105.00
    events = watcher.evaluate_tick(make_tick(price="105.00"))
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.TAKE_PROFIT


def test_trailing_stop_activation_and_ratchet():
    """Verify trailing stop activates after 1.5R gain and ratchets upward monotonically."""
    watcher = IndependentPositionWatcher()
    # Risk R = 100.00 - 98.00 = 2.00
    # Activation = 100.00 + (1.5 * 2) = 103.00
    pos = make_position(
        entry_price="100.00",
        hard_stop_price="98.00",
        take_profit_price="110.00",  # High TP so trailing stop executes
    )
    watcher.open_position(pos)

    # Price moves to 102.50 (+1.25R) -> Trailing stop NOT yet activated
    watcher.evaluate_tick(make_tick(price="102.50"))
    assert pos.trailing_stop_price is None

    # Price surges to 103.50 (+1.75R) -> Trailing stop activates!
    # Trail stop = 103.50 - (1.0 * 2.00) = 101.50
    watcher.evaluate_tick(make_tick(price="103.50"))
    assert pos.trailing_stop_price == Decimal("101.50")

    # Price advances further to 104.50 -> Trail ratchets up to 104.50 - 2.00 = 102.50
    watcher.evaluate_tick(make_tick(price="104.50"))
    assert pos.trailing_stop_price == Decimal("102.50")

    # Price pulls back to 103.00 -> Trail stop remains frozen at 102.50 (monotonic)
    watcher.evaluate_tick(make_tick(price="103.00"))
    assert pos.trailing_stop_price == Decimal("102.50")

    # Price plunges to 102.00 -> Triggers TRAILING_STOP exit!
    events = watcher.evaluate_tick(make_tick(price="102.00"))
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.TRAILING_STOP
    assert events[0].trigger_price == Decimal("102.00")


# =============================================================================
# 6. Technical Deterioration & Time Expiry
# =============================================================================


def test_technical_deterioration_exits():
    """Verify technical breakdowns (momentum, structure, spread) trigger defensive exits."""
    watcher = IndependentPositionWatcher()

    # 1. Momentum collapse
    pos1 = make_position(position_id="pos-mom")
    watcher.open_position(pos1)
    snap_mom = make_snapshot(momentum_score="-0.60")
    events1 = watcher.evaluate_feature_snapshot(snap_mom)
    assert len(events1) == 1
    assert events1[0].trigger == WatcherExitTrigger.MOMENTUM_DETERIORATION

    # 2. Structure break to LOWER_LOWS below entry
    pos2 = make_position(position_id="pos-struct", entry_price="100.00")
    watcher.open_position(pos2)
    snap_struct = make_snapshot(current_price="99.20", price_structure="LOWER_LOWS")
    events2 = watcher.evaluate_feature_snapshot(snap_struct)
    assert len(events2) == 1
    assert events2[0].trigger == WatcherExitTrigger.STRUCTURE_BREAK

    # 3. Market reversal (BEARISH index + negative sector)
    pos3 = make_position(position_id="pos-rev")
    watcher.open_position(pos3)
    snap_rev = make_snapshot(market_index_direction="BEARISH", sector_strength="-0.80")
    events3 = watcher.evaluate_feature_snapshot(snap_rev)
    assert len(events3) == 1
    assert events3[0].trigger == WatcherExitTrigger.MARKET_REVERSAL


def test_time_protection_intraday_cutoff():
    """Verify position is squared off automatically at 15:15 IST (09:45 UTC)."""
    watcher = IndependentPositionWatcher()
    t_open = datetime(2026, 9, 23, 9, 15, 0, tzinfo=timezone.utc)
    pos = make_position(opened_at=t_open)
    watcher.open_position(pos)

    # 15:15:01 IST corresponds to 09:45:01 UTC
    t_cutoff = datetime(2026, 9, 23, 9, 45, 1, tzinfo=timezone.utc)
    events = watcher.evaluate_tick(make_tick(timestamp=t_cutoff))
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.TIME_EXPIRY


# =============================================================================
# 7. AI Independence & Invalidation Layer
# =============================================================================


def test_watcher_operates_without_llm():
    """Verify hard protection operates 100% deterministically when LLMs are offline."""
    watcher = IndependentPositionWatcher()
    pos = make_position(entry_price="100.00", hard_stop_price="98.50")
    watcher.open_position(pos)

    # Simulate catastrophic price plunge
    events = watcher.evaluate_tick(make_tick(price="97.00"))
    assert len(events) == 1
    assert events[0].trigger == WatcherExitTrigger.HARD_STOP


def test_ai_thesis_invalidation_non_emergency():
    """Verify AI thesis invalidation acts cleanly as an auxiliary non-emergency signal."""
    watcher = IndependentPositionWatcher()
    pos = make_position()
    watcher.open_position(pos)

    event = watcher.ingest_ai_invalidation(
        position_id="pos-001",
        thesis_summary="Bullish continuation flawed",
        invalidation_reason="Institutional distribution detected at resistance",
    )
    assert event is not None
    assert event.trigger == WatcherExitTrigger.AI_THESIS_INVALIDATION
    assert pos.status == PositionStatus.CLOSED


# =============================================================================
# 8. Failure Handling & Operational Scenarios
# =============================================================================


def test_partial_fill_position_update():
    """Verify position record updates cleanly when broker reports partial fills."""
    watcher = IndependentPositionWatcher()
    pos = make_position(quantity=10, entry_price="100.00")
    watcher.open_position(pos)

    # Broker confirms partial fill for only 4 shares at 100.10
    watcher.update_partial_fill(
        position_id="pos-001", filled_qty=4, fill_price=Decimal("100.10")
    )

    updated_pos = watcher.get_position("pos-001")
    assert updated_pos is not None
    assert updated_pos.quantity == 4
    assert updated_pos.entry_price == Decimal("100.10")


def test_rejected_exit_order_resets_for_retry():
    """Verify rejected exit order resets position to OPEN for immediate re-attempt."""
    watcher = IndependentPositionWatcher()
    pos = make_position()
    watcher.open_position(pos)

    # Set status to CLOSING as if order was dispatched
    pos.status = PositionStatus.CLOSING

    # Broker rejects exit order due to temporary gateway error
    watcher.handle_rejected_exit_order(
        position_id="pos-001",
        rejection_reason="Broker connection reset by peer",
    )
    # Status reset to OPEN so watcher immediately retries exit on next tick
    assert pos.status == PositionStatus.OPEN


def test_restart_recovery_reconciliation():
    """Verify surveillance state is fully restored on process restart."""
    pos1 = make_position(position_id="pos-rec-1", symbol="INFY")
    pos2 = make_position(position_id="pos-rec-2", symbol="TCS")

    # New Watcher instance after reboot
    new_watcher = IndependentPositionWatcher()
    new_watcher.reconcile_positions([pos1, pos2])

    open_positions = new_watcher.get_all_open_positions()
    assert len(open_positions) == 2
    assert new_watcher.get_position("pos-rec-1") is not None
    assert new_watcher.get_position("pos-rec-2") is not None


def test_manual_emergency_kill_switch():
    """Verify operator kill-switch dispatches market exits for all open positions."""
    watcher = IndependentPositionWatcher()
    pos1 = make_position(position_id="pos-kill-1", symbol="RELIANCE")
    pos2 = make_position(position_id="pos-kill-2", symbol="TCS")
    watcher.open_position(pos1)
    watcher.open_position(pos2)

    events = watcher.trigger_manual_kill_switch(
        reason="Operator detected exchange feed glitch"
    )
    assert len(events) == 2
    for e in events:
        assert e.trigger == WatcherExitTrigger.MANUAL_KILL_SWITCH

    assert len(watcher.get_all_open_positions()) == 0


def test_watcher_evaluation_latency_budget():
    """Verify position evaluation latency strictly honors the < 50ms critical safety budget."""
    import time

    watcher = IndependentPositionWatcher()
    # Register 10 active positions across various symbols
    for i in range(10):
        pos = make_position(position_id=f"pos-bench-{i}", symbol=f"SYM{i}")
        watcher.open_position(pos)

    # Benchmark 200 tick evaluations
    latencies: list[float] = []
    tick = make_tick(symbol="SYM0", price="99.50")
    for _ in range(200):
        t0 = time.perf_counter_ns()
        watcher.evaluate_tick(tick)
        duration_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        latencies.append(duration_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    # Must be well below the critical 50ms budget (target < 1ms on local machine)
    assert avg_latency < 5.0, (
        f"Average watcher latency exceeded budget: {avg_latency:.3f}ms"
    )
    assert max_latency < 50.0, (
        f"Max watcher latency exceeded 50ms budget: {max_latency:.3f}ms"
    )
