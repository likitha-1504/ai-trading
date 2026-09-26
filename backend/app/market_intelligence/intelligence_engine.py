"""Unified Point-in-Time Advanced Market Intelligence Engine.

Integrates Trend Regime Detection, Volatility State Analysis, Sector Context,
and Cross-Sectional Market Breadth. Enforces point-in-time calculation with
leakage and look-ahead bias auditing via LeakageAuditor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, Sequence

from app.engine.bar_aggregator import Bar
from app.market_intelligence.market_breadth import BreadthAnalyzer
from app.market_intelligence.models import (
    AdvancedMarketIntelligenceSnapshot,
    BreadthRegime,
    MarketBreadthSummary,
    MarketIntelligenceAction,
    RegimeClassification,
    SectorContextSummary,
    TrendRegime,
    VolatilityClassification,
    VolatilityState,
)
from app.market_intelligence.regime_detector import RegimeDetector
from app.market_intelligence.sector_context import SectorAnalyzer
from app.market_intelligence.volatility_regime import VolatilityAnalyzer
from app.research.leakage_auditor import LeakageAuditor

_PREC_2 = Decimal("0.01")


class AdvancedMarketIntelligenceEngine:
    """Unified engine producing point-in-time composite market intelligence snapshots."""

    def __init__(self) -> None:
        self._history_snapshots: list[AdvancedMarketIntelligenceSnapshot] = []

    def evaluate_symbol(
        self,
        symbol: str,
        asset_bars: Sequence[Bar],
        current_price: Decimal | None = None,
        sector_bars: Sequence[Bar] | None = None,
        universe_bars: Mapping[str, Sequence[Bar]] | None = None,
        as_of_time: datetime | None = None,
    ) -> AdvancedMarketIntelligenceSnapshot:
        """Evaluates comprehensive market intelligence for an asset strictly point-in-time.

        Args:
            symbol: Ticker symbol.
            asset_bars: Chronological historical bars.
            current_price: Optional real-time price; defaults to last bar close.
            sector_bars: Optional sector benchmark bars.
            universe_bars: Optional mapping of universe bars for breadth calculation.
            as_of_time: Evaluation timestamp for point-in-time leakage verification.

        Returns:
            AdvancedMarketIntelligenceSnapshot.
        """
        now_utc = as_of_time or (
            asset_bars[-1].timestamp if asset_bars else datetime.now(timezone.utc)
        )
        cur_price = current_price if current_price is not None else (
            asset_bars[-1].close if asset_bars else Decimal("100.00")
        )

        # 1. Leakage and Look-Ahead Bias Verification
        leakage_passed = True
        if asset_bars:
            audit_report = LeakageAuditor.audit_event_stream(asset_bars)
            if not audit_report.is_leakage_free:
                leakage_passed = False

            # Check no future bars beyond as_of_time
            if any(b.timestamp > now_utc for b in asset_bars):
                leakage_passed = False

        # 2. Compute Regime Classification
        regime = RegimeDetector.classify(asset_bars, current_price=cur_price)

        # 3. Compute Volatility Classification
        volatility = VolatilityAnalyzer.analyze(asset_bars)

        # 4. Compute Sector Context
        sector_context = SectorAnalyzer.analyze_asset_sector_context(
            symbol=symbol,
            asset_bars=asset_bars,
            sector_bars=sector_bars,
        )

        # 5. Compute Market Breadth
        breadth = BreadthAnalyzer.analyze_universe_breadth(universe_bars or {})

        # 6. Composite Recommendation & Size Multiplier Determination
        recommended_action, size_multiplier, trade_allowed = self._synthesize_guidance(
            regime=regime,
            volatility=volatility,
            sector_context=sector_context,
            breadth=breadth,
        )

        snapshot = AdvancedMarketIntelligenceSnapshot(
            snapshot_id=f"SNAP-{uuid.uuid4().hex[:8].upper()}",
            timestamp=now_utc,
            symbol=symbol,
            regime=regime,
            volatility=volatility,
            sector_context=sector_context,
            breadth=breadth,
            recommended_action=recommended_action,
            suggested_size_multiplier=size_multiplier.quantize(_PREC_2),
            is_trade_allowed=trade_allowed,
            leakage_free=leakage_passed,
        )

        self._history_snapshots.append(snapshot)
        return snapshot

    def _synthesize_guidance(
        self,
        regime: RegimeClassification,
        volatility: VolatilityClassification,
        sector_context: SectorContextSummary,
        breadth: MarketBreadthSummary,
    ) -> tuple[MarketIntelligenceAction, Decimal, bool]:
        """Synthesizes all analytical components into actionable strategy guidance."""
        # Hard circuit halts: Extreme Volatility or Strong Market Liquidation
        if volatility.volatility_state == VolatilityState.EXTREME_VOLATILITY_CIRCUIT:
            return MarketIntelligenceAction.HALT_NEW_POSITIONS, Decimal("0.00"), False

        if breadth.breadth_regime == BreadthRegime.STRONG_LIQUIDATION:
            return MarketIntelligenceAction.HALT_NEW_POSITIONS, Decimal("0.00"), False

        # Baseline sizing from volatility risk multiplier
        base_multiplier = volatility.risk_multiplier

        # Sector alignment adjustment
        sector_factor = Decimal("1.00") if sector_context.has_sector_tailwind else Decimal("0.80")

        # Breadth alignment adjustment
        if breadth.breadth_regime == BreadthRegime.STRONG_EXPANSION or breadth.breadth_thrust_active or breadth.breadth_regime == BreadthRegime.HEALTHY_BULL:
            breadth_factor = Decimal("1.00")
        elif breadth.breadth_regime == BreadthRegime.NEUTRAL_CHURN:
            breadth_factor = Decimal("0.85")
        else:  # WEAK_BEAR
            breadth_factor = Decimal("0.60")

        composite_multiplier = max(
            Decimal("0.00"),
            min(Decimal("1.00"), base_multiplier * sector_factor * breadth_factor),
        )

        # Determine strategy specialization
        if volatility.volatility_state == VolatilityState.HIGH_VOLATILITY or breadth.breadth_regime == BreadthRegime.WEAK_BEAR:
            action = MarketIntelligenceAction.DEFENSIVE_REDUCE_SIZE
        elif regime.trend_regime == TrendRegime.VOLATILE_BREAKOUT or (
            volatility.volatility_state == VolatilityState.VOLATILITY_COMPRESSION and volatility.is_squeeze
        ):
            action = MarketIntelligenceAction.FAVOR_VOLATILITY_BREAKOUT
        elif regime.trend_regime == TrendRegime.MEAN_REVERTING_RANGE:
            action = MarketIntelligenceAction.FAVOR_MEAN_REVERSION
        elif regime.trend_regime in (TrendRegime.BULL_MOMENTUM, TrendRegime.BEAR_MOMENTUM):
            action = MarketIntelligenceAction.FAVOR_TREND_FOLLOWING
        else:
            action = MarketIntelligenceAction.DEFENSIVE_REDUCE_SIZE

        return action, composite_multiplier, True

    def get_history(self) -> list[AdvancedMarketIntelligenceSnapshot]:
        """Returns recorded snapshots history."""
        return list(self._history_snapshots)
