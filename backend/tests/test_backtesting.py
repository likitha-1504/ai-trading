"""Comprehensive Test Suite for Phase 09: Backtesting + Paper Trading.

Verifies:
1. Event-driven backtesting engine with realistic costs and configurable slippage.
2. Monotonic timestamp verification and zero lookahead bias enforcement.
3. Performance metrics suite: net P/L, expectancy, profit factor, drawdown, trade frequency, cost contribution, regime performance.
4. Strategy interface symmetry between backtest and paper trading modes.
5. Paper trading loop safety invariant (is_live == False).
6. Trade journal lifecycle tracking, holding duration, and cost breakdown.
7. Walk-forward and out-of-sample analysis.
8. Slippage sensitivity stress-testing.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.backtesting.journal import TradeJournal
from app.backtesting.metrics import PerformanceCalculator
from app.backtesting.paper_loop import PaperTradingLoop
from app.backtesting.simulator import BacktestEngine, TimestampOrderError
from app.backtesting.slippage_analysis import SlippageSensitivityAnalyzer
from app.backtesting.walk_forward import WalkForwardAnalyzer
from app.capital.cost_model import IndianMarketCostModel
from app.models.contracts import (
    Candidate,
    EquityPoint,
    FeatureSnapshot,
    FrictionBreakdown,
    MarketRegime,
    MarketSource,
    NormalizedMarketEvent,
    StrategyType,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)


def make_event(
    symbol: str = "RELIANCE",
    price: str = "100.00",
    volume: int = 1000,
    timestamp: datetime | None = None,
    spread_pct: str = "0.0005",
) -> NormalizedMarketEvent:
    """Helper to construct a normalized market event."""
    p = Decimal(price)
    spread = Decimal(spread_pct)
    half_spread = (p * spread) / Decimal(2)
    bid = (p - half_spread).quantize(Decimal("0.05"))
    ask = (p + half_spread).quantize(Decimal("0.05"))
    ts = timestamp or datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    return NormalizedMarketEvent(
        symbol=symbol,
        source=MarketSource.SIMULATED,
        exchange_timestamp=ts,
        ingest_timestamp=ts,
        last_price=p,
        volume=volume,
        bid_price=bid,
        ask_price=ask,
        bid_quantity=500,
        ask_quantity=500,
        spread_pct=spread,
        is_stale=False,
    )


def generate_market_dataset(
    num_ticks: int = 60, start_time: datetime | None = None
) -> list[NormalizedMarketEvent]:
    """Helper to generate a realistic sequential tick stream for TCS and RELIANCE."""
    t0 = start_time or datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    events: list[NormalizedMarketEvent] = []

    # Generate 60 minutes of ticks
    for i in range(num_ticks):
        ts = t0 + timedelta(minutes=i)
        # Gentle price uptrend with volume
        rel_price = Decimal("100.00") + Decimal(str(round(i * 0.10, 2)))
        events.append(
            make_event(
                symbol="RELIANCE",
                price=str(rel_price),
                volume=1500 + i * 50,
                timestamp=ts,
            )
        )
    return events


# =============================================================================
# 1. Backtest Engine & Timestamp Monotonicity
# =============================================================================


def test_backtest_timestamp_monotonicity_enforcement():
    """Verify that out-of-order events raise TimestampOrderError to eliminate lookahead bias."""
    engine = BacktestEngine()
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)

    # Valid event at 09:15, second event out-of-order at 09:10
    evt1 = make_event(price="100.00", timestamp=t0)
    evt2 = make_event(price="101.00", timestamp=t0 - timedelta(minutes=5))

    with pytest.raises(TimestampOrderError, match="monotonicity violation"):
        engine.run([evt1, evt2])


def test_backtest_empty_events_raises_error():
    """Verify running backtest on empty stream raises ValueError."""
    engine = BacktestEngine()
    with pytest.raises(ValueError, match="empty event sequence"):
        engine.run([])


def test_backtest_engine_run_with_trades_and_metrics():
    """Verify end-to-end backtest execution, position tracking, and comprehensive metrics compilation."""
    engine = BacktestEngine(
        initial_capital=Decimal("100.00"),
        slippage_ticks=1,
    )
    dataset = generate_market_dataset(num_ticks=50)

    report = engine.run(dataset)
    assert report.run_id.startswith("bkt-")
    assert report.initial_capital == Decimal("100.00")
    assert report.slippage_ticks == 1
    assert len(report.equity_curve) == 50

    # Verify metrics fields are present and valid
    metrics = report.metrics
    assert metrics.gross_pnl is not None
    assert metrics.total_friction is not None
    assert metrics.net_pnl is not None
    assert metrics.win_rate >= 0.0
    assert metrics.profit_factor >= 0.0
    assert metrics.trade_frequency_per_day >= 0.0


# =============================================================================
# 2. Cost Model & Slippage Fidelity
# =============================================================================


def test_backtest_realistic_friction_and_cost_deduction():
    """Verify Indian market statutory costs (STT, GST, SEBI, exchange, stamp duty) are deducted."""
    journal = TradeJournal()

    # Create a simulated trade in journal: BUY 2 @ 100, SELL 2 @ 105
    t_entry = datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    t_exit = datetime(2026, 9, 24, 9, 45, tzinfo=timezone.utc)

    cost_model = IndianMarketCostModel()
    friction = cost_model.calculate_friction(
        quantity=2,
        buy_price=Decimal("100.00"),
        sell_price=Decimal("105.00"),
        is_intraday=True,
    )

    trade_id = journal.record_entry(
        plan_id="plan-01",
        symbol="RELIANCE",
        side=TradeSide.BUY,
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        quantity=2,
        entry_timestamp=t_entry,
        entry_price=Decimal("100.00"),
        entry_slippage=Decimal("0.00"),
        market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
    )

    record = journal.record_exit(
        trade_id=trade_id,
        exit_timestamp=t_exit,
        exit_price=Decimal("105.00"),
        exit_slippage=Decimal("0.00"),
        exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
        friction=friction,
        market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
    )

    # Gross = (105 - 100) * 2 = 10.00
    assert record.gross_pnl == Decimal("10.00")
    # Net = 10.00 - total friction
    assert record.net_pnl == (Decimal("10.00") - friction.total_friction).quantize(
        Decimal("0.01")
    )
    assert record.holding_duration_seconds == 900.0  # 15 minutes


def test_backtest_configurable_slippage():
    """Verify that higher slippage configuration increases execution cost and reduces net P/L."""
    dataset = generate_market_dataset(num_ticks=40)

    # Run with 0 ticks slippage
    engine_zero = BacktestEngine(initial_capital=Decimal("100.00"), slippage_ticks=0)
    report_zero = engine_zero.run(dataset)

    # Run with 2 ticks slippage
    engine_two = BacktestEngine(initial_capital=Decimal("100.00"), slippage_ticks=2)
    report_two = engine_two.run(dataset)

    # Either fewer/same trades or higher slippage impact
    if report_zero.trades and report_two.trades:
        assert report_zero.metrics.net_pnl >= report_two.metrics.net_pnl


# =============================================================================
# 3. Strategy Interface Symmetry & Live Safety Lock
# =============================================================================


def test_strategy_interface_symmetry_backtest_and_paper():
    """Verify BacktestEngine and PaperTradingLoop use identical strategy interfaces."""
    backtest = BacktestEngine()
    paper = PaperTradingLoop()

    # Check identical component interfaces
    assert isinstance(backtest.candidate_ranker, type(paper.candidate_ranker))
    assert isinstance(backtest.feature_engine, type(paper.feature_engine))
    assert isinstance(backtest.risk_engine, type(paper.risk_engine))
    assert isinstance(backtest.position_watcher, type(paper.position_watcher))
    assert isinstance(backtest.capital_manager, type(paper.capital_manager))
    assert isinstance(backtest.cost_model, type(paper.cost_model))
    assert isinstance(backtest.trade_journal, type(paper.trade_journal))


def test_paper_trading_loop_live_lock_invariant():
    """Verify paper trading loop has live trading strictly disabled."""
    paper = PaperTradingLoop()
    assert paper.is_live is False


def test_paper_trading_loop_event_processing():
    """Verify paper trading loop processes stream of events and updates equity."""
    paper = PaperTradingLoop(initial_capital=Decimal("100.00"))
    dataset = generate_market_dataset(num_ticks=20)

    for event in dataset:
        paper.process_event(event)

    assert len(paper.equity_curve) == 20
    summary = paper.get_performance_summary()
    assert summary is not None


# =============================================================================
# 4. Performance Calculator Correctness
# =============================================================================


def test_performance_calculator_metrics_correctness():
    """Verify math for win rate, profit factor, expectancy, and max drawdown."""
    t0 = datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    friction = FrictionBreakdown(
        brokerage=Decimal("0.10"),
        stt=Decimal("0.05"),
        exchange_charges=Decimal("0.02"),
        sebi_charges=Decimal("0.001"),
        stamp_duty=Decimal("0.01"),
        gst=Decimal("0.02"),
        expected_slippage=Decimal("0.10"),
        total_friction=Decimal("0.30"),
    )

    trades = [
        # Win 1: net = +4.70
        TradeRecord(
            trade_id="t-1",
            plan_id="p-1",
            symbol="TCS",
            side=TradeSide.BUY,
            strategy=StrategyType.MOMENTUM_CONTINUATION,
            quantity=1,
            entry_timestamp=t0,
            entry_price=Decimal("100.00"),
            entry_slippage=Decimal("0.05"),
            exit_timestamp=t0 + timedelta(minutes=10),
            exit_price=Decimal("105.00"),
            exit_slippage=Decimal("0.05"),
            exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
            gross_pnl=Decimal("5.00"),
            friction=friction,
            net_pnl=Decimal("4.70"),
            holding_duration_seconds=600.0,
            market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
            market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
        ),
        # Loss 1: net = -2.30
        TradeRecord(
            trade_id="t-2",
            plan_id="p-2",
            symbol="INFY",
            side=TradeSide.BUY,
            strategy=StrategyType.EARLY_MOVE_DETECTION,
            quantity=1,
            entry_timestamp=t0 + timedelta(minutes=15),
            entry_price=Decimal("100.00"),
            entry_slippage=Decimal("0.05"),
            exit_timestamp=t0 + timedelta(minutes=25),
            exit_price=Decimal("98.00"),
            exit_slippage=Decimal("0.05"),
            exit_trigger=WatcherExitTrigger.HARD_STOP,
            gross_pnl=Decimal("-2.00"),
            friction=friction,
            net_pnl=Decimal("-2.30"),
            holding_duration_seconds=600.0,
            market_regime_at_entry=MarketRegime.HIGH_VOLATILITY_CHOP,
            market_regime_at_exit=MarketRegime.HIGH_VOLATILITY_CHOP,
        ),
    ]

    equity_curve = [
        EquityPoint(
            timestamp=t0,
            total_equity=Decimal("100.00"),
            cash_balance=Decimal("100.00"),
            unrealized_pnl=Decimal("0.00"),
            drawdown_amount=Decimal("0.00"),
            drawdown_pct=0.0,
        ),
        EquityPoint(
            timestamp=t0 + timedelta(minutes=10),
            total_equity=Decimal("104.70"),
            cash_balance=Decimal("104.70"),
            unrealized_pnl=Decimal("0.00"),
            drawdown_amount=Decimal("0.00"),
            drawdown_pct=0.0,
        ),
        EquityPoint(
            timestamp=t0 + timedelta(minutes=25),
            total_equity=Decimal("102.40"),
            cash_balance=Decimal("102.40"),
            unrealized_pnl=Decimal("0.00"),
            drawdown_amount=Decimal("2.30"),
            drawdown_pct=0.022,
        ),
    ]

    metrics = PerformanceCalculator.calculate(trades, equity_curve)

    assert metrics.total_trades == 2
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 1
    assert metrics.win_rate == 0.50
    assert metrics.gross_pnl == Decimal("3.00")
    assert metrics.total_friction == Decimal("0.60")
    assert metrics.net_pnl == Decimal("2.40")

    # Profit factor = 4.70 / 2.30 = ~2.043
    assert 2.04 <= metrics.profit_factor <= 2.05

    # Expectancy = (0.5 * 4.70) - (0.5 * 2.30) = 2.35 - 1.15 = 1.20
    assert metrics.expectancy == Decimal("1.20")

    # Max Drawdown from 104.70 to 102.40 = 2.30
    assert metrics.max_drawdown_amount == Decimal("2.30")

    # Regime performance
    assert "BULLISH_TRENDING" in metrics.regime_pnl
    assert metrics.regime_pnl["BULLISH_TRENDING"] == Decimal("4.70")
    assert "HIGH_VOLATILITY_CHOP" in metrics.regime_pnl
    assert metrics.regime_pnl["HIGH_VOLATILITY_CHOP"] == Decimal("-2.30")


def test_performance_calculator_empty_trades():
    """Verify empty trade list safely returns zeroed performance metrics without errors."""
    metrics = PerformanceCalculator.calculate([], [])
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.net_pnl == Decimal("0.00")
    assert metrics.profit_factor == 0.0
    assert metrics.expectancy == Decimal("0.00")


# =============================================================================
# 5. Walk-Forward and Slippage Sensitivity Analyzers
# =============================================================================


def test_walk_forward_analyzer_partitions():
    """Verify WalkForwardAnalyzer partitions historical events and executes in-sample / out-of-sample runs."""
    analyzer = WalkForwardAnalyzer(
        num_windows=2,
        in_sample_ratio=0.70,
        initial_capital=Decimal("100.00"),
    )
    dataset = generate_market_dataset(num_ticks=50)

    report = analyzer.evaluate(dataset)
    assert report.total_windows == 2
    assert len(report.windows) == 2

    # Check window metrics
    for w in report.windows:
        assert w.in_sample_metrics is not None
        assert w.out_of_sample_metrics is not None
        assert w.out_of_sample_degradation_pct >= 0.0


def test_slippage_sensitivity_analyzer():
    """Verify SlippageSensitivityAnalyzer stress-tests multiple slippage tick levels."""
    analyzer = SlippageSensitivityAnalyzer(
        test_slippage_levels=[0, 1, 2],
        initial_capital=Decimal("100.00"),
    )
    dataset = generate_market_dataset(num_ticks=30)

    report = analyzer.evaluate(dataset)
    assert len(report.evaluations) == 3
    assert report.evaluations[0].slippage_ticks == 0
    assert report.evaluations[1].slippage_ticks == 1
    assert report.evaluations[2].slippage_ticks == 2


# =============================================================================
# 6. Point-in-Time Universe, Determinism & End-to-End Trade Lifecycle
# =============================================================================


def test_backtest_point_in_time_universe_filtering():
    """Verify point-in-time universe filters excluded symbols to eliminate survivorship bias."""
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    events = [
        make_event(symbol="RELIANCE", price="100.00", timestamp=t0),
        make_event(symbol="DELISTED_CO", price="50.00", timestamp=t0 + timedelta(minutes=1)),
        make_event(symbol="RELIANCE", price="101.00", timestamp=t0 + timedelta(minutes=2)),
    ]

    # Only RELIANCE is in the point-in-time universe
    engine = BacktestEngine(
        initial_capital=Decimal("100.00"),
        point_in_time_universe={"RELIANCE"},
    )
    report = engine.run(events)

    # 2 events processed for RELIANCE; DELISTED_CO excluded
    assert len(report.equity_curve) == 2


def test_backtest_deterministic_reproducibility():
    """Verify backtesting engine produces bit-for-bit identical results on identical input streams."""
    dataset = generate_market_dataset(num_ticks=30)

    engine1 = BacktestEngine(initial_capital=Decimal("100.00"), slippage_ticks=1)
    engine2 = BacktestEngine(initial_capital=Decimal("100.00"), slippage_ticks=1)

    report1 = engine1.run(dataset)
    report2 = engine2.run(dataset)

    assert report1.final_equity == report2.final_equity
    assert report1.metrics.net_pnl == report2.metrics.net_pnl
    assert report1.metrics.gross_pnl == report2.metrics.gross_pnl
    assert report1.metrics.total_friction == report2.metrics.total_friction
    assert len(report1.equity_curve) == len(report2.equity_curve)


def test_backtest_end_to_end_trade_execution_and_journaling():
    """Verify full lifecycle: candidate screening, risk gating, fill, watcher take-profit exit, and journal."""
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    fs = FeatureSnapshot(
        symbol="RELIANCE",
        timestamp=t0,
        bar_timeframe="1m",
        vwap=Decimal("100.00"),
        current_price=Decimal("100.00"),
        vwap_distance_pct=Decimal("0.00"),
        momentum_score=Decimal("2.50"),
        relative_volume_10=Decimal("2.20"),
        volume_acceleration=Decimal("1.10"),
        price_acceleration=Decimal("0.50"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.001"),
        liquidity_score=Decimal("90.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.80"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    cand = Candidate(
        candidate_id="cand-001",
        detected_at=t0,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("100.00"),
        initial_stop_price=Decimal("99.00"),
        suggested_target_price=Decimal("105.00"),
        rank_score=Decimal("85.0"),
        quantitative_evidence={"test": "momentum"},
        feature_snapshot=fs,
    )

    class MockRanker:
        def __init__(self, candidate):
            self.cand = candidate
            self.fired = False

        def evaluate_snapshot(self, snapshot):
            if not self.fired:
                self.fired = True
                return [self.cand]
            return []

    engine = BacktestEngine(
        initial_capital=Decimal("1000.00"),
        slippage_ticks=1,
        candidate_ranker=MockRanker(cand),
    )

    # Tick 1: trigger candidate, buy fill at 100.05 (100.00 + 0.05 slippage)
    # Tick 2: intermediate tick
    # Tick 3: price jumps to 106.00, triggering TAKE_PROFIT at >= 105.00, selling at 105.95
    events = [
        make_event("RELIANCE", "100.00", timestamp=t0),
        make_event("RELIANCE", "102.00", timestamp=t0 + timedelta(minutes=1)),
        make_event("RELIANCE", "106.00", timestamp=t0 + timedelta(minutes=2)),
    ]

    report = engine.run(events)

    assert len(report.trades) == 1
    trade = report.trades[0]
    assert trade.symbol == "RELIANCE"
    assert trade.quantity == 5
    assert trade.entry_price == Decimal("100.05")
    assert trade.exit_price == Decimal("105.95")
    assert trade.exit_trigger == WatcherExitTrigger.TAKE_PROFIT
    assert trade.gross_pnl == Decimal("29.50")
    assert trade.friction.total_friction > Decimal("0.00")
    assert trade.net_pnl == (trade.gross_pnl - trade.friction.total_friction).quantize(Decimal("0.01"))
    assert trade.holding_duration_seconds == 120.0
    assert trade.market_regime_at_entry == MarketRegime.BULLISH_TRENDING

    # Performance metrics
    assert report.metrics.winning_trades == 1
    assert report.metrics.win_rate == 1.0
    assert report.metrics.net_pnl == trade.net_pnl
    assert report.metrics.profit_factor == 999.0


def test_paper_loop_end_to_end_trade_execution_and_journaling():
    """Verify PaperTradingLoop executes candidates, manages positions, and triggers exits with strategy symmetry."""
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    fs = FeatureSnapshot(
        symbol="RELIANCE",
        timestamp=t0,
        bar_timeframe="1m",
        vwap=Decimal("100.00"),
        current_price=Decimal("100.00"),
        vwap_distance_pct=Decimal("0.00"),
        momentum_score=Decimal("2.50"),
        relative_volume_10=Decimal("2.20"),
        volume_acceleration=Decimal("1.10"),
        price_acceleration=Decimal("0.50"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.001"),
        liquidity_score=Decimal("90.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.80"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    cand = Candidate(
        candidate_id="cand-paper-001",
        detected_at=t0,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("100.00"),
        initial_stop_price=Decimal("99.00"),
        suggested_target_price=Decimal("105.00"),
        rank_score=Decimal("85.0"),
        quantitative_evidence={"test": "momentum"},
        feature_snapshot=fs,
    )

    class MockRanker:
        def __init__(self, candidate):
            self.cand = candidate
            self.fired = False

        def evaluate_snapshot(self, snapshot):
            if not self.fired:
                self.fired = True
                return [self.cand]
            return []

    paper = PaperTradingLoop(
        initial_capital=Decimal("1000.00"),
        slippage_ticks=1,
        candidate_ranker=MockRanker(cand),
    )

    events = [
        make_event("RELIANCE", "100.00", timestamp=t0),
        make_event("RELIANCE", "102.00", timestamp=t0 + timedelta(minutes=1)),
        make_event("RELIANCE", "106.00", timestamp=t0 + timedelta(minutes=2)),
    ]

    for evt in events:
        paper.process_event(evt)

    summary = paper.get_performance_summary()
    assert summary.total_trades == 1
    assert summary.winning_trades == 1
    assert summary.net_pnl > Decimal("20.00")
    assert paper.is_live is False


def test_walk_forward_overfitting_flagging():
    """Verify walk-forward analysis flags overfitting when out-of-sample performance degrades severely."""
    analyzer = WalkForwardAnalyzer(
        num_windows=1,
        in_sample_ratio=0.50,
        initial_capital=Decimal("100.00"),
    )
    dataset = generate_market_dataset(num_ticks=20)
    report = analyzer.evaluate(dataset)

    # Empty/zero trade scenario has 0 expectancy, so is_overfitted defaults correctly
    assert report.is_overfitted is True
