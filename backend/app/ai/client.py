"""Qwen3 Primary Market Analyst client implementation."""

import asyncio
import logging
import time

import httpx

from app.ai.config import Qwen3Config
from app.ai.metrics import AIAnalystMetrics
from app.ai.prompts import Qwen3PromptBuilder
from app.ai.validator import MalformedAIOutputError, Qwen3OutputValidator
from app.models.contracts import Candidate, MarketThesis

logger = logging.getLogger(__name__)


class Qwen3AnalystClient:
    """Client for interfacing with local Qwen3 model via Ollama with robust resilience."""

    def __init__(
        self,
        config: Qwen3Config | None = None,
        http_client: httpx.AsyncClient | None = None,
        sync_http_client: httpx.Client | None = None,
        metrics: AIAnalystMetrics | None = None,
    ) -> None:
        self.config = config or Qwen3Config()
        self._async_client = http_client
        self._sync_client = sync_http_client
        self.metrics = metrics or AIAnalystMetrics()

    async def analyze_candidate(self, candidate: Candidate) -> MarketThesis:
        """Asynchronously analyze candidate indicators and produce validated MarketThesis.

        Resilience guarantees:
        - Strict timeout per attempt
        - Exponential backoff retry policy for transient network drops / timeouts
        - Model unavailable fallback
        - Malformed output handling with safe fallback
        - Never raises uncaught exception to caller
        """
        start_time = time.perf_counter()
        system_prompt, user_prompt = Qwen3PromptBuilder.build_prompt(
            candidate=candidate, prompt_version=self.config.prompt_version
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
                        "Dispatching Qwen3 analysis for %s (attempt %d/%d)",
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
                    thesis = Qwen3OutputValidator.validate_and_parse(
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
                        "Qwen3 analysis completed for %s in %dms (Action: %s, Confidence: %s)",
                        candidate.symbol,
                        latency_ms,
                        thesis.suggested_action.value,
                        thesis.confidence_score,
                    )
                    return thesis

                except MalformedAIOutputError as e:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self.metrics.record_malformed(latency_ms)
                    self.metrics.record_fallback()
                    logger.warning("Qwen3 produced malformed output for %s: %s", candidate.candidate_id, e)
                    return Qwen3OutputValidator.create_fallback_thesis(
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
                        "Qwen3 request timed out on attempt %d for %s: %s",
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
                        "Qwen3 connection error on attempt %d for %s: %s",
                        attempt + 1,
                        candidate.candidate_id,
                        e,
                    )
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_backoff_seconds * (2**attempt))
                        continue

                except Exception as e:
                    last_error_reason = f"Unexpected error ({type(e).__name__}: {e})"
                    logger.exception("Unexpected error in Qwen3 client")
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
        return Qwen3OutputValidator.create_fallback_thesis(
            candidate_id=candidate.candidate_id,
            reason=f"Model unavailable or exhausted retries: {last_error_reason}",
            latency_ms=latency_ms,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
        )

    def analyze_candidate_sync(self, candidate: Candidate) -> MarketThesis:
        """Synchronously analyze candidate indicators and produce validated MarketThesis."""
        start_time = time.perf_counter()
        system_prompt, user_prompt = Qwen3PromptBuilder.build_prompt(
            candidate=candidate, prompt_version=self.config.prompt_version
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

                    thesis = Qwen3OutputValidator.validate_and_parse(
                        raw_output=raw_text,
                        candidate_id=candidate.candidate_id,
                        latency_ms=latency_ms,
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        prompt_version=self.config.prompt_version,
                        token_count=token_count if token_count > 0 else None,
                    )

                    self.metrics.record_success(latency_ms, token_count)
                    return thesis

                except MalformedAIOutputError as e:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self.metrics.record_malformed(latency_ms)
                    self.metrics.record_fallback()
                    return Qwen3OutputValidator.create_fallback_thesis(
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
                    logger.exception("Unexpected error in Qwen3 client sync")
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
        return Qwen3OutputValidator.create_fallback_thesis(
            candidate_id=candidate.candidate_id,
            reason=f"Model unavailable or exhausted retries: {last_error_reason}",
            latency_ms=latency_ms,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
        )
