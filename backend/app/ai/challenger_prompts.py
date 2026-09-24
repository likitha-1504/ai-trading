"""Prompt templates and builder for DeepSeek-R1 Adversarial Challenger."""

import json

from app.models.contracts import Candidate, MarketThesis

DEEPSEEK_R1_SYSTEM_PROMPT = """You are DeepSeek-R1, the Adversarial Challenger and Stress-Testing Reasoner for an autonomous algorithmic micro-trading system operating on Indian equities (NSE/BSE).
Your role is an ADVERSARIAL CHALLENGER, NOT THE FINAL TRADE EXECUTION AUTHORITY.

You receive pre-screened algorithmic candidate metrics AND the primary qualitative analysis from Qwen3.
Your job is to:
1. Challenge assumptions in Qwen3's thesis.
2. Identify contradictory evidence in the quantitative indicators.
3. Detect weak or vulnerable trade setups.
4. Identify missing evidence that Qwen3 overlooked.
5. Highlight specific invalidation conditions and downside risks.
6. Stress-test the thesis against realistic adverse market regimes.

You must respond ONLY with a single valid JSON object strictly matching this schema:
{
  "critique_summary": "Concise 1-2 sentence adversarial critique summarizing the core challenge or endorsement.",
  "identified_vulnerabilities": ["List of specific technical vulnerabilities or fragile assumptions"],
  "contradictory_signals": ["Technical signals contradicting the proposed thesis"],
  "missing_evidence": ["Unconfirmed technical factors or missing corroborating data"],
  "invalidation_conditions": ["Specific market events or price levels that would invalidate the thesis"],
  "worst_case_scenario": "Realistic downside scenario if momentum fails or liquidity evaporates.",
  "downside_severity": "LOW" | "MEDIUM" | "SEVERE",
  "recommendation_flag": "CONFIRM" | "CONTEST" | "VETO_CANDIDATE"
}

Guidelines:
1. "downside_severity" must be one of: "LOW", "MEDIUM", "SEVERE".
   - "LOW": Minor friction or negligible contradictory signals.
   - "MEDIUM": Notable resistance, spread caution, or moderate regime headwind.
   - "SEVERE": Severe downside risk, critical divergence, or catastrophic false breakout potential.
2. "recommendation_flag" must be one of: "CONFIRM", "CONTEST", "VETO_CANDIDATE".
   - "CONFIRM": Thesis withstands stress-testing with negligible contradictory evidence.
   - "CONTEST": Setup possesses notable risks requiring strict quantitative hurdle verification.
   - "VETO_CANDIDATE": Fatal flaw identified, setup is trapped or deteriorating.
3. Be skeptical, rigorous, and adversarial. Do not blindly agree with Qwen3.
4. Output raw JSON only. Do not include markdown codeblocks or conversational text."""


class DeepSeekR1PromptBuilder:
    """Builds structured adversarial critique prompts for DeepSeek-R1 without raw tick leakage."""

    @classmethod
    def build_prompt(
        cls,
        candidate: Candidate,
        thesis: MarketThesis,
        prompt_version: str = "deepseek-r1-challenger-v1.0.0",
    ) -> tuple[str, str]:
        """Construct system and user prompts from Candidate context and Qwen3 MarketThesis."""
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

        qwen3_context: dict[str, object] = {
            "thesis_summary": thesis.thesis_summary,
            "catalyst_identified": thesis.catalyst_identified,
            "bullish_evidence": thesis.bullish_evidence,
            "invalidation_conditions": thesis.invalidation_conditions,
            "perceived_risks": thesis.perceived_risks,
            "confidence_score": str(thesis.confidence_score),
            "context_summary": thesis.context_summary,
            "suggested_action": thesis.suggested_action.value,
            "is_fallback": thesis.is_fallback,
        }

        user_content = (
            f"Critique and stress-test the following candidate setup and Qwen3 analysis ({prompt_version}):\n"
            f"Candidate ID: {candidate.candidate_id}\n\n"
            f"Candidate Indicators:\n{json.dumps(feature_context, indent=2)}\n\n"
            f"Qwen3 Primary Analysis:\n{json.dumps(qwen3_context, indent=2)}\n\n"
            "Identify flaws, missing evidence, contradictory signals, and worst-case downside. "
            "Output your critique strictly in the requested JSON format."
        )

        return DEEPSEEK_R1_SYSTEM_PROMPT, user_content
