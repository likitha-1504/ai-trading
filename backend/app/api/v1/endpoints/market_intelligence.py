"""FastAPI REST API Endpoints for Phase 30 Advanced Market Intelligence.

Exposes endpoints for:
- Market intelligence snapshots
- Trend regime classifications
- Volatility analysis and squeeze states
- Sector context and relative strength
- Cross-sectional market breadth
- Regime-conditioned backtesting runs
- Leakage and look-ahead audits
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query

from app.engine.bar_aggregator import Bar
from app.market_intelligence.backtest_evaluator import RegimeBacktestEvaluator
from app.market_intelligence.intelligence_engine import (
    AdvancedMarketIntelligenceEngine,
)
from app.market_intelligence.market_breadth import BreadthAnalyzer
from app.market_intelligence.models import (
    AdvancedMarketIntelligenceSnapshot,
    MarketBreadthSummary,
    RegimeBacktestSummary,
    RegimeClassification,
    SectorContextSummary,
    VolatilityClassification,
)
from app.market_intelligence.regime_detector import RegimeDetector
from app.market_intelligence.sector_context import SectorAnalyzer
from app.market_intelligence.volatility_regime import VolatilityAnalyzer
from app.research.models import LeakageAuditReport

router = APIRouter(prefix="/market-intelligence", tags=["Advanced Market Intelligence"])

# Shared engine instance
_engine = AdvancedMarketIntelligenceEngine()


def _get_mock_sample_bars(symbol: str, count: int = 30) -> list[Bar]:
    """Generates synthetic historical sample bars for API demonstrations."""
    import datetime as dt

    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = Decimal("2450.00")

    for i in range(count):
        t = base_time + dt.timedelta(minutes=i)
        # Gentle upward trend with minor noise
        noise = Decimal(str(round((i % 5 - 2) * 1.5, 2)))
        o = price + noise
        h = o + Decimal("3.50")
        l = o - Decimal("2.20")
        c = o + Decimal("1.20")
        v = 15000 + (i % 7) * 2000
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=t,
                timeframe_seconds=60,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                typical_price_volume_sum=(h + l + c) / Decimal(3) * Decimal(v),
                volume_sum=v,
                vwap=c - Decimal("0.50"),
                last_spread_pct=Decimal("0.0150"),
                ticks_count=120,
            )
        )
        price = c

    return bars


@router.get("/snapshot", response_model=AdvancedMarketIntelligenceSnapshot)
def get_market_intelligence_snapshot(
    symbol: str = Query("RELIANCE", description="NSE symbol to evaluate"),
) -> AdvancedMarketIntelligenceSnapshot:
    """Returns a unified point-in-time market intelligence snapshot for a symbol."""
    bars = _get_mock_sample_bars(symbol)
    return _engine.evaluate_symbol(symbol=symbol, asset_bars=bars)


@router.get("/regimes", response_model=RegimeClassification)
def get_trend_regime(
    symbol: str = Query("RELIANCE", description="NSE symbol"),
) -> RegimeClassification:
    """Returns the trend and directional regime classification for a symbol."""
    bars = _get_mock_sample_bars(symbol)
    return RegimeDetector.classify(bars)


@router.get("/volatility", response_model=VolatilityClassification)
def get_volatility_state(
    symbol: str = Query("RELIANCE", description="NSE symbol"),
) -> VolatilityClassification:
    """Returns the volatility state, ATR percentiles, and squeeze status."""
    bars = _get_mock_sample_bars(symbol)
    return VolatilityAnalyzer.analyze(bars)


@router.get("/sector-context", response_model=SectorContextSummary)
def get_sector_context(
    symbol: str = Query("RELIANCE", description="NSE symbol"),
) -> SectorContextSummary:
    """Returns the sector mapping, relative strength, and sector leadership."""
    bars = _get_mock_sample_bars(symbol)
    return SectorAnalyzer.analyze_asset_sector_context(symbol=symbol, asset_bars=bars)


@router.get("/breadth", response_model=MarketBreadthSummary)
def get_market_breadth() -> MarketBreadthSummary:
    """Returns cross-sectional market breadth, A/D ratio, and participation metrics."""
    universe_bars = {
        "RELIANCE": _get_mock_sample_bars("RELIANCE"),
        "TCS": _get_mock_sample_bars("TCS"),
        "INFY": _get_mock_sample_bars("INFY"),
        "HDFCBANK": _get_mock_sample_bars("HDFCBANK"),
        "TATAMOTORS": _get_mock_sample_bars("TATAMOTORS"),
    }
    return BreadthAnalyzer.analyze_universe_breadth(universe_bars)


@router.post("/backtest", response_model=RegimeBacktestSummary)
def run_regime_backtest() -> RegimeBacktestSummary:
    """Runs a backtest evaluating baseline vs regime-conditioned strategy returns."""
    return RegimeBacktestEvaluator.run_regime_backtest()


@router.post("/audit-leakage", response_model=LeakageAuditReport)
def audit_feature_leakage(
    symbol: str = Query("RELIANCE", description="NSE symbol"),
) -> LeakageAuditReport:
    """Audits market intelligence feature stream for forward-looking and timestamp inversions."""
    from app.research.leakage_auditor import LeakageAuditor

    bars = _get_mock_sample_bars(symbol)
    return LeakageAuditor.audit_event_stream(bars)
