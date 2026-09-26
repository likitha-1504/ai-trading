"""Order Timing and Scheduling Optimizer for Phase 32.

Recommends execution urgency and order type based on intraday market session regimes
and candidate momentum characteristics:
- OPENING_AUCTION_RUSH (09:15 - 09:45): Elevated volatility, prefer PASSIVE_PEG
- MORNING_TREND (09:45 - 11:30): High liquidity, optimal for AGGRESSIVE / PASSIVE
- MIDDAY_CONSOLIDATION (11:30 - 13:30): Thin book, prefer LIQUIDITY_SEEKING / sliced
- AFTERNOON_SESSION (13:30 - 15:00): Strong flow, AGGRESSIVE permitted
- INTRADAY_CUTOFF_RISK (15:00 - 15:30): No new positions admitted
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime, timezone
from decimal import Decimal

from app.execution_opt.models import ExecutionUrgency, TimeOfDayRegime
from app.models.contracts import StrategyType


class OrderScheduler:
    """Evaluates optimal execution timing and order urgency."""

    @classmethod
    def classify_time_of_day(cls, timestamp: datetime | None = None) -> TimeOfDayRegime:
        """Classifies IST market hour regime from UTC or local timestamp."""
        now_utc = timestamp or datetime.now(timezone.utc)
        # Convert UTC to IST (+5:30)
        ist_time = now_utc + dt.timedelta(hours=5, minutes=30)
        t = ist_time.time()

        if t < dt.time(9, 45):
            return TimeOfDayRegime.OPENING_AUCTION_RUSH
        elif t < dt.time(11, 30):
            return TimeOfDayRegime.MORNING_TREND
        elif t < dt.time(13, 30):
            return TimeOfDayRegime.MIDDAY_CONSOLIDATION
        elif t < dt.time(15, 0):
            return TimeOfDayRegime.AFTERNOON_SESSION
        else:
            return TimeOfDayRegime.INTRADAY_CUTOFF_RISK

    @classmethod
    def schedule_execution(
        cls,
        strategy_type: StrategyType,
        rank_score: Decimal,
        spread_pct: Decimal,
        volume_participation_pct: Decimal,
        timestamp: datetime | None = None,
    ) -> tuple[ExecutionUrgency, str, str]:
        """Determines execution urgency, order type (LIMIT vs MARKET), and guidance rationale.

        Args:
            strategy_type: Strategy producing the candidate.
            rank_score: 0-100 rank score from CandidateRanker.
            spread_pct: Current bid-ask spread percentage.
            volume_participation_pct: Order size / bar volume %.
            timestamp: Execution timestamp.

        Returns:
            Tuple of (ExecutionUrgency, order_type_str, rationale).
        """
        regime = cls.classify_time_of_day(timestamp)

        # 1. Cutoff Risk: Prohibit new entries
        if regime == TimeOfDayRegime.INTRADAY_CUTOFF_RISK:
            return (
                ExecutionUrgency.PASSIVE_PEG,
                "REJECT",
                "Execution prohibited during 15:00-15:30 IST square-off window.",
            )

        # 2. Large relative volume: LIQUIDITY_SEEKING
        if volume_participation_pct > Decimal("1.50"):
            return (
                ExecutionUrgency.LIQUIDITY_SEEKING,
                "LIMIT",
                f"High volume participation ({volume_participation_pct}% > 1.5%): liquidity-seeking limit slicing recommended.",
            )

        # 3. High Conviction Momentum Breakout in Active Session: AGGRESSIVE
        if (
            strategy_type == StrategyType.MOMENTUM_CONTINUATION
            and rank_score >= Decimal("85.00")
            and spread_pct <= Decimal("0.0300")
            and regime in (TimeOfDayRegime.MORNING_TREND, TimeOfDayRegime.AFTERNOON_SESSION)
        ):
            return (
                ExecutionUrgency.AGGRESSIVE,
                "MARKET",
                "High conviction momentum setup with tight spread: aggressive market execution recommended.",
            )

        # 4. Standard Default: PASSIVE_PEG at touch to earn half-spread
        return (
            ExecutionUrgency.PASSIVE_PEG,
            "LIMIT",
            f"Passive pegging at best quote recommended to capture half-spread during {regime.value}.",
        )
