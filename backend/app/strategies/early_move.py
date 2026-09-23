"""Strategy B: Early-Move Detection.

Detects nascent breakouts and directional expansion from volatility compression
prior to widespread retail participation, utilizing price/volume acceleration,
VWAP structure, and sector/market trend alignment.
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
from app.strategies.config import EarlyMoveDetectionConfig


class EarlyMoveDetectionStrategy(BaseStrategy):
    """Deterministic Early-Move Detection Strategy."""

    def __init__(self, config: EarlyMoveDetectionConfig | None = None) -> None:
        self.config = config or EarlyMoveDetectionConfig()

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.EARLY_MOVE_DETECTION

    def evaluate(self, snapshot: FeatureSnapshot) -> Candidate | None:
        """Evaluate FeatureSnapshot for early breakout from compression.

        Strictly rejects:
        - Excessive volatility (prior move already expanded/late)
        - Non-positive or inadequate price acceleration
        - Lack of volume surge
        - Bearish broad market index or negative sector strength
        - Inadequate liquidity or wide spread
        - Structure breakdown (LOWER_LOWS)
        """
        # 1. Compression condition: low realized volatility or explicit compression structure
        is_compressed = (
            snapshot.realized_volatility_15 <= self.config.max_volatility
            or snapshot.price_structure == "COMPRESSION"
        )
        if not is_compressed:
            return None

        # 2. Emerging price acceleration
        if snapshot.price_acceleration < self.config.min_price_acceleration:
            return None

        # 3. Volume surge: initial volume uptick
        if (
            snapshot.volume_acceleration <= self.config.min_volume_acceleration
            or snapshot.relative_volume_10 < self.config.min_rvol
        ):
            return None

        # 4. Structure: reject if lower lows
        if snapshot.price_structure == "LOWER_LOWS":
            return None

        # 5. VWAP relationship: must not be significantly below VWAP
        if snapshot.current_price < snapshot.vwap * Decimal("0.999"):
            return None

        # 6. Sector and Market alignment
        if snapshot.market_index_direction not in ("BULLISH", "NEUTRAL"):
            return None

        if snapshot.sector_strength < self.config.min_sector_strength:
            return None

        # 7. Liquidity and Spread
        if snapshot.liquidity_score < self.config.min_liquidity_score:
            return None

        if snapshot.spread_pct > self.config.max_spread_pct:
            return None

        # Calculate tight compression stop loss and expansion target
        trigger_price = snapshot.current_price

        # Tight stop: typically 0.5% - 0.8% below trigger, capped at max_stop_distance_pct
        stop_dist = max(
            self.config.min_stop_distance_pct,
            min(self.config.max_stop_distance_pct, Decimal("0.0060")),
        )
        initial_stop_price = (trigger_price * (Decimal(1) - stop_dist)).quantize(
            Decimal("0.0001")
        )
        risk_per_share = trigger_price - initial_stop_price

        suggested_target_price = (
            trigger_price + (risk_per_share * self.config.target_risk_multiple)
        ).quantize(Decimal("0.0001"))

        # Calculate rank score
        rank_score = self._compute_rank_score(snapshot)

        # Build candidate ID
        ts_str = snapshot.timestamp.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
        candidate_id = (
            f"cand-em-{snapshot.symbol.lower()}-{ts_str}-{uuid.uuid4().hex[:6]}"
        )

        quantitative_evidence = {
            "strategy": "EARLY_MOVE_DETECTION",
            "volatility_compressed": True,
            "realized_volatility_15": float(snapshot.realized_volatility_15),
            "price_acceleration": float(snapshot.price_acceleration),
            "volume_acceleration": float(snapshot.volume_acceleration),
            "rvol_10": float(snapshot.relative_volume_10),
            "price_structure": snapshot.price_structure,
            "vwap_distance_pct": float(snapshot.vwap_distance_pct),
            "market_index_direction": snapshot.market_index_direction,
            "sector_strength": float(snapshot.sector_strength),
            "liquidity_score": float(snapshot.liquidity_score),
            "spread_pct": float(snapshot.spread_pct),
            "risk_per_share": float(risk_per_share),
            "risk_multiple": float(self.config.target_risk_multiple),
            "reasons": [
                f"Realized volatility {snapshot.realized_volatility_15:.2f}% confirms compression",
                f"Price acceleration {snapshot.price_acceleration:.2f}% marks initial expansion",
                f"Volume acceleration {snapshot.volume_acceleration:.2f}% and RVOL {snapshot.relative_volume_10:.2f} confirm surge",
                f"Market direction {snapshot.market_index_direction} and sector strength {snapshot.sector_strength:.2f} align",
                f"Liquidity score {snapshot.liquidity_score:.1f} meets execution standard",
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

        # Price acceleration bonus: up to 20 pts
        accel_pts = min(20.0, float(snapshot.price_acceleration) * 20.0)

        # Volume expansion bonus: up to 15 pts
        vol_accel_pts = min(15.0, float(snapshot.volume_acceleration) * 0.25)

        # Liquidity bonus: up to 10 pts
        liq_pts = (float(snapshot.liquidity_score) / 100.0) * 10.0

        # Sector alignment bonus: up to 5 pts
        sector_pts = min(5.0, max(0.0, float(snapshot.sector_strength) * 2.5))

        total = min(
            100.0,
            max(50.0, base_score + accel_pts + vol_accel_pts + liq_pts + sector_pts),
        )
        return Decimal(str(round(total, 2)))
