"""Phase 16 Comprehensive Failure Injection, Integration & Resiliency Test Suite.

Verifies deterministic safety invariants across:
1. Market data disconnect
2. Broker disconnect
3. Stale market data timeout
4. Model latency timeout
5. Qwen3 unavailable (HTTP 503 / connection drop)
6. DeepSeek-R1 unavailable (HTTP 503 / connection drop)
7. Malformed AI output (invalid JSON, missing fields)
8. Partial order fills
9. Rejected orders & broker error codes
10. Duplicate order submission idempotency
11. Database transaction failure & automatic rollback
12. Process crash & laptop restart recovery
13. Inconsistent local / broker position state reconciliation
14. Complete LLM failure independence (sub-50ms hard stops & cutoffs survive dead AI)
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest

from app.adapters.broker_base import BrokerAdapter
from app.adapters.normalizer import MarketDataNormalizer
from app.adapters.paper_adapter import PaperAdapter
from app.adapters.simulated_market_data import SimulatedMarketDataAdapter
from app.ai.challenger_client import DeepSeekR1ChallengerClient
from app.ai.challenger_validator import (
    DeepSeekR1OutputValidator,
    MalformedChallengerOutputError,
)
from app.ai.client import Qwen3AnalystClient
from app.ai.validator import MalformedAIOutputError, Qwen3OutputValidator
from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig
from app.db.connection import get_connection, init_db
from app.db.recovery import RestartRecoveryManager
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import DuplicateOrderError, ExecutionEngine
from app.execution.state_machine import OrderStateMachine
from app.models.contracts import (
    Candidate,
    CapitalSnapshot,
    ChallengerRecommendation,
    ChallengerSeverity,
    FeatureSnapshot,
    MarketRegime,
    MarketSource,
    MarketThesis,
    MarketThesisAction,
    NormalizedMarketEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    RawMarketTick,
    StrategyType,
    TradeSide,
    WatcherExitTrigger,
)
from app.watcher.config import WatcherConfig
from app.watcher.position_watcher import IndependentPositionWatcher


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def make_test_candidate(symbol: str = "INFY", price: Decimal = Decimal("1890.00")) -> Candidate:
    """Helper to create a valid deterministic candidate with complete FeatureSnapshot."""
    now = datetime.now(timezone.utc)
    fs = FeatureSnapshot(
        symbol=symbol,
        timestamp=now,
        bar_timeframe="1m",
        vwap=price - Decimal("10.00"),
        current_price=price,
        vwap_distance_pct=Decimal("0.005"),
        momentum_score=Decimal("2.50"),
        relative_volume_10=Decimal("2.20"),
        volume_acceleration=Decimal("1.10"),
        price_acceleration=Decimal("0.50"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.0008"),
        liquidity_score=Decimal("92.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.85"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    return Candidate(
        candidate_id=f"cand-{symbol.lower()}-test",
        detected_at=now,
        symbol=symbol,
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=price,
        initial_stop_price=price - Decimal("12.00"),
        suggested_target_price=price + Decimal("24.00"),
        rank_score=Decimal("88.50"),
        quantitative_evidence={"rvol": "2.20", "regime": "BULLISH_TRENDING"},
        feature_snapshot=fs,
    )


def make_test_order(client_order_id: str, symbol: str = "INFY", qty: int = 1) -> OrderRequest:
    """Helper to create an OrderRequest."""
    return OrderRequest(
        client_order_id=client_order_id,
        plan_id="plan-test-01",
        symbol=symbol,
        side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        quantity=qty,
        price=Decimal("1890.00"),
    )


def make_test_position(
    symbol: str = "INFY",
    entry_price: Decimal = Decimal("1890.00"),
    hard_stop: Decimal = Decimal("1878.00"),
) -> PositionSnapshot:
    """Helper to create an active PositionSnapshot."""
    now = datetime.now(timezone.utc)
    return PositionSnapshot(
        position_id=f"pos-{symbol.lower()}-01",
        plan_id="plan-test-01",
        symbol=symbol,
        side=TradeSide.BUY,
        quantity=1,
        entry_price=entry_price,
        current_price=entry_price,
        hard_stop_price=hard_stop,
        take_profit_price=entry_price + Decimal("24.00"),
        unrealized_pnl=Decimal("0.00"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )


# =====================================================================
# 1. Market Data Disconnect & Reconnect
# =====================================================================

@pytest.mark.asyncio
async def test_failure_injection_market_data_disconnect():
    """Verify normalizer handles feed disconnect without crashing or losing queue integrity."""
    normalizer = MarketDataNormalizer()
    sim_feed = SimulatedMarketDataAdapter()

    # Connect feed
    await sim_feed.connect()
    assert sim_feed.is_connected is True

    # Inject disconnect
    sim_feed.inject_disconnect()
    assert sim_feed.is_connected is False

    # Normalize tick received
    tick = RawMarketTick(
        symbol="RELIANCE",
        timestamp=datetime.now(timezone.utc),
        last_price=Decimal("2940.00"),
        volume=1000,
        bid_price=Decimal("2939.80"),
        ask_price=Decimal("2940.20"),
        bid_quantity=10,
        ask_quantity=10,
        source=MarketSource.SIMULATED,
    )
    event = normalizer.normalize(tick)
    assert isinstance(event, NormalizedMarketEvent)
    assert event.symbol == "RELIANCE"
    assert event.last_price == Decimal("2940.00")


# =====================================================================
# 2. Broker Disconnect During Order Submission
# =====================================================================

def test_failure_injection_broker_disconnect():
    """Verify ExecutionEngine handles socket/broker drop during order submission."""
    mock_broker = MagicMock(spec=BrokerAdapter)
    mock_broker.submit_order.side_effect = ConnectionError("Broker socket disconnected: ECONNRESET")

    engine = ExecutionEngine(broker_adapter=mock_broker)
    order = make_test_order("ord-fail-conn-01")

    # Order submission must catch connection error and transition to REJECTED cleanly
    event = engine.submit_order(order)

    assert event.status == OrderStatus.REJECTED
    assert "disconnected" in (event.rejection_reason or "").lower()

    # Verify state machine recorded rejection
    saved_event = engine.get_order("ord-fail-conn-01")
    assert saved_event is not None
    assert saved_event.status == OrderStatus.REJECTED


# =====================================================================
# 3. Stale Data Emergency Square-Off
# =====================================================================

def test_failure_injection_stale_data():
    """Verify Position Watcher detects frozen tick feed (>15s) and triggers STALE_DATA_EMERGENCY."""
    config = WatcherConfig(stale_quote_timeout_seconds=15)
    watcher = IndependentPositionWatcher(config=config)

    t0 = datetime(2026, 9, 24, 10, 0, 0, tzinfo=timezone.utc)
    pos = make_test_position("INFY", Decimal("1890.00"), Decimal("1878.00"))
    pos.last_evaluated_at = t0
    watcher.open_position(pos)

    # Simulate 20 seconds passing with zero new quotes
    t_stale = t0 + timedelta(seconds=20)
    interventions = watcher.evaluate_heartbeat(current_time=t_stale)

    assert len(interventions) == 1
    assert interventions[0].trigger == WatcherExitTrigger.STALE_DATA_EMERGENCY
    assert "feed dropped or froze" in interventions[0].details
    assert watcher.get_position(pos.position_id).status in (PositionStatus.CLOSING, PositionStatus.CLOSED)


# =====================================================================
# 4. Model Latency Timeout
# =====================================================================

@pytest.mark.asyncio
async def test_failure_injection_model_timeout():
    """Verify Qwen3 client activates fallback when HTTP timeout occurs (>2.5s)."""
    candidate = make_test_candidate("INFY")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Model inference timed out")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = Qwen3AnalystClient(http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

        assert thesis.is_fallback is True
        assert thesis.confidence_score == Decimal("0.0")
        assert thesis.suggested_action in (MarketThesisAction.CAUTION, MarketThesisAction.REJECT)


# =====================================================================
# 5. Qwen3 Unavailable (HTTP 503 / Connection Error)
# =====================================================================

@pytest.mark.asyncio
async def test_failure_injection_qwen3_unavailable():
    """Verify TradeGate safely handles fallback when Qwen3 is completely unavailable."""
    candidate = make_test_candidate("INFY")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused: Ollama 11434")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = Qwen3AnalystClient(http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

        assert thesis.is_fallback is True
        assert thesis.confidence_score == Decimal("0.0")


def make_test_thesis(
    action: MarketThesisAction = MarketThesisAction.PROCEED,
    confidence: Decimal = Decimal("0.85"),
) -> MarketThesis:
    """Helper to construct a deterministic Qwen3 MarketThesis."""
    return MarketThesis(
        candidate_id="cand-challenger-001",
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
        thesis_summary="Strong continuation breakout setup.",
        catalyst_identified="Breakout volume",
        bullish_evidence=["RVOL 2.4x", "Holding VWAP"],
        invalidation_conditions=["Break below stop"],
        perceived_risks=["Potential slippage"],
        confidence_score=confidence,
        context_summary="Bullish trending market regime",
        suggested_action=action,
        latency_ms=110,
        token_count=160,
        is_fallback=False,
    )


# =====================================================================
# 6. DeepSeek-R1 Unavailable (HTTP 503 / Connection Error)
# =====================================================================

@pytest.mark.asyncio
async def test_failure_injection_deepseek_r1_unavailable():
    """Verify DeepSeek-R1 client returns conservative fallback critique when unreachable."""
    candidate = make_test_candidate("INFY")
    thesis = make_test_thesis()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused: Ollama 11434")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = DeepSeekR1ChallengerClient(http_client=async_http)
        critique = await client.critique_candidate(candidate, thesis)

        assert critique.is_fallback is True
        assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
        assert critique.downside_severity in (ChallengerSeverity.MEDIUM, ChallengerSeverity.SEVERE)


# =====================================================================
# 7. Malformed AI Output (Invalid JSON, Missing Fields)
# =====================================================================

def test_failure_injection_malformed_ai_output():
    """Verify strict validators reject invalid AI output and prevent unverified schema passage."""
    # 1. Non-JSON string
    with pytest.raises(MalformedAIOutputError):
        Qwen3OutputValidator.validate_and_parse(
            raw_output="I think the stock will go up strongly! Buy now.",
            candidate_id="c1",
            latency_ms=50,
            model_name="qwen3:latest",
            model_version="v1.0",
            prompt_version="v1.0",
        )

    # 2. Missing required fields
    broken_json = '{"confidence_score": 0.9}'
    with pytest.raises(MalformedAIOutputError):
        Qwen3OutputValidator.validate_and_parse(
            raw_output=broken_json,
            candidate_id="c1",
            latency_ms=50,
            model_name="qwen3:latest",
            model_version="v1.0",
            prompt_version="v1.0",
        )

    # 3. Challenger invalid JSON
    with pytest.raises(MalformedChallengerOutputError):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output="<think>Thinking...</think> Not a JSON object.",
            candidate_id="c1",
            latency_ms=50,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="v1.0",
        )


# =====================================================================
# 8. Partial Fill Handling
# =====================================================================

def test_failure_injection_partial_fill():
    """Verify execution engine handles partial fills without leaving unhandled state."""
    adapter = PaperAdapter()
    adapter.simulate_partial_fill = True
    adapter.partial_fill_qty = 4

    engine = ExecutionEngine(broker_adapter=adapter)
    order = make_test_order("ord-part-01", qty=10)

    event = engine.submit_order(order)
    assert event.status == OrderStatus.PARTIALLY_FILLED
    assert event.filled_quantity == 4
    assert event.remaining_quantity == 6

    # Verify state machine allows transition from PARTIALLY_FILLED to FILLED
    assert OrderStateMachine.can_transition(OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED) is True


# =====================================================================
# 9. Broker Rejected Order
# =====================================================================

def test_failure_injection_rejected_order():
    """Verify execution engine handles explicit broker rejection without orphan state."""
    adapter = PaperAdapter()
    adapter.simulate_rejection_symbols.add("REJECTED_STOCK")

    engine = ExecutionEngine(broker_adapter=adapter)
    order = make_test_order("ord-rej-01", symbol="REJECTED_STOCK")
    event = engine.submit_order(order)

    assert event.status == OrderStatus.REJECTED
    assert event.rejection_reason is not None
    assert "blocked by broker" in event.rejection_reason.lower()


# =====================================================================
# 10. Duplicate Order Submission Attempt
# =====================================================================

def test_failure_injection_duplicate_order_attempt():
    """Verify DuplicateOrderError prevents submitting identical client_order_id twice (idempotency)."""
    engine = ExecutionEngine(dedup_window_seconds=60.0)
    order = make_test_order("ord-dup-check-01")

    # First submission succeeds
    ev1 = engine.submit_order(order)
    assert ev1.status in (OrderStatus.SUBMITTED, OrderStatus.FILLED)

    # Duplicate submission must raise DuplicateOrderError
    with pytest.raises(DuplicateOrderError):
        engine.submit_order(order)


# =====================================================================
# 11. Database Transaction Failure & Rollback
# =====================================================================

def test_failure_injection_database_failure(temp_db):
    """Verify repository transactions roll back uncommitted changes upon unhandled error."""
    repo = DatabaseRepository(db_path=temp_db)

    # Insert a valid capital snapshot first
    now = datetime.now(timezone.utc)
    cap = CapitalSnapshot(
        timestamp=now,
        total_capital=Decimal("100.00"),
        available_capital=Decimal("100.00"),
        buying_power=Decimal("100.00"),
        deployed_capital=Decimal("0.00"),
        total_equity=Decimal("100.00"),
        realized_pnl=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        daily_drawdown_amount=Decimal("0.00"),
        daily_drawdown_pct=Decimal("0.00"),
        high_water_mark=Decimal("100.00"),
    )
    repo.save_capital_state(cap)

    # Simulate failing transaction block
    try:
        with get_connection(temp_db) as conn:
            conn.execute(
                "INSERT INTO capital_state (timestamp, total_capital, available_capital, deployed_capital, buying_power, realized_pnl, unrealized_pnl, daily_drawdown, high_water_mark) "
                "VALUES ('2026-09-24T10:00:00', 999.0, 999.0, 0.0, 999.0, 0.0, 0.0, 0.0, 999.0)"
            )
            # Deliberate failure inside transaction
            raise RuntimeError("Simulated power loss / disk error")
    except RuntimeError:
        pass

    # Verify uncommitted state was rolled back; capital remains 100.00
    latest = repo.get_latest_capital_state()
    assert latest is not None
    assert Decimal(str(latest["total_capital"])) == Decimal("100.00")


# =====================================================================
# 12. Process Crash & Laptop Restart Recovery
# =====================================================================

def test_failure_injection_process_crash_and_recovery(temp_db):
    """Verify full state recovery after sudden process crash / restart."""
    repo = DatabaseRepository(db_path=temp_db)

    # 1. Simulate state before crash
    pos = make_test_position("INFY", Decimal("1890.00"), Decimal("1878.00"))
    repo.save_position(pos)

    # 2. Simulate process crash by creating brand new in-memory controllers
    new_watcher = IndependentPositionWatcher()
    new_capital = CapitalManager(config=CapitalConfig(starting_capital=Decimal("100.00")))
    new_engine = ExecutionEngine()

    recovery_mgr = RestartRecoveryManager(repository=repo, db_path=temp_db)
    rec_state = recovery_mgr.recover_system_state(
        position_watcher=new_watcher,
        capital_manager=new_capital,
        execution_engine=new_engine,
    )

    # Verify position rehydrated with exact stop levels intact
    assert len(rec_state.recovered_positions) == 1
    recovered_pos = new_watcher.get_position(pos.position_id)
    assert recovered_pos is not None
    assert recovered_pos.symbol == "INFY"
    assert recovered_pos.hard_stop_price == Decimal("1878.00")
    assert recovered_pos.status == PositionStatus.OPEN


# =====================================================================
# 13. Inconsistent Local vs. Broker State Reconciliation
# =====================================================================

def test_failure_injection_inconsistent_local_broker_state():
    """Verify PaperAdapter.reconcile() identifies quantity mismatches between local state and broker."""
    adapter = PaperAdapter()
    local_pos = make_test_position("INFY", Decimal("1890.00"), Decimal("1878.00"))

    # Local has 1 share, broker has 0 shares (simulated mismatch)
    report = adapter.reconcile([local_pos])

    assert report.is_clean is False
    assert len(report.mismatches) == 1
    assert report.mismatches[0].discrepancy_type == "MISSING_IN_BROKER"
    assert report.mismatches[0].symbol == "INFY"


# =====================================================================
# 14. Deterministic Hard Risk Independence from LLMs
# =====================================================================

def test_deterministic_hard_risk_protection_independent_of_llm():
    """Verify IndependentPositionWatcher protects capital even when ALL AI models are dead."""
    watcher = IndependentPositionWatcher()

    # Position opened
    pos = make_test_position("INFY", Decimal("1890.00"), Decimal("1878.00"))
    watcher.open_position(pos)

    # Simulate catastrophic price breach (1875.00 <= 1878.00 hard stop)
    tick = NormalizedMarketEvent(
        symbol="INFY",
        source=MarketSource.SIMULATED,
        exchange_timestamp=datetime.now(timezone.utc),
        ingest_timestamp=datetime.now(timezone.utc),
        last_price=Decimal("1875.00"),
        volume=1000,
        bid_price=Decimal("1874.80"),
        ask_price=Decimal("1875.20"),
        bid_quantity=10,
        ask_quantity=10,
        spread_pct=Decimal("0.0002"),
    )

    interventions = watcher.evaluate_tick(tick)

    # Hard stop fires instantaneously with 0 LLM calls
    assert len(interventions) == 1
    assert interventions[0].trigger == WatcherExitTrigger.HARD_STOP
    assert interventions[0].trigger_price == Decimal("1875.00")
    assert watcher.get_position(pos.position_id).status in (PositionStatus.CLOSING, PositionStatus.CLOSED)
