"""Deterministic Point-in-Time Market Breadth Analyzer.

Calculates cross-sectional breadth participation (Advance/Decline, % above 20 EMA,
% above 50 SMA), Breadth Thrust identification, and regime classification
with zero look-ahead bias.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.models import (
    BreadthRegime,
    MarketBreadthSummary,
)

_PREC_2 = Decimal("0.01")


class BreadthAnalyzer:
    """Evaluates cross-sectional market breadth across a universe of assets."""

    @classmethod
    def analyze_universe_breadth(
        cls,
        universe_bars: Mapping[str, Sequence[Bar]],
    ) -> MarketBreadthSummary:
        """Computes aggregate cross-sectional breadth from universe bar histories.

        Args:
            universe_bars: Mapping of symbol -> sequence of historical bars up to current time.

        Returns:
            MarketBreadthSummary object.
        """
        if not universe_bars:
            return MarketBreadthSummary(
                breadth_regime=BreadthRegime.NEUTRAL_CHURN,
                advancing_count=25,
                declining_count=25,
                unchanged_count=0,
                ad_ratio=Decimal("1.00"),
                pct_above_20_ma=Decimal("50.00"),
                pct_above_50_ma=Decimal("50.00"),
                breadth_thrust_active=False,
            )

        advancing = 0
        declining = 0
        unchanged = 0
        above_20_count = 0
        above_50_count = 0
        total_symbols = 0

        for bars in universe_bars.values():
            if not bars:
                continue
            total_symbols += 1
            latest_bar = bars[-1]
            closes = [float(b.close) for b in bars]
            cur_p = float(latest_bar.close)

            # Advance / Decline vs first bar or previous bar
            if len(bars) >= 2:
                prev_p = float(bars[-2].close)
                if cur_p > prev_p:
                    advancing += 1
                elif cur_p < prev_p:
                    declining += 1
                else:
                    unchanged += 1
            else:
                unchanged += 1

            # 20 EMA check
            if len(closes) >= 5:
                ema_20 = cls._compute_ema(closes, span=min(20, len(closes)))
                if cur_p >= ema_20:
                    above_20_count += 1

            # 50 SMA check
            if len(closes) >= 10:
                w50 = min(50, len(closes))
                sma_50 = sum(closes[-w50:]) / float(w50)
                if cur_p >= sma_50:
                    above_50_count += 1

        denom = max(1, total_symbols)
        pct_20 = (above_20_count / denom) * 100.0
        pct_50 = (above_50_count / denom) * 100.0

        ad_ratio_float = float(advancing) / max(1.0, float(declining))
        ad_ratio = Decimal(str(round(ad_ratio_float, 2)))

        # Breadth thrust: extreme surge in advances and broad participation
        breadth_thrust = (ad_ratio_float >= 2.5) and (pct_20 >= 70.0)

        # Classify Breadth Regime
        if ad_ratio_float >= 2.0 and pct_20 >= 65.0:
            regime = BreadthRegime.STRONG_EXPANSION
        elif ad_ratio_float >= 1.2 and pct_20 >= 50.0:
            regime = BreadthRegime.HEALTHY_BULL
        elif ad_ratio_float <= 0.5 and pct_20 <= 35.0:
            regime = BreadthRegime.STRONG_LIQUIDATION
        elif ad_ratio_float <= 0.8:
            regime = BreadthRegime.WEAK_BEAR
        else:
            regime = BreadthRegime.NEUTRAL_CHURN

        return MarketBreadthSummary(
            breadth_regime=regime,
            advancing_count=advancing,
            declining_count=declining,
            unchanged_count=unchanged,
            ad_ratio=ad_ratio.quantize(_PREC_2),
            pct_above_20_ma=Decimal(str(round(pct_20, 2))).quantize(_PREC_2),
            pct_above_50_ma=Decimal(str(round(pct_50, 2))).quantize(_PREC_2),
            breadth_thrust_active=breadth_thrust,
        )

    @classmethod
    def _compute_ema(cls, values: list[float], span: int) -> float:
        """Computes exponential moving average."""
        k = 2.0 / (span + 1.0)
        ema = values[0]
        for val in values[1:]:
            ema = val * k + ema * (1.0 - k)
        return ema
