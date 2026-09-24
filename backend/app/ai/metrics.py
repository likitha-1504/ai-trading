"""Token and latency telemetry tracking for AI Analyst invocations."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AIAnalystMetrics:
    """Telemetry collector for Qwen3 AI Analyst invocations, errors, and latencies."""

    total_requests: int = 0
    successful_analyses: int = 0
    failed_requests: int = 0
    timeout_count: int = 0
    malformed_output_count: int = 0
    fallback_count: int = 0
    total_tokens_consumed: int = 0
    _latencies_ms: list[int] = field(default_factory=list)

    def record_success(self, latency_ms: int, token_count: int | None = None) -> None:
        """Record a successful model inference and parsing cycle."""
        self.total_requests += 1
        self.successful_analyses += 1
        self._latencies_ms.append(latency_ms)
        if token_count:
            self.total_tokens_consumed += token_count

    def record_timeout(self, latency_ms: int) -> None:
        """Record a request timeout."""
        self.total_requests += 1
        self.timeout_count += 1
        self.failed_requests += 1
        self._latencies_ms.append(latency_ms)

    def record_malformed(self, latency_ms: int) -> None:
        """Record a response that failed JSON schema validation."""
        self.total_requests += 1
        self.malformed_output_count += 1
        self.failed_requests += 1
        self._latencies_ms.append(latency_ms)

    def record_failure(self, latency_ms: int) -> None:
        """Record a network or server HTTP failure."""
        self.total_requests += 1
        self.failed_requests += 1
        self._latencies_ms.append(latency_ms)

    def record_fallback(self) -> None:
        """Increment fallback thesis generation count."""
        self.fallback_count += 1

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if not self._latencies_ms:
            return 0.0
        return round(sum(self._latencies_ms) / len(self._latencies_ms), 2)

    @property
    def p95_latency_ms(self) -> int:
        """Calculate 95th percentile latency in milliseconds."""
        if not self._latencies_ms:
            return 0
        sorted_lat = sorted(self._latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def get_summary(self) -> dict[str, Any]:
        """Produce a dictionary snapshot of AI analyst telemetry."""
        success_rate = (
            round((self.successful_analyses / self.total_requests) * 100, 2)
            if self.total_requests > 0
            else 0.0
        )
        return {
            "total_requests": self.total_requests,
            "successful_analyses": self.successful_analyses,
            "failed_requests": self.failed_requests,
            "timeout_count": self.timeout_count,
            "malformed_output_count": self.malformed_output_count,
            "fallback_count": self.fallback_count,
            "total_tokens_consumed": self.total_tokens_consumed,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "success_rate_pct": success_rate,
        }

    def reset(self) -> None:
        """Reset all metric counters."""
        self.total_requests = 0
        self.successful_analyses = 0
        self.failed_requests = 0
        self.timeout_count = 0
        self.malformed_output_count = 0
        self.fallback_count = 0
        self.total_tokens_consumed = 0
        self._latencies_ms.clear()
