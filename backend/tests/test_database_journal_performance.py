"""Comprehensive Test Suite for Phase 13: Database, Journal & Performance.

Verifies:
1. SQLite WAL mode, foreign keys, and safe transaction handling (commit/rollback).
2. All 13 core entities:
   - capital_state, positions, orders, trades, candidates, features,
     ai_analyses, trade_plans, risk_events, strategy_versions, model_calls,
     execution_metrics, system_events.
3. Trade Journal and accurate P/L calculations (Gross, Indian friction, Net).
4. Performance aggregation and strategy-level metrics stratification.
5. Model and execution latency metrics tracking.
6. Audit trail reconstruction ensuring decision reproducibility.
7. Restart recovery rehydrating Position Watcher, Capital Manager, and Execution Engine.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.capital.capital_manager import CapitalManager
from app.db.audit import DecisionAuditTrailManager
from app.db.connection import get_connection, init_db
from app.db.journal import DatabaseTradeJournal
from app.db.performance import PerformanceAggregator
from app.db.recovery import RestartRecoveryManager
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import ExecutionEngine
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    CapitalSnapshot,
    ChallengerCritique,
    ChallengerRecommendation,
    ChallengerSeverity,
    ExecutionMetricsSnapshot,
    FeatureSnapshot,
    FrictionBreakdown,
    MarketRegime,
    MarketThesis,
    MarketThesisAction,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    RiskLimits,
    StopProtection,
    StrategyType,
    TradePlan,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)
from app.watcher.position_watcher import IndependentPositionWatcher


@pytest.fixture
def temp_db():
    """Create and initialize a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def make_feature_snapshot(symbol: str = "TCS", ts: datetime | None = None) -> FeatureSnapshot:
    """Helper to generate a valid FeatureSnapshot for tests."""
    return FeatureSnapshot(
        symbol=symbol,
        timestamp=ts or datetime.now(timezone.utc),
        bar_timeframe="1m",
        vwap=Decimal("3490.00"),
        current_price=Decimal("3500.00"),
        vwap_distance_pct=Decimal("0.0028"),
        momentum_score=Decimal("2.3"),
        relative_volume_10=Decimal("2.4"),
        volume_acceleration=Decimal("1.2"),
        price_acceleration=Decimal("0.6"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.0008"),
        liquidity_score=Decimal("88.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.8"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )


# =====================================================================
# 1. SQLite Engine, WAL Mode & Safe Transactions Tests
# =====================================================================


def test_sqlite_wal_mode_and_pragma_settings(temp_db):
    """Verify WAL mode, foreign keys, and busy timeout are configured."""
    with get_connection(temp_db) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

    assert journal_mode.lower() in ("wal", "memory")
    assert foreign_keys == 1
    assert busy_timeout >= 5000


def test_transaction_rollback_on_exception(temp_db):
    """Verify safe transaction context manager rolls back on unhandled error."""
    repo = DatabaseRepository(db_path=temp_db)
    cand = Candidate(
        candidate_id="cand-rollback-01",
        detected_at=datetime.now(timezone.utc),
        symbol="INFY",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("1500.00"),
        initial_stop_price=Decimal("1480.00"),
        suggested_target_price=Decimal("1540.00"),
        rank_score=Decimal("85.0"),
        quantitative_evidence={"rvol": "2.1"},
        feature_snapshot=make_feature_snapshot("INFY"),
    )
    repo.save_candidate(cand)

    # Trigger rollback
    with pytest.raises(RuntimeError), get_connection(temp_db) as conn:
        conn.execute(
            "UPDATE candidates SET symbol = 'CORRUPTED' WHERE id = 'cand-rollback-01'"
        )
        raise RuntimeError("Forced simulation error")

    # Verify rollback preserved original state
    retrieved = repo.get_candidate("cand-rollback-01")
    assert retrieved is not None
    assert retrieved.symbol == "INFY"


# =====================================================================
# 2. All 13 Core Entities CRUD Tests
# =====================================================================


def test_all_13_core_entities_persisted_and_queried(temp_db):
    """Verify full CRUD functionality across all 13 core entities required by PDF."""
    repo = DatabaseRepository(db_path=temp_db)
    now = datetime.now(timezone.utc)

    # 1. capital_state
    cap_snap = CapitalSnapshot(
        timestamp=now,
        total_capital=Decimal("100.00"),
        available_capital=Decimal("80.00"),
        deployed_capital=Decimal("20.00"),
        buying_power=Decimal("80.00"),
        realized_pnl=Decimal("5.00"),
        unrealized_pnl=Decimal("1.50"),
        daily_drawdown_amount=Decimal("0.50"),
        daily_drawdown_pct=Decimal("0.005"),
        high_water_mark=Decimal("105.00"),
    )
    cap_id = repo.save_capital_state(
        cap_snap, daily_drawdown=Decimal("0.50"), high_water_mark=Decimal("105.00")
    )
    assert cap_id > 0
    latest_cap = repo.get_latest_capital_state()
    assert latest_cap is not None
    assert latest_cap["total_capital"] == 100.0

    # 2. candidates
    cand = Candidate(
        candidate_id="cand-entity-001",
        detected_at=now,
        symbol="TCS",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("3500.00"),
        initial_stop_price=Decimal("3470.00"),
        suggested_target_price=Decimal("3560.00"),
        rank_score=Decimal("92.5"),
        quantitative_evidence={"rvol": "2.4"},
        feature_snapshot=make_feature_snapshot("TCS", now),
    )
    repo.save_candidate(cand, status="DETECTED")
    ret_cand = repo.get_candidate("cand-entity-001")
    assert ret_cand is not None
    assert ret_cand.symbol == "TCS"

    # 3. features
    fs = FeatureSnapshot(
        symbol="TCS",
        timestamp=now,
        bar_timeframe="1m",
        vwap=Decimal("3490.00"),
        current_price=Decimal("3500.00"),
        vwap_distance_pct=Decimal("0.0028"),
        momentum_score=Decimal("2.3"),
        relative_volume_10=Decimal("2.4"),
        volume_acceleration=Decimal("1.2"),
        price_acceleration=Decimal("0.6"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.0008"),
        liquidity_score=Decimal("88.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.8"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    f_id = repo.save_feature_snapshot(fs)
    assert f_id > 0
    ret_fs = repo.get_latest_feature("TCS")
    assert ret_fs is not None
    assert ret_fs.vwap == Decimal("3490.00")

    # 4. ai_analyses (Qwen3 & DeepSeek-R1)
    thesis = MarketThesis(
        candidate_id="cand-entity-001",
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-v1",
        thesis_summary="Bullish continuation",
        catalyst_identified="Earnings",
        bullish_evidence=["High RVOL"],
        invalidation_conditions=["Below 3470"],
        perceived_risks=["None"],
        confidence_score=Decimal("0.85"),
        context_summary="Strong sector",
        suggested_action=MarketThesisAction.PROCEED,
        latency_ms=120,
    )
    critique = ChallengerCritique(
        candidate_id="cand-entity-001",
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="r1-v1",
        critique_summary="Stress test passed",
        identified_vulnerabilities=["Overhead resistance"],
        contradictory_signals=[],
        invalidation_conditions=["Below 3470"],
        worst_case_scenario="Stop out",
        downside_severity=ChallengerSeverity.LOW,
        recommendation_flag=ChallengerRecommendation.CONFIRM,
        latency_ms=150,
    )
    repo.save_ai_analysis("cand-entity-001", thesis)
    repo.save_ai_analysis("cand-entity-001", critique)
    analyses = repo.get_ai_analyses_for_candidate("cand-entity-001")
    assert len(analyses) == 2

    # 5. trade_plans
    plan = TradePlan(
        plan_id="plan-entity-001",
        candidate_id="cand-entity-001",
        created_at=now,
        instrument="TCS",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price_target=Decimal("3500.00"),
        entry_context={"trigger": "3500.00"},
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        expected_edge=Decimal("4.50"),
        expected_gross_edge=Decimal("5.00"),
        expected_net_edge=Decimal("4.50"),
        estimated_costs=FrictionBreakdown(
            brokerage=Decimal("0.10"),
            stt=Decimal("0.10"),
            exchange_charges=Decimal("0.02"),
            sebi_charges=Decimal("0.001"),
            stamp_duty=Decimal("0.02"),
            gst=Decimal("0.02"),
            expected_slippage=Decimal("0.05"),
            total_friction=Decimal("0.50"),
        ),
        risk_limits=RiskLimits(
            max_loss_amount=Decimal("30.00"),
            max_capital_allocation=Decimal("3500.00"),
        ),
        stop_protection=StopProtection(
            hard_stop_price=Decimal("3470.00"),
            take_profit_price=Decimal("3560.00"),
        ),
        invalidation=["Below 3470"],
        decision_reason="Valid setup",
        approval_mode=ApprovalMode.AUTONOMOUS,
    )
    repo.save_trade_plan(plan)
    ret_plan = repo.get_trade_plan("plan-entity-001")
    assert ret_plan is not None
    assert ret_plan.instrument == "TCS"
    assert ret_plan.quantity == 1

    # 6. orders
    order_req = OrderRequest(
        client_order_id="order-entity-001",
        plan_id="plan-entity-001",
        symbol="TCS",
        side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        price=Decimal("3500.00"),
        stop_price=Decimal("3470.00"),
    )
    repo.save_order(order_req, status=OrderStatus.SUBMITTED, position_id="pos-001")
    repo.update_order_status(
        client_order_id="order-entity-001",
        status=OrderStatus.FILLED,
        filled_quantity=1,
        average_fill_price=Decimal("3500.05"),
        position_id="pos-001",
    )
    ret_order = repo.get_order("order-entity-001")
    assert ret_order is not None
    assert ret_order["status"] == "FILLED"

    # 7. positions
    pos = PositionSnapshot(
        position_id="pos-001",
        plan_id="plan-entity-001",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("3500.05"),
        current_price=Decimal("3520.00"),
        hard_stop_price=Decimal("3470.00"),
        unrealized_pnl=Decimal("19.95"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )
    repo.save_position(pos)
    ret_pos = repo.get_position("pos-001")
    assert ret_pos is not None
    assert ret_pos.status == PositionStatus.OPEN

    # 8. trades
    trade_rec = TradeRecord(
        trade_id="trd-001",
        plan_id="plan-entity-001",
        symbol="TCS",
        side=TradeSide.BUY,
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        quantity=1,
        entry_timestamp=now,
        entry_price=Decimal("3500.05"),
        entry_slippage=Decimal("0.05"),
        exit_timestamp=now,
        exit_price=Decimal("3530.00"),
        exit_slippage=Decimal("0.05"),
        exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
        gross_pnl=Decimal("29.95"),
        friction=plan.estimated_costs,
        net_pnl=Decimal("29.45"),
        holding_duration_seconds=120.0,
        market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
        market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
    )
    repo.save_trade(trade_rec)
    ret_trade = repo.get_trade("trd-001")
    assert ret_trade is not None
    assert ret_trade.net_pnl == Decimal("29.45")

    # 9. risk_events
    re_id = repo.save_risk_event(
        event_type="CIRCUIT_BREAKER_CHECK",
        severity="INFO",
        details={"drawdown_pct": 0.005},
        symbol="TCS",
    )
    assert re_id > 0
    assert len(repo.get_recent_risk_events()) >= 1

    # 10. strategy_versions
    sv_id = repo.save_strategy_version(
        strategy_name="MOMENTUM_CONTINUATION",
        version="v1.0.0",
        parameters={"rvol_threshold": 1.8},
        is_active=True,
    )
    assert sv_id == "MOMENTUM_CONTINUATION-v1.0.0"
    active_sv = repo.get_active_strategy_version("MOMENTUM_CONTINUATION")
    assert active_sv is not None
    assert json.loads(active_sv["parameters"])["rvol_threshold"] == 1.8

    # 11. model_calls
    mc_id = repo.save_model_call(
        model_name="qwen3:latest",
        role="ANALYST",
        prompt_version="qwen3-v1",
        latency_ms=115,
        success=True,
        token_count=180,
    )
    assert mc_id > 0

    # 12. execution_metrics
    em_snap = ExecutionMetricsSnapshot(
        total_orders_submitted=10,
        total_orders_acknowledged=10,
        total_orders_filled=9,
        total_orders_partially_filled=0,
        total_orders_cancelled=0,
        total_orders_rejected=1,
        total_quantity_ordered=10,
        total_quantity_filled=9,
        total_slippage_incurred=Decimal("0.45"),
        avg_submission_latency_ms=12.5,
        avg_ack_latency_ms=25.0,
        avg_fill_latency_ms=35.0,
    )
    em_id = repo.save_execution_metrics(em_snap)
    assert em_id > 0

    # 13. system_events
    se_id = repo.save_system_event(
        source="TRADE_GATE",
        level="INFO",
        message="System fully operational",
        metadata={"mode": "PAPER"},
    )
    assert se_id > 0
    assert len(repo.get_recent_system_events()) >= 1


# =====================================================================
# 3. Trade Journal & P/L Calculation Tests
# =====================================================================


def test_database_trade_journal_entry_exit_and_pnl(temp_db):
    """Verify Trade Journal calculates Gross P/L, friction, Net P/L and persists."""
    journal = DatabaseTradeJournal(db_path=temp_db)
    t0 = datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 24, 9, 35, tzinfo=timezone.utc)

    # 1. Record Entry
    trade_id = journal.record_entry(
        plan_id="plan-pnl-01",
        symbol="RELIANCE",
        side=TradeSide.BUY,
        strategy=StrategyType.EARLY_MOVE_DETECTION,
        quantity=2,
        entry_timestamp=t0,
        entry_price=Decimal("2500.00"),
        entry_slippage=Decimal("0.05"),
    )
    assert trade_id.startswith("trd-")

    # 2. Record Exit with profit
    friction = FrictionBreakdown(
        brokerage=Decimal("0.50"),
        stt=Decimal("0.60"),
        exchange_charges=Decimal("0.10"),
        sebi_charges=Decimal("0.01"),
        stamp_duty=Decimal("0.08"),
        gst=Decimal("0.11"),
        expected_slippage=Decimal("0.10"),
        total_friction=Decimal("1.50"),
    )
    record = journal.record_exit(
        trade_id=trade_id,
        exit_price=Decimal("2520.00"),  # +20 INR per share * 2 = 40 INR gross
        exit_timestamp=t1,
        friction=friction,
        exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
    )

    assert record.gross_pnl == Decimal("40.00")
    assert record.net_pnl == Decimal("38.50")  # 40 - 1.50 friction
    assert record.holding_duration_seconds == 300.0

    # Verify query from database matches
    saved_record = journal.get_trade(trade_id)
    assert saved_record is not None
    assert saved_record.net_pnl == Decimal("38.50")
    assert saved_record.strategy == StrategyType.EARLY_MOVE_DETECTION


# =====================================================================
# 4. Performance Aggregator & Strategy Stratification Tests
# =====================================================================


def test_performance_aggregation_and_strategy_metrics(temp_db):
    """Verify performance metrics, win rate, profit factor, and strategy stratification."""
    journal = DatabaseTradeJournal(db_path=temp_db)
    aggregator = PerformanceAggregator(db_path=temp_db)
    t0 = datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc)

    friction = FrictionBreakdown(
        brokerage=Decimal("0.10"),
        stt=Decimal("0.10"),
        exchange_charges=Decimal("0.02"),
        sebi_charges=Decimal("0.001"),
        stamp_duty=Decimal("0.02"),
        gst=Decimal("0.02"),
        expected_slippage=Decimal("0.05"),
        total_friction=Decimal("0.50"),
    )

    # Trade 1: Momentum Win (+50 gross, -0.50 friction = +49.50 net)
    t1_id = journal.record_entry("p1", "TCS", TradeSide.BUY, StrategyType.MOMENTUM_CONTINUATION, 1, t0, Decimal(3500))
    journal.record_exit(t1_id, Decimal(3550), t0, friction)

    # Trade 2: Momentum Loss (-20 gross, -0.50 friction = -20.50 net)
    t2_id = journal.record_entry("p2", "TCS", TradeSide.BUY, StrategyType.MOMENTUM_CONTINUATION, 1, t0, Decimal(3500))
    journal.record_exit(t2_id, Decimal(3480), t0, friction)

    # Trade 3: Early Move Win (+30 gross, -0.50 friction = +29.50 net)
    t3_id = journal.record_entry("p3", "INFY", TradeSide.BUY, StrategyType.EARLY_MOVE_DETECTION, 1, t0, Decimal(1500))
    journal.record_exit(t3_id, Decimal(1530), t0, friction)

    metrics = aggregator.calculate_metrics()
    assert metrics.total_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert metrics.win_rate_pct == 66.67
    assert metrics.total_gross_pnl == Decimal("60.00")  # 50 - 20 + 30
    assert metrics.total_friction == Decimal("1.50")
    assert metrics.total_net_pnl == Decimal("58.50")
    assert metrics.profit_factor > 1.0

    # Strategy-level stratification
    strat_metrics = aggregator.calculate_strategy_metrics()
    mom = strat_metrics[StrategyType.MOMENTUM_CONTINUATION.value]
    early = strat_metrics[StrategyType.EARLY_MOVE_DETECTION.value]

    assert mom["total_trades"] == 2
    assert mom["win_rate_pct"] == 50.0
    assert mom["net_pnl"] == "29.00"  # 49.50 - 20.50

    assert early["total_trades"] == 1
    assert early["win_rate_pct"] == 100.0
    assert early["net_pnl"] == "29.50"


def test_model_latency_metrics_aggregation(temp_db):
    """Verify model latency, tokens, and fallback aggregation."""
    repo = DatabaseRepository(db_path=temp_db)
    aggregator = PerformanceAggregator(db_path=temp_db)

    # Qwen3 calls (100ms, 120ms, 140ms)
    repo.save_model_call("qwen3:latest", "ANALYST", "v1", 100, True, 150)
    repo.save_model_call("qwen3:latest", "ANALYST", "v1", 120, True, 160)
    repo.save_model_call("qwen3:latest", "ANALYST", "v1", 140, False, 0, is_fallback=True)

    # DeepSeek-R1 calls (200ms, 250ms)
    repo.save_model_call("deepseek-r1:latest", "CHALLENGER", "v1", 200, True, 200)
    repo.save_model_call("deepseek-r1:latest", "CHALLENGER", "v1", 250, True, 220)

    model_stats = aggregator.get_model_latency_metrics()
    assert "qwen3:latest" in model_stats
    assert "deepseek-r1:latest" in model_stats

    qwen = model_stats["qwen3:latest"]
    assert qwen["total_calls"] == 3
    assert qwen["successful_calls"] == 2
    assert qwen["fallback_calls"] == 1
    assert qwen["avg_latency_ms"] == 120.0


# =====================================================================
# 5. Decision Audit Trail & Reproducibility Tests
# =====================================================================


def test_decision_trail_reconstruction_and_reproducibility(temp_db):
    """Verify entire decision pipeline is reconstructed from stored database records."""
    repo = DatabaseRepository(db_path=temp_db)
    trail_mgr = DecisionAuditTrailManager(repository=repo, db_path=temp_db)
    now = datetime.now(timezone.utc)

    # 1. Candidate
    cand = Candidate(
        candidate_id="cand-trail-001",
        detected_at=now,
        symbol="TCS",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("3500.00"),
        initial_stop_price=Decimal("3470.00"),
        suggested_target_price=Decimal("3560.00"),
        rank_score=Decimal("90.0"),
        quantitative_evidence={"rvol": "2.5"},
        feature_snapshot=make_feature_snapshot("TCS", now),
    )
    repo.save_candidate(cand)

    # 2. Features
    fs = FeatureSnapshot(
        symbol="TCS",
        timestamp=now,
        bar_timeframe="1m",
        vwap=Decimal("3485.00"),
        current_price=Decimal("3500.00"),
        vwap_distance_pct=Decimal("0.0043"),
        momentum_score=Decimal("2.1"),
        relative_volume_10=Decimal("2.5"),
        volume_acceleration=Decimal("1.1"),
        price_acceleration=Decimal("0.5"),
        realized_volatility_15=Decimal("0.012"),
        spread_pct=Decimal("0.0008"),
        liquidity_score=Decimal("92.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.8"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    repo.save_feature_snapshot(fs)

    # 3. AI Analyses
    thesis = MarketThesis(
        candidate_id="cand-trail-001",
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-v1",
        thesis_summary="Trend continuation",
        catalyst_identified="IT Rally",
        bullish_evidence=["Volume support"],
        invalidation_conditions=["Break below 3470"],
        perceived_risks=["None"],
        confidence_score=Decimal("0.88"),
        context_summary="Bullish",
        suggested_action=MarketThesisAction.PROCEED,
        latency_ms=105,
    )
    critique = ChallengerCritique(
        candidate_id="cand-trail-001",
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="r1-v1",
        critique_summary="Stress-testing confirms momentum",
        identified_vulnerabilities=[],
        contradictory_signals=[],
        invalidation_conditions=["Break below 3470"],
        worst_case_scenario="Stop triggered",
        downside_severity=ChallengerSeverity.LOW,
        recommendation_flag=ChallengerRecommendation.CONFIRM,
        latency_ms=130,
    )
    repo.save_ai_analysis("cand-trail-001", thesis)
    repo.save_ai_analysis("cand-trail-001", critique)

    # 4. TradePlan
    plan = TradePlan(
        plan_id="plan-trail-001",
        candidate_id="cand-trail-001",
        created_at=now,
        instrument="TCS",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price_target=Decimal("3500.00"),
        entry_context={"trigger": "3500.00"},
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        expected_edge=Decimal("4.50"),
        expected_gross_edge=Decimal("5.00"),
        expected_net_edge=Decimal("4.50"),
        estimated_costs=FrictionBreakdown(
            brokerage=Decimal("0.10"),
            stt=Decimal("0.10"),
            exchange_charges=Decimal("0.02"),
            sebi_charges=Decimal("0.001"),
            stamp_duty=Decimal("0.02"),
            gst=Decimal("0.02"),
            expected_slippage=Decimal("0.05"),
            total_friction=Decimal("0.50"),
        ),
        risk_limits=RiskLimits(
            max_loss_amount=Decimal("30.00"),
            max_capital_allocation=Decimal("3500.00"),
        ),
        stop_protection=StopProtection(
            hard_stop_price=Decimal("3470.00"),
            take_profit_price=Decimal("3560.00"),
        ),
        invalidation=["Break below 3470"],
        decision_reason="Autonomous clearance",
        approval_mode=ApprovalMode.AUTONOMOUS,
    )
    repo.save_trade_plan(plan)

    # 5. Order
    order_req = OrderRequest(
        client_order_id="order-trail-001",
        plan_id="plan-trail-001",
        symbol="TCS",
        side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        price=Decimal("3500.00"),
        stop_price=Decimal("3470.00"),
    )
    repo.save_order(order_req, status=OrderStatus.FILLED, position_id="pos-trail-001")

    # 6. Position
    pos = PositionSnapshot(
        position_id="pos-trail-001",
        plan_id="plan-trail-001",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("3500.00"),
        current_price=Decimal("3520.00"),
        hard_stop_price=Decimal("3470.00"),
        unrealized_pnl=Decimal("20.00"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )
    repo.save_position(pos)

    # Reconstruct audit trail from candidate_id
    trail = trail_mgr.reconstruct_trail(candidate_id="cand-trail-001")
    assert trail.is_fully_reproducible is True
    assert trail.candidate is not None
    assert trail.candidate.symbol == "TCS"
    assert trail.trade_plan is not None
    assert trail.trade_plan.plan_id == "plan-trail-001"
    assert len(trail.ai_analyses) == 2
    assert len(trail.orders) == 1
    assert len(trail.positions) == 1
    assert trail.positions[0].position_id == "pos-trail-001"


# =====================================================================
# 6. Restart Recovery Tests
# =====================================================================


def test_restart_recovery_rehydrates_watcher_capital_and_execution(temp_db):
    """Verify system recovery from SQLite restores live controllers after restart/crash."""
    repo = DatabaseRepository(db_path=temp_db)
    recovery_mgr = RestartRecoveryManager(repository=repo, db_path=temp_db)
    now = datetime.now(timezone.utc)

    # 1. Store Capital State (Equity=150, Available=120, HWM=160, Drawdown=5)
    cap_snap = CapitalSnapshot(
        timestamp=now,
        total_capital=Decimal("150.00"),
        available_capital=Decimal("120.00"),
        deployed_capital=Decimal("30.00"),
        buying_power=Decimal("120.00"),
        realized_pnl=Decimal("10.00"),
        unrealized_pnl=Decimal("2.00"),
        daily_drawdown_amount=Decimal("5.00"),
        daily_drawdown_pct=Decimal("0.033"),
        high_water_mark=Decimal("160.00"),
    )
    repo.save_capital_state(cap_snap, daily_drawdown=Decimal("5.00"), high_water_mark=Decimal("160.00"))

    # 2. Store Open Position
    pos = PositionSnapshot(
        position_id="pos-recovered-001",
        plan_id="plan-rec-001",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("3500.00"),
        current_price=Decimal("3510.00"),
        hard_stop_price=Decimal("3470.00"),
        unrealized_pnl=Decimal("10.00"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )
    repo.save_position(pos)

    # 3. Store Active Order in SUBMITTED state
    order_req = OrderRequest(
        client_order_id="order-rec-001",
        plan_id="plan-rec-001",
        symbol="TCS",
        side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        price=Decimal("3500.00"),
        stop_price=Decimal("3470.00"),
    )
    repo.save_order(order_req, status=OrderStatus.SUBMITTED, position_id="pos-recovered-001")

    # In-memory fresh controllers
    watcher = IndependentPositionWatcher()
    cap_mgr = CapitalManager()
    exec_engine = ExecutionEngine()

    assert len(watcher.get_all_open_positions()) == 0
    assert "order-rec-001" not in exec_engine._order_requests

    # Perform crash recovery
    state = recovery_mgr.recover_system_state(
        position_watcher=watcher,
        capital_manager=cap_mgr,
        execution_engine=exec_engine,
    )

    # Verify state report
    assert state.status == "SUCCESS"
    assert len(state.recovered_positions) == 1
    assert len(state.recovered_orders) == 1
    assert state.latest_equity == Decimal("150.00")
    assert state.high_water_mark == Decimal("160.00")

    # Verify PositionWatcher restored the position
    open_positions = watcher.get_all_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0].position_id == "pos-recovered-001"
    assert open_positions[0].hard_stop_price == Decimal("3470.00")

    # Verify CapitalManager restored balances
    assert cap_mgr.available_capital == Decimal("120.00")
    assert cap_mgr.high_water_mark == Decimal("160.00")

    # Verify ExecutionEngine restored active order
    assert "order-rec-001" in exec_engine._order_requests
    assert exec_engine._order_requests["order-rec-001"].symbol == "TCS"
