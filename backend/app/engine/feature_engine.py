"""Deterministic Point-in-Time Feature Engine.

Calculates quantitative features from NormalizedMarketEvents and OHLCV Bars
with zero look-ahead bias, strict timestamp safety, and bounded latency.
"""

import math
from collections import deque
from datetime import datetime
from decimal import Decimal

from app.engine.bar_aggregator import Bar, BarAggregator
from app.models.contracts import (
    FeatureSnapshot,
    MarketRegime,
    NormalizedMarketEvent,
)

_PREC_4 = Decimal("0.0001")
_PREC_2 = Decimal("0.01")
_ZERO = Decimal(0)
_HUNDRED = Decimal(100)


class FeatureEngine:
    """Deterministic, point-in-time technical and market feature computation engine."""

    def __init__(
        self,
        bar_aggregator: BarAggregator | None = None,
        bar_timeframe: str = "1m",
        max_history_bars: int = 100,
    ) -> None:
        """Initialize FeatureEngine with aggregator and history buffers."""
        self.bar_timeframe = bar_timeframe
        self.aggregator = bar_aggregator or BarAggregator(timeframe_seconds=60)
        self.max_history_bars = max_history_bars

        # Completed bars ring-buffer per symbol
        self._bar_history: dict[str, deque[Bar]] = {}

        # Session cumulative stats for session-level VWAP: (cum_pv, cum_vol)
        self._session_vwap_stats: dict[str, tuple[Decimal, int]] = {}

        # Market context
        self._market_index_direction: str = "NEUTRAL"
        self._sector_strengths: dict[str, Decimal] = {}

    def set_market_index_direction(self, direction: str) -> None:
        """Set broad market index direction: BULLISH, BEARISH, or NEUTRAL."""
        if direction not in ("BULLISH", "BEARISH", "NEUTRAL"):
            raise ValueError(f"Invalid market index direction: {direction}")
        self._market_index_direction = direction

    def set_sector_strength(self, symbol_or_sector: str, strength: Decimal) -> None:
        """Set relative sector strength score for a symbol or sector."""
        self._sector_strengths[symbol_or_sector.upper()] = strength

    def get_sector_strength(self, symbol: str) -> Decimal:
        """Retrieve sector strength for a symbol, defaulting to 0."""
        return self._sector_strengths.get(symbol.upper(), Decimal(0))

    def reset_symbol_session(self, symbol: str) -> None:
        """Reset historical session state for a specific symbol."""
        if symbol in self._bar_history:
            self._bar_history[symbol].clear()
        if symbol in self._session_vwap_stats:
            del self._session_vwap_stats[symbol]

    def register_completed_bar(self, bar: Bar) -> None:
        """Archive a completed bar into historical memory and update VWAP cumulative counters."""
        symbol = bar.symbol
        if symbol not in self._bar_history:
            self._bar_history[symbol] = deque(maxlen=self.max_history_bars)
        self._bar_history[symbol].append(bar)

        # Update session VWAP cumulative totals
        cum_pv, cum_vol = self._session_vwap_stats.get(symbol, (Decimal(0), 0))
        cum_pv += bar.typical_price * Decimal(bar.volume)
        cum_vol += bar.volume
        self._session_vwap_stats[symbol] = (cum_pv, cum_vol)

    def process_tick(self, event: NormalizedMarketEvent) -> FeatureSnapshot:
        """Ingest a normalized tick, aggregate into bars, and compute point-in-time features.

        Guarantees zero look-ahead bias: only completed historical bars and current
        tick data up to event.exchange_timestamp are accessible.
        """
        symbol = event.symbol
        completed_bar = self.aggregator.process_tick(event)

        if completed_bar is not None:
            self.register_completed_bar(completed_bar)

        current_in_progress = self.aggregator.get_current_in_progress_bar(symbol)

        return self.compute_features(
            symbol=symbol,
            timestamp=event.exchange_timestamp,
            current_price=event.last_price,
            current_spread_pct=event.spread_pct,
            current_tick_volume=event.volume,
            current_in_progress_bar=current_in_progress,
        )

    def process_completed_bar(self, bar: Bar) -> FeatureSnapshot:
        """Ingest an already completed bar directly and compute its feature snapshot."""
        self.register_completed_bar(bar)
        return self.compute_features(
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            current_price=bar.close,
            current_spread_pct=bar.last_spread_pct,
            current_tick_volume=bar.volume,
            current_in_progress_bar=bar,
        )

    def compute_features(
        self,
        symbol: str,
        timestamp: datetime,
        current_price: Decimal,
        current_spread_pct: Decimal,
        current_tick_volume: int = 0,
        current_in_progress_bar: Bar | None = None,
    ) -> FeatureSnapshot:
        """Compute all 12 quantitative features deterministically at the exact given point in time."""
        history = list(self._bar_history.get(symbol, []))

        # 1. VWAP & VWAP Distance %
        vwap = self._calculate_vwap(symbol, current_price, current_in_progress_bar)
        if vwap > Decimal(0):
            vwap_dist_pct = ((current_price - vwap) / vwap) * Decimal(100)
        else:
            vwap_dist_pct = Decimal(0)

        # 2. Momentum Score (5-bar ROC)
        momentum_score = self._calculate_momentum(current_price, history)

        # 3. Relative Volume (RVOL over 10-bar baseline)
        curr_vol = (
            current_in_progress_bar.volume
            if current_in_progress_bar
            else current_tick_volume
        )
        rvol_10 = self._calculate_rvol(curr_vol, history, window=10)

        # 4. Volume Acceleration (% change vs previous bar volume)
        vol_accel = self._calculate_volume_acceleration(curr_vol, history)

        # 5. Price Acceleration (2nd derivative of price)
        price_accel = self._calculate_price_acceleration(current_price, history)

        # 6. Realized Volatility (15-bar sample std dev of returns)
        realized_vol_15 = self._calculate_realized_volatility(
            current_price, history, window=15
        )

        # 7. Spread %
        spread_pct = max(Decimal(0), current_spread_pct)

        # 8. Liquidity Score (0 - 100)
        liquidity_score = self._calculate_liquidity_score(spread_pct, rvol_10)

        # 9. Market Index Direction
        market_index_direction = self._market_index_direction

        # 10. Sector Strength
        sector_strength = self.get_sector_strength(symbol)

        # 11. Price Structure (HIGHER_HIGHS, LOWER_LOWS, COMPRESSION, BREAKOUT, RANGE)
        price_structure = self._calculate_price_structure(
            current_price, history, rvol_10
        )

        # 12. Market Regime
        regime = self._determine_market_regime(
            current_price=current_price,
            vwap=vwap,
            momentum_score=momentum_score,
            price_structure=price_structure,
            realized_volatility=realized_vol_15,
            market_index_direction=market_index_direction,
        )

        return FeatureSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            bar_timeframe=self.bar_timeframe,
            vwap=vwap.quantize(_PREC_4),
            current_price=current_price.quantize(_PREC_4),
            vwap_distance_pct=vwap_dist_pct.quantize(_PREC_4),
            momentum_score=momentum_score.quantize(_PREC_4),
            relative_volume_10=rvol_10.quantize(_PREC_4),
            volume_acceleration=vol_accel.quantize(_PREC_4),
            price_acceleration=price_accel.quantize(_PREC_4),
            realized_volatility_15=realized_vol_15.quantize(_PREC_4),
            spread_pct=spread_pct.quantize(_PREC_4),
            liquidity_score=liquidity_score.quantize(_PREC_2),
            market_index_direction=market_index_direction,
            sector_strength=sector_strength.quantize(_PREC_4),
            price_structure=price_structure,
            regime=regime,
        )

    # -------------------------------------------------------------------------
    # Internal Deterministic Calculators
    # -------------------------------------------------------------------------

    def _calculate_vwap(
        self,
        symbol: str,
        current_price: Decimal,
        in_progress_bar: Bar | None,
    ) -> Decimal:
        """Calculate session VWAP including completed bars and current in-progress bar."""
        cum_pv, cum_vol = self._session_vwap_stats.get(symbol, (Decimal(0), 0))

        if in_progress_bar is not None and in_progress_bar.volume > 0:
            cum_pv += in_progress_bar.typical_price * Decimal(in_progress_bar.volume)
            cum_vol += in_progress_bar.volume

        if cum_vol > 0:
            return cum_pv / Decimal(cum_vol)
        return current_price

    def _calculate_momentum(
        self,
        current_price: Decimal,
        history: list[Bar],
        lookback: int = 5,
    ) -> Decimal:
        """Calculate Rate of Change momentum score over lookback bars."""
        if not history:
            return Decimal(0)

        # Baseline price from lookback bars ago
        if len(history) >= lookback:
            base_price = history[-lookback].close
        else:
            base_price = history[0].open

        if base_price <= Decimal(0):
            return Decimal(0)

        return ((current_price - base_price) / base_price) * Decimal(100)

    def _calculate_rvol(
        self,
        current_volume: int,
        history: list[Bar],
        window: int = 10,
    ) -> Decimal:
        """Calculate Relative Volume (RVOL) against the rolling average baseline."""
        if not history:
            return Decimal("1.0")

        recent_bars = history[-window:]
        total_vol = sum(b.volume for b in recent_bars)
        avg_vol = Decimal(total_vol) / Decimal(len(recent_bars))

        if avg_vol <= Decimal(0):
            return Decimal("1.0")

        return Decimal(current_volume) / avg_vol

    def _calculate_volume_acceleration(
        self,
        current_volume: int,
        history: list[Bar],
    ) -> Decimal:
        """Calculate volume acceleration percentage vs the previous bar."""
        if not history:
            return Decimal(0)

        prev_vol = history[-1].volume
        if prev_vol <= 0:
            if current_volume > 0:
                return Decimal(100)
            return Decimal(0)

        return (
            (Decimal(current_volume) - Decimal(prev_vol)) / Decimal(prev_vol)
        ) * Decimal(100)

    def _calculate_price_acceleration(
        self,
        current_price: Decimal,
        history: list[Bar],
    ) -> Decimal:
        """Calculate 2nd derivative of price: rate of change of price velocity."""
        if len(history) < 2:
            return Decimal(0)

        p_t = current_price
        p_t1 = history[-1].close
        p_t2 = history[-2].close

        if p_t1 <= Decimal(0) or p_t2 <= Decimal(0):
            return Decimal(0)

        # Velocity t and Velocity t-1
        vel_t = ((p_t - p_t1) / p_t1) * Decimal(100)
        vel_t1 = ((p_t1 - p_t2) / p_t2) * Decimal(100)

        return vel_t - vel_t1

    def _calculate_realized_volatility(
        self,
        current_price: Decimal,
        history: list[Bar],
        window: int = 15,
    ) -> Decimal:
        """Calculate sample standard deviation of bar percentage returns over rolling window."""
        if not history:
            return _ZERO

        n_bars = min(window - 1, len(history))
        if n_bars < 1:
            return _ZERO

        # Compute percentage returns in a single pass without allocating intermediate price lists
        start_idx = len(history) - n_bars
        returns: list[float] = []
        prev_f = float(history[start_idx].close)

        for i in range(start_idx + 1, len(history)):
            curr_f = float(history[i].close)
            if prev_f > 0:
                returns.append(((curr_f - prev_f) / prev_f) * 100.0)
            prev_f = curr_f

        p_curr_f = float(current_price)
        if prev_f > 0:
            returns.append(((p_curr_f - prev_f) / prev_f) * 100.0)

        n = len(returns)
        if n < 2:
            return _ZERO

        mean_ret = sum(returns) / n
        variance = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
        std_dev = math.sqrt(variance)

        return Decimal(str(round(std_dev, 6)))

    def _calculate_liquidity_score(
        self,
        spread_pct: Decimal,
        rvol_10: Decimal,
    ) -> Decimal:
        """Compute composite 0-100 liquidity score from spread tightness and volume turnover."""
        # 1. Spread score (0 to 50 pts): tight spread (<0.02%) gets 50 pts; decays to 0 at 0.50%
        spread_float = float(spread_pct)
        if spread_float <= 0.0002:
            spread_score = 50.0
        elif spread_float >= 0.0050:
            spread_score = 0.0
        else:
            spread_score = 50.0 * (1.0 - (spread_float - 0.0002) / (0.0050 - 0.0002))

        # 2. Volume/Depth score (0 to 50 pts): baseline RVOL=1.0 gets 25 pts, RVOL>=2.0 gets 50 pts
        rvol_float = float(rvol_10)
        vol_score = min(50.0, max(0.0, rvol_float * 25.0))

        total_score = max(0.0, min(100.0, spread_score + vol_score))
        return Decimal(str(round(total_score, 2)))

    def _calculate_price_structure(
        self,
        current_price: Decimal,
        history: list[Bar],
        rvol_10: Decimal,
    ) -> str:
        """Classify deterministic price structure.

        Returns one of: HIGHER_HIGHS, LOWER_LOWS, COMPRESSION, BREAKOUT, RANGE.
        """
        if len(history) < 3:
            return "RANGE"

        # Check for Breakout: current price above max high of last 10 bars with high volume
        lookback = min(10, len(history))
        max_prev_high = max(b.high for b in history[-lookback:])

        if current_price > max_prev_high and rvol_10 >= Decimal("1.2"):
            return "BREAKOUT"

        # Check for Higher Highs & Higher Lows (last 3 bars)
        b1, b2, b3 = history[-3], history[-2], history[-1]
        if (
            b3.high > b2.high > b1.high
            and b3.low > b2.low > b1.low
            and current_price >= b3.close
        ):
            return "HIGHER_HIGHS"

        # Check for Lower Lows & Lower Highs (last 3 bars)
        if (
            b3.high < b2.high < b1.high
            and b3.low < b2.low < b1.low
            and current_price <= b3.close
        ):
            return "LOWER_LOWS"

        # Check for Compression: High-Low range across recent bars is very tight (< 0.25% range)
        recent_5 = history[-min(5, len(history)) :]
        recent_max = max(b.high for b in recent_5)
        recent_min = min(b.low for b in recent_5)
        if recent_min > Decimal(0):
            span_pct = ((recent_max - recent_min) / recent_min) * Decimal(100)
            if span_pct < Decimal("0.25"):
                return "COMPRESSION"

        return "RANGE"

    def _determine_market_regime(
        self,
        current_price: Decimal,
        vwap: Decimal,
        momentum_score: Decimal,
        price_structure: str,
        realized_volatility: Decimal,
        market_index_direction: str,
    ) -> MarketRegime:
        """Determine deterministic MarketRegime classification."""
        is_above_vwap = current_price >= vwap
        is_bullish_mom = momentum_score > Decimal("0.05")
        is_bearish_mom = momentum_score < Decimal("-0.05")

        if (
            is_above_vwap
            and is_bullish_mom
            and price_structure in ("HIGHER_HIGHS", "BREAKOUT")
            and market_index_direction != "BEARISH"
        ):
            return MarketRegime.BULLISH_TRENDING

        if (
            not is_above_vwap
            and is_bearish_mom
            and price_structure == "LOWER_LOWS"
            and market_index_direction != "BULLISH"
        ):
            return MarketRegime.BEARISH_TRENDING

        if realized_volatility >= Decimal("0.80"):
            return MarketRegime.HIGH_VOLATILITY_CHOP

        if price_structure == "COMPRESSION" or realized_volatility < Decimal("0.25"):
            return MarketRegime.LOW_VOLATILITY_COMPRESSION

        # Fallback based on momentum direction
        if momentum_score > Decimal(0):
            return MarketRegime.BULLISH_TRENDING
        return MarketRegime.LOW_VOLATILITY_COMPRESSION
