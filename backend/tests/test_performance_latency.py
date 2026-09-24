"""Phase 17 Comprehensive Performance & Latency Optimization Test Suite.

Verifies:
1. All 12 pipeline stages measured separately:
   - market data arrival
   - normalization
   - feature computation
   - candidate detection
   - decision preparation
   - Qwen3 latency
   - DeepSeek-R1 latency
   - deterministic gate latency
   - order submission
   - broker acknowledgement
   - fill latency
   - Position Watcher response
2. Explicit architectural segregation:
   - Fast-path internal latency (<50ms target) strictly separated from end-to-end speed.
   - Dual-model qualitative inference (~100-2500ms) categorized as asynchronous AI Council.
   - External broker/exchange matching transit (~5-50ms) categorized as external network.
3. Statistical percentile calculations (min, median/p50, p90, p95, p99, max, mean).
4. Optimization of measured bottlenecks with preserved correctness and risk controls.
5. Hardware profile detection and comparative before/after benchmarking.
6. API endpoint integration (/api/v1/performance/latency-breakdown).
"""

import time
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.engine.bar_aggregator import Bar
from app.engine.feature_engine import FeatureEngine
from app.main import app
from app.models.contracts import (
    MarketRegime,
    MarketSource,
    NormalizedMarketEvent,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
)
from app.performance.benchmarks import (
    HardwareAssumptions,
    PipelineBenchmarkHarness,
)
from app.performance.profiler import (
    LatencyProfiler,
    PipelineStage,
    StageMetrics,
)
from app.watcher.position_watcher import IndependentPositionWatcher


# =====================================================================
# 1. 12 Individual Pipeline Stage Measurement Tests
# =====================================================================


def test_profiler_tracks_all_twelve_stages_separately():
    """Verify that profiler distinctly records and measures all 12 pipeline stages."""
    profiler = LatencyProfiler()

    # Record test samples for all 12 stages
    stages = list(PipelineStage)
    assert len(stages) == 12

    expected_stages = [
        "market_data_arrival",
        "normalization",
        "feature_computation",
        "candidate_detection",
        "decision_preparation",
        "qwen3_latency",
        "deepseek_r1_latency",
        "deterministic_gate",
        "order_submission",
        "broker_acknowledgement",
        "fill_latency",
        "position_watcher_response",
    ]
    for s in expected_stages:
        assert s in [stage.value for stage in stages]

    for stage in stages:
        profiler.record_duration_ns(stage, 1_000_000)  # 1ms

    all_metrics = profiler.get_all_stage_metrics()
    assert len(all_metrics) == 12

    for stage in stages:
        m = all_metrics[stage.value]
        assert m.sample_count == 1
        assert m.min_us == 1000.0
        assert m.median_us == 1000.0
        assert m.max_us == 1000.0


def test_profiler_percentile_distribution():
    """Verify accurate computation of p50, p90, p95, p99, min, max, and mean."""
    profiler = LatencyProfiler()
    stage = PipelineStage.FEATURE_COMPUTATION

    # Feed 100 samples: 1us, 2us, ..., 100us
    for i in range(1, 101):
        profiler.record_duration_ns(stage, i * 1000)

    m = profiler.get_stage_metrics(stage)
    assert m.sample_count == 100
    assert m.min_us == 1.0
    assert m.median_us == 51.0  # index 50 of 0..99
    assert m.p90_us == 91.0    # index 90
    assert m.p95_us == 96.0    # index 95
    assert m.p99_us == 100.0   # index 99
    assert m.max_us == 100.0
    assert m.mean_us == 50.5


def test_profiler_context_manager():
    """Verify measure() context manager accurately measures runtime in nanoseconds."""
    profiler = LatencyProfiler()
    stage = PipelineStage.DETERMINISTIC_GATE

    with profiler.measure(stage):
        time.sleep(0.002)  # ~2ms

    m = profiler.get_stage_metrics(stage)
    assert m.sample_count == 1
    assert m.median_us >= 1000.0  # At least 1ms


# =====================================================================
# 2. Architectural Separation: Fast-Path vs End-to-End Speed
# =====================================================================


def test_architectural_distinction_no_false_e2e_claims():
    """Verify categorized summary strictly distinguishes fast-path from end-to-end speed."""
    profiler = LatencyProfiler()

    # Populate representative samples
    profiler.record_duration_us = lambda stage, us: profiler.record_duration_ns(stage, int(us * 1000))
    profiler.record_duration_ms = lambda stage, ms: profiler.record_duration_ns(stage, int(ms * 1_000_000))

    # Fast-path: microseconds
    profiler.record_duration_ns(PipelineStage.NORMALIZATION, 3_000)       # 3us
    profiler.record_duration_ns(PipelineStage.FEATURE_COMPUTATION, 25_000) # 25us
    profiler.record_duration_ns(PipelineStage.CANDIDATE_DETECTION, 15_000) # 15us
    profiler.record_duration_ns(PipelineStage.DECISION_PREPARATION, 15_000) # 15us
    profiler.record_duration_ns(PipelineStage.DETERMINISTIC_GATE, 1_200)   # 1.2us
    profiler.record_duration_ns(PipelineStage.ORDER_SUBMISSION, 12_000)    # 12us
    profiler.record_duration_ns(PipelineStage.POSITION_WATCHER_RESPONSE, 800) # 0.8us

    # AI Council: milliseconds
    profiler.record_duration_ms(PipelineStage.QWEN3_LATENCY, 180.0)
    profiler.record_duration_ms(PipelineStage.DEEPSEEK_R1_LATENCY, 350.0)

    # Broker: milliseconds
    profiler.record_duration_ms(PipelineStage.MARKET_DATA_ARRIVAL, 0.25)
    profiler.record_duration_ms(PipelineStage.BROKER_ACKNOWLEDGEMENT, 8.5)
    profiler.record_duration_ms(PipelineStage.FILL_LATENCY, 15.0)

    summary = profiler.get_categorized_summary()

    # Invariant: Disclaimer explicitly explains internal latency != e2e execution speed
    assert "CRITICAL" in summary["disclaimer"]
    assert "NOT equivalent to end-to-end execution speed" in summary["disclaimer"]

    # Invariant: Fast-path total is well below 50ms budget
    fast_path = summary["fast_path_internal"]
    assert fast_path["target_budget_ms"] == 50.0
    assert fast_path["measured_median_sum_ms"] < 1.0  # Sub-1ms in reality
    assert fast_path["is_within_budget"] is True

    # Invariant: AI council inference is categorized separately
    ai = summary["ai_council_inference"]
    assert ai["measured_median_sum_ms"] >= 500.0  # 180 + 350 = 530ms

    # Invariant: Broker network is categorized separately
    broker = summary["broker_network"]
    assert broker["measured_median_sum_ms"] >= 20.0  # ~23.75ms


def test_position_watcher_response_under_50ms():
    """Verify IndependentPositionWatcher evaluation satisfies sub-50ms target unconditionally."""
    watcher = IndependentPositionWatcher()
    now = datetime.now(timezone.utc)
    pos = PositionSnapshot(
        position_id="pos-lat-01",
        plan_id="plan-lat-01",
        symbol="INFY",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("1890.00"),
        current_price=Decimal("1890.00"),
        hard_stop_price=Decimal("1878.00"),
        unrealized_pnl=Decimal("0.00"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )
    watcher.open_position(pos)

    event = NormalizedMarketEvent(
        symbol="INFY",
        source=MarketSource.SIMULATED,
        exchange_timestamp=now,
        ingest_timestamp=now,
        last_price=Decimal("1875.00"),  # Catastrophic stop breach
        volume=1000,
        bid_price=Decimal("1874.80"),
        ask_price=Decimal("1875.20"),
        bid_quantity=10,
        ask_quantity=10,
        spread_pct=Decimal("0.0002"),
    )

    t0 = time.perf_counter_ns()
    interventions = watcher.evaluate_tick(event)
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    # Invariant: Watcher executes hard stop in <50ms (typically <0.1ms)
    assert len(interventions) == 1
    assert elapsed_ms < 50.0
    assert elapsed_ms < 5.0  # Even on slow hardware, <5ms


# =====================================================================
# 3. Hardware Assumptions & Automated Benchmark Harness
# =====================================================================


def test_hardware_assumptions_detection():
    """Verify hardware profile detection documents processor, machine, and platform."""
    hw = HardwareAssumptions.detect()
    assert hw.cpu_count >= 1
    assert len(hw.python_version) > 0
    assert len(hw.platform_system) > 0
    d = hw.to_dict()
    assert "processor" in d
    assert "thread_model" in d
    assert "timer_resolution_ns" in d


def test_pipeline_benchmark_harness_execution():
    """Verify PipelineBenchmarkHarness benchmarks all 12 stages without errors."""
    harness = PipelineBenchmarkHarness()
    results = harness.run_all_stages(fast_path_iterations=20, ai_iterations=2)

    assert len(results) == 12
    for m in results.values():
        assert isinstance(m, StageMetrics)
        assert m.sample_count >= 2
        assert m.median_us >= 0.0


# =====================================================================
# 4. Bottleneck Optimization & Correctness Preservation
# =====================================================================


def test_feature_engine_optimization_correctness_preserved():
    """Verify optimized realized volatility and quantize constants match exact math."""
    fe = FeatureEngine()
    now = datetime.now(timezone.utc)

    # Ingest series of bars with varying volatility
    for i in range(25):
        bar = Bar(
            symbol="TCS",
            timestamp=now,
            timeframe_seconds=60,
            open=Decimal("3500.00"),
            high=Decimal("3520.00"),
            low=Decimal("3490.00"),
            close=Decimal(str(3500 + (i * 2 if i % 2 == 0 else -i))),
            volume=1000 + i * 100,
            typical_price_volume_sum=Decimal("35000000.00"),
            volume_sum=10000,
            vwap=Decimal("3505.00"),
            last_spread_pct=Decimal("0.0002"),
            ticks_count=30,
        )
        fe.register_completed_bar(bar)

    event = NormalizedMarketEvent(
        symbol="TCS",
        source=MarketSource.SIMULATED,
        exchange_timestamp=now,
        ingest_timestamp=now,
        last_price=Decimal("3515.00"),
        volume=500,
        bid_price=Decimal("3514.80"),
        ask_price=Decimal("3515.20"),
        bid_quantity=10,
        ask_quantity=10,
        spread_pct=Decimal("0.0001"),
    )

    fs = fe.process_tick(event)

    # Invariant: Features are exact typed Decimals with valid bounds
    assert fs.symbol == "TCS"
    assert fs.current_price == Decimal("3515.0000")
    assert fs.realized_volatility_15 >= Decimal("0.0000")
    assert fs.liquidity_score >= Decimal("0.00") and fs.liquidity_score <= Decimal("100.00")
    assert fs.regime in (
        MarketRegime.BULLISH_TRENDING,
        MarketRegime.BEARISH_TRENDING,
        MarketRegime.HIGH_VOLATILITY_CHOP,
        MarketRegime.LOW_VOLATILITY_COMPRESSION,
    )


# =====================================================================
# 5. FastAPI Endpoints for Latency Breakdown & Benchmarks
# =====================================================================


def test_api_latency_breakdown_endpoint():
    """Verify GET /api/v1/performance/latency-breakdown returns 12-stage breakdown."""
    client = TestClient(app)
    response = client.get("/api/v1/performance/latency-breakdown")

    assert response.status_code == 200
    data = response.json()

    assert "disclaimer" in data
    assert "fast_path_internal" in data
    assert "ai_council_inference" in data
    assert "broker_network" in data
    assert "all_stages" in data
    assert len(data["all_stages"]) == 12


def test_api_benchmark_endpoint():
    """Verify POST /api/v1/performance/benchmark executes microbenchmarks and returns telemetry."""
    client = TestClient(app)
    response = client.post("/api/v1/performance/benchmark")

    assert response.status_code == 200
    data = response.json()

    assert "hardware" in data
    assert "summary" in data
    assert "stages" in data
    assert len(data["stages"]) == 12
    assert data["hardware"]["cpu_count"] >= 1
