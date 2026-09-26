"""Comprehensive test suite for Phase 32 Execution Optimization.

Tests cover:
- Slippage & Market Impact Modeling (Half-spread, square-root law)
- Liquidity-Aware Position Sizing (Volume participation cap, spread penalty)
- Session Timing & Urgency Scheduling (Market hours, cutoffs, aggressive vs passive)
- Paper Execution Comparative Study (Slippage reduction, friction savings, latency)
- Unified Execution Optimizer Orchestrator
- FastAPI REST Endpoints & Schemas
- Operational CLI Runner Execution
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.execution_opt.execution_optimizer import ExecutionOptimizer
from app.execution_opt.liquidity_sizer import LiquidityAwareSizer
from app.execution_opt.models import (
    ExecutionUrgency,
    TimeOfDayRegime,
)
from app.execution_opt.order_scheduler import OrderScheduler
from app.execution_opt.paper_validator import ExecutionPaperValidator
from app.execution_opt.slippage_model import SlippageModel
from app.main import app
from app.models.contracts import StrategyType, TradeSide


def test_slippage_model_half_spread() -> None:
    """Tests half-spread cost in basis points calculation."""
    est = SlippageModel.estimate_slippage(
        symbol="RELIANCE",
        order_qty=10,
        expected_price=Decimal("2450.00"),
        spread_pct=Decimal("0.0200"),  # 2 bps spread
        bar_volume=50000,
        realized_volatility=Decimal("0.10"),
    )
    # Half-spread of 0.02% is 1.0 bps
    assert est.spread_cost_bps == Decimal("1.00")
    assert est.total_slippage_bps >= Decimal("1.00")


def test_slippage_model_market_impact() -> None:
    """Tests square-root market impact scaling with order quantity."""
    est_small = SlippageModel.estimate_slippage(
        symbol="RELIANCE",
        order_qty=10,
        expected_price=Decimal("2450.00"),
        bar_volume=10000,
        realized_volatility=Decimal("0.50"),
    )
    est_large = SlippageModel.estimate_slippage(
        symbol="RELIANCE",
        order_qty=400,
        expected_price=Decimal("2450.00"),
        bar_volume=10000,
        realized_volatility=Decimal("0.50"),
    )
    # Market impact must increase with order size
    assert est_large.market_impact_bps > est_small.market_impact_bps
    assert est_large.slippage_drag_inr > est_small.slippage_drag_inr


def test_slippage_model_fill_prices() -> None:
    """Tests that BUY fill prices increase and SELL fill prices decrease with slippage."""
    p = Decimal("100.00")
    est_buy = SlippageModel.estimate_slippage(
        symbol="TEST",
        order_qty=50,
        expected_price=p,
        side=TradeSide.BUY,
    )
    est_sell = SlippageModel.estimate_slippage(
        symbol="TEST",
        order_qty=50,
        expected_price=p,
        side=TradeSide.SELL,
    )
    assert est_buy.estimated_fill_price > p
    assert est_sell.estimated_fill_price < p


def test_liquidity_sizer_within_bounds() -> None:
    """Tests that an order well within participation cap is unconstrained."""
    rec = LiquidityAwareSizer.size_order(
        symbol="RELIANCE",
        requested_qty=20,
        bar_volume=10000,  # 20 / 10000 = 0.2% <= 2.0%
        spread_pct=Decimal("0.02"),
    )
    assert rec.recommended_qty == 20
    assert rec.size_scaled_down is False
    assert rec.scale_factor == Decimal("1.00")


def test_liquidity_sizer_volume_cap() -> None:
    """Tests that an order exceeding 2% volume cap is scaled down."""
    rec = LiquidityAwareSizer.size_order(
        symbol="ILLIQUID_SYM",
        requested_qty=100,
        bar_volume=2000,  # 2% of 2000 = 40 shares
        spread_pct=Decimal("0.02"),
    )
    assert rec.recommended_qty == 40
    assert rec.size_scaled_down is True
    assert rec.scale_factor == Decimal("0.40")


def test_liquidity_sizer_spread_penalty() -> None:
    """Tests that a wide bid-ask spread past 15 bps triggers scale-down penalty."""
    rec = LiquidityAwareSizer.size_order(
        symbol="WIDE_SYM",
        requested_qty=30,
        bar_volume=10000,
        spread_pct=Decimal("0.25"),  # 25 bps > 15 bps
    )
    assert rec.spread_penalty_applied is True
    assert rec.recommended_qty < 30
    assert rec.size_scaled_down is True


def test_order_scheduler_session_regimes() -> None:
    """Tests time of day session regime classification."""
    # 09:30 IST = 04:00 UTC (Opening rush)
    t_open = datetime(2026, 9, 26, 4, 0, tzinfo=timezone.utc)
    assert OrderScheduler.classify_time_of_day(t_open) == TimeOfDayRegime.OPENING_AUCTION_RUSH

    # 10:30 IST = 05:00 UTC (Morning trend)
    t_morn = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)
    assert OrderScheduler.classify_time_of_day(t_morn) == TimeOfDayRegime.MORNING_TREND

    # 12:30 IST = 07:00 UTC (Midday consolidation)
    t_mid = datetime(2026, 9, 26, 7, 0, tzinfo=timezone.utc)
    assert OrderScheduler.classify_time_of_day(t_mid) == TimeOfDayRegime.MIDDAY_CONSOLIDATION

    # 14:15 IST = 08:45 UTC (Afternoon session)
    t_aft = datetime(2026, 9, 26, 8, 45, tzinfo=timezone.utc)
    assert OrderScheduler.classify_time_of_day(t_aft) == TimeOfDayRegime.AFTERNOON_SESSION

    # 15:15 IST = 09:45 UTC (Cutoff risk)
    t_cut = datetime(2026, 9, 26, 9, 45, tzinfo=timezone.utc)
    assert OrderScheduler.classify_time_of_day(t_cut) == TimeOfDayRegime.INTRADAY_CUTOFF_RISK


def test_order_scheduler_cutoff_rejection() -> None:
    """Tests that orders scheduled during cutoff window are rejected."""
    t_cut = datetime(2026, 9, 26, 9, 45, tzinfo=timezone.utc)
    _urgency, order_type, rationale = OrderScheduler.schedule_execution(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        rank_score=Decimal("95.00"),
        spread_pct=Decimal("0.01"),
        volume_participation_pct=Decimal("0.50"),
        timestamp=t_cut,
    )
    assert order_type == "REJECT"
    assert "square-off window" in rationale


def test_order_scheduler_urgency_scheduling() -> None:
    """Tests urgency recommendations for aggressive vs liquidity-seeking orders."""
    t_morn = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)  # Morning session

    # High rank, tight spread -> AGGRESSIVE
    urg_agg, typ_agg, _ = OrderScheduler.schedule_execution(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        rank_score=Decimal("92.00"),
        spread_pct=Decimal("0.02"),
        volume_participation_pct=Decimal("0.50"),
        timestamp=t_morn,
    )
    assert urg_agg == ExecutionUrgency.AGGRESSIVE
    assert typ_agg == "MARKET"

    # High volume participation -> LIQUIDITY_SEEKING
    urg_liq, typ_liq, _ = OrderScheduler.schedule_execution(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        rank_score=Decimal("80.00"),
        spread_pct=Decimal("0.02"),
        volume_participation_pct=Decimal("2.50"),  # > 1.5%
        timestamp=t_morn,
    )
    assert urg_liq == ExecutionUrgency.LIQUIDITY_SEEKING
    assert typ_liq == "LIMIT"


def test_paper_validator_study() -> None:
    """Tests comparative paper validation study executing benchmark orders."""
    study = ExecutionPaperValidator.run_study(sample_orders_count=30)
    assert study.orders_analyzed_count == 30
    assert study.paper_validated is True
    # Optimized slippage must be lower than baseline
    assert study.optimized_avg_slippage_bps < study.baseline_avg_slippage_bps
    assert study.slippage_reduction_pct > Decimal("0.0")
    assert study.friction_savings_inr > Decimal("0.0")
    assert study.fill_rate_optimized_pct == Decimal("100.00")
    assert len(study.key_findings) > 0


def test_execution_optimizer_orchestration() -> None:
    """Tests unified ExecutionOptimizer producing complete execution plan."""
    opt = ExecutionOptimizer()
    # 10:30 IST morning session
    t_morn = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)
    sizing, urgency, order_type, slippage = opt.optimize_order(
        symbol="RELIANCE",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        requested_qty=50,
        expected_price=Decimal("2450.00"),
        bar_volume=15000,
        spread_pct=Decimal("0.02"),
        realized_volatility=Decimal("0.40"),
        rank_score=Decimal("88.00"),
        timestamp=t_morn,
    )
    assert sizing.symbol == "RELIANCE"
    assert sizing.recommended_qty > 0
    assert urgency in (ExecutionUrgency.AGGRESSIVE, ExecutionUrgency.PASSIVE_PEG, ExecutionUrgency.LIQUIDITY_SEEKING)
    assert order_type in ("MARKET", "LIMIT")
    assert slippage.total_slippage_bps > Decimal("0.0")


def test_fastapi_execution_opt_endpoints() -> None:
    """Tests all FastAPI execution optimization routes."""
    client = TestClient(app)

    # 1. Study
    res_std = client.get("/api/v1/execution-opt/study")
    assert res_std.status_code == 200
    data_std = res_std.json()
    assert "study_id" in data_std
    assert "slippage_reduction_pct" in data_std

    # 2. Estimate Slippage
    res_slip = client.post("/api/v1/execution-opt/estimate-slippage?symbol=RELIANCE&order_qty=20&expected_price=2450.00")
    assert res_slip.status_code == 200
    assert "total_slippage_bps" in res_slip.json()

    # 3. Size Order
    res_size = client.post("/api/v1/execution-opt/size-order?symbol=RELIANCE&requested_qty=60&bar_volume=2000")
    assert res_size.status_code == 200
    assert "recommended_qty" in res_size.json()

    # 4. Run Paper Validation Study
    res_run = client.post("/api/v1/execution-opt/run-paper-validation?orders_count=20")
    assert res_run.status_code == 200
    assert res_run.json()["orders_analyzed_count"] == 20


def test_cli_execution_opt_runner() -> None:
    """Tests CLI runner script across multiple flags."""
    # Standard ASCII dashboard
    res_ascii = subprocess.run(
        [sys.executable, "backend/scripts/execution_opt_runner.py", "--orders", "20"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_ascii.returncode == 0
    assert "PHASE 32 EXECUTION OPTIMIZATION AUDIT DASHBOARD" in res_ascii.stdout

    # JSON streaming
    res_json = subprocess.run(
        [sys.executable, "backend/scripts/execution_opt_runner.py", "--json", "--orders", "20"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_json.returncode == 0
    assert '"study_id":' in res_json.stdout


def test_order_scheduler_midday_liquidity_seeking() -> None:
    """Tests midday consolidation recommends passive or liquidity-seeking limit order."""
    t_mid = datetime(2026, 9, 26, 7, 0, tzinfo=timezone.utc)  # 12:30 IST
    urg, typ, _ = OrderScheduler.schedule_execution(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        rank_score=Decimal("75.00"),
        spread_pct=Decimal("0.02"),
        volume_participation_pct=Decimal("0.80"),
        timestamp=t_mid,
    )
    assert typ == "LIMIT"
    assert urg == ExecutionUrgency.PASSIVE_PEG


def test_liquidity_sizer_minimum_floor() -> None:
    """Tests that liquidity sizer always enforces a minimum 1 share execution floor."""
    rec = LiquidityAwareSizer.size_order(
        symbol="TINY_SYM",
        requested_qty=1,
        bar_volume=10,  # 2% of 10 is 0.2 shares -> floor is 1
        spread_pct=Decimal("0.50"),  # heavy spread penalty
    )
    assert rec.recommended_qty >= 1


def test_slippage_model_zero_spread() -> None:
    """Tests slippage model with minimal spread still computes non-zero market impact."""
    est = SlippageModel.estimate_slippage(
        symbol="TIGHT_SYM",
        order_qty=20,
        expected_price=Decimal("100.00"),
        spread_pct=Decimal("0.0001"),
        bar_volume=5000,
        realized_volatility=Decimal("0.80"),
    )
    assert est.spread_cost_bps >= Decimal("0.50")
    assert est.market_impact_bps > Decimal("0.0")
    assert est.total_slippage_bps > Decimal("0.0")

