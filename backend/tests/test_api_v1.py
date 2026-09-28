"""Comprehensive test suite for Phase 14: FastAPI Backend + API Contracts.

Verifies:
1. OpenAPI documentation and schema validity.
2. All 13 safe read/query API endpoints:
   - Dashboard summary
   - Market scanner
   - Candidates
   - Positions
   - Orders
   - Trades
   - P/L
   - AI analysis
   - Performance
   - Backtests
   - Risk
   - System health
   - Logs
3. Segregation of read APIs from guarded mutation APIs.
4. Protection of live-trading endpoints behind explicit approval controls.
5. Exclusion of unrestricted arbitrary order creation (POST /orders is blocked).
6. TradePlan approval/rejection lifecycle.
7. Emergency kill-switch intervention.
"""

import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.api.deps import get_db_path, get_system_state
from app.db.connection import init_db
from app.db.repository import DatabaseRepository
from app.main import app
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    CapitalSnapshot,
    ChallengerCritique,
    ChallengerRecommendation,
    ChallengerSeverity,
    FeatureSnapshot,
    FrictionBreakdown,
    MarketRegime,
    MarketThesis,
    MarketThesisAction,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    RiskLimits,
    StopProtection,
    StrategyType,
    TradePlan,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)
from fastapi.testclient import TestClient


@pytest.fixture
def temp_api_db():
    """Create isolated SQLite database with initial test fixtures."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)

    repo = DatabaseRepository(db_path=path)
    now = datetime.now(timezone.utc)

    # 1. Capital State
    cap_snap = CapitalSnapshot(
        timestamp=now,
        total_capital=Decimal("100.00"),
        available_capital=Decimal("80.00"),
        deployed_capital=Decimal("20.00"),
        buying_power=Decimal("80.00"),
        realized_pnl=Decimal("5.00"),
        unrealized_pnl=Decimal("2.50"),
        daily_drawdown_amount=Decimal("0.50"),
        daily_drawdown_pct=Decimal("0.005"),
        high_water_mark=Decimal("105.00"),
    )
    repo.save_capital_state(cap_snap)

    # 2. Features
    fs = FeatureSnapshot(
        symbol="TCS",
        timestamp=now,
        bar_timeframe="1m",
        vwap=Decimal("3490.00"),
        current_price=Decimal("3500.00"),
        vwap_distance_pct=Decimal("0.0028"),
        momentum_score=Decimal("2.5"),
        relative_volume_10=Decimal("2.2"),
        volume_acceleration=Decimal("1.2"),
        price_acceleration=Decimal("0.6"),
        realized_volatility_15=Decimal("0.015"),
        spread_pct=Decimal("0.0008"),
        liquidity_score=Decimal("88.0"),
        market_index_direction="BULLISH",
        sector_strength=Decimal("0.8"),
        price_structure="HIGHER_HIGHS",
        regime=MarketRegime.BULLISH_TRENDING,
    )
    repo.save_feature_snapshot(fs)

    # 3. Candidates
    cand = Candidate(
        candidate_id="cand-api-001",
        detected_at=now,
        symbol="TCS",
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        side=TradeSide.BUY,
        trigger_price=Decimal("3500.00"),
        initial_stop_price=Decimal("3470.00"),
        suggested_target_price=Decimal("3560.00"),
        rank_score=Decimal("92.0"),
        quantitative_evidence={"rvol": "2.2", "momentum": "2.5"},
        feature_snapshot=fs,
    )
    repo.save_candidate(cand)

    # 4. AI Analyses
    thesis = MarketThesis(
        candidate_id="cand-api-001",
        model_name="qwen3:latest",
        model_version="v1.0",
        prompt_version="qwen3-v1",
        thesis_summary="Bullish VWAP continuation",
        catalyst_identified="Earnings momentum",
        bullish_evidence=["RVOL 2.2", "Higher highs"],
        invalidation_conditions=["Break below 3470"],
        perceived_risks=["Resistance at 3560"],
        confidence_score=Decimal("0.85"),
        context_summary="Strong sector",
        suggested_action=MarketThesisAction.PROCEED,
        latency_ms=110,
    )
    critique = ChallengerCritique(
        candidate_id="cand-api-001",
        model_name="deepseek-r1:latest",
        model_version="v1.0",
        prompt_version="r1-v1",
        critique_summary="Stress-tested without critical flaw",
        identified_vulnerabilities=["Overhead supply"],
        contradictory_signals=[],
        invalidation_conditions=["Break below 3470"],
        worst_case_scenario="Hard stop hit",
        downside_severity=ChallengerSeverity.LOW,
        recommendation_flag=ChallengerRecommendation.CONFIRM,
        latency_ms=140,
    )
    repo.save_ai_analysis("cand-api-001", thesis)
    repo.save_ai_analysis("cand-api-001", critique)

    # 5. TradePlan
    friction = FrictionBreakdown(
        brokerage=Decimal("0.10"),
        stt=Decimal("0.10"),
        exchange_charges=Decimal("0.02"),
        sebi_charges=Decimal("0.001"),
        stamp_duty=Decimal("0.02"),
        gst=Decimal("0.02"),
        expected_slippage=Decimal("0.05"),
        total_friction=Decimal("0.50"),
    )
    plan_manual = TradePlan(
        plan_id="plan-manual-001",
        candidate_id="cand-api-001",
        created_at=now,
        instrument="TCS",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price_target=Decimal("3500.00"),
        entry_context={"trigger": "3500.00"},
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        expected_edge=Decimal("4.50"),
        expected_gross_edge=Decimal("5.00"),
        expected_net_edge=Decimal("4.50"),
        estimated_costs=friction,
        friction=friction,
        risk_limits=RiskLimits(
            max_loss_amount=Decimal("30.00"),
            max_capital_allocation=Decimal("3500.00"),
        ),
        stop_protection=StopProtection(
            hard_stop_price=Decimal("3470.00"),
            take_profit_price=Decimal("3560.00"),
        ),
        invalidation=["Break below 3470"],
        decision_reason="Requires manual operator authorization (> ₹300)",
        approval_mode=ApprovalMode.MANUAL_PENDING,
    )
    repo.save_trade_plan(plan_manual)

    # 6. Position
    pos = PositionSnapshot(
        position_id="pos-api-001",
        plan_id="plan-manual-001",
        symbol="TCS",
        side=TradeSide.BUY,
        quantity=1,
        entry_price=Decimal("3500.00"),
        current_price=Decimal("3525.00"),
        hard_stop_price=Decimal("3470.00"),
        unrealized_pnl=Decimal("25.00"),
        status=PositionStatus.OPEN,
        opened_at=now,
        last_evaluated_at=now,
    )
    repo.save_position(pos)

    # 7. Order
    order_req = OrderRequest(
        client_order_id="order-api-001",
        plan_id="plan-manual-001",
        symbol="TCS",
        side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        price=Decimal("3500.00"),
        stop_price=Decimal("3470.00"),
    )
    repo.save_order(order_req, status=OrderStatus.FILLED, position_id="pos-api-001")

    # 8. Trade
    trade = TradeRecord(
        trade_id="trd-api-001",
        plan_id="plan-manual-001",
        symbol="TCS",
        side=TradeSide.BUY,
        strategy=StrategyType.MOMENTUM_CONTINUATION,
        quantity=1,
        entry_timestamp=now,
        entry_price=Decimal("3500.00"),
        entry_slippage=Decimal("0.05"),
        exit_timestamp=now,
        exit_price=Decimal("3530.00"),
        exit_slippage=Decimal("0.05"),
        exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
        gross_pnl=Decimal("30.00"),
        friction=friction,
        net_pnl=Decimal("29.50"),
        holding_duration_seconds=180.0,
        market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
        market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
    )
    repo.save_trade(trade)

    # 9. Risk Event
    repo.save_risk_event(
        event_type="CIRCUIT_BREAKER_CHECK",
        severity="INFO",
        details={"drawdown": 0.005},
        symbol="TCS",
    )

    # 10. System Event
    repo.save_system_event(
        source="SYSTEM_INIT",
        level="INFO",
        message="Backend initialized in test mode",
        metadata={"env": "test"},
    )

    # Override get_db_path in FastAPI app
    app.dependency_overrides[get_db_path] = lambda: path

    yield path

    app.dependency_overrides.clear()
    # Reset system state after test
    sys_state = get_system_state()
    sys_state.is_halted = False
    sys_state.mode = "PAPER"
    sys_state.live_trading_allowed = False

    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def client(temp_api_db):
    """Provide FastAPI TestClient bound to isolated test database."""
    return TestClient(app)


# =====================================================================
# 1. OpenAPI & Documentation Tests
# =====================================================================


def test_root_and_openapi_documentation(client):
    """Verify OpenAPI 3.x schema and interactive documentation endpoints."""
    # Root
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert r_root.json()["status"] == "online"

    # OpenAPI schema
    r_schema = client.get("/api/v1/openapi.json")
    assert r_schema.status_code == 200
    schema = r_schema.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/api/v1/dashboard/summary" in schema["paths"]
    assert "/api/v1/system/kill-switch" in schema["paths"]
    assert "/api/v1/trades/approve/{plan_id}" in schema["paths"]

    # Basic Health
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"


# =====================================================================
# 2. All 13 Safe Read/Query API Endpoints Tests
# =====================================================================


def test_safe_read_dashboard_and_capital(client):
    """Verify 1. dashboard summary and capital telemetry."""
    r_dash = client.get("/api/v1/dashboard/summary")
    assert r_dash.status_code == 200
    data = r_dash.json()
    assert "total_equity" in data
    assert data["total_equity"] == "100.00"
    assert data["open_positions_count"] >= 1
    assert data["system_mode"] == "PAPER"
    assert data["live_trading_allowed"] is False

    r_cap = client.get("/api/v1/telemetry/capital")
    assert r_cap.status_code == 200
    cap = r_cap.json()
    assert cap["total_capital"] == "100.00"
    assert cap["currency"] == "INR"


def test_safe_read_market_scanner_and_features(client):
    """Verify 2. market scanner and symbol features."""
    r_scanner = client.get("/api/v1/market/scanner")
    assert r_scanner.status_code == 200
    items = r_scanner.json()
    assert len(items) >= 1
    assert items[0]["symbol"] == "TCS"
    assert items[0]["momentum_score"] == "2.5"

    r_feat = client.get("/api/v1/market/features/TCS")
    assert r_feat.status_code == 200
    feat = r_feat.json()
    assert feat["symbol"] == "TCS"
    assert feat["bar_timeframe"] == "1m"

    # Non-existent symbol
    r_nf = client.get("/api/v1/market/features/NONEXISTENT")
    assert r_nf.status_code == 404


def test_safe_read_candidates(client):
    """Verify 3. candidates query."""
    r = client.get("/api/v1/candidates")
    assert r.status_code == 200
    candidates = r.json()
    assert len(candidates) >= 1
    assert candidates[0]["candidate_id"] == "cand-api-001"
    assert candidates[0]["symbol"] == "TCS"

    # Single candidate
    r_single = client.get("/api/v1/candidates/cand-api-001")
    assert r_single.status_code == 200
    assert r_single.json()["rank_score"] == "92.0"

    # 404 on unknown
    assert client.get("/api/v1/candidates/unknown").status_code == 404


def test_safe_read_positions(client):
    """Verify 4. positions query."""
    r = client.get("/api/v1/positions?status=OPEN")
    assert r.status_code == 200
    positions = r.json()
    assert len(positions) >= 1
    assert positions[0]["position_id"] == "pos-api-001"
    assert positions[0]["symbol"] == "TCS"
    assert float(positions[0]["unrealized_pnl"]) == 25.0

    r_single = client.get("/api/v1/positions/pos-api-001")
    assert r_single.status_code == 200
    assert r_single.json()["status"] == "OPEN"

    assert client.get("/api/v1/positions/unknown").status_code == 404


def test_safe_read_orders(client):
    """Verify 5. orders query."""
    r = client.get("/api/v1/orders")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) >= 1
    assert orders[0]["client_order_id"] == "order-api-001"

    r_single = client.get("/api/v1/orders/order-api-001")
    assert r_single.status_code == 200
    assert r_single.json()["status"] == "FILLED"

    assert client.get("/api/v1/orders/unknown").status_code == 404


def test_safe_read_trades_and_plans(client):
    """Verify 6. trades and trade plans query."""
    r_trades = client.get("/api/v1/trades")
    assert r_trades.status_code == 200
    trades = r_trades.json()
    assert len(trades) >= 1
    assert trades[0]["trade_id"] == "trd-api-001"
    assert float(trades[0]["net_pnl"]) == 29.50

    r_single = client.get("/api/v1/trades/trd-api-001")
    assert r_single.status_code == 200
    assert r_single.json()["exit_trigger"] == "TAKE_PROFIT"

    r_plans = client.get("/api/v1/trade-plans")
    assert r_plans.status_code == 200
    plans = r_plans.json()
    assert len(plans) >= 1
    assert plans[0]["plan_id"] == "plan-manual-001"
    assert plans[0]["approval_mode"] == "MANUAL_PENDING"


def test_safe_read_pnl(client):
    """Verify 7. P/L summary and statutory friction breakdown."""
    r = client.get("/api/v1/pnl")
    assert r.status_code == 200
    pnl = r.json()
    assert "realized_pnl" in pnl
    assert "total_friction" in pnl
    assert pnl["currency"] == "INR"

    r_bd = client.get("/api/v1/pnl/breakdown")
    assert r_bd.status_code == 200
    bd = r_bd.json()
    assert "friction_itemization" in bd
    assert "stt" in bd["friction_itemization"]
    assert "gst" in bd["friction_itemization"]


def test_safe_read_ai_analyses_and_latency(client):
    """Verify 8. AI analysis qualitative reports and latency telemetry."""
    r = client.get("/api/v1/ai/analyses")
    assert r.status_code == 200
    analyses = r.json()
    assert len(analyses) >= 2

    r_cand = client.get("/api/v1/ai/analyses/cand-api-001")
    assert r_cand.status_code == 200
    res = r_cand.json()
    assert res["candidate_id"] == "cand-api-001"
    assert res["analyst_thesis"] is not None
    assert res["challenger_critique"] is not None

    r_lat = client.get("/api/v1/ai/latency")
    assert r_lat.status_code == 200


def test_safe_read_performance(client):
    """Verify 9. performance metrics and strategy stratification."""
    r = client.get("/api/v1/performance")
    assert r.status_code == 200
    perf = r.json()
    assert "win_rate" in perf
    assert "profit_factor" in perf

    r_strat = client.get("/api/v1/performance/strategies")
    assert r_strat.status_code == 200

    r_exec = client.get("/api/v1/performance/execution")
    assert r_exec.status_code == 200


def test_safe_read_backtests(client):
    """Verify 10. backtest runs and reports."""
    r = client.get("/api/v1/backtests")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) >= 1
    run_id = runs[0]["run_id"]

    r_single = client.get(f"/api/v1/backtests/{run_id}")
    assert r_single.status_code == 200
    report = r_single.json()
    assert report["run_id"] == run_id
    assert "metrics" in report
    assert "equity_curve" in report


def test_safe_read_risk(client):
    """Verify 11. risk monitoring, limits, and circuit breaker status."""
    r_status = client.get("/api/v1/risk/status")
    assert r_status.status_code == 200
    st = r_status.json()
    assert st["circuit_breaker_tripped"] is False
    assert st["max_positions_cap"] == 2

    r_events = client.get("/api/v1/risk/events")
    assert r_events.status_code == 200
    assert len(r_events.json()) >= 1

    r_limits = client.get("/api/v1/risk/limits")
    assert r_limits.status_code == 200
    lim = r_limits.json()
    assert lim["max_daily_drawdown_pct"] == "0.03"
    assert lim["intraday_cutoff_ist"] == "15:15 IST"


def test_safe_read_system_health(client):
    """Verify 12. system health and component connectivity status."""
    r = client.get("/api/v1/system/health")
    assert r.status_code == 200
    h = r.json()
    assert h["status"] in ("HEALTHY", "WARNING", "CRITICAL")
    assert h["database"] in ("CONNECTED_WAL", "WARNING_NON_WAL")
    assert h["mode"] == "PAPER"
    assert h["live_trading_allowed"] is False

    r_st = client.get("/api/v1/system/status")
    assert r_st.status_code == 200
    assert r_st.json()["status"] == "OPERATIONAL"


def test_runtime_env(client):
    """Verify safe, read-only runtime diagnostics endpoint returns expected keys."""
    r = client.get("/api/v1/system/runtime-env")
    assert r.status_code == 200
    data = r.json()

    expected_keys = {
        "project_name",
        "version",
        "python_version",
        "platform",
        "is_paper_trading",
        "database_path",
        "database_journal_mode",
    }
    assert expected_keys.issubset(data.keys())

    assert data["project_name"] == "AI Micro-Trading Agent"
    assert isinstance(data["version"], str) and len(data["version"]) > 0
    assert isinstance(data["python_version"], str) and len(data["python_version"]) > 0
    assert isinstance(data["platform"], str) and len(data["platform"]) > 0
    assert data["is_paper_trading"] is True
    assert isinstance(data["database_path"], str) and len(data["database_path"]) > 0
    assert data["database_journal_mode"].lower() in ("wal", "memory", "unknown")


def test_safe_read_logs_and_audit_trail(client):
    """Verify 13. system event logs and complete decision audit trail."""
    r_logs = client.get("/api/v1/logs/system")
    assert r_logs.status_code == 200
    assert len(r_logs.json()) >= 1

    # Audit trail for cand-api-001
    r_audit = client.get("/api/v1/logs/audit/cand-api-001")
    assert r_audit.status_code == 200
    trail = r_audit.json()
    assert trail["candidate_id"] == "cand-api-001"
    assert trail["candidate"] is not None
    assert trail["features"] is not None
    assert len(trail["ai_analyses"]) >= 2
    assert trail["trade_plan"] is not None
    assert trail["is_fully_reproducible"] is True


# =====================================================================
# 3. Guard Against Arbitrary Order Creation (PDF Constraint)
# =====================================================================


def test_arbitrary_order_execution_endpoint_not_exposed(client):
    """Verify system does NOT expose unrestricted arbitrary order execution.

    Direct POST /api/v1/orders must return 405 Method Not Allowed or 404 Not Found.
    """
    payload = {"symbol": "TCS", "side": "BUY", "quantity": 10, "price": 3500.0}
    r = client.post("/api/v1/orders", json=payload)
    # 405 Method Not Allowed because GET /orders exists, but POST does not
    assert r.status_code in (404, 405)


# =====================================================================
# 4. Guarded Mutation: TradePlan Approval & Rejection Flow
# =====================================================================


def test_guarded_trade_plan_approval_and_rejection(client):
    """Verify guarded approval mutation dispatches order only via validated TradePlan."""
    # 1. Approval without confirmation fails (400)
    r_unconfirmed = client.post(
        "/api/v1/trades/approve/plan-manual-001",
        json={"confirm": False},
    )
    assert r_unconfirmed.status_code == 400

    # 2. Confirmed approval succeeds
    r_ok = client.post(
        "/api/v1/trades/approve/plan-manual-001",
        json={"confirm": True, "operator_notes": "Authorized by operator"},
    )
    assert r_ok.status_code == 200
    resp = r_ok.json()
    assert resp["success"] is True
    assert resp["approval_mode"] == "MANUAL_APPROVED"
    assert resp["client_order_id"] == "ord-plan-manual-001"

    # 3. Repeated approval on already approved plan fails (400)
    r_repeat = client.post(
        "/api/v1/trades/approve/plan-manual-001",
        json={"confirm": True},
    )
    assert r_repeat.status_code == 400

    # 4. Rejection on unknown plan fails (404)
    assert client.post("/api/v1/trades/reject/unknown").status_code == 404


# =====================================================================
# 5. Live Trading Security Lockout & Approval Controls
# =====================================================================


def test_live_trading_security_lockout_and_approval_controls(client):
    """Verify live-trading endpoints are protected behind explicit multi-layer approvals."""
    # 1. Missing confirmation fails (400)
    r1 = client.post(
        "/api/v1/system/mode",
        json={"target_mode": "LIVE", "confirmation": False},
    )
    assert r1.status_code == 400

    # 2. In paper trading configuration, live mode switch is strictly forbidden (403)
    r2 = client.post(
        "/api/v1/system/mode",
        json={
            "target_mode": "LIVE",
            "confirmation": True,
            "live_trading_approval_token": "DUMMY_TOKEN",
        },
    )
    assert r2.status_code == 403
    assert "prohibited by configuration" in r2.json()["detail"].lower()

    # 3. Switching back to PAPER mode is always safe and permitted
    r3 = client.post(
        "/api/v1/system/mode",
        json={"target_mode": "PAPER", "confirmation": True},
    )
    assert r3.status_code == 200
    assert r3.json()["current_mode"] == "PAPER"


# =====================================================================
# 6. Emergency Kill Switch Mutation
# =====================================================================


def test_emergency_kill_switch_intervention(client):
    """Verify emergency kill switch closes positions, cancels orders, and halts trading."""
    # Missing confirmation fails (400)
    r_unconfirmed = client.post(
        "/api/v1/system/kill-switch",
        json={"confirm": False},
    )
    assert r_unconfirmed.status_code == 400

    # Trigger confirmed kill-switch
    r_kill = client.post(
        "/api/v1/system/kill-switch",
        json={"confirm": True, "reason": "Severe network latency test"},
    )
    assert r_kill.status_code == 200
    kill_data = r_kill.json()
    assert kill_data["success"] is True
    assert kill_data["system_halted"] is True

    # System health immediately reflects critical / halted status
    r_health = client.get("/api/v1/system/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "CRITICAL"
    assert r_health.json()["execution_engine"] == "SUSPENDED"

    # Further trade approvals are blocked while halted
    r_blocked = client.post(
        "/api/v1/trades/approve/plan-manual-001",
        json={"confirm": True},
    )
    assert r_blocked.status_code == 400
    assert "halted" in r_blocked.json()["detail"].lower()
