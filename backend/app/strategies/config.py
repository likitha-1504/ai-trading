"""Strategy and Candidate Ranker configuration parameters.

Eliminates magic numbers by defining typed, configurable thresholds
for Momentum Continuation, Early-Move Detection, and Candidate Ranking.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class MomentumContinuationConfig(BaseModel):
    """Configuration thresholds for Strategy A: Momentum Continuation."""

    min_rvol: Decimal = Field(
        default=Decimal("1.80"), description="Minimum Relative Volume (10-bar)"
    )
    min_volume_acceleration: Decimal = Field(
        default=Decimal("0.00"), description="Minimum volume acceleration %"
    )
    max_spread_pct: Decimal = Field(
        default=Decimal("0.0015"), description="Max allowable bid-ask spread % (15 bps)"
    )
    min_momentum_score: Decimal = Field(
        default=Decimal("0.10"), description="Minimum 5-bar ROC momentum %"
    )
    target_risk_multiple: Decimal = Field(
        default=Decimal("2.0"), description="Target profit multiple of risk (2R)"
    )
    min_stop_distance_pct: Decimal = Field(
        default=Decimal("0.0050"), description="Minimum stop distance % (0.5%)"
    )
    max_stop_distance_pct: Decimal = Field(
        default=Decimal("0.0150"),
        description="Maximum stop distance % (1.5% equity cap)",
    )


class EarlyMoveDetectionConfig(BaseModel):
    """Configuration thresholds for Strategy B: Early-Move Detection."""

    max_volatility: Decimal = Field(
        default=Decimal("0.35"),
        description="Max realized volatility for compression band",
    )
    min_price_acceleration: Decimal = Field(
        default=Decimal("0.05"), description="Min emerging price acceleration %"
    )
    min_volume_acceleration: Decimal = Field(
        default=Decimal("0.00"), description="Min volume acceleration %"
    )
    min_rvol: Decimal = Field(
        default=Decimal("1.10"),
        description="Minimum Relative Volume to signal early surge",
    )
    max_spread_pct: Decimal = Field(
        default=Decimal("0.0015"), description="Max allowable spread % (15 bps)"
    )
    min_liquidity_score: Decimal = Field(
        default=Decimal("60.0"), description="Minimum composite liquidity score"
    )
    min_sector_strength: Decimal = Field(
        default=Decimal("0.00"),
        description="Minimum sector strength (no lagging sectors)",
    )
    target_risk_multiple: Decimal = Field(
        default=Decimal("2.5"), description="Target profit multiple of risk (2.5R)"
    )
    min_stop_distance_pct: Decimal = Field(
        default=Decimal("0.0040"), description="Minimum stop distance % (0.4%)"
    )
    max_stop_distance_pct: Decimal = Field(
        default=Decimal("0.0150"),
        description="Maximum stop distance % (1.5% equity cap)",
    )


class CandidateRankerConfig(BaseModel):
    """Configuration thresholds for Candidate Ranking and Cooldown deduplication."""

    cooldown_seconds: int = Field(
        default=300, description="Deduplication cooldown window in seconds (5 min)"
    )
    min_rank_score: Decimal = Field(
        default=Decimal("50.00"),
        description="Minimum rank score to qualify as candidate",
    )
    max_candidates_per_evaluation: int = Field(
        default=10, description="Maximum number of candidates returned per cycle"
    )
