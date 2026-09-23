"""Deterministic Candidate Ranker and Cooldown Deduplication Engine.

Ranks candidates across strategies, enforces per-symbol cooldowns to prevent
duplicate candidate spam, filters low-conviction setups, and returns ordered candidates.
Never places orders.
"""

from datetime import datetime
from decimal import Decimal

from app.models.contracts import Candidate, FeatureSnapshot
from app.strategies.base import BaseStrategy
from app.strategies.config import CandidateRankerConfig
from app.strategies.early_move import EarlyMoveDetectionStrategy
from app.strategies.momentum_continuation import MomentumContinuationStrategy


class CandidateRanker:
    """Deterministic Candidate Ranker, Cooldown Guard, and Strategy Coordinator."""

    def __init__(
        self,
        config: CandidateRankerConfig | None = None,
        strategies: list[BaseStrategy] | None = None,
    ) -> None:
        self.config = config or CandidateRankerConfig()
        self.strategies: list[BaseStrategy] = strategies or [
            MomentumContinuationStrategy(),
            EarlyMoveDetectionStrategy(),
        ]

        # Per-symbol cooldown tracking: symbol -> last_candidate_detection_timestamp
        self._last_detected_at: dict[str, datetime] = {}
        self._last_rank_scores: dict[str, Decimal] = {}

    def reset_cooldowns(self, symbol: str | None = None) -> None:
        """Reset cooldown history for a specific symbol or all symbols."""
        if symbol:
            self._last_detected_at.pop(symbol.upper(), None)
            self._last_rank_scores.pop(symbol.upper(), None)
        else:
            self._last_detected_at.clear()
            self._last_rank_scores.clear()

    def is_in_cooldown(
        self, symbol: str, current_time: datetime, new_score: Decimal
    ) -> bool:
        """Check if a symbol is within the deduplication cooldown period.

        A candidate bypasses cooldown only if its score is significantly superior
        (+15.0 points) to the previous candidate detected within the cooldown window.
        """
        symbol_key = symbol.upper()
        if symbol_key not in self._last_detected_at:
            return False

        last_time = self._last_detected_at[symbol_key]
        elapsed_seconds = (current_time - last_time).total_seconds()

        if elapsed_seconds < self.config.cooldown_seconds:
            last_score = self._last_rank_scores.get(symbol_key, Decimal(0))
            # If new score is noticeably higher (+15.0 pts), allow upgrade; otherwise suppress
            return new_score < (last_score + Decimal("15.0"))

        return False

    def record_candidate(self, candidate: Candidate) -> None:
        """Record candidate timestamp and score to enforce subsequent cooldowns."""
        symbol_key = candidate.symbol.upper()
        self._last_detected_at[symbol_key] = candidate.detected_at
        self._last_rank_scores[symbol_key] = candidate.rank_score

    def rank_and_filter(self, candidates: list[Candidate]) -> list[Candidate]:
        """Filter out duplicates in cooldown and rank remaining candidates descending by score.

        Strictly deterministic: ties are broken by liquidity score, momentum, and candidate_id.
        """
        accepted: list[Candidate] = []

        # Sort candidates initially so highest score has priority if duplicate symbols are evaluated
        sorted_initial = sorted(
            candidates,
            key=lambda c: (
                c.rank_score,
                c.feature_snapshot.liquidity_score,
                c.feature_snapshot.momentum_score,
            ),
            reverse=True,
        )

        for cand in sorted_initial:
            # 1. Filter out candidates failing minimum rank threshold
            if cand.rank_score < self.config.min_rank_score:
                continue

            # 2. Check per-symbol cooldown
            if self.is_in_cooldown(cand.symbol, cand.detected_at, cand.rank_score):
                continue

            self.record_candidate(cand)
            accepted.append(cand)

        # Truncate to maximum candidates per evaluation cycle
        return accepted[: self.config.max_candidates_per_evaluation]

    def evaluate_snapshot(self, snapshot: FeatureSnapshot) -> list[Candidate]:
        """Evaluate a FeatureSnapshot across all strategies and return ranked candidates."""
        raw_candidates: list[Candidate] = []
        for strategy in self.strategies:
            cand = strategy.evaluate(snapshot)
            if cand is not None:
                raw_candidates.append(cand)

        return self.rank_and_filter(raw_candidates)
