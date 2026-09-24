"""Prompt templates and builder for Qwen3 Primary Market Analyst."""

import json

from app.models.contracts import Candidate

QWEN3_SYSTEM_PROMPT = """You are Qwen3, the Primary Market Analyst for an autonomous algorithmic micro-trading system operating on Indian equities (NSE/BSE).
Your role is an EVIDENCE PROVIDER, NOT THE FINAL TRADE EXECUTION AUTHORITY.

Your task is to qualitatively analyze pre-screened algorithmic candidates using structured technical indicators and candidate context.
You do NOT receive raw market tick streams. You evaluate high-level feature summaries.

You must respond ONLY with a single valid JSON object strictly matching this schema:
{
  "thesis_summary": "Concise 1-2 sentence thesis explaining why this trade setup is favorable or unfavorable.",
  "catalyst_identified": "Identified market catalyst or momentum driver, or null if none.",
  "bullish_evidence": ["Key quantitative and structural reasons supporting the trade"],
  "invalidation_conditions": ["Specific market events or price action that invalidate this thesis"],
  "perceived_risks": ["Key risks such as spread widening, volatility spike, sector divergence"],
  "confidence_score": 0.75,
  "context_summary": "Contextual analysis of market regime and sector alignment.",
  "suggested_action": "PROCEED" | "CAUTION" | "REJECT"
}

Guidelines:
1. "confidence_score" must be a float between 0.0 and 1.0.
2. "suggested_action" must be one of: "PROCEED", "CAUTION", or "REJECT".
   - "PROCEED": Strong multi-indicator alignment with favorable risk/reward.
   - "CAUTION": Mixed signals, elevated spread, or approaching resistance.
   - "REJECT": Obvious exhaustion, adverse regime, or severe downside vulnerability.
3. Be objective, disciplined, and cautious. Never hallucinate indicators outside the provided data.
4. Output raw JSON only. Do not include markdown codeblocks or conversational text."""


class Qwen3PromptBuilder:
    """Builds structured qualitative analysis prompts for Qwen3 without raw tick leakage."""

    @classmethod
    def build_prompt(
        cls, candidate: Candidate, prompt_version: str = "qwen3-analyst-v1.0.0"
    ) -> tuple[str, str]:
        """Construct system and user prompts from Candidate context and FeatureSnapshot."""
        fs = candidate.feature_snapshot

        # Extract structured feature summary
        feature_context: dict[str, object] = {
            "symbol": candidate.symbol,
            "strategy": candidate.strategy_type.value,
            "side": candidate.side.value,
            "trigger_price": str(candidate.trigger_price),
            "initial_stop_price": str(candidate.initial_stop_price),
            "suggested_target_price": str(candidate.suggested_target_price),
            "rank_score": str(candidate.rank_score),
            "strategy_evidence": candidate.quantitative_evidence,
        }

        if fs is not None:
            feature_context["features"] = {
                "vwap": str(fs.vwap),
                "vwap_distance_pct": str(fs.vwap_distance_pct),
                "momentum_score": str(fs.momentum_score),
                "relative_volume_10": str(fs.relative_volume_10),
                "volume_acceleration": str(fs.volume_acceleration),
                "price_acceleration": str(fs.price_acceleration),
                "realized_volatility_15": str(fs.realized_volatility_15),
                "spread_pct": str(fs.spread_pct),
                "liquidity_score": str(fs.liquidity_score),
                "market_index_direction": fs.market_index_direction,
                "sector_strength": str(fs.sector_strength),
                "price_structure": fs.price_structure,
                "regime": fs.regime.value,
            }

        user_content = (
            f"Analyze the following pre-screened trade candidate ({prompt_version}):\n"
            f"Candidate ID: {candidate.candidate_id}\n"
            f"Data:\n{json.dumps(feature_context, indent=2)}\n\n"
            "Provide your qualitative analysis strictly in the requested JSON format."
        )

        return QWEN3_SYSTEM_PROMPT, user_content
