"""Liquidity-Aware Position Sizing for Phase 32.

Dynamically modulates order quantity to prevent market impact and adverse selection:
- Caps participation to a maximum percentage of 1-minute candle volume (default 2.0%)
- Penalizes orders when bid-ask spreads widen (> 15 bps)
"""

from __future__ import annotations

import math
from decimal import Decimal

from app.execution_opt.models import LiquiditySizingRecommendation

_PREC_2 = Decimal("0.01")


class LiquidityAwareSizer:
    """Modulates position sizing based on real-time market liquidity and spread conditions."""

    DEFAULT_MAX_PARTICIPATION_PCT: Decimal = Decimal("2.00")  # Max 2% of bar volume
    SPREAD_PENALTY_THRESHOLD_PCT: Decimal = Decimal("0.15")   # 15 bps

    @classmethod
    def size_order(
        cls,
        symbol: str,
        requested_qty: int,
        bar_volume: int = 15000,
        spread_pct: Decimal = Decimal("0.0200"),
        max_participation_pct: Decimal | None = None,
    ) -> LiquiditySizingRecommendation:
        """Computes liquidity-adjusted order quantity.

        Args:
            symbol: Ticker symbol.
            requested_qty: Strategy-requested quantity.
            bar_volume: Prevailing 1-minute bar volume.
            spread_pct: Current bid-ask spread percentage.
            max_participation_pct: Custom participation cap (defaults to 2.0%).

        Returns:
            LiquiditySizingRecommendation object.
        """
        cap_pct = max_participation_pct or cls.DEFAULT_MAX_PARTICIPATION_PCT
        vol_safe = max(1, bar_volume)

        # 1. Volume participation calculation
        participation_float = (float(requested_qty) / float(vol_safe)) * 100.0
        participation_dec = Decimal(str(round(participation_float, 2)))

        # 2. Maximum shares allowed by volume cap
        max_allowed_by_vol = max(1, math.floor(float(vol_safe) * (float(cap_pct) / 100.0)))

        # 3. Spread penalty calculation
        spread_penalty_applied = False
        spread_factor = 1.0

        # If spread > 15 bps (0.15%), scale down size
        if spread_pct > cls.SPREAD_PENALTY_THRESHOLD_PCT:
            spread_penalty_applied = True
            excess = float(spread_pct - cls.SPREAD_PENALTY_THRESHOLD_PCT)
            # Decays from 1.0 down to 0.50 at 0.35% spread
            spread_factor = max(0.50, 1.0 - (excess / 0.20))

        # 4. Synthesize recommended size
        intermediate_qty = min(requested_qty, max_allowed_by_vol)
        final_qty = max(1, math.floor(float(intermediate_qty) * spread_factor))

        size_scaled = final_qty < requested_qty
        scale_factor = (
            Decimal(str(round(final_qty / requested_qty, 2)))
            if requested_qty > 0
            else Decimal("1.00")
        )

        rationale_parts: list[str] = []
        if requested_qty > max_allowed_by_vol:
            rationale_parts.append(
                f"Volume participation ({participation_dec}%) exceeded {cap_pct}% cap: "
                f"capped from {requested_qty} to {max_allowed_by_vol} shares"
            )
        if spread_penalty_applied:
            rationale_parts.append(
                f"Wide spread ({spread_pct}% > {cls.SPREAD_PENALTY_THRESHOLD_PCT}%): "
                f"applied {spread_factor:.2f}x penalty"
            )

        rationale = (
            "; ".join(rationale_parts)
            if rationale_parts
            else "Requested quantity fully within liquidity and spread boundaries."
        )

        return LiquiditySizingRecommendation(
            symbol=symbol,
            requested_qty=requested_qty,
            recommended_qty=final_qty,
            volume_participation_pct=participation_dec.quantize(_PREC_2),
            max_participation_cap_pct=cap_pct.quantize(_PREC_2),
            spread_penalty_applied=spread_penalty_applied,
            size_scaled_down=size_scaled,
            scale_factor=scale_factor,
            rationale=rationale,
        )
