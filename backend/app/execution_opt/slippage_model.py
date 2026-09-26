"""Deterministic Slippage and Market Impact Modeling for Phase 32.

Models execution friction via square-root market impact law and bid-ask spread costs:
Slippage = Half-Spread + Market Impact (gamma * volatility * sqrt(Q / V))
"""

from __future__ import annotations

import math
from decimal import Decimal

from app.execution_opt.models import SlippageEstimate
from app.models.contracts import TradeSide

_PREC_2 = Decimal("0.01")
_PREC_4 = Decimal("0.0001")


class SlippageModel:
    """Calculates point-in-time expected execution slippage and market impact."""

    IMPACT_GAMMA: float = 0.25  # Standard equity microstructure impact coefficient

    @classmethod
    def estimate_slippage(
        cls,
        symbol: str,
        order_qty: int,
        expected_price: Decimal,
        spread_pct: Decimal = Decimal("0.0200"),  # 0.02% = 2 bps
        bar_volume: int = 15000,
        realized_volatility: Decimal = Decimal("0.50"),  # 0.5%
        side: TradeSide = TradeSide.BUY,
    ) -> SlippageEstimate:
        """Estimates total execution slippage in basis points and rupee drag.

        Args:
            symbol: Ticker symbol.
            order_qty: Number of shares.
            expected_price: Quoted market price before execution.
            spread_pct: Bid-ask spread percentage.
            bar_volume: Volume of prevailing 1-minute candle.
            realized_volatility: Realized return volatility (in %).
            side: BUY or SELL.

        Returns:
            SlippageEstimate with decomposed friction.
        """
        # 1. Half-spread cost in bps
        # If spread_pct is 0.02% (0.0002), spread_bps is 2.0 bps, half-spread is 1.0 bps
        spread_float = float(spread_pct)
        half_spread_bps = (spread_float / 2.0) * 100.0  # e.g. 0.02% -> 1.0 bps
        half_spread_bps = max(0.5, half_spread_bps)

        # 2. Square-Root Market Impact
        # Participation ratio = Q / V
        vol_safe = max(100, bar_volume)
        participation = float(order_qty) / float(vol_safe)
        volatility_float = float(realized_volatility)  # e.g. 0.5%

        # Impact = gamma * volatility * sqrt(participation)
        impact_pct = cls.IMPACT_GAMMA * (volatility_float / 100.0) * math.sqrt(participation)
        impact_bps = impact_pct * 10000.0  # in bps

        total_slippage_bps = Decimal(str(round(half_spread_bps + impact_bps, 2)))

        # 3. Estimated Fill Price
        slippage_fraction = total_slippage_bps / Decimal("10000.00")
        if side == TradeSide.BUY:
            estimated_fill = expected_price * (Decimal("1.00") + slippage_fraction)
        else:
            estimated_fill = expected_price * (Decimal("1.00") - slippage_fraction)

        # 4. Total Rupee Drag
        rupee_drag = abs(estimated_fill - expected_price) * Decimal(order_qty)

        return SlippageEstimate(
            symbol=symbol,
            order_qty=order_qty,
            expected_price=expected_price.quantize(_PREC_4),
            spread_cost_bps=Decimal(str(round(half_spread_bps, 2))),
            market_impact_bps=Decimal(str(round(impact_bps, 2))),
            total_slippage_bps=total_slippage_bps,
            estimated_fill_price=estimated_fill.quantize(_PREC_2),
            slippage_drag_inr=rupee_drag.quantize(_PREC_2),
        )
