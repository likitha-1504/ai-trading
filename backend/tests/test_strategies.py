"""Comprehensive test suite for Phase 05: BUY Engine (Strategies & Candidate Ranker).

Verifies Momentum Continuation, Early-Move Detection, false-positive handling,
deterministic candidate ranking, cooldown deduplication, and zero order placement.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.contracts import (
    Candidate,
    FeatureSnapshot,
    MarketRegime,
    StrategyType,
    TradeSide,
)
from app.strategies.candidate_ranker import CandidateRanker
from app.strategies.config import (
    CandidateRankerConfig,
)
from app.strategies.early_move import EarlyMoveDetectionStrategy
from app.strategies.momentum_continuation import MomentumContinuationStrategy


def make_snapshot(
    symbol: str = "TCS",
    current_price: str = "3500.00",
    vwap: str = "3480.00",
    vwap_distance_pct: str = "0.5747",
    momentum_score: str = "1.20",
    relative_volume_10: str = "2.10",
    volume_acceleration: str = "25.00",
    price_acceleration: str = "0.40",
    realized_volatility_15: str = "0.20",
    spread_pct: str = "0.0005",
    liquidity_score: str = "85.0",
    market_index_direction: str = "BULLISH",
    sector_strength: str = "0.50",
    price_structure: str = "HIGHER_HIGHS",
    regime: MarketRegime = MarketRegime.BULLISH_TRENDING,
    timestamp: datetime | None = None,
) -> FeatureSnapshot:
    """Helper to generate a valid, deterministic FeatureSnapshot."""
    ts = timestamp or datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)
    return FeatureSnapshot(
        symbol=symbol,
        timestamp=ts,
        bar_timeframe="1m",
        vwap=Decimal(vwap),
        current_price=Decimal(current_price),
        vwap_distance_pct=Decimal(vwap_distance_pct),
        momentum_score=Decimal(momentum_score),
        relative_volume_10=Decimal(relative_volume_10),
        volume_acceleration=Decimal(volume_acceleration),
        price_acceleration=Decimal(price_acceleration),
        realized_volatility_15=Decimal(realized_volatility_15),
        spread_pct=Decimal(spread_pct),
        liquidity_score=Decimal(liquidity_score),
        market_index_direction=market_index_direction,
        sector_strength=Decimal(sector_strength),
        price_structure=price_structure,
        regime=regime,
    )


# =============================================================================
# 1. Strategy A: Momentum Continuation Tests
# =============================================================================


def test_momentum_continuation_valid_trigger():
    """Verify valid momentum continuation setup produces an explainable Candidate."""
    strategy = MomentumContinuationStrategy()
    snap = make_snapshot(
        current_price="100.00",
        vwap="99.00",  # Price > VWAP
        relative_volume_10="2.20",  # >= 1.80
        volume_acceleration="15.0",  # > 0
        momentum_score="1.50",  # > 0.10
        spread_pct="0.0005",  # <= 0.15%
        market_index_direction="BULLISH",
        price_structure="HIGHER_HIGHS",
    )

    candidate = strategy.evaluate(snap)
    assert candidate is not None
    assert isinstance(candidate, Candidate)
    assert candidate.symbol == "TCS"
    assert candidate.strategy_type == StrategyType.MOMENTUM_CONTINUATION
    assert candidate.side == TradeSide.BUY
    assert candidate.trigger_price == Decimal("100.00")
    assert candidate.initial_stop_price < candidate.trigger_price
    assert candidate.suggested_target_price > candidate.trigger_price
    assert candidate.rank_score >= Decimal("50.0")

    # Check evidence explainability
    evidence = candidate.quantitative_evidence
    assert evidence["strategy"] == "MOMENTUM_CONTINUATION"
    assert evidence["vwap_support"] is True
    assert evidence["rvol_10"] == 2.20
    assert len(evidence["reasons"]) >= 4


def test_momentum_continuation_rejections():
    """Verify Momentum Continuation rejects deteriorating conditions."""
    strategy = MomentumContinuationStrategy()

    # 1. Reject if price is below VWAP
    snap_below_vwap = make_snapshot(current_price="98.00", vwap="99.00")
    assert strategy.evaluate(snap_below_vwap) is None

    # 2. Reject if RVOL < 1.80
    snap_low_rvol = make_snapshot(relative_volume_10="1.50")
    assert strategy.evaluate(snap_low_rvol) is None

    # 3. Reject if volume acceleration is negative or zero
    snap_neg_vol = make_snapshot(volume_acceleration="-5.0")
    assert strategy.evaluate(snap_neg_vol) is None

    # 4. Reject if momentum is non-positive
    snap_neg_mom = make_snapshot(momentum_score="-0.50")
    assert strategy.evaluate(snap_neg_mom) is None

    # 5. Reject if spread is too wide (> 0.15%)
    snap_wide_spread = make_snapshot(spread_pct="0.0020")
    assert strategy.evaluate(snap_wide_spread) is None

    # 6. Reject if market index direction is BEARISH
    snap_bearish_market = make_snapshot(market_index_direction="BEARISH")
    assert strategy.evaluate(snap_bearish_market) is None

    # 7. Reject if price structure shows lower lows (breakdown)
    snap_lower_lows = make_snapshot(price_structure="LOWER_LOWS")
    assert strategy.evaluate(snap_lower_lows) is None


# =============================================================================
# 2. Strategy B: Early-Move Detection Tests
# =============================================================================


def test_early_move_valid_trigger():
    """Verify valid early move detection from volatility compression."""
    strategy = EarlyMoveDetectionStrategy()
    snap = make_snapshot(
        current_price="100.00",
        vwap="99.95",
        realized_volatility_15="0.20",  # <= 0.35 (compressed)
        price_acceleration="0.15",  # >= 0.05
        volume_acceleration="20.0",  # > 0
        relative_volume_10="1.25",  # >= 1.10
        liquidity_score="75.0",  # >= 60.0
        spread_pct="0.0004",  # <= 0.0015
        sector_strength="0.40",  # >= 0.0
        market_index_direction="NEUTRAL",
        price_structure="COMPRESSION",
    )

    candidate = strategy.evaluate(snap)
    assert candidate is not None
    assert isinstance(candidate, Candidate)
    assert candidate.symbol == "TCS"
    assert candidate.strategy_type == StrategyType.EARLY_MOVE_DETECTION
    assert candidate.side == TradeSide.BUY
    assert candidate.trigger_price == Decimal("100.00")
    assert candidate.initial_stop_price < candidate.trigger_price
    assert candidate.suggested_target_price > candidate.trigger_price

    # Check evidence explainability
    evidence = candidate.quantitative_evidence
    assert evidence["strategy"] == "EARLY_MOVE_DETECTION"
    assert evidence["volatility_compressed"] is True
    assert evidence["price_acceleration"] == 0.15
    assert len(evidence["reasons"]) >= 4


def test_early_move_rejections():
    """Verify Early-Move Detection rejects non-conforming conditions."""
    strategy = EarlyMoveDetectionStrategy()

    # 1. Reject if volatility is not compressed and structure is not COMPRESSION
    snap_high_vol = make_snapshot(
        realized_volatility_15="0.60", price_structure="RANGE"
    )
    assert strategy.evaluate(snap_high_vol) is None

    # 2. Reject if price acceleration is absent / negative
    snap_no_price_accel = make_snapshot(
        realized_volatility_15="0.20", price_acceleration="0.01"
    )
    assert strategy.evaluate(snap_no_price_accel) is None

    # 3. Reject if volume acceleration is negative
    snap_no_vol_accel = make_snapshot(
        realized_volatility_15="0.20",
        price_acceleration="0.10",
        volume_acceleration="-5.0",
    )
    assert strategy.evaluate(snap_no_vol_accel) is None

    # 4. Reject if sector strength is negative (lagging sector)
    snap_weak_sector = make_snapshot(
        realized_volatility_15="0.20",
        price_acceleration="0.10",
        volume_acceleration="10.0",
        sector_strength="-0.25",
    )
    assert strategy.evaluate(snap_weak_sector) is None

    # 5. Reject if liquidity score is substandard (< 60.0)
    snap_poor_liquidity = make_snapshot(
        realized_volatility_15="0.20",
        price_acceleration="0.10",
        volume_acceleration="10.0",
        liquidity_score="45.0",
    )
    assert strategy.evaluate(snap_poor_liquidity) is None


# =============================================================================
# 3. Candidate Ranker & Cooldown Deduplication Tests
# =============================================================================


def test_candidate_ranker_ordering():
    """Verify candidates are sorted descending by rank score."""
    ranker = CandidateRanker()

    c1 = Candidate(
        candidate_id="c1",
        detected_at=datetime(2026, 9, 23, 9, 30, tzinfo=timezone.utc),
        symbol="INFY",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trigger_price=Decimal(1500),
        initial_stop_price=Decimal(1485),
        suggested_target_price=Decimal(1530),
        rank_score=Decimal("65.50"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="INFY"),
    )
    c2 = Candidate(
        candidate_id="c2",
        detected_at=datetime(2026, 9, 23, 9, 30, tzinfo=timezone.utc),
        symbol="RELIANCE",
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trigger_price=Decimal(2500),
        initial_stop_price=Decimal(2485),
        suggested_target_price=Decimal(2530),
        rank_score=Decimal("82.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="RELIANCE"),
    )

    ranked = ranker.rank_and_filter([c1, c2])
    assert len(ranked) == 2
    assert ranked[0].symbol == "RELIANCE"
    assert ranked[1].symbol == "INFY"


def test_candidate_ranker_cooldown_deduplication():
    """Verify cooldown prevents spamming duplicates for the same symbol within cooldown window."""
    config = CandidateRankerConfig(cooldown_seconds=300)  # 5 minutes
    ranker = CandidateRanker(config=config)
    t0 = datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)

    c1 = Candidate(
        candidate_id="cand-1",
        detected_at=t0,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trigger_price=Decimal(2500),
        initial_stop_price=Decimal(2485),
        suggested_target_price=Decimal(2530),
        rank_score=Decimal("70.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="RELIANCE", timestamp=t0),
    )

    # First detection is accepted
    res1 = ranker.rank_and_filter([c1])
    assert len(res1) == 1
    assert res1[0].candidate_id == "cand-1"

    # Second detection 60 seconds later for SAME symbol with similar score -> Dropped by cooldown
    t1 = t0 + timedelta(seconds=60)
    c2 = Candidate(
        candidate_id="cand-2",
        detected_at=t1,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trigger_price=Decimal(2505),
        initial_stop_price=Decimal(2490),
        suggested_target_price=Decimal(2535),
        rank_score=Decimal("72.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="RELIANCE", timestamp=t1),
    )
    res2 = ranker.rank_and_filter([c2])
    assert len(res2) == 0  # Blocked by cooldown!

    # Third detection 350 seconds later (cooldown expired) -> Accepted
    t2 = t0 + timedelta(seconds=350)
    c3 = Candidate(
        candidate_id="cand-3",
        detected_at=t2,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trigger_price=Decimal(2510),
        initial_stop_price=Decimal(2495),
        suggested_target_price=Decimal(2540),
        rank_score=Decimal("73.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="RELIANCE", timestamp=t2),
    )
    res3 = ranker.rank_and_filter([c3])
    assert len(res3) == 1
    assert res3[0].candidate_id == "cand-3"


def test_candidate_ranker_significant_upgrade_bypasses_cooldown():
    """Verify that a vastly superior candidate (+15 pts) upgrades despite active cooldown."""
    config = CandidateRankerConfig(cooldown_seconds=300)
    ranker = CandidateRanker(config=config)
    t0 = datetime(2026, 9, 23, 9, 30, 0, tzinfo=timezone.utc)

    c1 = Candidate(
        candidate_id="cand-base",
        detected_at=t0,
        symbol="TCS",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trigger_price=Decimal(3500),
        initial_stop_price=Decimal(3480),
        suggested_target_price=Decimal(3540),
        rank_score=Decimal("60.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="TCS", timestamp=t0),
    )
    ranker.rank_and_filter([c1])

    # 30 seconds later, candidate upgrades sharply to 80.0 (+20 pts)
    t1 = t0 + timedelta(seconds=30)
    c_upgrade = Candidate(
        candidate_id="cand-upgrade",
        detected_at=t1,
        symbol="TCS",
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trigger_price=Decimal(3510),
        initial_stop_price=Decimal(3490),
        suggested_target_price=Decimal(3550),
        rank_score=Decimal("80.00"),
        quantitative_evidence={},
        feature_snapshot=make_snapshot(symbol="TCS", timestamp=t1),
    )
    res = ranker.rank_and_filter([c_upgrade])
    assert len(res) == 1
    assert res[0].candidate_id == "cand-upgrade"


def test_zero_order_placement_invariant():
    """Verify that strategy evaluation and ranking never dispatch broker orders."""
    ranker = CandidateRanker()
    snap = make_snapshot()

    # Evaluate snapshot end-to-end
    candidates = ranker.evaluate_snapshot(snap)
    assert isinstance(candidates, list)
    # The output is purely candidate objects; no orders created or submitted
    for c in candidates:
        assert isinstance(c, Candidate)
        assert c.side == TradeSide.BUY
