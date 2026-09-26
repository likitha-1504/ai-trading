"""Deterministic Point-in-Time Trend & Market Regime Detector.

Calculates directional movement indicators (ADX, +DI, -DI), moving average alignment,
and classifies market conditions into discrete trend regimes with zero lookahead bias.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.models import RegimeClassification, TrendRegime

_PREC_2 = Decimal("0.01")
_PREC_4 = Decimal("0.0001")
_ZERO = Decimal("0.00")


class RegimeDetector:
    """Classifies market regime strictly using historical completed bars."""

    @classmethod
    def classify(
        cls,
        bars: Sequence[Bar],
        current_price: Decimal | None = None,
        adx_period: int = 14,
    ) -> RegimeClassification:
        """Classify market regime point-in-time.

        Args:
            bars: Completed historical bars up to current time (must be >= 1 bar).
            current_price: Optional real-time price; defaults to last bar close.
            adx_period: Period for directional movement calculation (default 14).

        Returns:
            RegimeClassification object.
        """
        if not bars:
            return RegimeClassification(
                trend_regime=TrendRegime.NEUTRAL_CHOP,
                adx=Decimal("15.00"),
                plus_di=Decimal("20.00"),
                minus_di=Decimal("20.00"),
                trend_strength=Decimal("20.00"),
                ema_alignment="TANGLED",
                details="Insufficient bar history; default neutral chop assigned.",
            )

        eval_price = current_price if current_price is not None else bars[-1].close

        # Compute ADX and DIs
        adx, plus_di, minus_di = cls._calculate_adx(bars, period=adx_period)

        # Compute EMA alignment (9 EMA, 21 EMA, 50 SMA if available)
        ema_alignment, _ema_9, ema_21, _sma_50 = cls._check_ma_alignment(bars, eval_price)

        # Trend strength score (0 to 100)
        # Based on ADX and MA distance
        trend_strength = cls._compute_trend_strength(adx, plus_di, minus_di, eval_price, ema_21)

        # Breakout check: did the latest bar expand significantly beyond recent range?
        is_breakout = cls._check_breakout(bars, eval_price)

        # Classification logic
        if is_breakout and adx >= Decimal("20.0"):
            regime = TrendRegime.VOLATILE_BREAKOUT
            details = f"Acute volatility breakout detected; ADX {adx:.1f} with wide candle expansion."
        elif plus_di > minus_di and adx >= Decimal("25.0") and ema_alignment == "BULLISH_STACK":
            regime = TrendRegime.BULL_MOMENTUM
            details = f"Bull momentum regime confirmed: +DI ({plus_di:.1f}) > -DI ({minus_di:.1f}), ADX {adx:.1f}, bullish MA stack."
        elif minus_di > plus_di and adx >= Decimal("25.0") and ema_alignment == "BEARISH_STACK":
            regime = TrendRegime.BEAR_MOMENTUM
            details = f"Bear momentum regime confirmed: -DI ({minus_di:.1f}) > +DI ({plus_di:.1f}), ADX {adx:.1f}, bearish MA stack."
        elif adx < Decimal("20.0"):
            regime = TrendRegime.MEAN_REVERTING_RANGE
            details = f"Range-bound mean reverting regime: low directional ADX {adx:.1f} < 20.0."
        elif plus_di > minus_di and eval_price >= ema_21:
            regime = TrendRegime.BULL_MOMENTUM
            details = "Mild bull momentum: +DI dominant with price above 21 EMA."
        elif minus_di > plus_di and eval_price < ema_21:
            regime = TrendRegime.BEAR_MOMENTUM
            details = "Mild bear momentum: -DI dominant with price below 21 EMA."
        else:
            regime = TrendRegime.NEUTRAL_CHOP
            details = f"Neutral chop: conflicted directional indicators (ADX: {adx:.1f})."

        return RegimeClassification(
            trend_regime=regime,
            adx=adx.quantize(_PREC_2),
            plus_di=plus_di.quantize(_PREC_2),
            minus_di=minus_di.quantize(_PREC_2),
            trend_strength=trend_strength.quantize(_PREC_2),
            ema_alignment=ema_alignment,
            details=details,
        )

    @classmethod
    def _calculate_adx(
        cls,
        bars: Sequence[Bar],
        period: int = 14,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calculates Average Directional Index (ADX), +DI, and -DI over bars."""
        if len(bars) < 2:
            return Decimal("15.00"), Decimal("20.00"), Decimal("20.00")

        tr_list: list[float] = []
        plus_dm_list: list[float] = []
        minus_dm_list: list[float] = []

        for i in range(1, len(bars)):
            cur = bars[i]
            prev = bars[i - 1]

            # True Range = max(H-L, abs(H - prevC), abs(L - prevC))
            high_diff = float(cur.high - cur.low)
            high_prev = abs(float(cur.high - prev.close))
            low_prev = abs(float(cur.low - prev.close))
            tr = max(high_diff, high_prev, low_prev)
            tr_list.append(tr)

            # Directional Movement (+DM, -DM)
            up_move = float(cur.high - prev.high)
            down_move = float(prev.low - cur.low)

            if up_move > down_move and up_move > 0:
                plus_dm_list.append(up_move)
            else:
                plus_dm_list.append(0.0)

            if down_move > up_move and down_move > 0:
                minus_dm_list.append(down_move)
            else:
                minus_dm_list.append(0.0)

        window = min(period, len(tr_list))
        if window == 0:
            return Decimal("15.00"), Decimal("20.00"), Decimal("20.00")

        # Wilder's smoothing or simple window average
        sum_tr = sum(tr_list[-window:])
        sum_plus_dm = sum(plus_dm_list[-window:])
        sum_minus_dm = sum(minus_dm_list[-window:])

        if sum_tr <= 0:
            return Decimal("15.00"), Decimal("20.00"), Decimal("20.00")

        plus_di_val = (sum_plus_dm / sum_tr) * 100.0
        minus_di_val = (sum_minus_dm / sum_tr) * 100.0

        di_sum = plus_di_val + minus_di_val
        if di_sum > 0:
            dx = (abs(plus_di_val - minus_di_val) / di_sum) * 100.0
        else:
            dx = 0.0

        adx_val = min(100.0, max(0.0, dx))
        return (
            Decimal(str(round(adx_val, 2))),
            Decimal(str(round(plus_di_val, 2))),
            Decimal(str(round(minus_di_val, 2))),
        )

    @classmethod
    def _check_ma_alignment(
        cls,
        bars: Sequence[Bar],
        current_price: Decimal,
    ) -> tuple[str, Decimal, Decimal, Decimal]:
        """Calculates moving averages and checks stack alignment."""
        closes = [float(b.close) for b in bars]
        cur_p = float(current_price)

        # 9 EMA
        ema_9_val = cls._compute_ema(closes, span=9)
        # 21 EMA
        ema_21_val = cls._compute_ema(closes, span=21)
        # 50 SMA or fallback
        sma_len = min(50, len(closes))
        sma_50_val = sum(closes[-sma_len:]) / float(sma_len)

        if cur_p > ema_9_val > ema_21_val >= sma_50_val:
            alignment = "BULLISH_STACK"
        elif cur_p < ema_9_val < ema_21_val <= sma_50_val:
            alignment = "BEARISH_STACK"
        else:
            alignment = "TANGLED"

        return (
            alignment,
            Decimal(str(round(ema_9_val, 4))),
            Decimal(str(round(ema_21_val, 4))),
            Decimal(str(round(sma_50_val, 4))),
        )

    @classmethod
    def _compute_ema(cls, values: list[float], span: int) -> float:
        """Computes exponential moving average over sequence."""
        if not values:
            return 0.0
        k = 2.0 / (span + 1.0)
        ema = values[0]
        for val in values[1:]:
            ema = val * k + ema * (1.0 - k)
        return ema

    @classmethod
    def _compute_trend_strength(
        cls,
        adx: Decimal,
        plus_di: Decimal,
        minus_di: Decimal,
        current_price: Decimal,
        ema_21: Decimal,
    ) -> Decimal:
        """Computes a normalized 0-100 trend strength score."""
        adx_factor = float(adx)  # 0 to 100
        di_spread = abs(float(plus_di - minus_di))  # 0 to 100
        if ema_21 > Decimal(0):
            ma_dist = abs(float((current_price - ema_21) / ema_21)) * 1000.0  # bps
            dist_score = min(25.0, ma_dist)
        else:
            dist_score = 0.0

        raw_score = (adx_factor * 0.5) + (min(100.0, di_spread) * 0.3) + (dist_score * 0.2)
        score = min(100.0, max(0.0, raw_score))
        return Decimal(str(round(score, 2)))

    @classmethod
    def _check_breakout(cls, bars: Sequence[Bar], current_price: Decimal) -> bool:
        """Determines if the latest bar exhibits breakout behavior."""
        if len(bars) < 5:
            return False
        recent_bars = bars[-10:-1] if len(bars) >= 10 else bars[:-1]
        highest_high = max(b.high for b in recent_bars)
        lowest_low = min(b.low for b in recent_bars)

        # Breakout if price exceeds highest high or breaks below lowest low
        return current_price > highest_high or current_price < lowest_low
