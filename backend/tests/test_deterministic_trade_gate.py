"""Comprehensive Test Suite for Phase 12: Deterministic Trade Gate + AI Council.

Verifies:
1. Complete 7-step decision pipeline:
   - Step 1: Deterministic candidate gate (price orientation, spread, liquidity, cutoff)
   - Step 2: Risk / capital / cost gate (circuit breaker, positions limit, Indian friction, net edge)
   - Step 3: Qwen3 qualitative analysis
   - Step 4: DeepSeek-R1 adversarial challenge
   - Step 5: Deterministic final TradePlan synthesis containing all 13 items from PDF
   - Step 6: Execution authorization (autonomous vs manual gating)
   - Step 7: Position Watcher ownership transfer
2. Critical safety invariant: AI models cannot directly submit orders to broker.
3. Complete audit logging across all pipeline transitions.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
from app.ai.challenger_client import DeepSeekR1ChallengerClient
from app.ai.client import Qwen3AnalystClient
from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig, RiskLimitsConfig
from app.capital.risk_engine import RiskEngine
from app.gate.audit_logger import TradeGateAuditLogger
from app.gate.config import TradeGateConfig
from app.gate.trade_gate import DeterministicTradeGate
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    FeatureSnapshot,
    MarketRegime,
    OrderStatus,
    PositionSnapshot,
    PositionStatus,
    StrategyType,
    TradeSide,
)


def make_candidate(
    candidate_id: str = "cand-gate-001",
    symbol: str = "TCS",
    trigger_price: Decimal = Decimal("3500.00"),
    stop_price: Decimal = Decimal("3470.00"),
    target_price: Decimal = Decimal("3560.00"),
    spread_pct: Decimal = Decimal("0.0008"),
    liquidity_score: Decimal = Decimal("90.0"),
    detected_at: datetime | None = None,
) -> Candidate:
    """Helper to construct a valid test Candidate."""
    t0 = detected_at or datetime(2026, 9, 24, 9, 30, tzinfo=timezone.utc)
    fs = FeatureSnapshot(
        symbol=symbol,
        timestamp=t0,
        bar_timeframe="1m",
        vwap=Decimal("3480.00"),
        current_price=trigger_price,
        vwap_distance_pct=Decimal("0.0057"),
        momentum_score=Decimal("2.20"),
        relative_volume_10=Decimal("2.50"),
        volume_acceleration=Decimal("1.10"),
        price_acceleration=Decimal("0.50"),
        realized_volatility_15=Decimal("0.012"),
        spread_pct=spread_pct,
        liquidity_score=liquidity_score,
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.75"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    return Candidate(
        candidate_id=candidate_id,
        detected_at=t0,
        symbol=symbol,
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=trigger_price,
        initial_stop_price=stop_price,
        suggested_target_price=target_price,
        rank_score=Decimal("91.0"),
        quantitative_evidence={"rvol": "2.50", "vwap": "3480.00"},
        feature_snapshot=fs,
    )


def create_mock_ai_clients(
    qwen_action: str = "PROCEED",
    qwen_confidence: float = 0.85,
    deepseek_rec: str = "CONFIRM",
    deepseek_severity: str = "LOW",
) -> tuple[Qwen3AnalystClient, DeepSeekR1ChallengerClient]:
    """Helper to create mock Qwen3 and DeepSeek-R1 clients returning deterministic payloads."""
    qwen_resp = {
        "response": json.dumps(
            {
                "thesis_summary": "High momentum continuation above VWAP with strong RVOL.",
                "catalyst_identified": "Sector breakout",
                "bullish_evidence": ["RVOL > 2.0", "Above VWAP", "Higher highs"],
                "invalidation_conditions": ["Break below 3470"],
                "perceived_risks": ["Minor overhead resistance"],
                "confidence_score": qwen_confidence,
                "context_summary": "Bullish trend",
                "suggested_action": qwen_action,
            }
        ),
        "eval_count": 120,
    }

    deepseek_resp = {
        "response": json.dumps(
            {
                "critique_summary": "Critique evaluates thesis; risk profile acceptable.",
                "identified_vulnerabilities": ["Potential resistance at 3550"],
                "contradictory_signals": [],
                "missing_evidence": [],
                "invalidation_conditions": ["Break below 3470"],
                "worst_case_scenario": "Stop hit with standard friction.",
                "downside_severity": deepseek_severity,
                "recommendation_flag": deepseek_rec,
            }
        ),
        "eval_count": 140,
    }

    def qwen_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=qwen_resp)

    def deepseek_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=deepseek_resp)

    qwen_client = Qwen3AnalystClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(qwen_handler)),
        sync_http_client=httpx.Client(transport=httpx.MockTransport(qwen_handler)),
    )
    deepseek_client = DeepSeekR1ChallengerClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(deepseek_handler)),
        sync_http_client=httpx.Client(transport=httpx.MockTransport(deepseek_handler)),
    )
    return qwen_client, deepseek_client


# =====================================================================
# 1. Step 1: Deterministic Candidate Gate Tests
# =====================================================================


def test_candidate_gate_rejection_invalid_stop_orientation():
    """Verify Candidate Gate rejects candidate when initial stop >= trigger price for BUY."""
    gate = DeterministicTradeGate()
    cand = make_candidate(trigger_price=Decimal("3500.00"), stop_price=Decimal("3510.00"))
    passed, reason = gate.evaluate_candidate_gate(cand)

    assert passed is False
    assert "Stop price" in reason
    assert "strictly below trigger" in reason


def test_candidate_gate_rejection_excessive_spread():
    """Verify Candidate Gate rejects candidate when spread exceeds 15 bps (0.0015)."""
    gate = DeterministicTradeGate()
    cand = make_candidate(spread_pct=Decimal("0.0025"))  # 25 bps
    passed, reason = gate.evaluate_candidate_gate(cand)

    assert passed is False
    assert "Spread" in reason
    assert "exceeds max tolerable" in reason


def test_candidate_gate_rejection_deficient_liquidity():
    """Verify Candidate Gate rejects candidate when liquidity score is below 70.0."""
    gate = DeterministicTradeGate()
    cand = make_candidate(liquidity_score=Decimal("65.0"))
    passed, reason = gate.evaluate_candidate_gate(cand)

    assert passed is False
    assert "Liquidity score" in reason
    assert "below minimum hurdle" in reason


@pytest.mark.asyncio
async def test_pipeline_halts_at_step1_without_invoking_ai():
    """Verify candidate gate rejection immediately returns REJECTED TradePlan without calling AI."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    gate = DeterministicTradeGate(
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    # Invalid candidate with excessive spread
    cand = make_candidate(spread_pct=Decimal("0.0030"))
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.REJECTED
    assert "Spread" in plan.decision_reason
    assert plan.ai_thesis_ref is None
    assert plan.ai_critique_ref is None
    # Verify AI metrics show 0 requests (AI was not called!)
    assert qwen_client.metrics.total_requests == 0
    assert deepseek_client.metrics.total_requests == 0


# =====================================================================
# 2. Step 2: Risk / Capital / Cost Gate Tests
# =====================================================================


@pytest.mark.asyncio
async def test_risk_gate_rejection_circuit_breaker():
    """Verify pipeline rejects candidate when daily drawdown circuit breaker is tripped."""
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("1000.00")))
    cap_mgr.realized_pnl = Decimal("-40.00")  # 4% loss > 3% max daily drawdown limit
    risk_engine = RiskEngine(capital_manager=cap_mgr)

    qwen_client, deepseek_client = create_mock_ai_clients()
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.REJECTED
    assert "circuit breaker" in plan.decision_reason.lower()
    assert qwen_client.metrics.total_requests == 0


@pytest.mark.asyncio
async def test_risk_gate_rejection_active_positions_limit():
    """Verify pipeline rejects candidate when maximum active positions (2) limit is reached."""
    gate = DeterministicTradeGate()
    t0 = datetime.now(timezone.utc)
    # Register 2 active positions in watcher
    pos1 = PositionSnapshot(
        position_id="pos-01",
        plan_id="plan-01",
        symbol="INFY",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("1500.00"),
        current_price=Decimal("1500.00"),
        hard_stop_price=Decimal("1480.00"),
        unrealized_pnl=Decimal("0.00"),
        status=PositionStatus.OPEN,
        opened_at=t0,
        last_evaluated_at=t0,
    )
    pos2 = PositionSnapshot(
        position_id="pos-02",
        plan_id="plan-02",
        symbol="WIPRO",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("500.00"),
        current_price=Decimal("500.00"),
        hard_stop_price=Decimal("490.00"),
        unrealized_pnl=Decimal("0.00"),
        status=PositionStatus.OPEN,
        opened_at=t0,
        last_evaluated_at=t0,
    )
    gate.position_watcher.open_position(pos1)
    gate.position_watcher.open_position(pos2)

    cand = make_candidate(symbol="TCS")
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.REJECTED
    assert "Active positions limit reached" in plan.decision_reason


# =====================================================================
# 3. Steps 3 & 4: AI Council Integration & Arbitration Tests
# =====================================================================


@pytest.mark.asyncio
async def test_ai_council_rejection_qwen3_reject():
    """Verify pipeline rejects candidate when Qwen3 suggests REJECT."""
    qwen_client, deepseek_client = create_mock_ai_clients(qwen_action="REJECT")
    # Provide capital so risk gate passes
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.REJECTED
    assert "Qwen3 thesis rejected candidate" in plan.decision_reason
    assert plan.ai_thesis_ref is not None


@pytest.mark.asyncio
async def test_ai_council_rejection_deepseek_severe_veto():
    """Verify pipeline rejects candidate when DeepSeek-R1 issues SEVERE VETO despite Qwen3 PROCEED."""
    qwen_client, deepseek_client = create_mock_ai_clients(
        qwen_action="PROCEED",
        deepseek_rec="VETO_CANDIDATE",
        deepseek_severity="SEVERE",
    )
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.REJECTED
    assert "DeepSeek-R1 vetoed candidate on severe risk" in plan.decision_reason


# =====================================================================
# 4. Step 5: TradePlan Contract Attributes Verification (13 Items)
# =====================================================================


@pytest.mark.asyncio
async def test_final_trade_plan_contains_all_13_pdf_items():
    """Verify the synthesized TradePlan strictly contains all 13 items specified in PDF."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = await gate.process_candidate(cand)

    # 1. instrument
    assert plan.instrument == "TCS"
    # 2. side
    assert plan.side == TradeSide.BUY
    # 3. quantity
    assert plan.quantity > 0
    # 4. entry context
    assert "trigger_price" in plan.entry_context
    assert "vwap" in plan.entry_context
    assert "momentum_score" in plan.entry_context
    # 5. expected edge
    assert isinstance(plan.expected_edge, Decimal)
    # 6. estimated costs
    assert plan.estimated_costs is not None
    assert plan.estimated_costs.total_friction >= Decimal("0.00")
    # 7. risk limits
    assert plan.risk_limits is not None
    assert plan.risk_limits.max_loss_amount > Decimal("0.00")
    assert plan.risk_limits.max_capital_allocation > Decimal("0.00")
    # 8. stop / protection
    assert plan.stop_protection is not None
    assert plan.stop_protection.hard_stop_price == Decimal("3470.00")
    assert "15:15" in plan.stop_protection.time_exit_time
    # 9. invalidation
    assert len(plan.invalidation) >= 2
    # 10. strategy
    assert plan.strategy == StrategyType.MOMENTUM_CONTINUATION
    # 11. AI evidence references
    assert "qwen3" in plan.ai_evidence_references
    assert "deepseek_r1" in plan.ai_evidence_references
    # 12. decision reason
    assert plan.decision_reason != ""
    # 13. approval mode
    assert plan.approval_mode in (ApprovalMode.AUTONOMOUS, ApprovalMode.MANUAL_PENDING)


# =====================================================================
# 5. Steps 6 & 7: Authorization & Position Watcher Ownership Tests
# =====================================================================


@pytest.mark.asyncio
async def test_execution_authorization_and_position_watcher_handoff():
    """Verify autonomous trade authorizes order and hands over position to Position Watcher."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
        autonomous_threshold=Decimal("50000.00"),  # allow autonomous execution
    )
    gate = DeterministicTradeGate(
        config=TradeGateConfig(autonomous_threshold=Decimal("50000.00")),
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.AUTONOMOUS
    # Verify order was dispatched to execution engine
    orders = gate.execution_engine.get_all_orders()
    assert len(orders) == 1
    assert orders[0].symbol == "TCS"
    assert orders[0].status == OrderStatus.FILLED

    # Verify position ownership transferred to Position Watcher
    open_positions = gate.position_watcher.get_all_open_positions()
    assert len(open_positions) == 1
    pos = open_positions[0]
    assert pos.symbol == "TCS"
    assert pos.hard_stop_price == Decimal("3470.00")
    assert pos.quantity == plan.quantity


@pytest.mark.asyncio
async def test_manual_pending_gating_and_approval_flow():
    """Verify trade with notional > ₹300 is held in MANUAL_PENDING until explicitly approved."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
        autonomous_threshold=Decimal("300.00"),  # strict ₹300 autonomous threshold
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate(trigger_price=Decimal("3500.00"))  # Notional >> ₹300
    plan = await gate.process_candidate(cand)

    assert plan.approval_mode == ApprovalMode.MANUAL_PENDING
    # Order NOT submitted yet
    assert len(gate.execution_engine.get_all_orders()) == 0
    assert len(gate.position_watcher.get_all_open_positions()) == 0

    # Explicit human approval via API
    order_event = gate.approve_manual_plan(plan.plan_id)
    assert order_event.status == OrderStatus.FILLED
    assert plan.approval_mode == ApprovalMode.MANUAL_APPROVED
    assert len(gate.position_watcher.get_all_open_positions()) == 1


def test_ai_models_have_zero_order_execution_authority():
    """Verify AI models have no order execution or broker methods."""
    qwen = Qwen3AnalystClient()
    deepseek = DeepSeekR1ChallengerClient()

    for forbidden in ["submit_order", "execute_trade", "place_order", "cancel_order", "send_order"]:
        assert not hasattr(qwen, forbidden)
        assert not hasattr(deepseek, forbidden)


# =====================================================================
# 6. Audit Logging & Synchronous Parity Tests
# =====================================================================


def test_sync_candidate_processing_parity():
    """Verify synchronous processing matches async behavior."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
    )
    cand = make_candidate()
    plan = gate.process_candidate_sync(cand)

    assert plan.instrument == "TCS"
    assert plan.approval_mode in (ApprovalMode.AUTONOMOUS, ApprovalMode.MANUAL_PENDING)


def test_audit_logging_tracks_all_stages():
    """Verify audit logger records stage transitions."""
    qwen_client, deepseek_client = create_mock_ai_clients()
    audit_logger = TradeGateAuditLogger()
    cap_mgr = CapitalManager(config=CapitalConfig(starting_capital=Decimal("50000.00")))
    risk_engine = RiskEngine(
        capital_manager=cap_mgr,
        config=RiskLimitsConfig(min_economical_trade_size=Decimal("100.00")),
    )
    gate = DeterministicTradeGate(
        risk_engine=risk_engine,
        qwen3_client=qwen_client,
        deepseek_client=deepseek_client,
        audit_logger=audit_logger,
    )
    cand = make_candidate()
    plan = gate.process_candidate_sync(cand)
    assert plan.instrument == "TCS"

    history = audit_logger.get_history(candidate_id=cand.candidate_id)
    stages = [entry["stage"] for entry in history]

    assert "CANDIDATE_GATE" in stages
    assert "RISK_GATE" in stages
    assert "QWEN3_ANALYSIS" in stages
    assert "DEEPSEEK_CHALLENGE" in stages
    assert "COUNCIL_ARBITRATION" in stages
    assert "TRADE_PLAN_SYNTHESIS" in stages
    assert len(history) >= 6
