"""Comprehensive Test Suite for Phase 11: DeepSeek-R1 Challenger Layer.

Verifies:
1. DeepSeek-R1 receives structured candidate metrics and Qwen3 thesis without raw tick streams.
2. Strict schema validation for critique summary, vulnerabilities, contradictory signals, missing evidence,
   worst-case scenario, downside severity, and recommendation flag.
3. Clean stripping of DeepSeek-R1 <think>...</think> reasoning blocks and markdown code fences.
4. Resilience to timeouts, connection drops, and HTTP errors with exponential backoff retries.
5. Malformed output extraction and deterministic safe fallback generation.
6. Telemetry recording for latency, token consumption, and failure modes.
7. Absolute safety invariant: DeepSeek-R1 has zero order execution authority.
8. Core PDF Requirement: Qwen3 is bullish but DeepSeek-R1 identifies a risk — verified that deterministic
   rules decide the final action without simple majority voting.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
from app.ai.challenger_client import DeepSeekR1ChallengerClient
from app.ai.challenger_config import DeepSeekR1Config
from app.ai.challenger_prompts import (
    DeepSeekR1PromptBuilder,
)
from app.ai.challenger_validator import (
    DeepSeekR1OutputValidator,
    MalformedChallengerOutputError,
)
from app.ai.council_evaluator import evaluate_council_signals
from app.models.contracts import (
    Candidate,
    ChallengerRecommendation,
    ChallengerSeverity,
    FeatureSnapshot,
    MarketRegime,
    MarketThesis,
    MarketThesisAction,
    StrategyType,
    TradeSide,
)


def make_test_candidate(spread_pct: Decimal = Decimal("0.0008"), liquidity: Decimal = Decimal("92.0")) -> Candidate:
    """Helper to construct a deterministic test Candidate with FeatureSnapshot."""
    t0 = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)
    fs = FeatureSnapshot(
        symbol="TCS",
        timestamp=t0,
        bar_timeframe="1m",
        vwap=Decimal("3500.00"),
        current_price=Decimal("3530.00"),
        vwap_distance_pct=Decimal("0.0085"),
        momentum_score=Decimal("2.10"),
        relative_volume_10=Decimal("2.40"),
        volume_acceleration=Decimal("1.20"),
        price_acceleration=Decimal("0.60"),
        realized_volatility_15=Decimal("0.012"),
        spread_pct=spread_pct,
        liquidity_score=liquidity,
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.80"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    return Candidate(
        candidate_id="cand-challenger-001",
        detected_at=t0,
        symbol="TCS",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("3530.00"),
        initial_stop_price=Decimal("3495.00"),
        suggested_target_price=Decimal("3590.00"),
        rank_score=Decimal("89.0"),
        quantitative_evidence={
            "rvol": "2.40",
            "vwap_distance_pct": "0.0085",
            "regime": "BULLISH_TRENDING",
        },
        feature_snapshot=fs,
    )


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
        thesis_summary="Strong continuation breakout in TCS supported by IT sector momentum.",
        catalyst_identified="IT sector quarterly results anticipation",
        bullish_evidence=["RVOL 2.4x", "Holding VWAP", "Higher highs"],
        invalidation_conditions=["Break below 3495.00"],
        perceived_risks=["Potential resistance at 3550.00"],
        confidence_score=confidence,
        context_summary="Bullish trending market regime",
        suggested_action=action,
        latency_ms=110,
        token_count=160,
        is_fallback=False,
    )


# =====================================================================
# 1. Prompt Engineering & Data Segregation Tests
# =====================================================================


def test_deepseek_r1_prompt_builder_structured_context():
    """Verify DeepSeek-R1 prompt receives structured metrics AND Qwen3 thesis without raw ticks."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()
    system_prompt, user_prompt = DeepSeekR1PromptBuilder.build_prompt(
        candidate=candidate,
        thesis=thesis,
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    # Check system prompt constraints
    assert "ADVERSARIAL CHALLENGER, NOT THE FINAL TRADE EXECUTION AUTHORITY" in system_prompt
    assert "downside_severity" in system_prompt
    assert "recommendation_flag" in system_prompt

    # Check candidate context inclusion
    assert candidate.candidate_id in user_prompt
    assert "TCS" in user_prompt
    assert "3530.00" in user_prompt
    assert "BULLISH_TRENDING" in user_prompt

    # Check Qwen3 thesis inclusion
    assert thesis.thesis_summary in user_prompt
    assert "0.85" in user_prompt
    assert "IT sector quarterly results anticipation" in user_prompt

    # Ensure raw ticks are NOT present
    assert "raw_ticks" not in user_prompt
    assert "tick_sequence" not in user_prompt


# =====================================================================
# 2. Schema Validation & Parsing Tests
# =====================================================================


def test_validator_valid_json_critique():
    """Verify strictly valid JSON response is parsed into typed ChallengerCritique."""
    valid_payload = {
        "critique_summary": "Thesis overemphasizes momentum while ignoring approaching multi-week resistance.",
        "identified_vulnerabilities": ["Heavy supply zone at 3550", "Declining volume on 1m bars"],
        "contradictory_signals": ["Sector index RSI showing bearish divergence"],
        "missing_evidence": ["Lack of broad institutional block deals"],
        "invalidation_conditions": ["Immediate rejection at 3545", "Break below VWAP 3500"],
        "worst_case_scenario": "Bull trap reversal resulting in stop-out at 3495 with slippage.",
        "downside_severity": "MEDIUM",
        "recommendation_flag": "CONTEST",
    }
    raw_output = json.dumps(valid_payload)

    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=raw_output,
        candidate_id="cand-challenger-001",
        latency_ms=180,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
        token_count=210,
    )

    assert critique.candidate_id == "cand-challenger-001"
    assert critique.critique_summary.startswith("Thesis overemphasizes")
    assert len(critique.identified_vulnerabilities) == 2
    assert len(critique.contradictory_signals) == 1
    assert len(critique.missing_evidence) == 1
    assert critique.downside_severity == ChallengerSeverity.MEDIUM
    assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
    assert critique.latency_ms == 180
    assert critique.token_count == 210
    assert critique.is_fallback is False


def test_validator_think_tag_stripping():
    """Verify DeepSeek-R1 <think>...</think> chain-of-thought tags are cleanly stripped."""
    raw_with_think = """<think>
    The candidate has strong momentum score 2.10 and RVOL 2.40.
    However, Qwen3 didn't consider the overhead resistance at 3550.
    The spread is 8 bps which is acceptable.
    I will flag this with CONTEST and MEDIUM severity.
    </think>
    ```json
    {
      "critique_summary": "Overhead resistance at 3550 creates unfavorable risk/reward.",
      "identified_vulnerabilities": ["Supply zone at 3550"],
      "contradictory_signals": ["Slowing price acceleration"],
      "missing_evidence": ["Index confirmation"],
      "invalidation_conditions": ["Rejection at 3540"],
      "worst_case_scenario": "Immediate pullback towards VWAP.",
      "downside_severity": "MEDIUM",
      "recommendation_flag": "CONTEST"
    }
    ```"""

    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=raw_with_think,
        candidate_id="cand-challenger-002",
        latency_ms=250,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    assert critique.critique_summary == "Overhead resistance at 3550 creates unfavorable risk/reward."
    assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
    assert critique.downside_severity == ChallengerSeverity.MEDIUM


def test_validator_invalid_severity_rejected():
    """Verify invalid downside severity raises MalformedChallengerOutputError."""
    payload = {
        "critique_summary": "Invalid severity test",
        "identified_vulnerabilities": ["Vuln"],
        "contradictory_signals": ["Signal"],
        "worst_case_scenario": "Worst case",
        "downside_severity": "CATASTROPHIC_EXPLOSION",  # Invalid severity
        "recommendation_flag": "CONTEST",
    }

    with pytest.raises(MalformedChallengerOutputError, match="Invalid downside_severity"):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload),
            candidate_id="cand-003",
            latency_ms=60,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="deepseek-r1-challenger-v1.0.0",
        )


def test_validator_invalid_recommendation_rejected():
    """Verify invalid recommendation flag raises MalformedChallengerOutputError."""
    payload = {
        "critique_summary": "Invalid recommendation test",
        "identified_vulnerabilities": ["Vuln"],
        "contradictory_signals": ["Signal"],
        "worst_case_scenario": "Worst case",
        "downside_severity": "LOW",
        "recommendation_flag": "MAYBE_BUY",  # Invalid recommendation
    }

    with pytest.raises(MalformedChallengerOutputError, match="Invalid recommendation_flag"):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload),
            candidate_id="cand-004",
            latency_ms=60,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="deepseek-r1-challenger-v1.0.0",
        )


def test_validator_fallback_critique_safety_invariants():
    """Verify fallback critique satisfies safety rules (CONTEST, MEDIUM, is_fallback=True)."""
    fallback = DeepSeekR1OutputValidator.create_fallback_critique(
        candidate_id="cand-fallback",
        reason="Challenger inference timeout",
        latency_ms=5000,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    assert fallback.candidate_id == "cand-fallback"
    assert fallback.is_fallback is True
    assert fallback.recommendation_flag == ChallengerRecommendation.CONTEST
    assert fallback.downside_severity == ChallengerSeverity.MEDIUM
    assert fallback.token_count == 0
    assert len(fallback.identified_vulnerabilities) > 0


# =====================================================================
# 3. Client Resilience: Timeout, Retries & Fallback Tests
# =====================================================================


@pytest.mark.asyncio
async def test_client_successful_async_critique():
    """Verify DeepSeekR1ChallengerClient executes async analysis and parses response."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()

    mock_ollama_resp = {
        "response": json.dumps(
            {
                "critique_summary": "Critique corroborates momentum with low counter-evidence.",
                "identified_vulnerabilities": ["Slight spread friction"],
                "contradictory_signals": [],
                "missing_evidence": [],
                "invalidation_conditions": ["Break below VWAP"],
                "worst_case_scenario": "Sideways chop before continuation.",
                "downside_severity": "LOW",
                "recommendation_flag": "CONFIRM",
            }
        ),
        "eval_count": 140,
        "prompt_eval_count": 70,
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_ollama_resp)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = DeepSeekR1ChallengerClient(http_client=async_http)
        critique = await client.critique_candidate(candidate, thesis)

    assert critique.candidate_id == candidate.candidate_id
    assert critique.is_fallback is False
    assert critique.recommendation_flag == ChallengerRecommendation.CONFIRM
    assert critique.downside_severity == ChallengerSeverity.LOW
    assert critique.token_count == 210
    assert client.metrics.successful_analyses == 1


@pytest.mark.asyncio
async def test_client_malformed_output_fallback():
    """Verify malformed JSON from DeepSeek-R1 triggers safe fallback."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "<think>Thinking...</think>Not a JSON object!"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        client = DeepSeekR1ChallengerClient(http_client=async_http)
        critique = await client.critique_candidate(candidate, thesis)

    assert critique.candidate_id == candidate.candidate_id
    assert critique.is_fallback is True
    assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
    assert client.metrics.malformed_output_count == 1
    assert client.metrics.fallback_count == 1


@pytest.mark.asyncio
async def test_client_timeout_and_retries():
    """Verify timeout triggers retries and returns fallback on exhaustion."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Mock timeout")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        config = DeepSeekR1Config(timeout_seconds=0.5, max_retries=2, retry_backoff_seconds=0.01)
        client = DeepSeekR1ChallengerClient(config=config, http_client=async_http)
        critique = await client.critique_candidate(candidate, thesis)

    # 1 initial + 2 retries = 3 calls
    assert call_count == 3
    assert critique.is_fallback is True
    assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
    assert client.metrics.timeout_count == 1


def test_client_sync_critique_parity():
    """Verify synchronous client execution matches async parity."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()

    mock_ollama_resp = {
        "response": json.dumps(
            {
                "critique_summary": "Sync critique test.",
                "identified_vulnerabilities": ["Minor resistance"],
                "contradictory_signals": [],
                "missing_evidence": [],
                "invalidation_conditions": ["Break below 3500"],
                "worst_case_scenario": "Stop hit",
                "downside_severity": "LOW",
                "recommendation_flag": "CONFIRM",
            }
        ),
        "eval_count": 90,
        "prompt_eval_count": 50,
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_ollama_resp)

    transport = httpx.MockTransport(mock_handler)
    with httpx.Client(transport=transport) as sync_http:
        client = DeepSeekR1ChallengerClient(sync_http_client=sync_http)
        critique = client.critique_candidate_sync(candidate, thesis)

    assert critique.candidate_id == candidate.candidate_id
    assert critique.is_fallback is False
    assert critique.recommendation_flag == ChallengerRecommendation.CONFIRM
    assert client.metrics.successful_analyses == 1


# =====================================================================
# 4. Core PDF Invariant: Deterministic Rules Decide Dispute (No Majority Voting)
# =====================================================================


def test_qwen3_bullish_vs_deepseek_severe_veto():
    """Verify deterministic rule REJECTS trade when DeepSeek-R1 issues SEVERE VETO despite Qwen3 PROCEED."""
    candidate = make_test_candidate()
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.90"))

    # DeepSeek-R1 finds fatal flaw
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Severe structural headwind: institutional distribution trap.",
                "identified_vulnerabilities": ["Massive iceberg selling detected on DOM"],
                "contradictory_signals": ["Sector index is plummeting while stock shows fake bid"],
                "worst_case_scenario": "Immediate flash gap down below stop-loss.",
                "downside_severity": "SEVERE",
                "recommendation_flag": "VETO_CANDIDATE",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=150,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)

    # Deterministic rule rejects candidate (no simple majority voting!)
    assert verdict.passed_filter is False
    assert verdict.action == MarketThesisAction.REJECT
    assert "DeepSeek-R1 vetoed candidate on severe risk" in verdict.decision_reason


def test_qwen3_bullish_vs_deepseek_contested_empirical_pass():
    """Verify deterministic rule evaluates empirical metrics when DeepSeek-R1 contests.

    Case: Qwen3 is bullish (PROCEED, 0.85), DeepSeek-R1 contests spread/liquidity.
    Empirical check: Spread is 8 bps (<= 15 bps limit) and liquidity is 92.0 (>= 70.0).
    Result: Candidate PASSES with CAUTION and audited risk notes.
    """
    candidate = make_test_candidate(spread_pct=Decimal("0.0008"), liquidity=Decimal("92.0"))
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.85"))

    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Contesting entry due to potential spread widening friction.",
                "identified_vulnerabilities": ["Spread sensitivity on micro-capital"],
                "contradictory_signals": ["Approaching session highs"],
                "worst_case_scenario": "Slight slippage attrition.",
                "downside_severity": "MEDIUM",
                "recommendation_flag": "CONTEST",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=130,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)

    # Passes under empirical verification with CAUTION
    assert verdict.passed_filter is True
    assert verdict.action == MarketThesisAction.CAUTION
    assert "empirical metrics satisfy risk hurdle" in verdict.decision_reason
    assert "Spread sensitivity on micro-capital" in verdict.risk_audit_notes


def test_qwen3_bullish_vs_deepseek_contested_empirical_fail():
    """Verify deterministic rule REJECTS trade when empirical metrics confirm DeepSeek-R1's warning.

    Case: Qwen3 is bullish (PROCEED, 0.85), DeepSeek-R1 contests spread.
    Empirical check: Spread is 22 bps (> 15 bps limit).
    Result: Candidate is REJECTED by deterministic rule.
    """
    # Candidate with wide spread (22 bps)
    candidate = make_test_candidate(spread_pct=Decimal("0.0022"), liquidity=Decimal("92.0"))
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.85"))

    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Contesting entry: excessive spread will destroy micro-capital edge.",
                "identified_vulnerabilities": ["Excessive bid-ask spread"],
                "contradictory_signals": [],
                "worst_case_scenario": "Friction loss exceeds gross profit target.",
                "downside_severity": "MEDIUM",
                "recommendation_flag": "CONTEST",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=130,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)

    # Rejection triggered by empirical verification of DeepSeek-R1's warning
    assert verdict.passed_filter is False
    assert verdict.action == MarketThesisAction.REJECT
    assert "confirmed by empirical spread" in verdict.decision_reason


def test_deepseek_r1_zero_order_execution_authority():
    """Verify DeepSeek-R1 client has zero broker communication or execution methods."""
    client = DeepSeekR1ChallengerClient()
    assert not hasattr(client, "submit_order")
    assert not hasattr(client, "execute_trade")
    assert not hasattr(client, "place_order")
    assert not hasattr(client, "cancel_order")


def test_council_fallback_safety_gate():
    """Verify deterministic gate blocks clearance when either AI model triggers fallback."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Clean thesis.",
                "identified_vulnerabilities": [],
                "contradictory_signals": [],
                "worst_case_scenario": "Mild pullback",
                "downside_severity": "LOW",
                "recommendation_flag": "CONFIRM",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=100,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    # 1. Thesis fallback
    fallback_thesis = MarketThesis(
        candidate_id=candidate.candidate_id,
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-analyst-v1.0.0",
        thesis_summary="Fallback thesis",
        catalyst_identified="None",
        bullish_evidence=[],
        invalidation_conditions=[],
        perceived_risks=["Model timeout"],
        confidence_score=Decimal("0.0"),
        context_summary="Fallback",
        suggested_action=MarketThesisAction.CAUTION,
        latency_ms=3000,
        is_fallback=True,
    )
    v1 = evaluate_council_signals(candidate, fallback_thesis, critique)
    assert v1.passed_filter is False
    assert v1.action == MarketThesisAction.CAUTION
    assert "AI Council fallback active" in v1.decision_reason

    # 2. Critique fallback
    fallback_critique = DeepSeekR1OutputValidator.create_fallback_critique(
        candidate_id=candidate.candidate_id,
        reason="Challenger timeout",
        latency_ms=5000,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )
    v2 = evaluate_council_signals(candidate, thesis, fallback_critique)
    assert v2.passed_filter is False
    assert v2.action == MarketThesisAction.CAUTION
    assert "AI Council fallback active" in v2.decision_reason


def test_council_qwen3_rejection_or_low_confidence():
    """Verify deterministic gate immediately rejects when Qwen3 rejects or confidence is low."""
    candidate = make_test_candidate()
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "DeepSeek endorses setup.",
                "identified_vulnerabilities": [],
                "contradictory_signals": [],
                "worst_case_scenario": "None",
                "downside_severity": "LOW",
                "recommendation_flag": "CONFIRM",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=100,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    # Qwen3 rejects
    rej_thesis = make_test_thesis(action=MarketThesisAction.REJECT, confidence=Decimal("0.80"))
    v_rej = evaluate_council_signals(candidate, rej_thesis, critique)
    assert v_rej.passed_filter is False
    assert v_rej.action == MarketThesisAction.REJECT
    assert "Qwen3 thesis rejected candidate" in v_rej.decision_reason

    # Qwen3 low confidence (0.45 < 0.60 threshold)
    low_conf_thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.45"))
    v_low = evaluate_council_signals(candidate, low_conf_thesis, critique)
    assert v_low.passed_filter is False
    assert v_low.action == MarketThesisAction.REJECT
    assert "below minimum hurdle" in v_low.decision_reason


def test_council_empirical_liquidity_failure():
    """Verify deterministic gate rejects contested candidate if liquidity score is deficient."""
    # Liquidity score is 55.0 (< 70.0 hurdle)
    candidate = make_test_candidate(spread_pct=Decimal("0.0008"), liquidity=Decimal("55.0"))
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.85"))
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Thin order book liquidity creates execution risk.",
                "identified_vulnerabilities": ["Low depth"],
                "contradictory_signals": [],
                "worst_case_scenario": "High slippage fill",
                "downside_severity": "MEDIUM",
                "recommendation_flag": "CONTEST",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=120,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)
    assert verdict.passed_filter is False
    assert verdict.action == MarketThesisAction.REJECT
    assert "deficient liquidity score" in verdict.decision_reason


def test_council_invalid_stop_orientation():
    """Verify deterministic gate rejects contested candidate if stop price >= trigger price for BUY."""
    candidate = make_test_candidate()
    candidate.initial_stop_price = Decimal("3540.00")  # Invalid stop above trigger 3530.00
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.85"))
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Contesting setup for stop validity verification.",
                "identified_vulnerabilities": ["Stop placement anomaly"],
                "contradictory_signals": [],
                "worst_case_scenario": "Immediate stop trigger",
                "downside_severity": "MEDIUM",
                "recommendation_flag": "CONTEST",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=110,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)
    assert verdict.passed_filter is False
    assert verdict.action == MarketThesisAction.REJECT
    assert "Invalid stop-loss orientation" in verdict.decision_reason


def test_council_full_agreement_proceed():
    """Verify deterministic gate approves trade with PROCEED when Qwen3 and DeepSeek-R1 fully agree."""
    candidate = make_test_candidate()
    thesis = make_test_thesis(action=MarketThesisAction.PROCEED, confidence=Decimal("0.88"))
    critique = DeepSeekR1OutputValidator.validate_and_parse(
        raw_output=json.dumps(
            {
                "critique_summary": "Robust momentum breakout with pristine volume confirmation.",
                "identified_vulnerabilities": [],
                "contradictory_signals": [],
                "worst_case_scenario": "Minor intraday consolidation",
                "downside_severity": "LOW",
                "recommendation_flag": "CONFIRM",
            }
        ),
        candidate_id=candidate.candidate_id,
        latency_ms=110,
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="deepseek-r1-challenger-v1.0.0",
    )

    verdict = evaluate_council_signals(candidate, thesis, critique)
    assert verdict.passed_filter is True
    assert verdict.action == MarketThesisAction.PROCEED
    assert "corroborated by DeepSeek-R1 stress test" in verdict.decision_reason
    assert verdict.confidence == Decimal("0.88")


@pytest.mark.asyncio
async def test_client_connection_error_retries_and_fallback():
    """Verify connection failure triggers retries and records failure metrics."""
    candidate = make_test_candidate()
    thesis = make_test_thesis()
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("Ollama daemon unreachable")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as async_http:
        config = DeepSeekR1Config(timeout_seconds=0.5, max_retries=1, retry_backoff_seconds=0.01)
        client = DeepSeekR1ChallengerClient(config=config, http_client=async_http)
        critique = await client.critique_candidate(candidate, thesis)

    assert call_count == 2  # 1 initial + 1 retry
    assert critique.is_fallback is True
    assert critique.recommendation_flag == ChallengerRecommendation.CONTEST
    assert client.metrics.failed_requests == 1
    assert client.metrics.fallback_count == 1


def test_validator_missing_required_fields():
    """Verify validator errors on missing required fields or non-dictionary JSON."""
    # 1. Missing worst_case_scenario
    payload1 = {
        "critique_summary": "Missing worst case",
        "identified_vulnerabilities": [],
        "contradictory_signals": [],
        "downside_severity": "LOW",
        "recommendation_flag": "CONFIRM",
    }
    with pytest.raises(MalformedChallengerOutputError, match="worst_case_scenario"):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload1),
            candidate_id="cand-err-1",
            latency_ms=50,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="deepseek-r1-challenger-v1.0.0",
        )

    # 2. Missing critique_summary
    payload2 = {
        "identified_vulnerabilities": [],
        "contradictory_signals": [],
        "worst_case_scenario": "Stop hit",
        "downside_severity": "LOW",
        "recommendation_flag": "CONFIRM",
    }
    with pytest.raises(MalformedChallengerOutputError, match="critique_summary"):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output=json.dumps(payload2),
            candidate_id="cand-err-2",
            latency_ms=50,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="deepseek-r1-challenger-v1.0.0",
        )

    # 3. Non-dictionary JSON (JSON array)
    with pytest.raises(MalformedChallengerOutputError, match="not a dictionary"):
        DeepSeekR1OutputValidator.validate_and_parse(
            raw_output=json.dumps(["item1", "item2"]),
            candidate_id="cand-err-3",
            latency_ms=50,
            model_name="deepseek-r1:latest",
            model_version="v1.0",
            prompt_version="deepseek-r1-challenger-v1.0.0",
        )

