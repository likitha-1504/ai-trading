"""Comprehensive test suite for Phase 22 Learning & Continuous Improvement."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_path
from app.core.config import settings
from app.db.connection import init_db
from app.db.repository import DatabaseRepository
from app.learning.analytics import PostTradeAnalyticsEngine
from app.learning.learning_loop import ControlledLearningLoop
from app.learning.models import (
    ComprehensivePostTradeReport,
    ProposalStatus,
    StrategyImprovementProposal,
    UncontrolledModificationError,
    ValidationPrerequisiteError,
)
from app.main import app
from app.models.contracts import (
    FrictionBreakdown,
    MarketRegime,
    StrategyType,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)


@pytest.fixture
def isolated_learning_db(tmp_path: str) -> str:
    """Create isolated SQLite database with Phase 22 tables initialized."""
    db_file = os.path.join(str(tmp_path), "test_learning_loop.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def sample_trades() -> list[TradeRecord]:
    """Construct deterministic sample trades representing winning, losing, and friction-heavy executions."""
    now = datetime.now(timezone.utc)
    return [
        TradeRecord(
            trade_id="TR-TEST-001",
            plan_id="PLAN-001",
            symbol="SUZLON",
            side=TradeSide.BUY,
            strategy=StrategyType.MOMENTUM_CONTINUATION,
            quantity=10,
            entry_timestamp=now,
            entry_price=Decimal("50.00"),
            entry_slippage=Decimal("0.05"),
            exit_timestamp=now,
            exit_price=Decimal("52.00"),
            exit_slippage=Decimal("0.05"),
            exit_trigger=WatcherExitTrigger.TAKE_PROFIT,
            gross_pnl=Decimal("20.00"),
            friction=FrictionBreakdown(
                brokerage=Decimal("0.50"),
                stt=Decimal("0.20"),
                exchange_charges=Decimal("0.05"),
                sebi_charges=Decimal("0.01"),
                stamp_duty=Decimal("0.02"),
                gst=Decimal("0.10"),
                expected_slippage=Decimal("0.10"),
                total_friction=Decimal("0.88"),
            ),
            net_pnl=Decimal("19.12"),
            holding_duration_seconds=150.0,
            market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
            market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
        ),
        TradeRecord(
            trade_id="TR-TEST-002",
            plan_id="PLAN-002",
            symbol="IDEA",
            side=TradeSide.BUY,
            strategy=StrategyType.MOMENTUM_CONTINUATION,
            quantity=15,
            entry_timestamp=now,
            entry_price=Decimal("15.00"),
            entry_slippage=Decimal("0.10"),
            exit_timestamp=now,
            exit_price=Decimal("14.50"),
            exit_slippage=Decimal("0.10"),
            exit_trigger=WatcherExitTrigger.HARD_STOP,
            gross_pnl=Decimal("-7.50"),
            friction=FrictionBreakdown(
                brokerage=Decimal("0.40"),
                stt=Decimal("0.10"),
                exchange_charges=Decimal("0.03"),
                sebi_charges=Decimal("0.01"),
                stamp_duty=Decimal("0.02"),
                gst=Decimal("0.08"),
                expected_slippage=Decimal("0.20"),
                total_friction=Decimal("0.64"),
            ),
            net_pnl=Decimal("-8.14"),
            holding_duration_seconds=45.0,
            market_regime_at_entry=MarketRegime.HIGH_VOLATILITY_CHOP,
            market_regime_at_exit=MarketRegime.HIGH_VOLATILITY_CHOP,
        ),
        TradeRecord(
            trade_id="TR-TEST-003",
            plan_id="PLAN-003",
            symbol="ZOMATO",
            side=TradeSide.BUY,
            strategy=StrategyType.EARLY_MOVE_DETECTION,
            quantity=2,
            entry_timestamp=now,
            entry_price=Decimal("140.00"),
            entry_slippage=Decimal("0.00"),
            exit_timestamp=now,
            exit_price=Decimal("142.00"),
            exit_slippage=Decimal("0.05"),
            exit_trigger=WatcherExitTrigger.TIME_EXPIRY,
            gross_pnl=Decimal("4.00"),
            friction=FrictionBreakdown(
                brokerage=Decimal("0.30"),
                stt=Decimal("0.15"),
                exchange_charges=Decimal("0.04"),
                sebi_charges=Decimal("0.01"),
                stamp_duty=Decimal("0.02"),
                gst=Decimal("0.07"),
                expected_slippage=Decimal("0.05"),
                total_friction=Decimal("0.59"),
            ),
            net_pnl=Decimal("3.41"),
            holding_duration_seconds=300.0,
            market_regime_at_entry=MarketRegime.LOW_VOLATILITY_COMPRESSION,
            market_regime_at_exit=MarketRegime.LOW_VOLATILITY_COMPRESSION,
        ),
    ]


def test_post_trade_analytics_dimensions(isolated_learning_db: str, sample_trades: list[TradeRecord]) -> None:
    """Verify PostTradeAnalyticsEngine computes all 8 dimensions with exact mathematical precision."""
    analytics = PostTradeAnalyticsEngine(db_path=isolated_learning_db)
    report = analytics.generate_comprehensive_report(trades=sample_trades)

    assert isinstance(report, ComprehensivePostTradeReport)
    assert report.total_trades_analyzed == 3

    # Dimension 1: Strategy Performance
    assert "MOMENTUM_CONTINUATION" in report.strategy_performance
    assert "EARLY_MOVE_DETECTION" in report.strategy_performance
    assert "ALL_STRATEGIES" in report.strategy_performance
    mom_perf = report.strategy_performance["MOMENTUM_CONTINUATION"]
    assert mom_perf.total_trades == 2
    assert mom_perf.winning_trades == 1
    assert mom_perf.losing_trades == 1
    assert mom_perf.win_rate_pct == 50.0

    # Dimension 2: Regime Performance
    assert MarketRegime.BULLISH_TRENDING.value in report.regime_performance
    assert MarketRegime.HIGH_VOLATILITY_CHOP.value in report.regime_performance
    chop_perf = report.regime_performance[MarketRegime.HIGH_VOLATILITY_CHOP.value]
    assert chop_perf.total_trades == 1
    assert chop_perf.is_underperforming is True

    # Dimension 3: Feature Usefulness
    assert len(report.feature_usefulness) >= 5
    rvol_feat = next(f for f in report.feature_usefulness if "RVOL" in f.feature_name)
    assert rvol_feat.usefulness_grade in ["HIGH_SIGNAL", "MODERATE_SIGNAL"]

    # Dimension 4: False Positives
    assert len(report.false_positives) > 0
    fp = report.false_positives[0]
    assert fp.count == 1
    assert "IDEA" in fp.characteristic_features["symbols"]

    # Dimension 5: False Exits
    assert len(report.false_exits) > 0

    # Dimension 6: AI Reasoning Quality
    assert "qwen3-analyst" in report.ai_reasoning
    assert "deepseek-r1-challenger" in report.ai_reasoning
    assert report.ai_reasoning["qwen3-analyst"].avg_confidence > 0

    # Dimension 7: Execution Quality
    assert report.execution_quality.total_orders == 3
    assert report.execution_quality.fill_rate_pct == 100.0

    # Dimension 8: Cost Leakage
    assert report.cost_leakage.total_friction == Decimal("2.11")
    assert report.cost_leakage.friction_pct_at_100_cap > 0


def test_proposal_generation(isolated_learning_db: str) -> None:
    """Verify ControlledLearningLoop generates auditable versioned proposals without live modification."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()

    assert len(proposals) == 2
    for p in proposals:
        assert isinstance(p, StrategyImprovementProposal)
        assert p.status == ProposalStatus.PROPOSED
        assert p.target_version.startswith("v1.1.0")
        assert len(p.parameter_changes) >= 3

    # Check persistence in SQLite
    repo = DatabaseRepository(db_path=isolated_learning_db)
    db_props = repo.get_all_strategy_proposals()
    assert len(db_props) >= 2


def test_backtest_validation_pass_and_fail(isolated_learning_db: str) -> None:
    """Verify Stage 1 Backtest Validation gate enforces quantitative hurdles."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()
    p = proposals[0]

    # Passing backtest validation
    bt_pass = loop.validate_backtest(p.id, force_pass=True)
    assert bt_pass.meets_hurdle is True
    assert bt_pass.profit_factor >= 1.20
    assert bt_pass.win_rate_pct >= 45.0
    assert bt_pass.max_drawdown_pct <= 5.0
    assert p.status == ProposalStatus.BACKTEST_VALIDATED

    # Failing backtest validation
    p2 = proposals[1]
    bt_fail = loop.validate_backtest(p2.id, force_pass=False)
    assert bt_fail.meets_hurdle is False
    assert p2.status == ProposalStatus.BACKTEST_FAILED


def test_paper_validation_prerequisite_enforcement(isolated_learning_db: str) -> None:
    """Verify Stage 2 Paper Validation strictly requires Backtest Validation as a prerequisite."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()
    p = proposals[0]

    # Attempt paper validation before backtest validation -> Must raise ValidationPrerequisiteError
    with pytest.raises(ValidationPrerequisiteError, match="must be completed and passed before paper validation"):
        loop.validate_paper(p.id, force_pass=True)

    # Now pass backtest validation
    loop.validate_backtest(p.id, force_pass=True)

    # Now paper validation succeeds and advances proposal to PENDING_HUMAN_APPROVAL
    paper_ev = loop.validate_paper(p.id, force_pass=True)
    assert paper_ev.meets_hurdle is True
    assert paper_ev.risk_violations == 0
    assert paper_ev.sub_50ms_watcher_compliance_pct == 100.0
    assert p.status == ProposalStatus.PENDING_HUMAN_APPROVAL


def test_anti_self_modification_security_gates(isolated_learning_db: str) -> None:
    """Verify anti-self-modification guards prevent unauthorized or unvalidated production promotion."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()
    p = proposals[0]

    # Test 1: Promoting when only PROPOSED -> Must raise ValidationPrerequisiteError
    with pytest.raises(ValidationPrerequisiteError, match="Requires state PENDING_HUMAN_APPROVAL"):
        loop.promote_to_production(p.id, human_approval_token="SOME_TOKEN")

    # Complete Backtest Validation
    loop.validate_backtest(p.id, force_pass=True)

    # Test 2: Promoting when only BACKTEST_VALIDATED (without paper validation) -> Must raise ValidationPrerequisiteError
    with pytest.raises(ValidationPrerequisiteError, match="Requires state PENDING_HUMAN_APPROVAL"):
        loop.promote_to_production(p.id, human_approval_token="SOME_TOKEN")

    # Complete Paper Validation -> Status advances to PENDING_HUMAN_APPROVAL
    loop.validate_paper(p.id, force_pass=True)
    assert p.status == ProposalStatus.PENDING_HUMAN_APPROVAL

    # Test 3: Promoting with missing token -> Must raise UncontrolledModificationError
    with pytest.raises(UncontrolledModificationError, match="strictly requires verified human operator"):
        loop.promote_to_production(p.id, human_approval_token=None)

    # Test 4: Promoting with invalid token -> Must raise UncontrolledModificationError
    with pytest.raises(UncontrolledModificationError, match="Invalid operator authorization token"):
        loop.promote_to_production(p.id, human_approval_token="WRONG-TOKEN-1234")

    # Test 5: Direct live rule rewrite attempt outside gated loop -> Must raise UncontrolledModificationError
    with pytest.raises(UncontrolledModificationError, match="Silent or direct modification of live trading rules"):
        loop.guard_live_trading_immutability("malicious_agent.direct_alteration")


def test_authorized_production_promotion(isolated_learning_db: str) -> None:
    """Verify operator promotion with valid cryptographic token creates immutable version in SQLite."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()
    p = proposals[0]

    # Pass Backtest and Paper validations
    loop.validate_backtest(p.id, force_pass=True)
    loop.validate_paper(p.id, force_pass=True)

    valid_token = getattr(settings, "LIVE_TRADING_APPROVAL_TOKEN", "PROD-LIVE-APPROVAL-KEY-9981")
    promoted = loop.promote_to_production(
        proposal_id=p.id,
        human_approval_token=valid_token,
        approver="CHIEF_RISK_OFFICER",
    )

    assert promoted.status == ProposalStatus.ACTIVE_IN_PRODUCTION
    assert promoted.approved_by == "CHIEF_RISK_OFFICER"
    assert promoted.approval_token_masked is not None
    assert "PROD" in promoted.approval_token_masked or "****" in promoted.approval_token_masked

    # Verify SQLite persistence in strategy_versions
    repo = DatabaseRepository(db_path=isolated_learning_db)
    active_v = repo.get_active_strategy_version(p.strategy_name)
    assert active_v is not None
    assert active_v["version"] == p.target_version

    # Verify system audit event was recorded
    events = repo.get_recent_system_events(limit=10)
    gov_events = [e for e in events if e["source"] == "STRATEGY_GOVERNANCE"]
    assert len(gov_events) > 0
    assert "promoted to production" in gov_events[0]["message"]


def test_operator_proposal_rejection(isolated_learning_db: str) -> None:
    """Verify human operator can reject a proposal with mandatory documented rationale."""
    loop = ControlledLearningLoop(db_path=isolated_learning_db)
    proposals = loop.generate_improvement_proposals()
    p = proposals[0]

    # Rejection without rationale must fail
    with pytest.raises(UncontrolledModificationError, match="without documenting an explicit rationale"):
        loop.reject_proposal(p.id, reason="   ")

    rejected = loop.reject_proposal(p.id, reason="Parameters too restrictive for current regime.")
    assert rejected.status == ProposalStatus.REJECTED
    assert "Parameters too restrictive" in str(rejected.rejection_reason)


def test_fastapi_learning_endpoints(isolated_learning_db: str) -> None:
    """Verify FastAPI learning endpoints respond according to API contracts."""
    app.dependency_overrides[get_db_path] = lambda: isolated_learning_db
    client = TestClient(app)

    try:
        # 1. Analytics endpoint
        r_analytics = client.get("/api/v1/learning/analytics")
        assert r_analytics.status_code == 200
        data_analytics = r_analytics.json()
        assert "strategy_performance" in data_analytics
        assert "regime_performance" in data_analytics

        # 2. Generate proposals endpoint
        r_gen = client.post("/api/v1/learning/proposals/generate")
        assert r_gen.status_code == 200
        proposals_data = r_gen.json()
        assert len(proposals_data) >= 2
        p_id = proposals_data[0]["id"]

        # 3. List proposals
        r_list = client.get("/api/v1/learning/proposals")
        assert r_list.status_code == 200
        assert len(r_list.json()) >= 2

        # 4. Get specific proposal
        r_get = client.get(f"/api/v1/learning/proposals/{p_id}")
        assert r_get.status_code == 200
        assert r_get.json()["id"] == p_id

        # 5. Validate Backtest
        r_bt = client.post(f"/api/v1/learning/proposals/{p_id}/validate-backtest")
        assert r_bt.status_code == 200
        assert r_bt.json()["status"] == "BACKTEST_VALIDATED"

        # 6. Validate Paper
        r_paper = client.post(f"/api/v1/learning/proposals/{p_id}/validate-paper")
        assert r_paper.status_code == 200
        assert r_paper.json()["status"] == "PENDING_HUMAN_APPROVAL"

        # 7. Promote with invalid token -> 403 Forbidden
        r_promo_fail = client.post(
            f"/api/v1/learning/proposals/{p_id}/promote",
            json={"human_approval_token": "BAD_TOKEN", "approver": "TEST"},
        )
        assert r_promo_fail.status_code == 403

        # 8. Promote with valid token -> 200 OK
        valid_token = getattr(settings, "LIVE_TRADING_APPROVAL_TOKEN", "PROD-LIVE-APPROVAL-KEY-9981")
        r_promo_pass = client.post(
            f"/api/v1/learning/proposals/{p_id}/promote",
            json={"human_approval_token": valid_token, "approver": "OPERATOR"},
        )
        assert r_promo_pass.status_code == 200
        assert r_promo_pass.json()["status"] == "ACTIVE_IN_PRODUCTION"

        # 9. List versions
        r_versions = client.get("/api/v1/learning/versions")
        assert r_versions.status_code == 200
        assert len(r_versions.json()) > 0

        # 10. Report endpoint
        r_report = client.get("/api/v1/learning/report")
        assert r_report.status_code == 200
        assert r_report.json()["gate_status"] == "PHASE_22_GATE_CHECKPOINT_REACHED"

    finally:
        app.dependency_overrides.clear()
