"""DeepSeek-R1 Adversarial Challenger client implementation."""

import asyncio
import logging
import time

import httpx

from app.ai.challenger_config import DeepSeekR1Config
from app.ai.challenger_prompts import DeepSeekR1PromptBuilder
from app.ai.challenger_validator import (
    DeepSeekR1OutputValidator,
    MalformedChallengerOutputError,
)
from app.ai.metrics import AIAnalystMetrics
from app.models.contracts import Candidate, ChallengerCritique, MarketThesis

logger = logging.getLogger(__name__)


class DeepSeekR1ChallengerClient:
    """Client for interfacing with local DeepSeek-R1 model via Ollama with robust resilience."""

    def __init__(
        self,
        config: DeepSeekR1Config | None = None,
        http_client: httpx.AsyncClient | None = None,
        sync_http_client: httpx.Client | None = None,
        metrics: AIAnalystMetrics | None = None,
    ) -> None:
        self.config = config or DeepSeekR1Config()
        self._async_client = http_client
        self._sync_client = sync_http_client
        self.metrics = metrics or AIAnalystMetrics()

    async def critique_candidate(
        self, candidate: Candidate, thesis: MarketThesis
    ) -> ChallengerCritique:
        """Asynchronously stress-test candidate indicators and Qwen3 thesis with DeepSeek-R1.

        Resilience guarantees:
        - Strict timeout per attempt
        - Exponential backoff retry policy for transient network drops / timeouts
        - Model unavailable fallback
        - Malformed output handling with safe fallback
        - Never raises uncaught exception to caller
        """
        start_time = time.perf_counter()
        system_prompt, user_prompt = DeepSeekR1PromptBuilder.build_prompt(
            candidate=candidate,
            thesis=thesis,
            prompt_version=self.config.prompt_version,
        )

        payload = {
            "model": self.config.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": self.config.format,
            "options": {
                "temperature": self.config.temperature,
            },
        }

        # Client lifecycle management
        client = self._async_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds)
        )
        should_close = self._async_client is None
        last_error_reason = "Unknown error"

        try:
            for attempt in range(self.config.max_retries + 1):
                try:
                    logger.debug(
                        "Dispatching DeepSeek-R1 critique for %s (attempt %d/%d)",
                        candidate.candidate_id,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )

                    response = await client.post(self.config.endpoint, json=payload)
                    response.raise_for_status()

                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    resp_json = response.json()
                    raw_text = resp_json.get("response", "")

                    # Extract token metadata from Ollama response
                    token_count = resp_json.get("eval_count", 0) + resp_json.get("prompt_eval_count", 0)

                    # Deterministic Schema Validation
                    critique = DeepSeekR1OutputValidator.validate_and_parse(
                        raw_output=raw_text,
                        candidate_id=candidate.candidate_id,
                        latency_ms=latency_ms,
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        prompt_version=self.config.prompt_version,
                        token_count=token_count if token_count > 0 else None,
                    )

                    self.metrics.record_success(latency_ms, token_count)
                    logger.info(
                        "DeepSeek-R1 critique completed for %s in %dms (Recommendation: %s, Severity: %s)",
                        candidate.symbol,
                        latency_ms,
                        critique.recommendation_flag.value,
                        critique.downside_severity.value,
                    )
                    return critique

                except MalformedChallengerOutputError as e:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self.metrics.record_malformed(latency_ms)
                    self.metrics.record_fallback()
                    logger.warning(
                        "DeepSeek-R1 produced malformed output for %s: %s",
                        candidate.candidate_id,
                        e,
                    )
                    return DeepSeekR1OutputValidator.create_fallback_critique(
                        candidate_id=candidate.candidate_id,
                        reason=f"Malformed output schema: {e}",
                        latency_ms=latency_ms,
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        prompt_version=self.config.prompt_version,
                        raw_output=locals().get("raw_text"),
                    )

                except httpx.TimeoutException as e:
                    last_error_reason = f"Timeout after {self.config.timeout_seconds}s"
                    logger.warning(
                        "DeepSeek-R1 request timed out on attempt %d for %s: %s",
                        attempt + 1,
                        candidate.candidate_id,
                        e,
                    )
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_backoff_seconds * (2**attempt))
                        continue

                except (httpx.ConnectError, httpx.HTTPStatusError, httpx.RequestError) as e:
                    last_error_reason = f"Service unavailable ({type(e).__name__}: {e})"
                    logger.warning(
                        "DeepSeek-R1 connection error on attempt %d for %s: %s",
                        attempt + 1,
                        candidate.candidate_id,
                        e,
                    )
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_backoff_seconds * (2**attempt))
                        continue

                except Exception as e:
                    last_error_reason = f"Unexpected error ({type(e).__name__}: {e})"
                    logger.exception("Unexpected error in DeepSeek-R1 client")
                    break

        finally:
            if should_close:
                await client.aclose()

        # Retries exhausted or unrecoverable error: produce deterministic safe fallback
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        if "Timeout" in last_error_reason:
            self.metrics.record_timeout(latency_ms)
        else:
            self.metrics.record_failure(latency_ms)

        self.metrics.record_fallback()
        return DeepSeekR1OutputValidator.create_fallback_critique(
            candidate_id=candidate.candidate_id,
            reason=f"Challenger unavailable or exhausted retries: {last_error_reason}",
            latency_ms=latency_ms,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
        )

    def critique_candidate_sync(
        self, candidate: Candidate, thesis: MarketThesis
    ) -> ChallengerCritique:
        """Synchronously stress-test candidate indicators and Qwen3 thesis with DeepSeek-R1."""
        start_time = time.perf_counter()
        system_prompt, user_prompt = DeepSeekR1PromptBuilder.build_prompt(
            candidate=candidate,
            thesis=thesis,
            prompt_version=self.config.prompt_version,
        )

        payload = {
            "model": self.config.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": self.config.format,
            "options": {
                "temperature": self.config.temperature,
            },
        }

        client = self._sync_client or httpx.Client(
            timeout=httpx.Timeout(self.config.timeout_seconds)
        )
        should_close = self._sync_client is None
        last_error_reason = "Unknown error"

        try:
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = client.post(self.config.endpoint, json=payload)
                    response.raise_for_status()

                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    resp_json = response.json()
                    raw_text = resp_json.get("response", "")
                    token_count = resp_json.get("eval_count", 0) + resp_json.get("prompt_eval_count", 0)

                    critique = DeepSeekR1OutputValidator.validate_and_parse(
                        raw_output=raw_text,
                        candidate_id=candidate.candidate_id,
                        latency_ms=latency_ms,
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        prompt_version=self.config.prompt_version,
                        token_count=token_count if token_count > 0 else None,
                    )

                    self.metrics.record_success(latency_ms, token_count)
                    return critique

                except MalformedChallengerOutputError as e:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self.metrics.record_malformed(latency_ms)
                    self.metrics.record_fallback()
                    return DeepSeekR1OutputValidator.create_fallback_critique(
                        candidate_id=candidate.candidate_id,
                        reason=f"Malformed output schema: {e}",
                        latency_ms=latency_ms,
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        prompt_version=self.config.prompt_version,
                        raw_output=locals().get("raw_text"),
                    )

                except httpx.TimeoutException:
                    last_error_reason = f"Timeout after {self.config.timeout_seconds}s"
                    if attempt < self.config.max_retries:
                        time.sleep(self.config.retry_backoff_seconds * (2**attempt))
                        continue

                except (httpx.ConnectError, httpx.HTTPStatusError, httpx.RequestError) as e:
                    last_error_reason = f"Service unavailable ({type(e).__name__}: {e})"
                    if attempt < self.config.max_retries:
                        time.sleep(self.config.retry_backoff_seconds * (2**attempt))
                        continue

                except Exception as e:
                    last_error_reason = f"Unexpected error ({type(e).__name__}: {e})"
                    logger.exception("Unexpected error in DeepSeek-R1 client sync")
                    break

        finally:
            if should_close:
                client.close()

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        if "Timeout" in last_error_reason:
            self.metrics.record_timeout(latency_ms)
        else:
            self.metrics.record_failure(latency_ms)

        self.metrics.record_fallback()
        return DeepSeekR1OutputValidator.create_fallback_critique(
            candidate_id=candidate.candidate_id,
            reason=f"Challenger unavailable or exhausted retries: {last_error_reason}",
            latency_ms=latency_ms,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
        )
