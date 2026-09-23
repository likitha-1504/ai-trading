"""Comprehensive test suite for Phase 07: Capital, Risk & Cost Engine.

Verifies:
1. Configurable Indian equity cost model (Brokerage, STT, Exchange, SEBI, Stamp Duty, GST, Slippage)
2. Zero hardcoded fees (verifying custom configurations)
3. Breakeven price and net edge evaluation with statistical hurdle
4. CapitalManager balance accounting (total capital, available, deployed, realized/unrealized P/L, buying power)
5. Position concentration and high-water mark tracking
6. RiskEngine position sizing (1.5% max risk, buying power, concentration limits)
7. Daily loss circuit breaker enforcement (3.0% drawdown)
8. Max active positions limit (2 concurrent positions) and duplicate symbol rejection
9. Minimum economical trade size enforcement
10. Autonomy threshold policy (₹100 baseline autonomous, > ₹300 requires human approval)
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig, CostModelConfig, RiskLimitsConfig
from app.capital.cost_model import IndianMarketCostModel
from app.capital.risk_engine import RiskEngine
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    FeatureSnapshot,
    MarketRegime,
    PositionSnapshot,
    PositionStatus,
    StrategyType,
    TradeSide,
)


def make_snapshot(
    symbol: str = "TCS",
    current_price: str = "100.00",
) -> FeatureSnapshot:
    """Helper to construct a valid FeatureSnapshot for tests."""
    return FeatureSnapshot(
        symbol=symbol,
        timestamp=datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc),
        bar_timeframe="1m",
        vwap=Decimal("99.50"),
        current_price=Decimal(current_price),
        vwap_distance_pct=Decimal("0.50"),
        momentum_score=Decimal("1.25"),
        relative_volume_10=Decimal("2.10"),
        volume_acceleration=Decimal("15.00"),
        price_acceleration=Decimal("0.35"),
        realized_volatility_15=Decimal("0.20"),
        spread_pct=Decimal("0.0005"),
        liquidity_score=Decimal("85.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.40"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )


def make_candidate(
    candidate_id: str = "cand-001",
    symbol: str = "TCS",
    entry_price: str = "100.00",
    initial_stop_price: str = "98.50",
    target_price: str = "104.50",
    score: float = 85.0,
) -> Candidate:
    """Helper to create a realistic Candidate instance for risk gating."""
    p_entry = Decimal(entry_price)
    return Candidate(
        candidate_id=candidate_id,
        detected_at=datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc),
        symbol=symbol,
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=p_entry,
        initial_stop_price=Decimal(initial_stop_price),
        suggested_target_price=Decimal(target_price),
        rank_score=Decimal(str(score)),
        quantitative_evidence={"momentum_roc": 1.25, "rvol": 2.1},
        feature_snapshot=make_snapshot(symbol=symbol, current_price=entry_price),
    )


def make_position(
    position_id: str = "pos-001",
    symbol: str = "INFY",
    entry_price: str = "50.00",
    quantity: int = 1,
    unrealized_pnl: str = "0.00",
) -> PositionSnapshot:
    """Helper to create an active PositionSnapshot."""
    t0 = datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    return PositionSnapshot(
        position_id=position_id,
        plan_id=f"plan-{position_id}",
        symbol=symbol,
        side=TradeSide.BUY,
        quantity=quantity,
        entry_price=Decimal(entry_price),
        current_price=Decimal(entry_price),
        hard_stop_price=Decimal("48.50"),
        unrealized_pnl=Decimal(unrealized_pnl),
        status=PositionStatus.OPEN,
        opened_at=t0,
        last_evaluated_at=t0,
    )


# =============================================================================
# 1. Cost Model & Friction Calculations
# =============================================================================


def test_cost_model_standard_intraday_friction():
    """Verify detailed statutory breakdown for a typical intraday trade."""
    cost_model = IndianMarketCostModel()
    # Buy 1 share at 100.00, Sell at 105.00
    # Buy turnover = 100.00, Sell turnover = 105.00, Total turnover = 205.00
    friction = cost_model.calculate_friction(
        quantity=1,
        buy_price=Decimal("100.00"),
        sell_price=Decimal("105.00"),
        is_intraday=True,
    )

    # 1. Brokerage: min(100 * 0.0003, 20) = 0.03; min(105 * 0.0003, 20) = 0.0315 -> total = 0.0615
    assert friction.brokerage == Decimal("0.0615")

    # 2. STT: intraday sell turnover only = 105 * 0.00025 = 0.02625 -> 0.0263
    assert friction.stt == Decimal("0.0263")

    # 3. Exchange charges: 205 * 0.0000345 = 0.0070725 -> 0.0071
    assert friction.exchange_charges == Decimal("0.0071")

    # 4. SEBI charges: 205 * 0.000001 = 0.000205 -> 0.0002
    assert friction.sebi_charges == Decimal("0.0002")

    # 5. Stamp duty: buy turnover only = 100 * 0.00003 = 0.0030
    assert friction.stamp_duty == Decimal("0.0030")

    # 6. GST: 18% on (0.0615 + 0.0071 + 0.0002) = 0.0688 * 0.18 = 0.012384 -> 0.0124
    assert friction.gst == Decimal("0.0124")

    # 7. Slippage: 2 legs * 0.05 tick size * 1 tick = 0.1000
    assert friction.expected_slippage == Decimal("0.1000")

    # 8. Total friction: sum of components
    expected_sum = (
        friction.brokerage
        + friction.stt
        + friction.exchange_charges
        + friction.sebi_charges
        + friction.stamp_duty
        + friction.gst
        + friction.expected_slippage
    )
    assert friction.total_friction == expected_sum


def test_cost_model_zero_hardcoded_fees_custom_rates():
    """Verify that cost model uses 100% configurable parameters without hardcoding."""
    custom_config = CostModelConfig(
        brokerage_rate=Decimal("0.0010"),  # 0.1%
        brokerage_flat_cap=Decimal("10.00"),
        stt_intraday_rate=Decimal("0.0005"),
        exchange_txn_charge_rate=Decimal("0.0001"),
        sebi_turnover_charge_rate=Decimal("0.00001"),
        stamp_duty_intraday_rate=Decimal("0.0001"),
        gst_rate=Decimal("0.20"),  # 20% GST
        slippage_ticks=2,
        tick_size=Decimal("0.10"),
    )
    cost_model = IndianMarketCostModel(config=custom_config)

    friction = cost_model.calculate_friction(
        quantity=10,
        buy_price=Decimal("50.00"),
        sell_price=Decimal("55.00"),
    )

    # Buy turnover = 500, Sell turnover = 550, Total = 1050
    # Brokerage: min(500 * 0.001, 10) = 0.50; min(550 * 0.001, 10) = 0.55 -> total = 1.05
    assert friction.brokerage == Decimal("1.0500")
    # Slippage: 10 * (0.10 * 2 * 2) = 4.00
    assert friction.expected_slippage == Decimal("4.0000")
    assert friction.total_friction > Decimal("5.00")


def test_cost_model_breakeven_price_calculation():
    """Verify breakeven calculation accurately computes the minimum profitable exit price."""
    cost_model = IndianMarketCostModel()
    buy_price = Decimal("100.00")
    quantity = 1

    breakeven_price = cost_model.calculate_breakeven_price(
        quantity=quantity,
        buy_price=buy_price,
    )

    # Breakeven price must be strictly greater than entry price to cover friction
    assert breakeven_price > buy_price

    # Selling at breakeven should generate gross gain matching total friction
    gross_gain = (breakeven_price - buy_price) * Decimal(quantity)
    friction = cost_model.calculate_friction(
        quantity=quantity,
        buy_price=buy_price,
        sell_price=breakeven_price,
    )
    assert abs(gross_gain - friction.total_friction) < Decimal("0.05")


def test_net_edge_evaluation():
    """Verify statistical net edge evaluation and hurdle rejection."""
    cost_model = IndianMarketCostModel()
    friction = cost_model.calculate_friction(
        quantity=1,
        buy_price=Decimal("100.00"),
        sell_price=Decimal("103.00"),
    )

    # Setup A: Strong positive edge (Target +3.00, Risk -1.00, 60% win rate)
    gross_edge, net_edge, passes = cost_model.evaluate_net_edge(
        expected_gross_gain=Decimal("3.00"),
        potential_loss=Decimal("1.00"),
        p_win=Decimal("0.60"),
        friction=friction,
        hurdle_rate=Decimal("0.10"),
    )
    # Gross edge = (3.00 * 0.60) - (1.00 * 0.40) = 1.80 - 0.40 = 1.40
    assert gross_edge == Decimal("1.4000")
    assert net_edge == Decimal("1.4000") - friction.total_friction
    assert passes is True

    # Setup B: Insufficient edge eaten by friction (Target +0.30, Risk -0.50, 50% win rate)
    _g2, net_edge2, passes2 = cost_model.evaluate_net_edge(
        expected_gross_gain=Decimal("0.30"),
        potential_loss=Decimal("0.50"),
        p_win=Decimal("0.50"),
        friction=friction,
        hurdle_rate=Decimal("0.10"),
    )
    # Gross edge = 0.15 - 0.25 = -0.10 -> Negative edge
    assert passes2 is False
    assert net_edge2 < Decimal("0.00")


# =============================================================================
# 2. Capital Manager Tracking & Balances
# =============================================================================


def test_capital_manager_lifecycle():
    """Verify complete capital state lifecycle: deposit, allocate, exit, and snapshot."""
    config = CapitalConfig(
        starting_capital=Decimal("100.00"), leverage_multiplier=Decimal("1.0")
    )
    manager = CapitalManager(config=config)

    # Initial state
    assert manager.total_capital == Decimal("100.00")
    assert manager.available_capital == Decimal("100.00")
    assert manager.deployed_capital == Decimal("0.00")
    assert manager.buying_power == Decimal("100.00")

    # Allocate 50 INR for 1 share of INFY at 50.00
    assert (
        manager.allocate_capital(
            position_id="pos-01", symbol="INFY", quantity=1, price=Decimal("50.00")
        )
        is True
    )

    assert manager.available_capital == Decimal("50.00")
    assert manager.deployed_capital == Decimal("50.00")
    assert manager.buying_power == Decimal("50.00")
    assert manager.total_capital == Decimal("100.00")
    assert manager.get_position_concentration("INFY") == Decimal("0.5000")

    # Position closes at 53.00: gross P/L = +3.00, friction = 0.20 -> net P/L = +2.80
    manager.release_capital(
        position_id="pos-01",
        symbol="INFY",
        quantity=1,
        exit_price=Decimal("53.00"),
        gross_realized_pnl=Decimal("3.00"),
        friction=Decimal("0.20"),
    )

    assert manager.deployed_capital == Decimal("0.00")
    assert manager.realized_pnl == Decimal("2.80")
    assert manager.available_capital == Decimal("102.80")
    assert manager.total_capital == Decimal("102.80")
    assert manager.high_water_mark == Decimal("102.80")
    assert manager.get_position_concentration("INFY") == Decimal("0.0000")


def test_capital_manager_drawdown_and_unrealized_pnl():
    """Verify floating P/L and daily drawdown tracking."""
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    manager.allocate_capital("p-1", "RELIANCE", 1, Decimal("100.00"))

    # Open position moves against us by -2.50
    pos = make_position("p-1", "RELIANCE", entry_price="100.00", unrealized_pnl="-2.50")
    manager.update_unrealized_pnl([pos])

    assert manager.unrealized_pnl == Decimal("-2.50")
    assert manager.total_capital == Decimal("97.50")

    dd_amt, dd_pct = manager.get_daily_drawdown()
    assert dd_amt == Decimal("2.50")
    assert dd_pct == Decimal("0.0250")  # 2.5% drawdown

    snapshot = manager.get_capital_snapshot()
    assert snapshot.total_capital == Decimal("97.50")
    assert snapshot.daily_drawdown_amount == Decimal("2.50")
    assert snapshot.daily_drawdown_pct == Decimal("0.0250")


def test_capital_manager_deposit_and_withdrawal():
    """Verify deposit and withdrawal safety constraints."""
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))

    manager.deposit(Decimal("50.00"))
    assert manager.available_capital == Decimal("150.00")
    assert manager.total_capital == Decimal("150.00")

    # Successful withdrawal
    assert manager.withdraw(Decimal("30.00")) is True
    assert manager.available_capital == Decimal("120.00")

    # Overdraft withdrawal rejected
    assert manager.withdraw(Decimal("200.00")) is False
    assert manager.available_capital == Decimal("120.00")

    with pytest.raises(ValueError):
        manager.deposit(Decimal("-10.00"))


# =============================================================================
# 3. Risk Engine Gating & Sizing
# =============================================================================


def test_risk_engine_position_sizing_constraints():
    """Verify position sizing honors 1.5% max risk, available buying power, and 50% concentration."""
    limits = RiskLimitsConfig(
        max_loss_per_trade_pct=Decimal("0.015"),  # 1.5% of 100 = 1.50 INR max risk
        max_position_concentration_pct=Decimal("0.50"),  # 50 INR max notional
    )
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    risk_engine = RiskEngine(capital_manager=manager, config=limits)

    # Stock at 20.00, stop at 19.50 -> Risk per share = 0.50
    # Shares by risk: 1.50 // 0.50 = 3 shares
    # Shares by concentration: 50.00 // 20.00 = 2 shares
    # Shares by capital: 100.00 // 20.00 = 5 shares
    # Approved size should be min(3, 2, 5) = 2 shares
    size = risk_engine.calculate_max_position_size(
        entry_price=Decimal("20.00"),
        stop_price=Decimal("19.50"),
    )
    assert size == 2


def test_risk_engine_circuit_breaker_rejection():
    """Verify that daily loss exceeding 3.0% trips the circuit breaker and rejects candidates."""
    limits = RiskLimitsConfig(max_daily_drawdown_pct=Decimal("0.030"))  # 3.0% limit
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    risk_engine = RiskEngine(capital_manager=manager, config=limits)

    # Incur daily loss of -3.50 (3.5% drawdown)
    manager.realized_pnl = Decimal("-3.50")

    candidate = make_candidate(entry_price="20.00", initial_stop_price="19.50")
    result = risk_engine.evaluate_candidate(candidate)

    assert result.approved is False
    assert result.approval_mode == ApprovalMode.REJECTED
    assert result.is_circuit_breaker_tripped is True
    assert any("circuit breaker active" in r.lower() for r in result.rejection_reasons)


def test_risk_engine_max_active_positions_limit():
    """Verify portfolio enforces maximum 2 active positions."""
    limits = RiskLimitsConfig(max_active_positions=2)
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("200.00")))
    risk_engine = RiskEngine(capital_manager=manager, config=limits)

    pos1 = make_position("pos-1", "INFY")
    pos2 = make_position("pos-2", "WIPRO")

    # When 2 positions are already open, 3rd candidate is rejected
    candidate = make_candidate(
        symbol="TCS", entry_price="20.00", initial_stop_price="19.50"
    )
    result = risk_engine.evaluate_candidate(candidate, current_positions=[pos1, pos2])

    assert result.approved is False
    assert any(
        "active positions limit reached" in r.lower() for r in result.rejection_reasons
    )


def test_risk_engine_duplicate_symbol_rejection():
    """Verify duplicate position in same symbol is rejected."""
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("200.00")))
    risk_engine = RiskEngine(capital_manager=manager)

    pos1 = make_position("pos-1", "TCS")
    candidate = make_candidate(
        symbol="TCS", entry_price="20.00", initial_stop_price="19.50"
    )

    result = risk_engine.evaluate_candidate(candidate, current_positions=[pos1])
    assert result.approved is False
    assert any("already open" in r.lower() for r in result.rejection_reasons)


def test_risk_engine_minimum_economical_trade_size():
    """Verify trades with notional value below minimum threshold (e.g. < ₹10) are rejected."""
    limits = RiskLimitsConfig(min_economical_trade_size=Decimal("15.00"))
    manager = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    risk_engine = RiskEngine(capital_manager=manager, config=limits)

    # 1 share of ₹5 stock (risk 1.00 -> 1 share allowed) = ₹5.00 notional (< ₹15.00)
    penny_candidate = make_candidate(
        symbol="PENNY",
        entry_price="5.00",
        initial_stop_price="4.00",
        target_price="6.00",
    )
    result = risk_engine.evaluate_candidate(penny_candidate)

    assert result.approved is False
    assert any(
        "minimum economical trade size" in r.lower() for r in result.rejection_reasons
    )


def test_risk_engine_autonomy_threshold_policy():
    """Verify autonomous execution up to ₹300, and human approval required above ₹300."""
    limits = RiskLimitsConfig(
        min_economical_trade_size=Decimal("10.00"),
        min_expected_net_edge=Decimal("0.01"),
    )

    # Case A: Micro capital (₹100 equity, ₹20 trade) -> AUTONOMOUS
    manager_a = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    risk_a = RiskEngine(
        capital_manager=manager_a,
        config=limits,
        autonomous_threshold=Decimal("300.00"),
    )
    cand_a = make_candidate(
        entry_price="20.00",
        initial_stop_price="19.50",
        target_price="22.00",
    )
    res_a = risk_a.evaluate_candidate(cand_a)
    assert res_a.approved is True
    assert res_a.approval_mode == ApprovalMode.AUTONOMOUS

    # Case B: Large capital (> ₹300 equity) -> MANUAL_PENDING
    manager_b = CapitalManager(CapitalConfig(starting_capital=Decimal("500.00")))
    risk_b = RiskEngine(
        capital_manager=manager_b,
        config=limits,
        autonomous_threshold=Decimal("300.00"),
    )
    cand_b = make_candidate(
        entry_price="20.00",
        initial_stop_price="19.50",
        target_price="22.00",
    )
    res_b = risk_b.evaluate_candidate(cand_b)
    assert res_b.approved is True
    assert res_b.approval_mode == ApprovalMode.MANUAL_PENDING
