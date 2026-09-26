"""Prompt and Model Configuration Versioning Registry for Phase 28.

Tracks prompt templates, hyperparameters, and cryptographic hashes to guarantee
reproducibility across AI Council iterations without silent prompt drift.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.ai_eval.models import PromptVersionRecord

logger = logging.getLogger(__name__)


def _compute_hash(text: str) -> str:
    """Computes SHA-256 hex digest of prompt text."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


class PromptConfigRegistry:
    """Immutable registry for tracking versioned AI prompt configurations."""

    def __init__(self) -> None:
        self._prompts: Dict[str, PromptVersionRecord] = {}
        self._seed_baseline_prompts()

    def _seed_baseline_prompts(self) -> None:
        """Seeds the standard Phase 20/21 baseline and optimized candidate prompt versions."""
        # 1. Qwen3 Baseline
        qwen_base_text = (
            "You are Qwen3, an expert quantitative intraday trading analyst specializing in Indian NSE equities. "
            "Analyze the provided feature snapshot and return a deterministic JSON thesis containing: "
            "direction (BULLISH/BEARISH/NEUTRAL), confidence (0.0-1.0), and key catalyst rationale."
        )
        p_qwen1 = PromptVersionRecord(
            prompt_id="PRM-QWEN3-V1",
            model_name="qwen2.5:3b",
            version_tag="v1.0.0-baseline",
            created_at=datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc),
            system_prompt_hash=_compute_hash(qwen_base_text),
            temperature=0.1,
            max_tokens=512,
            timeout_seconds=5.0,
            is_active=False,
            change_summary="Initial Phase 20 baseline prompt with JSON output enforcement.",
        )
        self._prompts[p_qwen1.prompt_id] = p_qwen1

        # 2. Qwen3 Macro-Aware (Active)
        qwen_macro_text = (
            "You are Qwen3, primary market analyst. Evaluate the market structure, sector trend, VWAP distance, "
            "and liquidity metrics for the candidate symbol. Formulate a rigorous thesis with directional bias and confidence score."
        )
        p_qwen2 = PromptVersionRecord(
            prompt_id="PRM-QWEN3-V2",
            model_name="qwen2.5:3b",
            version_tag="v1.1.0-macro-aware",
            created_at=datetime(2026, 9, 26, 8, 0, 0, tzinfo=timezone.utc),
            system_prompt_hash=_compute_hash(qwen_macro_text),
            temperature=0.1,
            max_tokens=512,
            timeout_seconds=5.0,
            is_active=True,
            change_summary="Enhanced prompt integrating sector trend alignment and VWAP structure.",
        )
        self._prompts[p_qwen2.prompt_id] = p_qwen2

        # 3. DeepSeek-R1 Baseline
        ds_base_text = (
            "You are DeepSeek-R1, an adversarial risk challenger. Your mission is to find counter-arguments, "
            "detect false breakouts, check for liquidity exhaustion, and protect capital from whipsaws."
        )
        p_ds1 = PromptVersionRecord(
            prompt_id="PRM-DEEPSEEK-V1",
            model_name="deepseek-r1:7b",
            version_tag="v1.0.0-baseline",
            created_at=datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc),
            system_prompt_hash=_compute_hash(ds_base_text),
            temperature=0.2,
            max_tokens=512,
            timeout_seconds=5.0,
            is_active=False,
            change_summary="Initial Phase 20 adversarial challenger prompt.",
        )
        self._prompts[p_ds1.prompt_id] = p_ds1

        # 4. DeepSeek-R1 Fee Drag Vigilant (Active)
        ds_fee_text = (
            "You are DeepSeek-R1, lead adversarial challenger. Examine the candidate trade and Qwen3 thesis for "
            "spread erosion, statutory Indian fee drag (STT, GST, Exchange charges), and false momentum traps. Veto ruthlessly."
        )
        p_ds2 = PromptVersionRecord(
            prompt_id="PRM-DEEPSEEK-V2",
            model_name="deepseek-r1:7b",
            version_tag="v1.1.0-fee-drag-vigilant",
            created_at=datetime(2026, 9, 26, 8, 30, 0, tzinfo=timezone.utc),
            system_prompt_hash=_compute_hash(ds_fee_text),
            temperature=0.2,
            max_tokens=512,
            timeout_seconds=5.0,
            is_active=True,
            change_summary="Upgraded challenger auditing statutory fee drag and penny-stock spread traps.",
        )
        self._prompts[p_ds2.prompt_id] = p_ds2

    def list_prompts(self) -> List[PromptVersionRecord]:
        """Returns all prompt versions sorted chronologically."""
        return sorted(self._prompts.values(), key=lambda p: p.created_at)

    def get_prompt(self, prompt_id: str) -> Optional[PromptVersionRecord]:
        """Retrieves a prompt version record by ID."""
        return self._prompts.get(prompt_id)

    def get_active_prompts(self) -> List[PromptVersionRecord]:
        """Returns currently active prompt configurations for all models."""
        return [p for p in self._prompts.values() if p.is_active]

    def register_prompt_version(self, record: PromptVersionRecord) -> None:
        """Registers a new prompt version immutably."""
        if record.prompt_id in self._prompts:
            raise ValueError(f"Prompt {record.prompt_id} already exists. Prompts are immutable.")
        self._prompts[record.prompt_id] = record
        logger.info(
            "Registered prompt version: id=%s model=%s version=%s",
            record.prompt_id,
            record.model_name,
            record.version_tag,
        )


_prompt_registry_instance: Optional[PromptConfigRegistry] = None


def get_prompt_registry() -> PromptConfigRegistry:
    """Singleton provider for prompt configuration registry."""
    global _prompt_registry_instance
    if _prompt_registry_instance is None:
        _prompt_registry_instance = PromptConfigRegistry()
    return _prompt_registry_instance
