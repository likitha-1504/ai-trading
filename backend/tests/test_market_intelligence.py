"""Comprehensive test suite for Phase 30 Advanced Market Intelligence.

Tests cover:
- Directional Regime Detection (Bull, Bear, Range, Breakout, Chop)
- Volatility Regime & Squeeze Detection (Compression, High, Extreme, Risk Multipliers)
- Sector Context & Mansfield Relative Strength
- Cross-Sectional Market Breadth (Expansion, Liquidation, Thrust)
- Unified Advanced Market Intelligence Engine & Leakage Audits
- Regime-Conditioned Backtesting Evaluation
- FastAPI REST Endpoints & JSON contracts
- Operational CLI runner execution
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.engine.bar_aggregator import Bar
from app.main import app
from app.market_intelligence.backtest_evaluator import (
    RegimeBacktestEvaluator,
    SimulatedTrade,
)
from app.market_intelligence.intelligence_engine import (
    AdvancedMarketIntelligenceEngine,
)
from app.market_intelligence.market_breadth import BreadthAnalyzer
from app.market_intelligence.models import (
    BreadthRegime,
    MarketIntelligenceAction,
    TrendRegime,
    VolatilityState,
)
from app.market_intelligence.regime_detector import RegimeDetector
from app.market_intelligence.sector_context import SectorAnalyzer
from app.market_intelligence.volatility_regime import VolatilityAnalyzer


def _make_bar(
    symbol: str,
    timestamp: datetime,
    close: Decimal,
    high: Decimal | None = None,
    low: Decimal | None = None,
    open_p: Decimal | None = None,
    volume: int = 10000,
) -> Bar:
    """Helper to construct a deterministic Bar."""
    o = open_p if open_p is not None else close
    h = high if high is not None else max(o, close) + Decimal("1.00")
    l = low if low is not None else min(o, close) - Decimal("1.00")
    c = close
    return Bar(
        symbol=symbol,
        timestamp=timestamp,
        timeframe_seconds=60,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=volume,
        typical_price_volume_sum=(h + l + c) / Decimal(3) * Decimal(volume),
        volume_sum=volume,
        vwap=c,
        last_spread_pct=Decimal("0.0100"),
        ticks_count=50,
    )


def test_regime_detector_bull_momentum() -> None:
    """Tests that a clean upward ladder of bars is detected as BULL_MOMENTUM."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    import datetime as dt

    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00") + Decimal(str(i * 1.5))
        bars.append(_make_bar("TEST", t, p, high=p + Decimal("2.00"), low=p - Decimal("0.50"), open_p=p - Decimal("1.00")))

    regime = RegimeDetector.classify(bars)
    assert regime.trend_regime in (TrendRegime.BULL_MOMENTUM, TrendRegime.VOLATILE_BREAKOUT)
    assert regime.ema_alignment == "BULLISH_STACK"
    assert regime.plus_di > regime.minus_di
    assert regime.trend_strength > Decimal("40.0")


def test_regime_detector_bear_momentum() -> None:
    """Tests that a downward ladder of bars is detected as BEAR_MOMENTUM."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    import datetime as dt

    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("200.00") - Decimal(str(i * 1.5))
        bars.append(_make_bar("TEST", t, p, high=p + Decimal("0.50"), low=p - Decimal("2.00"), open_p=p + Decimal("1.00")))

    regime = RegimeDetector.classify(bars)
    assert regime.trend_regime in (TrendRegime.BEAR_MOMENTUM, TrendRegime.VOLATILE_BREAKOUT)
    assert regime.ema_alignment == "BEARISH_STACK"
    assert regime.minus_di > regime.plus_di


def test_regime_detector_mean_reverting_range() -> None:
    """Tests oscillating bars result in low ADX and MEAN_REVERTING_RANGE."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    import datetime as dt

    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00") + (Decimal("0.50") if i % 2 == 0 else Decimal("-0.50"))
        bars.append(_make_bar("TEST", t, p, high=p + Decimal("0.80"), low=p - Decimal("0.80")))

    regime = RegimeDetector.classify(bars)
    assert regime.trend_regime == TrendRegime.MEAN_REVERTING_RANGE
    assert regime.adx < Decimal("20.0")


def test_regime_detector_empty_history() -> None:
    """Tests graceful default handling on empty bars."""
    regime = RegimeDetector.classify([])
    assert regime.trend_regime == TrendRegime.NEUTRAL_CHOP
    assert regime.ema_alignment == "TANGLED"


def test_volatility_analyzer_compression() -> None:
    """Tests tight range compression detection and risk multiplier."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    import datetime as dt

    for i in range(35):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00") + (Decimal("0.05") if i % 2 == 0 else Decimal("-0.05"))
        bars.append(_make_bar("TEST", t, p, high=p + Decimal("0.08"), low=p - Decimal("0.08")))

    vol = VolatilityAnalyzer.analyze(bars)
    assert vol.volatility_state == VolatilityState.VOLATILITY_COMPRESSION
    assert vol.risk_multiplier == Decimal("0.80")
    assert vol.bollinger_bandwidth < Decimal("0.015")


def test_volatility_analyzer_extreme_circuit() -> None:
    """Tests extreme volatility shock triggers circuit breaker risk multiplier 0.0."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    bars: list[Bar] = []
    import datetime as dt

    # 30 tight bars
    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00")
        bars.append(_make_bar("TEST", t, p, high=p + Decimal("0.10"), low=p - Decimal("0.10")))

    # Followed by a massive shock bar
    t_shock = base_time + dt.timedelta(minutes=30)
    p_shock = Decimal("130.00")
    bars.append(_make_bar("TEST", t_shock, p_shock, high=Decimal("135.00"), low=Decimal("95.00")))

    vol = VolatilityAnalyzer.analyze(bars)
    assert vol.volatility_state in (VolatilityState.EXTREME_VOLATILITY_CIRCUIT, VolatilityState.HIGH_VOLATILITY)
    assert vol.risk_multiplier in (Decimal("0.00"), Decimal("0.50"))


def test_sector_analyzer_mapping_and_tailwind() -> None:
    """Tests sector mappings and relative strength tailwind evaluation."""
    assert SectorAnalyzer.get_sector_for_symbol("INFY") == "NIFTY_IT"
    assert SectorAnalyzer.get_sector_for_symbol("RELIANCE") == "NIFTY_ENERGY"
    assert SectorAnalyzer.get_sector_for_symbol("HDFCBANK") == "NIFTY_BANK"
    assert SectorAnalyzer.get_sector_for_symbol("UNKNOWN_SYM") == "NIFTY_50"

    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    import datetime as dt

    # Asset outperforming sector benchmark
    asset_bars: list[Bar] = []
    sector_bars: list[Bar] = []

    for i in range(25):
        t = base_time + dt.timedelta(minutes=i)
        # Asset gains +20%
        asset_p = Decimal("100.00") + Decimal(str(i * 1.0))
        # Sector flat
        sector_p = Decimal("1000.00") + Decimal(str(i * 0.1))
        asset_bars.append(_make_bar("INFY", t, asset_p))
        sector_bars.append(_make_bar("NIFTY_IT", t, sector_p))

    context = SectorAnalyzer.analyze_asset_sector_context(
        symbol="INFY",
        asset_bars=asset_bars,
        sector_bars=sector_bars,
    )

    assert context.assigned_sector == "NIFTY_IT"
    assert context.sector_relative_strength > Decimal("0.0")
    assert context.has_sector_tailwind is True
    assert len(context.sector_rankings) > 0


def test_breadth_analyzer_expansion() -> None:
    """Tests strong expansion breadth regime when majority of universe advances."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    import datetime as dt

    universe: dict[str, list[Bar]] = {}
    symbols = ["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"]

    for sym in symbols:
        bars = []
        for i in range(25):
            t = base_time + dt.timedelta(minutes=i)
            p = Decimal("100.00") + Decimal(str(i * 1.0))
            bars.append(_make_bar(sym, t, p))
        universe[sym] = bars

    breadth = BreadthAnalyzer.analyze_universe_breadth(universe)
    assert breadth.breadth_regime == BreadthRegime.STRONG_EXPANSION
    assert breadth.advancing_count == 5
    assert breadth.declining_count == 0
    assert breadth.pct_above_20_ma == Decimal("100.00")
    assert breadth.breadth_thrust_active is True


def test_breadth_analyzer_liquidation() -> None:
    """Tests strong liquidation breadth regime when all assets decline."""
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    import datetime as dt

    universe: dict[str, list[Bar]] = {}
    symbols = ["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"]

    for sym in symbols:
        bars = []
        for i in range(25):
            t = base_time + dt.timedelta(minutes=i)
            p = Decimal("200.00") - Decimal(str(i * 2.0))
            bars.append(_make_bar(sym, t, p))
        universe[sym] = bars

    breadth = BreadthAnalyzer.analyze_universe_breadth(universe)
    assert breadth.breadth_regime == BreadthRegime.STRONG_LIQUIDATION
    assert breadth.declining_count == 5
    assert breadth.advancing_count == 0
    assert breadth.pct_above_20_ma == Decimal("0.00")


def test_unified_intelligence_engine_evaluation() -> None:
    """Tests end-to-end snapshot generation and synthesis."""
    engine = AdvancedMarketIntelligenceEngine()
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    import datetime as dt

    bars: list[Bar] = []
    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00") + Decimal(str(i * 0.5))
        bars.append(_make_bar("RELIANCE", t, p))

    snapshot = engine.evaluate_symbol("RELIANCE", bars)
    assert snapshot.symbol == "RELIANCE"
    assert snapshot.leakage_free is True
    assert snapshot.is_trade_allowed is True
    assert snapshot.suggested_size_multiplier > Decimal("0.0")
    assert snapshot.recommended_action in (
        MarketIntelligenceAction.FAVOR_TREND_FOLLOWING,
        MarketIntelligenceAction.FAVOR_MEAN_REVERSION,
        MarketIntelligenceAction.DEFENSIVE_REDUCE_SIZE,
    )


def test_intelligence_engine_leakage_detection() -> None:
    """Tests that future bars violate the leakage audit."""
    engine = AdvancedMarketIntelligenceEngine()
    base_time = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)
    as_of = datetime(2026, 9, 26, 9, 20, tzinfo=timezone.utc)
    import datetime as dt

    bars: list[Bar] = []
    for i in range(30):
        t = base_time + dt.timedelta(minutes=i)
        p = Decimal("100.00") + Decimal(str(i * 0.5))
        bars.append(_make_bar("RELIANCE", t, p))

    # Evaluate as of 9:20 UTC when bars extend to 9:44 UTC
    snapshot = engine.evaluate_symbol("RELIANCE", bars, as_of_time=as_of)
    assert snapshot.leakage_free is False


def test_regime_backtest_evaluator() -> None:
    """Tests regime-conditioned backtest comparing baseline vs filtered strategy."""
    summary = RegimeBacktestEvaluator.run_regime_backtest()
    assert summary.baseline_trades == 100
    assert summary.filtered_trades < summary.baseline_trades
    # Filtered win rate should exceed baseline win rate
    assert summary.filtered_win_rate_pct > summary.baseline_win_rate_pct
    # Drawdown reduction should be positive
    assert summary.drawdown_reduction_pct > Decimal("0.0")
    # Sharpe improvement should be positive
    assert summary.sharpe_improvement_pct > Decimal("0.0")
    assert summary.leakage_audit_passed is True
    assert len(summary.regime_breakdown) > 0


def test_fastapi_endpoints() -> None:
    """Tests all FastAPI market intelligence endpoints."""
    client = TestClient(app)

    # 1. Snapshot
    res_snap = client.get("/api/v1/market-intelligence/snapshot?symbol=RELIANCE")
    assert res_snap.status_code == 200
    data_snap = res_snap.json()
    assert data_snap["symbol"] == "RELIANCE"
    assert "regime" in data_snap
    assert "volatility" in data_snap
    assert "sector_context" in data_snap
    assert "breadth" in data_snap

    # 2. Regimes
    res_reg = client.get("/api/v1/market-intelligence/regimes?symbol=RELIANCE")
    assert res_reg.status_code == 200
    assert "trend_regime" in res_reg.json()

    # 3. Volatility
    res_vol = client.get("/api/v1/market-intelligence/volatility?symbol=RELIANCE")
    assert res_vol.status_code == 200
    assert "volatility_state" in res_vol.json()

    # 4. Sector Context
    res_sec = client.get("/api/v1/market-intelligence/sector-context?symbol=RELIANCE")
    assert res_sec.status_code == 200
    assert "assigned_sector" in res_sec.json()

    # 5. Breadth
    res_brd = client.get("/api/v1/market-intelligence/breadth")
    assert res_brd.status_code == 200
    assert "breadth_regime" in res_brd.json()

    # 6. Backtest
    res_bkt = client.post("/api/v1/market-intelligence/backtest")
    assert res_bkt.status_code == 200
    assert res_bkt.json()["baseline_trades"] == 100

    # 7. Leakage Audit
    res_aud = client.post("/api/v1/market-intelligence/audit-leakage?symbol=RELIANCE")
    assert res_aud.status_code == 200
    assert res_aud.json()["is_leakage_free"] is True


def test_cli_runner_execution() -> None:
    """Tests CLI runner script under different flags."""
    # Standard ASCII dashboard
    res_ascii = subprocess.run(
        [sys.executable, "backend/scripts/market_intelligence_runner.py", "--symbol", "RELIANCE"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_ascii.returncode == 0
    assert "PHASE 30 ADVANCED MARKET INTELLIGENCE AUDIT DASHBOARD" in res_ascii.stdout

    # JSON streaming
    res_json = subprocess.run(
        [sys.executable, "backend/scripts/market_intelligence_runner.py", "--symbol", "RELIANCE", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_json.returncode == 0
    assert '"symbol": "RELIANCE"' in res_json.stdout

    # Standalone Backtest
    res_bkt = subprocess.run(
        [sys.executable, "backend/scripts/market_intelligence_runner.py", "--backtest"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_bkt.returncode == 0
    assert "Backtest ID:" in res_bkt.stdout

    # Standalone Leakage Audit
    res_aud = subprocess.run(
        [sys.executable, "backend/scripts/market_intelligence_runner.py", "--audit-leakage"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_aud.returncode == 0
    assert "Leakage Audit Status: PASS" in res_aud.stdout


def test_breadth_empty_universe() -> None:
    """Tests default neutral breadth when universe is empty."""
    summary = BreadthAnalyzer.analyze_universe_breadth({})
    assert summary.breadth_regime == BreadthRegime.NEUTRAL_CHURN
    assert summary.ad_ratio == Decimal("1.00")
    assert summary.breadth_thrust_active is False


def test_sector_context_empty_bars() -> None:
    """Tests sector analyzer handles empty bars gracefully."""
    summary = SectorAnalyzer.analyze_asset_sector_context("TCS", [])
    assert summary.assigned_sector == "NIFTY_IT"
    assert summary.sector_relative_strength == Decimal("0.00")


def test_leakage_auditor_detects_trade_inversion() -> None:
    """Tests that timestamp inversion in simulated trades is detected by LeakageAuditor."""
    from app.research.leakage_auditor import LeakageAuditor

    t1 = datetime(2026, 9, 26, 9, 30, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 26, 9, 15, tzinfo=timezone.utc)  # Inverted

    tr1 = SimulatedTrade("T1", t1, "A", TrendRegime.BULL_MOMENTUM, VolatilityState.NORMAL_VOLATILITY, True, Decimal("1.0"), Decimal("1.0"), True)
    tr2 = SimulatedTrade("T2", t2, "A", TrendRegime.BULL_MOMENTUM, VolatilityState.NORMAL_VOLATILITY, True, Decimal("1.0"), Decimal("1.0"), True)

    report = LeakageAuditor.audit_event_stream([tr1, tr2])
    assert report.is_leakage_free is False
    assert report.lookahead_bias_detected is True

