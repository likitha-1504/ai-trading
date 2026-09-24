"""Comprehensive Test Suite for Phase 10: Qwen3 Analyst Integration.

Verifies:
1. Structured feature context formatting without raw tick stream leakage.
2. Strict JSON schema validation for thesis, evidence, confidence, invalidation, risks, action.
3. Resilience to model timeouts, connection failures, and HTTP errors with configurable retries.
4. Malformed output extraction, validation rejection, and deterministic safe fallback.
5. Telemetry recording for latency, token consumption, and failure modes.
6. Absolute safety invariant: Qwen3 is an evidence provider with zero order execution authority.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
from app.ai.client import Qwen3AnalystClient
from app.ai.config import Qwen3Config
from app.ai.metrics import AIAnalystMetrics
from app.ai.prompts import Qwen3PromptBuilder
from app.ai.validator import MalformedAIOutputError, Qwen3OutputValidator
from app.models.contracts import (
    Candidate,
    FeatureSnapshot,
    MarketRegime,
    MarketThesisAction,
    StrategyType,
    TradeSide,
)


def make_test_candidate() -> Candidate:
    """Helper to construct a deterministic test Candidate with FeatureSnapshot."""
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    fs = FeatureSnapshot(
        symbol="RELIANCE",
        timestamp=t0,
        bar_timeframe="1m",
        vwap=Decimal("100.00"),
        current_price=Decimal("101.50"),
        vwap_distance_pct=Decimal("0.015"),
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
        candidate_id="cand-qwen-001",
        detected_at=t0,
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("101.50"),
        initial_stop_price=Decimal("99.50"),
        suggested_target_price=Decimal("105.00"),
        rank_score=Decimal("88.5"),
        quantitative_evidence={
            "rvol": "2.20",
            "vwap_distance_pct": "0.015",
            "regime": "BULLISH_TRENDING",
        },
        feature_snapshot=fs,
    )


# =====================================================================
# 1. Prompt Engineering & Data Segregation Tests
# =====================================================================


def test_qwen3_prompt_builder_structured_features():
    """Verify Qwen3 prompt receives structured feature summaries without raw tick streams."""
    candidate = make_test_candidate()
    system_prompt, user_prompt = Qwen3PromptBuilder.build_prompt(
        candidate=candidate, prompt_version="qwen3-analyst-v1.0.0"
    )

    # Check system prompt safety rules
    assert "EVIDENCE PROVIDER, NOT THE FINAL TRADE EXECUTION AUTHORITY" in system_prompt
    assert "confidence_score" in system_prompt
    assert "suggested_action" in system_prompt

    # Check user prompt contents
    assert candidate.candidate_id in user_prompt
    assert "RELIANCE" in user_prompt
    assert "101.50" in user_prompt
    assert "BULLISH_TRENDING" in user_prompt
    assert "HIGHER_HIGHS" in user_prompt

    # Ensure raw tick streams are NOT present
    assert "raw_ticks" not in user_prompt
    assert "tick_sequence" not in user_prompt


# =====================================================================
# 2. Schema Validation & Parsing Tests
# =====================================================================


def test_validator_valid_json_parsing():
    """Verify strictly valid JSON response is parsed into typed MarketThesis."""
    valid_payload = {
        "thesis_summary": "Strong momentum breakout supported by 2.2x RVOL and bullish sector alignment.",
        "catalyst_identified": "Energy sector earnings optimism and institutional volume surge.",
        "bullish_evidence": ["RVOL at 2.2x", "Price holding above VWAP", "Higher-high structure"],
        "invalidation_conditions": ["Price breaks below 99.50 stop", "Spread expands beyond 20 bps"],
        "perceived_risks": ["Broader index reversal", "Sudden liquidity drop"],
        "confidence_score": 0.82,
        "context_summary": "Bullish trending regime with strong sector momentum.",
        "suggested_action": "PROCEED",
    }
    raw_output = json.dumps(valid_payload)

    thesis = Qwen3OutputValidator.validate_and_parse(
        raw_output=raw_output,
        candidate_id="cand-001",
        latency_ms=120,
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
        token_count=180,
    )

    assert thesis.candidate_id == "cand-001"
    assert thesis.thesis_summary.startswith("Strong momentum breakout")
    assert thesis.catalyst_identified == "Energy sector earnings optimism and institutional volume surge."
    assert len(thesis.bullish_evidence) == 3
    assert thesis.confidence_score == Decimal("0.82")
    assert thesis.suggested_action == MarketThesisAction.PROCEED
    assert thesis.latency_ms == 120
    assert thesis.token_count == 180
    assert thesis.is_fallback is False


def test_validator_markdown_fence_cleaning():
    """Verify JSON wrapped inside markdown codeblocks (```json ... ```) is cleaned and parsed."""
    raw_with_fences = """```json
    {
      "thesis_summary": "Fenced output test thesis.",
      "catalyst_identified": null,
      "bullish_evidence": ["Solid volume"],
      "invalidation_conditions": ["Stop breach"],
      "perceived_risks": ["Low liquidity"],
      "confidence_score": 0.70,
      "context_summary": null,
      "suggested_action": "CAUTION"
    }
    ```"""

    thesis = Qwen3OutputValidator.validate_and_parse(
        raw_output=raw_with_fences,
        candidate_id="cand-002",
        latency_ms=95,
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
    )

    assert thesis.thesis_summary == "Fenced output test thesis."
    assert thesis.suggested_action == MarketThesisAction.CAUTION
    assert thesis.confidence_score == Decimal("0.70")


def test_validator_confidence_bounds_enforcement():
    """Verify confidence score outside [0.0, 1.0] raises MalformedAIOutputError."""
    payload = {
        "thesis_summary": "Invalid confidence test",
        "bullish_evidence": ["Evidence"],
        "invalidation_conditions": ["Stop"],
        "perceived_risks": ["Risk"],
        "confidence_score": 1.5,  # Out of bounds
        "suggested_action": "PROCEED",
    }

    with pytest.raises(MalformedAIOutputError, match="out of valid range"):
        Qwen3OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload),
            candidate_id="cand-003",
            latency_ms=50,
            model_name="qwen3:latest",
            model_version="v1.0",
            prompt_version="qwen3-analyst-v1.0.0",
        )


def test_validator_invalid_suggested_action_rejected():
    """Verify unknown suggested action is rejected by deterministic validator."""
    payload = {
        "thesis_summary": "Invalid action test",
        "bullish_evidence": ["Evidence"],
        "invalidation_conditions": ["Stop"],
        "perceived_risks": ["Risk"],
        "confidence_score": 0.5,
        "suggested_action": "YOLO_BUY",  # Invalid action
    }

    with pytest.raises(MalformedAIOutputError, match="Invalid suggested_action"):
        Qwen3OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload),
            candidate_id="cand-004",
            latency_ms=50,
            model_name="qwen3:latest",
            model_version="v1.0",
            prompt_version="qwen3-analyst-v1.0.0",
        )


def test_validator_missing_required_fields():
    """Verify missing required fields triggers validation error."""
    payload = {
        # Missing thesis_summary
        "bullish_evidence": ["Evidence"],
        "invalidation_conditions": ["Stop"],
        "perceived_risks": ["Risk"],
        "confidence_score": 0.5,
        "suggested_action": "PROCEED",
    }

    with pytest.raises(MalformedAIOutputError, match="Missing or invalid 'thesis_summary'"):
        Qwen3OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload),
            candidate_id="cand-005",
            latency_ms=50,
            model_name="qwen3:latest",
            model_version="v1.0",
            prompt_version="qwen3-analyst-v1.0.0",
        )


def test_validator_fallback_thesis_safety_invariants():
    """Verify fallback thesis strictly satisfies safety rules (confidence 0.0, CAUTION, is_fallback=True)."""
    fallback = Qwen3OutputValidator.create_fallback_thesis(
        candidate_id="cand-fallback",
        reason="Model connection timeout",
        latency_ms=3000,
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
    )

    assert fallback.candidate_id == "cand-fallback"
    assert fallback.is_fallback is True
    assert fallback.confidence_score == Decimal("0.0")
    assert fallback.suggested_action == MarketThesisAction.CAUTION
    assert len(fallback.invalidation_conditions) > 0
    assert len(fallback.perceived_risks) > 0


# =====================================================================
# 3. Client Resilience: Timeout, Retries & Fallback Tests
# =====================================================================


@pytest.mark.asyncio
async def test_client_successful_async_analysis():
    """Verify Qwen3AnalystClient executes async analysis and parses valid response via mock transport."""
    candidate = make_test_candidate()

    mock_ollama_resp = {
        "response": json.dumps(
            {
                "thesis_summary": "Verified momentum setup with clean order flow.",
                "catalyst_identified": "Sector breakout",
                "bullish_evidence": ["RVOL > 2.0", "Above VWAP"],
                "invalidation_conditions": ["VWAP breakdown"],
                "perceived_risks": ["Spread slippage"],
                "confidence_score": 0.85,
                "context_summary": "Bullish trending market",
                "suggested_action": "PROCEED",
            }
        ),
        "eval_count": 120,
        "prompt_eval_count": 50,
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_ollama_resp)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = Qwen3AnalystClient(http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

    assert thesis.candidate_id == candidate.candidate_id
    assert thesis.is_fallback is False
    assert thesis.suggested_action == MarketThesisAction.PROCEED
    assert thesis.confidence_score == Decimal("0.85")
    assert thesis.token_count == 170
    assert client.metrics.successful_analyses == 1
    assert client.metrics.fallback_count == 0


@pytest.mark.asyncio
async def test_client_malformed_output_fallback():
    """Verify malformed JSON from model is safely caught and returns a safe fallback thesis."""
    candidate = make_test_candidate()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "I think you should buy RELIANCE it looks good!"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = Qwen3AnalystClient(http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

    assert thesis.candidate_id == candidate.candidate_id
    assert thesis.is_fallback is True
    assert thesis.confidence_score == Decimal("0.0")
    assert thesis.suggested_action == MarketThesisAction.CAUTION
    assert client.metrics.malformed_output_count == 1
    assert client.metrics.fallback_count == 1


@pytest.mark.asyncio
async def test_client_timeout_and_retries():
    """Verify timeout triggers configured retries and generates safe fallback on exhaustion."""
    candidate = make_test_candidate()
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Mock timeout")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        config = Qwen3Config(timeout_seconds=0.5, max_retries=2, retry_backoff_seconds=0.01)
        client = Qwen3AnalystClient(config=config, http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

    # 1 initial + 2 retries = 3 calls
    assert call_count == 3
    assert thesis.is_fallback is True
    assert thesis.confidence_score == Decimal("0.0")
    assert client.metrics.timeout_count == 1
    assert client.metrics.fallback_count == 1


@pytest.mark.asyncio
async def test_client_model_unavailable_http_error():
    """Verify 503 or 500 error from model endpoint generates deterministic fallback."""
    candidate = make_test_candidate()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content="Service Unavailable")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        config = Qwen3Config(max_retries=1, retry_backoff_seconds=0.01)
        client = Qwen3AnalystClient(config=config, http_client=async_http)
        thesis = await client.analyze_candidate(candidate)

    assert thesis.is_fallback is True
    assert "unavailable" in thesis.thesis_summary.lower()
    assert client.metrics.failed_requests == 1
    assert client.metrics.fallback_count == 1


# =====================================================================
# 4. Synchronous Parity & Telemetry Tests
# =====================================================================


def test_client_sync_analysis_parity():
    """Verify synchronous client execution matches async behavior."""
    candidate = make_test_candidate()

    mock_ollama_resp = {
        "response": json.dumps(
            {
                "thesis_summary": "Sync analysis test setup.",
                "catalyst_identified": None,
                "bullish_evidence": ["RVOL confirmation"],
                "invalidation_conditions": ["Reversal"],
                "perceived_risks": ["Market wide selloff"],
                "confidence_score": 0.75,
                "context_summary": None,
                "suggested_action": "PROCEED",
            }
        ),
        "eval_count": 80,
        "prompt_eval_count": 40,
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_ollama_resp)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as sync_http:
        client = Qwen3AnalystClient(sync_http_client=sync_http)
        thesis = client.analyze_candidate_sync(candidate)

    assert thesis.candidate_id == candidate.candidate_id
    assert thesis.is_fallback is False
    assert thesis.confidence_score == Decimal("0.75")
    assert thesis.token_count == 120
    assert client.metrics.successful_analyses == 1


def test_telemetry_metrics_accumulation():
    """Verify AIAnalystMetrics accurately records counts, latencies, tokens, and summary snapshot."""
    metrics = AIAnalystMetrics()
    metrics.record_success(latency_ms=100, token_count=150)
    metrics.record_success(latency_ms=200, token_count=250)
    metrics.record_timeout(latency_ms=500)
    metrics.record_malformed(latency_ms=50)
    metrics.record_fallback()

    summary = metrics.get_summary()
    assert summary["total_requests"] == 4
    assert summary["successful_analyses"] == 2
    assert summary["timeout_count"] == 1
    assert summary["malformed_output_count"] == 1
    assert summary["fallback_count"] == 1
    assert summary["total_tokens_consumed"] == 400
    assert summary["avg_latency_ms"] == 212.5
    assert summary["success_rate_pct"] == 50.0


# =====================================================================
# 5. Core Safety Invariants: Evidence Provider & Zero Order Authority
# =====================================================================


def test_qwen3_cannot_bypass_risk_rules_or_execute_orders():
    """Verify Qwen3 is strictly an evidence provider and cannot bypass deterministic risk rules or place orders."""
    from app.capital.capital_manager import CapitalManager
    from app.capital.config import CapitalConfig
    from app.capital.cost_model import IndianMarketCostModel
    from app.capital.risk_engine import RiskEngine

    # 1. Verification: Qwen3 client and thesis have no broker execution methods
    client = Qwen3AnalystClient()
    assert not hasattr(client, "submit_order")
    assert not hasattr(client, "execute_trade")
    assert not hasattr(client, "place_order")

    candidate = make_test_candidate()
    # High risk candidate: entry 101.50, stop 90.00 -> risk 11.50 per share
    candidate.initial_stop_price = Decimal("90.00")

    # 2. Qwen3 returns ultra-bullish recommendation
    thesis = Qwen3OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "thesis_summary": "Extremely high conviction buy setup.",
                "catalyst_identified": "Major contract win",
                "bullish_evidence": ["Massive volume"],
                "invalidation_conditions": ["Break below 90.00"],
                "perceived_risks": ["General market"],
                "confidence_score": 1.0,  # Maximum confidence
                "context_summary": "Bullish",
                "suggested_action": "PROCEED",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=50,
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
    )
    assert thesis.suggested_action == MarketThesisAction.PROCEED
    assert thesis.confidence_score == Decimal("1.0")

    # 3. Deterministic Risk Engine evaluation on ₹100 capital (1.5% max risk = ₹1.50)
    cap_mgr = CapitalManager(CapitalConfig(starting_capital=Decimal("100.00")))
    cost_model = IndianMarketCostModel()
    risk_engine = RiskEngine(capital_manager=cap_mgr, cost_model=cost_model)

    risk_res = risk_engine.evaluate_candidate(candidate, current_positions=[])

    # Deterministic risk engine REJECTS because ₹11.50 risk > ₹1.50 risk budget
    assert risk_res.approved is False
    assert risk_res.approved_quantity == 0
    assert any("Insufficient capital or risk budget" in reason for reason in risk_res.rejection_reasons)

