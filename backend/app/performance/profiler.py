"""High-precision pipeline latency profiling and instrumentation.

Measures all 12 distinct pipeline stages mandated by Phase 17:
1. market data arrival
2. normalization
3. feature computation
4. candidate detection
5. decision preparation
6. Qwen3 latency
7. DeepSeek-R1 latency
8. deterministic gate latency
9. order submission
10. broker acknowledgement
11. fill latency
12. Position Watcher response

CRITICAL ARCHITECTURAL DISTINCTION:
Internal synchronous fast-path latency (<50ms target for position safety) MUST NOT
be claimed as equivalent to end-to-end execution speed, which includes external
socket transit, exchange matching engine delay, and asynchronous LLM inference.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """The 12 individual stages measured across the trading pipeline."""

    MARKET_DATA_ARRIVAL = "market_data_arrival"
    NORMALIZATION = "normalization"
    FEATURE_COMPUTATION = "feature_computation"
    CANDIDATE_DETECTION = "candidate_detection"
    DECISION_PREPARATION = "decision_preparation"
    QWEN3_LATENCY = "qwen3_latency"
    DEEPSEEK_R1_LATENCY = "deepseek_r1_latency"
    DETERMINISTIC_GATE = "deterministic_gate"
    ORDER_SUBMISSION = "order_submission"
    BROKER_ACKNOWLEDGEMENT = "broker_acknowledgement"
    FILL_LATENCY = "fill_latency"
    POSITION_WATCHER_RESPONSE = "position_watcher_response"


class LatencyCategory(str, Enum):
    """Domain grouping for distinct latency regimes."""

    FAST_PATH_INTERNAL = "fast_path_internal"  # Synchronous CPU-bound in-memory safety loops (<50ms budget)
    AI_COUNCIL_INFERENCE = "ai_council_inference"  # Asynchronous Ollama LLM queries (~100ms - 2500ms)
    BROKER_NETWORK = "broker_network"  # External transit and broker matching engine (~5ms - 50ms)


STAGE_CATEGORY_MAP: dict[PipelineStage, LatencyCategory] = {
    PipelineStage.MARKET_DATA_ARRIVAL: LatencyCategory.BROKER_NETWORK,
    PipelineStage.NORMALIZATION: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.FEATURE_COMPUTATION: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.CANDIDATE_DETECTION: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.DECISION_PREPARATION: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.QWEN3_LATENCY: LatencyCategory.AI_COUNCIL_INFERENCE,
    PipelineStage.DEEPSEEK_R1_LATENCY: LatencyCategory.AI_COUNCIL_INFERENCE,
    PipelineStage.DETERMINISTIC_GATE: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.ORDER_SUBMISSION: LatencyCategory.FAST_PATH_INTERNAL,
    PipelineStage.BROKER_ACKNOWLEDGEMENT: LatencyCategory.BROKER_NETWORK,
    PipelineStage.FILL_LATENCY: LatencyCategory.BROKER_NETWORK,
    PipelineStage.POSITION_WATCHER_RESPONSE: LatencyCategory.FAST_PATH_INTERNAL,
}


@dataclass
class StageMetrics:
    """Comprehensive statistical distribution for a single pipeline stage."""

    stage: str
    category: str
    sample_count: int
    min_us: float
    median_us: float  # p50
    p90_us: float
    p95_us: float
    p99_us: float
    max_us: float
    mean_us: float
    total_duration_us: float

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to serializable dictionary format."""
        return {
            "stage": self.stage,
            "category": self.category,
            "sample_count": self.sample_count,
            "min_us": round(self.min_us, 2),
            "median_us": round(self.median_us, 2),
            "p90_us": round(self.p90_us, 2),
            "p95_us": round(self.p95_us, 2),
            "p99_us": round(self.p99_us, 2),
            "max_us": round(self.max_us, 2),
            "mean_us": round(self.mean_us, 2),
            "min_ms": round(self.min_us / 1000.0, 4),
            "median_ms": round(self.median_us / 1000.0, 4),
            "p95_ms": round(self.p95_us / 1000.0, 4),
            "max_ms": round(self.max_us / 1000.0, 4),
        }


class LatencyProfiler:
    """Thread-safe, microsecond-precision profiler for trading pipeline stages."""

    def __init__(self, max_samples_per_stage: int = 10_000) -> None:
        self.max_samples_per_stage = max_samples_per_stage
        self._lock = threading.Lock()
        # stage -> list of durations in nanoseconds
        self._samples: dict[PipelineStage, list[int]] = defaultdict(list)

    def record_duration_ns(self, stage: PipelineStage, duration_ns: int) -> None:
        """Record an explicit elapsed duration in nanoseconds."""
        with self._lock:
            sample_list = self._samples[stage]
            if len(sample_list) >= self.max_samples_per_stage:
                # Evict oldest sample to bound memory
                sample_list.pop(0)
            sample_list.append(max(0, duration_ns))

    def record_duration_ms(self, stage: PipelineStage, duration_ms: float) -> None:
        """Record an elapsed duration in milliseconds."""
        self.record_duration_ns(stage, int(duration_ms * 1_000_000))

    @contextmanager
    def measure(self, stage: PipelineStage):
        """Context manager to measure execution time of a code block with nanosecond clock."""
        start_ns = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_ns = time.perf_counter_ns() - start_ns
            self.record_duration_ns(stage, elapsed_ns)

    def timed(self, stage: PipelineStage) -> Callable:
        """Decorator to instrument any synchronous function or method."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_ns = time.perf_counter_ns()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed_ns = time.perf_counter_ns() - start_ns
                    self.record_duration_ns(stage, elapsed_ns)
            return wrapper
        return decorator

    def get_stage_metrics(self, stage: PipelineStage) -> StageMetrics:
        """Compute statistical percentiles for a single pipeline stage."""
        with self._lock:
            raw_ns = list(self._samples.get(stage, []))

        category = STAGE_CATEGORY_MAP.get(stage, LatencyCategory.FAST_PATH_INTERNAL).value

        if not raw_ns:
            return StageMetrics(
                stage=stage.value,
                category=category,
                sample_count=0,
                min_us=0.0,
                median_us=0.0,
                p90_us=0.0,
                p95_us=0.0,
                p99_us=0.0,
                max_us=0.0,
                mean_us=0.0,
                total_duration_us=0.0,
            )

        # Convert ns to us
        us_samples = sorted(d / 1000.0 for d in raw_ns)
        count = len(us_samples)
        total_us = sum(us_samples)

        p50 = us_samples[int(count * 0.50)]
        p90 = us_samples[int(count * 0.90)] if count >= 10 else us_samples[-1]
        p95 = us_samples[int(count * 0.95)] if count >= 20 else us_samples[-1]
        p99 = us_samples[int(count * 0.99)] if count >= 100 else us_samples[-1]

        return StageMetrics(
            stage=stage.value,
            category=category,
            sample_count=count,
            min_us=us_samples[0],
            median_us=p50,
            p90_us=p90,
            p95_us=p95,
            p99_us=p99,
            max_us=us_samples[-1],
            mean_us=total_us / count,
            total_duration_us=total_us,
        )

    def get_all_stage_metrics(self) -> dict[str, StageMetrics]:
        """Compute statistical breakdown across all 12 pipeline stages."""
        result: dict[str, StageMetrics] = {}
        for stage in PipelineStage:
            result[stage.value] = self.get_stage_metrics(stage)
        return result

    def get_categorized_summary(self) -> dict[str, Any]:
        """Return categorized latency metrics with explicit architectural disclaimers."""
        metrics = self.get_all_stage_metrics()

        # Fast-Path Synchronous Core (Internal Target <= 50,000 us / 50ms)
        fast_path_stages = [
            PipelineStage.NORMALIZATION.value,
            PipelineStage.FEATURE_COMPUTATION.value,
            PipelineStage.CANDIDATE_DETECTION.value,
            PipelineStage.DECISION_PREPARATION.value,
            PipelineStage.DETERMINISTIC_GATE.value,
            PipelineStage.ORDER_SUBMISSION.value,
            PipelineStage.POSITION_WATCHER_RESPONSE.value,
        ]
        fast_path_median_sum_us = sum(metrics[s].median_us for s in fast_path_stages)
        fast_path_p95_sum_us = sum(metrics[s].p95_us for s in fast_path_stages)

        # AI Council (Ollama Qualitative Inference)
        ai_stages = [
            PipelineStage.QWEN3_LATENCY.value,
            PipelineStage.DEEPSEEK_R1_LATENCY.value,
        ]
        ai_median_sum_ms = sum(metrics[s].median_us / 1000.0 for s in ai_stages)
        ai_p95_sum_ms = sum(metrics[s].p95_us / 1000.0 for s in ai_stages)

        # Broker & Network Transit
        broker_stages = [
            PipelineStage.MARKET_DATA_ARRIVAL.value,
            PipelineStage.BROKER_ACKNOWLEDGEMENT.value,
            PipelineStage.FILL_LATENCY.value,
        ]
        broker_median_sum_ms = sum(metrics[s].median_us / 1000.0 for s in broker_stages)

        return {
            "disclaimer": (
                "CRITICAL: Internal fast-path latency (<50ms target) measures synchronous in-memory "
                "risk checks and position watcher operations. It is NOT equivalent to end-to-end execution "
                "speed, which additionally includes asynchronous AI Council inference (~100-2500ms) and "
                "external broker/exchange network round trips (~5-50ms)."
            ),
            "fast_path_internal": {
                "description": "Deterministic in-memory fast-path (Target <= 50ms / 50,000us)",
                "target_budget_ms": 50.0,
                "measured_median_sum_us": round(fast_path_median_sum_us, 2),
                "measured_median_sum_ms": round(fast_path_median_sum_us / 1000.0, 4),
                "measured_p95_sum_ms": round(fast_path_p95_sum_us / 1000.0, 4),
                "is_within_budget": (fast_path_p95_sum_us / 1000.0) <= 50.0,
                "stages": {s: metrics[s].to_dict() for s in fast_path_stages},
            },
            "ai_council_inference": {
                "description": "Asynchronous dual-model qualitative analysis (Ollama local inference)",
                "measured_median_sum_ms": round(ai_median_sum_ms, 2),
                "measured_p95_sum_ms": round(ai_p95_sum_ms, 2),
                "stages": {s: metrics[s].to_dict() for s in ai_stages},
            },
            "broker_network": {
                "description": "External market data arrival and broker matching engine transit",
                "measured_median_sum_ms": round(broker_median_sum_ms, 2),
                "stages": {s: metrics[s].to_dict() for s in broker_stages},
            },
            "all_stages": {name: m.to_dict() for name, m in metrics.items()},
        }

    def reset(self) -> None:
        """Clear all accumulated samples."""
        with self._lock:
            self._samples.clear()


# Global profiler singleton
_GLOBAL_PROFILER = LatencyProfiler()


def get_pipeline_profiler() -> LatencyProfiler:
    """Retrieve the application-wide pipeline latency profiler instance."""
    return _GLOBAL_PROFILER
