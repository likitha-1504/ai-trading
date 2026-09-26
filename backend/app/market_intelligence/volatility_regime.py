"""Deterministic Point-in-Time Volatility Regime and Squeeze Analyzer.

Calculates Average True Range (ATR), ATR historical percentiles, Bollinger Bandwidth,
Keltner Channel Squeeze conditions, and defensive capital risk multipliers.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.models import VolatilityClassification, VolatilityState

_PREC_2 = Decimal("0.01")
_PREC_4 = Decimal("0.0001")


class VolatilityAnalyzer:
    """Classifies volatility regime and determines risk multipliers strictly point-in-time."""

    @classmethod
    def analyze(
        cls,
        bars: Sequence[Bar],
        lookback_percentile: int = 50,
    ) -> VolatilityClassification:
        """Evaluates historical volatility and identifies compression / expansion regimes.

        Args:
            bars: Completed historical bars up to current time (must be >= 1).
            lookback_percentile: Number of past bars to compute the ATR percentile rank.

        Returns:
            VolatilityClassification object.
        """
        if not bars:
            return VolatilityClassification(
                volatility_state=VolatilityState.NORMAL_VOLATILITY,
                atr=Decimal("1.00"),
                atr_percentile=Decimal("50.00"),
                bollinger_bandwidth=Decimal("0.0200"),
                is_squeeze=False,
                risk_multiplier=Decimal("1.00"),
                details="Insufficient bar history; default normal volatility assigned.",
            )

        # 1. Compute ATR series
        atr_series = cls._calculate_atr_series(bars, period=14)
        current_atr = atr_series[-1] if atr_series else Decimal("1.00")

        # 2. Compute ATR Percentile Rank
        window = min(lookback_percentile, len(atr_series))
        recent_atrs = atr_series[-window:]
        atr_percentile = cls._compute_percentile(current_atr, recent_atrs)

        # 3. Compute Bollinger Bands & Keltner Channels for Squeeze Detection
        bb_upper, bb_lower, _bb_sma, bandwidth = cls._compute_bollinger(bars, period=20, num_std=2.0)
        kc_upper, kc_lower = cls._compute_keltner(bars, period=20, atr=current_atr, multiplier=1.5)

        # Squeeze exists when Bollinger Bands are completely inside Keltner Channels
        is_squeeze = (bb_upper < kc_upper) and (bb_lower > kc_lower)

        # 4. Classify Volatility State and determine risk multiplier
        pct_float = float(atr_percentile)
        bw_float = float(bandwidth)
        cur_price = float(bars[-1].close) if bars else 100.0
        atr_pct_of_price = (float(current_atr) / max(1.0, cur_price)) * 100.0

        if (pct_float > 95.0 and atr_pct_of_price > 3.0) or bw_float > 0.18 or atr_pct_of_price > 5.0:
            state = VolatilityState.EXTREME_VOLATILITY_CIRCUIT
            risk_multiplier = Decimal("0.00")
            details = f"Extreme volatility shock: ATR {current_atr:.2f} ({atr_pct_of_price:.2f}% of price) at {pct_float:.1f}th percentile; trading halted (risk multiplier: 0.0)."
        elif (pct_float > 80.0 and atr_pct_of_price > 1.5) or bw_float > 0.08:
            state = VolatilityState.HIGH_VOLATILITY
            risk_multiplier = Decimal("0.50")
            details = f"Elevated volatility regime: ATR at {pct_float:.1f}th percentile; defensive sizing applied (risk multiplier: 0.5)."
        elif is_squeeze or pct_float < 20.0 or bw_float < 0.015:
            state = VolatilityState.VOLATILITY_COMPRESSION
            risk_multiplier = Decimal("0.80")
            details = f"Volatility compression/squeeze active: Bandwidth {bandwidth:.4f}, preparing for breakout (risk multiplier: 0.8)."
        else:
            state = VolatilityState.NORMAL_VOLATILITY
            risk_multiplier = Decimal("1.00")
            details = f"Normal volatility regime: ATR at {pct_float:.1f}th percentile (risk multiplier: 1.0)."

        return VolatilityClassification(
            volatility_state=state,
            atr=current_atr.quantize(_PREC_2),
            atr_percentile=atr_percentile.quantize(_PREC_2),
            bollinger_bandwidth=bandwidth.quantize(_PREC_4),
            is_squeeze=is_squeeze,
            risk_multiplier=risk_multiplier.quantize(_PREC_2),
            details=details,
        )

    @classmethod
    def _calculate_atr_series(cls, bars: Sequence[Bar], period: int = 14) -> list[Decimal]:
        """Calculates rolling ATR series."""
        if len(bars) < 2:
            return [Decimal("1.00")]

        tr_list: list[float] = []
        for i in range(1, len(bars)):
            cur = bars[i]
            prev = bars[i - 1]
            tr = max(
                float(cur.high - cur.low),
                abs(float(cur.high - prev.close)),
                abs(float(cur.low - prev.close)),
            )
            tr_list.append(tr)

        atr_series: list[Decimal] = []
        rolling_tr = sum(tr_list[:period]) / max(1, min(period, len(tr_list)))
        atr_series.append(Decimal(str(round(rolling_tr, 4))))

        for tr in tr_list[period:]:
            rolling_tr = (rolling_tr * (period - 1) + tr) / period
            atr_series.append(Decimal(str(round(rolling_tr, 4))))

        return atr_series

    @classmethod
    def _compute_percentile(cls, value: Decimal, history: list[Decimal]) -> Decimal:
        """Calculates historical percentile of value within history."""
        if not history:
            return Decimal("50.00")
        val_float = float(value)
        min_val = min(float(h) for h in history)
        max_val = max(float(h) for h in history)
        if math.isclose(min_val, max_val, rel_tol=1e-5):
            return Decimal("50.00")
        count_below = sum(1 for h in history if float(h) < val_float)
        count_equal = sum(1 for h in history if math.isclose(float(h), val_float, rel_tol=1e-5))
        pct = ((count_below + 0.5 * count_equal) / len(history)) * 100.0
        return Decimal(str(round(pct, 2)))

    @classmethod
    def _compute_bollinger(
        cls,
        bars: Sequence[Bar],
        period: int = 20,
        num_std: float = 2.0,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Calculates Bollinger Upper, Lower, SMA, and normalized Bandwidth."""
        closes = [float(b.close) for b in bars]
        window = min(period, len(closes))
        recent = closes[-window:]

        sma = sum(recent) / float(window)
        variance = sum((x - sma) ** 2 for x in recent) / float(window)
        std_dev = math.sqrt(variance)

        upper = sma + (std_dev * num_std)
        lower = sma - (std_dev * num_std)
        bandwidth = (upper - lower) / sma if sma > 0 else 0.02

        return (
            Decimal(str(round(upper, 4))),
            Decimal(str(round(lower, 4))),
            Decimal(str(round(sma, 4))),
            Decimal(str(round(bandwidth, 6))),
        )

    @classmethod
    def _compute_keltner(
        cls,
        bars: Sequence[Bar],
        period: int = 20,
        atr: Decimal = Decimal("1.00"),
        multiplier: float = 1.5,
    ) -> tuple[Decimal, Decimal]:
        """Calculates Keltner Channels Upper and Lower."""
        closes = [float(b.close) for b in bars]
        window = min(period, len(closes))
        recent = closes[-window:]
        sma = sum(recent) / float(window)

        offset = float(atr) * multiplier
        upper = sma + offset
        lower = sma - offset

        return (
            Decimal(str(round(upper, 4))),
            Decimal(str(round(lower, 4))),
        )
