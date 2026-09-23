"""Strategy A: Momentum Continuation.

Identifies assets exhibiting established bullish momentum, volume expansion,
and VWAP support while rejecting deteriorating price acceleration or market divergence.
"""

import uuid
from datetime import timezone
from decimal import Decimal

from app.models.contracts import (
    Candidate,
    FeatureSnapshot,
    StrategyType,
    TradeSide,
)
from app.strategies.base import BaseStrategy
from app.strategies.config import MomentumContinuationConfig


class MomentumContinuationStrategy(BaseStrategy):
    """Deterministic Momentum Continuation Strategy."""

    def __init__(self, config: MomentumContinuationConfig | None = None) -> None:
        self.config = config or MomentumContinuationConfig()

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM_CONTINUATION

    def evaluate(self, snapshot: FeatureSnapshot) -> Candidate | None:
        """Evaluate FeatureSnapshot for valid momentum continuation setup.

        Strictly rejects:
        - Price at or below VWAP
        - RVOL < 1.80
        - Non-positive volume acceleration
        - Excessive spread (> 0.15%)
        - Deteriorating momentum (negative score or sharp negative price acceleration)
        - Adverse market index direction (BEARISH)
        - Breakdown price structure (LOWER_LOWS)
        """
        # 1. VWAP condition: price must be strictly above VWAP
        if snapshot.current_price <= snapshot.vwap:
            return None

        # 2. Relative Volume condition: RVOL >= min_rvol (1.80 baseline)
        if snapshot.relative_volume_10 < self.config.min_rvol:
            return None

        # 3. Volume Acceleration condition: positive volume trend
        if snapshot.volume_acceleration <= self.config.min_volume_acceleration:
            return None

        # 4. Spread condition: tight execution spread <= max_spread_pct (15 bps)
        if snapshot.spread_pct > self.config.max_spread_pct:
            return None

        # 5. Momentum score condition: strictly positive momentum
        if snapshot.momentum_score < self.config.min_momentum_score:
            return None

        # 6. Reject deteriorating momentum / deceleration
        if snapshot.price_acceleration < Decimal("-0.50"):
            return None

        # 7. Reject structure breakdown
        if snapshot.price_structure == "LOWER_LOWS":
            return None

        # 8. Market alignment: reject if broad market is BEARISH
        if snapshot.market_index_direction == "BEARISH":
            return None

        # Calculate deterministic stop loss and profit target
        trigger_price = snapshot.current_price
        vwap_dist = (trigger_price - snapshot.vwap) / trigger_price

        # Clamp stop loss distance between min and max risk caps (e.g. 0.5% to 1.5%)
        stop_dist = max(
            self.config.min_stop_distance_pct,
            min(self.config.max_stop_distance_pct, vwap_dist),
        )
        initial_stop_price = (trigger_price * (Decimal(1) - stop_dist)).quantize(
            Decimal("0.0001")
        )
        risk_per_share = trigger_price - initial_stop_price

        suggested_target_price = (
            trigger_price + (risk_per_share * self.config.target_risk_multiple)
        ).quantize(Decimal("0.0001"))

        # Calculate explainable rank score (50.0 to 100.0)
        rank_score = self._compute_rank_score(snapshot)

        # Build candidate ID
        ts_str = snapshot.timestamp.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
        candidate_id = (
            f"cand-mc-{snapshot.symbol.lower()}-{ts_str}-{uuid.uuid4().hex[:6]}"
        )

        quantitative_evidence = {
            "strategy": "MOMENTUM_CONTINUATION",
            "vwap_support": True,
            "vwap": float(snapshot.vwap),
            "vwap_distance_pct": float(snapshot.vwap_distance_pct),
            "rvol_10": float(snapshot.relative_volume_10),
            "volume_acceleration": float(snapshot.volume_acceleration),
            "momentum_score": float(snapshot.momentum_score),
            "price_acceleration": float(snapshot.price_acceleration),
            "spread_pct": float(snapshot.spread_pct),
            "liquidity_score": float(snapshot.liquidity_score),
            "market_index_direction": snapshot.market_index_direction,
            "sector_strength": float(snapshot.sector_strength),
            "risk_per_share": float(risk_per_share),
            "risk_multiple": float(self.config.target_risk_multiple),
            "reasons": [
                f"Price {snapshot.current_price} > VWAP {snapshot.vwap}",
                f"RVOL {snapshot.relative_volume_10:.2f} >= {self.config.min_rvol}",
                f"Volume acceleration {snapshot.volume_acceleration:.2f}% is positive",
                f"Momentum {snapshot.momentum_score:.2f}% confirms strong trend",
                f"Spread {snapshot.spread_pct * 100:.3f}% is within acceptable limit",
            ],
        }

        return Candidate(
            candidate_id=candidate_id,
            detected_at=snapshot.timestamp,
            symbol=snapshot.symbol,
            strategy_type=self.strategy_type,
            side=TradeSide.BUY,
            trigger_price=trigger_price,
            initial_stop_price=initial_stop_price,
            suggested_target_price=suggested_target_price,
            rank_score=rank_score,
            quantitative_evidence=quantitative_evidence,
            feature_snapshot=snapshot,
        )

    def _compute_rank_score(self, snapshot: FeatureSnapshot) -> Decimal:
        """Compute normalized deterministic candidate score [50.0 - 100.0]."""
        base_score = 50.0

        # Momentum bonus: up to 20 pts
        mom_pts = min(20.0, float(snapshot.momentum_score) * 5.0)

        # RVOL bonus: up to 15 pts (excess above 1.80)
        excess_rvol = max(0.0, float(snapshot.relative_volume_10) - 1.80)
        rvol_pts = min(15.0, excess_rvol * 7.5)

        # Liquidity bonus: up to 10 pts
        liq_pts = (float(snapshot.liquidity_score) / 100.0) * 10.0

        # Sector alignment bonus: up to 5 pts
        sector_pts = min(5.0, max(0.0, float(snapshot.sector_strength) * 2.5))

        total = min(
            100.0, max(50.0, base_score + mom_pts + rvol_pts + liq_pts + sector_pts)
        )
        return Decimal(str(round(total, 2)))
