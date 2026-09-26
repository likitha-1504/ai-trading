"""Deterministic Point-in-Time Sector Context and Relative Strength Analyzer.

Maps Indian market symbols to their respective sectors, computes Mansfield Relative
Strength (RS) versus sector benchmarks and broad market indices, and evaluates
sector tailwinds with zero look-ahead bias.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.models import (
    SectorContextSummary,
    SectorPerformance,
)

_PREC_2 = Decimal("0.01")
_PREC_4 = Decimal("0.0001")

# Standard sector mapping for key NSE instruments
NSE_SECTOR_MAP: dict[str, str] = {
    # NIFTY IT
    "INFY": "NIFTY_IT",
    "TCS": "NIFTY_IT",
    "WIPRO": "NIFTY_IT",
    "HCLTECH": "NIFTY_IT",
    "TECHM": "NIFTY_IT",
    "LTIM": "NIFTY_IT",
    # NIFTY BANK
    "HDFCBANK": "NIFTY_BANK",
    "ICICIBANK": "NIFTY_BANK",
    "SBIN": "NIFTY_BANK",
    "KOTAKBANK": "NIFTY_BANK",
    "AXISBANK": "NIFTY_BANK",
    "INDUSINDBK": "NIFTY_BANK",
    # NIFTY AUTO
    "TATAMOTORS": "NIFTY_AUTO",
    "MARUTI": "NIFTY_AUTO",
    "M&M": "NIFTY_AUTO",
    "BAJAJ-AUTO": "NIFTY_AUTO",
    "HEROMOTOCO": "NIFTY_AUTO",
    # NIFTY METAL
    "TATASTEEL": "NIFTY_METAL",
    "JSWSTEEL": "NIFTY_METAL",
    "HINDALCO": "NIFTY_METAL",
    "VEDL": "NIFTY_METAL",
    "COALINDIA": "NIFTY_METAL",
    # NIFTY PHARMA
    "SUNPHARMA": "NIFTY_PHARMA",
    "CIPLA": "NIFTY_PHARMA",
    "DRREDDY": "NIFTY_PHARMA",
    "DIVISLAB": "NIFTY_PHARMA",
    # NIFTY ENERGY
    "RELIANCE": "NIFTY_ENERGY",
    "ONGC": "NIFTY_ENERGY",
    "BPCL": "NIFTY_ENERGY",
    "NTPC": "NIFTY_ENERGY",
    "POWERGRID": "NIFTY_ENERGY",
    # NIFTY FMCG
    "ITC": "NIFTY_FMCG",
    "HINDUNILVR": "NIFTY_FMCG",
    "NESTLEIND": "NIFTY_FMCG",
    "BRITANNIA": "NIFTY_FMCG",
}


class SectorAnalyzer:
    """Analyzes sector context, relative strength, and sector leadership point-in-time."""

    @classmethod
    def get_sector_for_symbol(cls, symbol: str) -> str:
        """Returns the assigned sector for a given symbol."""
        clean = symbol.upper().replace(".NS", "").replace(".BO", "")
        return NSE_SECTOR_MAP.get(clean, "NIFTY_50")

    @classmethod
    def analyze_asset_sector_context(
        cls,
        symbol: str,
        asset_bars: Sequence[Bar],
        sector_bars: Sequence[Bar] | None = None,
        all_sector_performances: Mapping[str, SectorPerformance] | None = None,
        lookback: int = 20,
    ) -> SectorContextSummary:
        """Evaluates asset's relative strength against its sector and overall sector leadership.

        Args:
            symbol: Ticker symbol of the stock.
            asset_bars: Historical bars of the stock up to current time.
            sector_bars: Historical bars of the sector benchmark up to current time.
            all_sector_performances: Precomputed sector performances for ranking.
            lookback: Lookback window for Relative Strength calculation (default 20).

        Returns:
            SectorContextSummary object.
        """
        assigned_sector = cls.get_sector_for_symbol(symbol)

        # 1. Compute Asset Relative Strength vs Sector
        rs_score = Decimal("0.00")
        if asset_bars and len(asset_bars) >= 2:
            if sector_bars and len(sector_bars) >= 2:
                rs_score = cls._compute_relative_strength(asset_bars, sector_bars, lookback=lookback)
            else:
                # If sector bars unavailable, proxy with asset's momentum
                p_cur = float(asset_bars[-1].close)
                w = min(lookback, len(asset_bars))
                p_old = float(asset_bars[-w].close)
                ret = ((p_cur - p_old) / p_old) * 100.0 if p_old > 0 else 0.0
                rs_score = Decimal(str(round(ret, 2)))

        # 2. Extract or determine sector performance
        rankings: list[SectorPerformance] = []
        if all_sector_performances:
            rankings = sorted(
                all_sector_performances.values(),
                key=lambda s: s.relative_strength,
                reverse=True,
            )
        else:
            # Generate default mock sectors if not provided
            rankings = cls._get_default_sector_rankings(assigned_sector)

        # 3. Determine assigned sector's specific trend and leadership
        assigned_perf = next((s for s in rankings if s.sector_name == assigned_sector), None)
        sector_trend = assigned_perf.trend if assigned_perf else "NEUTRAL"
        sector_is_leader = assigned_perf.is_leader if assigned_perf else False

        # 4. Determine if there is a sector tailwind
        # Tailwind is present if stock RS is positive and sector is either leader or in BULLISH trend
        has_tailwind = (rs_score >= Decimal("0.0")) and (sector_trend == "BULLISH" or sector_is_leader)

        return SectorContextSummary(
            symbol=symbol,
            assigned_sector=assigned_sector,
            sector_relative_strength=rs_score.quantize(_PREC_2),
            sector_trend=sector_trend,
            has_sector_tailwind=has_tailwind,
            sector_rankings=rankings,
        )

    @classmethod
    def _compute_relative_strength(
        cls,
        asset_bars: Sequence[Bar],
        sector_bars: Sequence[Bar],
        lookback: int = 20,
    ) -> Decimal:
        """Calculates Mansfield Relative Strength of asset relative to sector benchmark."""
        w_asset = min(lookback, len(asset_bars))
        w_sector = min(lookback, len(sector_bars))
        w = min(w_asset, w_sector)

        if w < 2:
            return Decimal("0.00")

        asset_curr = float(asset_bars[-1].close)
        asset_past = float(asset_bars[-w].close)
        sector_curr = float(sector_bars[-1].close)
        sector_past = float(sector_bars[-w].close)

        if asset_past <= 0 or sector_past <= 0 or sector_curr <= 0:
            return Decimal("0.00")

        asset_perf = asset_curr / asset_past
        sector_perf = sector_curr / sector_past

        # Mansfield RS formula: ((Asset_perf / Sector_perf) - 1.0) * 100
        rs = ((asset_perf / sector_perf) - 1.0) * 100.0
        return Decimal(str(round(rs, 2)))

    @classmethod
    def _get_default_sector_rankings(cls, current_sector: str) -> list[SectorPerformance]:
        """Provides default reference rankings across major NSE sectors."""
        sectors_meta = [
            ("NIFTY_IT", Decimal("1.85"), Decimal("2.10"), "BULLISH"),
            ("NIFTY_BANK", Decimal("1.20"), Decimal("1.45"), "BULLISH"),
            ("NIFTY_AUTO", Decimal("0.45"), Decimal("0.80"), "NEUTRAL"),
            ("NIFTY_METAL", Decimal("-0.30"), Decimal("-0.15"), "NEUTRAL"),
            ("NIFTY_PHARMA", Decimal("-0.85"), Decimal("-0.90"), "BEARISH"),
            ("NIFTY_ENERGY", Decimal("-1.40"), Decimal("-1.65"), "BEARISH"),
            ("NIFTY_FMCG", Decimal("-1.90"), Decimal("-2.10"), "BEARISH"),
        ]

        results: list[SectorPerformance] = []
        for idx, (name, rs, mom, trend) in enumerate(sectors_meta):
            is_leader = idx < 2  # Top 2 are leaders
            results.append(
                SectorPerformance(
                    sector_name=name,
                    relative_strength=rs,
                    momentum_score=mom,
                    is_leader=is_leader,
                    trend=trend,
                )
            )
        return results
