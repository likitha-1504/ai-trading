"""Comprehensive test suite for Phase 18 Paper Trading Validation."""

import os
from decimal import Decimal

import pytest

from app.models.contracts import WatcherExitTrigger
from app.paper.paper_validator import (
    CandidateQualityMetrics,
    CostMetrics,
    EntryExitMetrics,
    PaperTradingValidationResult,
    PaperTradingValidator,
    PaperValidationConfig,
    RecoveryBehaviorMetrics,
    SlippageMetrics,
    WatcherBehaviorMetrics,
)
from app.paper.runner import main as runner_main


@pytest.fixture
def clean_db_path(tmp_path: str) -> str:
    """Provide a isolated sqlite db path for each test."""
    db_file = os.path.join(str(tmp_path), "test_paper_validation.db")
    return db_file


@pytest.fixture
def paper_validator(clean_db_path: str) -> PaperTradingValidator:
    """Fixture providing initialized PaperTradingValidator."""
    cfg = PaperValidationConfig(
        initial_capital=Decimal("100.00"),
        autonomous_threshold=Decimal("300.00"),
        slippage_ticks=1,
        tick_size=Decimal("0.05"),
        num_sessions=5,
        db_path=clean_db_path,
        enable_crash_recovery_test=True,
    )
    return PaperTradingValidator(config=cfg)


def test_paper_validation_full_execution(paper_validator: PaperTradingValidator) -> None:
    """Verify end-to-end execution of Phase 18 paper simulation across 5 sessions."""
    result = paper_validator.run_validation()

    assert isinstance(result, PaperTradingValidationResult)
    assert result.initial_capital == Decimal("100.00")
    assert result.trade_frequency.total_trades == 5
    assert result.win_rate_pct == 60.0  # 3 wins, 2 losses
    assert result.max_drawdown_pct <= 3.0  # within 3% circuit breaker
    assert result.candidate_quality.total_candidates_detected == 5
    assert result.entry_exit.total_orders_filled == 5
    assert result.costs.total_friction > Decimal("0.00")
    assert result.recovery_behavior.crash_injected is True
    assert result.recovery_behavior.positions_rehydrated == 1
    assert result.recovery_behavior.position_integrity_verified is True
    assert result.recovery_behavior.capital_parity_verified is True
    assert result.is_fully_reproducible is True
    assert "STOP AT PHASE 18 GATE CHECKPOINT" in result.gate_recommendation


def test_candidate_quality_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 1: Candidate quality tracking for both Strategy A and B."""
    result = paper_validator.run_validation()
    cq = result.candidate_quality

    assert isinstance(cq, CandidateQualityMetrics)
    assert cq.strategy_a_candidates >= 1
    assert cq.strategy_b_candidates >= 1
    assert cq.candidate_gate_passed == 5
    assert cq.candidate_gate_rejected == 0
    assert cq.risk_gate_passed == 5
    assert cq.average_rank_score > 80.0
    assert cq.average_expected_gross_edge > Decimal("0.00")
    assert cq.average_expected_net_edge > Decimal("0.00")


def test_entry_exit_behavior_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 2: Orders submitted, fills, and exit triggers breakdown."""
    result = paper_validator.run_validation()
    ee = result.entry_exit

    assert isinstance(ee, EntryExitMetrics)
    assert ee.total_orders_submitted == 5
    assert ee.total_orders_filled == 5
    assert ee.fill_rate_pct == 100.0
    assert ee.average_entry_delay_ms >= 0.0

    # Ensure hard stop, take profit, and time expiry were triggered
    breakdown = ee.exit_triggers_breakdown
    assert breakdown.get(WatcherExitTrigger.TAKE_PROFIT.value, 0) == 2
    assert breakdown.get(WatcherExitTrigger.HARD_STOP.value, 0) == 2
    assert breakdown.get(WatcherExitTrigger.TIME_EXPIRY.value, 0) == 1
    assert ee.average_holding_duration_seconds > 0.0


def test_cost_and_statutory_deductions_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 3: Indian market transaction fees and statutory levies."""
    result = paper_validator.run_validation()
    costs = result.costs

    assert isinstance(costs, CostMetrics)
    assert costs.brokerage > Decimal("0.00")
    assert costs.stt > Decimal("0.00")
    assert costs.exchange_charges > Decimal("0.00")
    assert costs.sebi_charges > Decimal("0.00")
    assert costs.stamp_duty > Decimal("0.00")
    assert costs.gst > Decimal("0.00")
    assert costs.total_friction == (
        costs.brokerage
        + costs.stt
        + costs.exchange_charges
        + costs.sebi_charges
        + costs.stamp_duty
        + costs.gst
        + result.slippage.total_slippage_amount
    )
    assert costs.zero_negative_edge_trades_verified is True


def test_slippage_sensitivity_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 4: Slippage sensitivity analysis across 0, 1, 2, and 3 ticks."""
    result = paper_validator.run_validation()
    slip = result.slippage

    assert isinstance(slip, SlippageMetrics)
    assert slip.modeled_slippage_ticks == 1
    assert len(slip.sensitivity_table) == 4

    ticks = [row["slippage_ticks"] for row in slip.sensitivity_table]
    assert ticks == [0, 1, 2, 3]

    # Increasing slippage must monotonically reduce net PnL
    net_pnls = [row["total_net_pnl_inr"] for row in slip.sensitivity_table]
    assert net_pnls[0] > net_pnls[1] > net_pnls[2] > net_pnls[3]


def test_model_disagreement_and_arbitration_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 8: Dual-Model Council evaluations and dispute arbitration."""
    result = paper_validator.run_validation()
    md = result.model_disagreement

    assert md.total_evaluations == 5
    assert md.qwen_proceed_count == 5
    assert md.deepseek_confirm_count == 3
    assert md.deepseek_contest_count == 2
    assert md.council_disagreement_count == 2
    assert md.council_arbitration_count == 2
    assert md.arbitration_approved_count == 2
    assert md.arbitration_rejected_count == 0
    assert md.think_tag_sanitizations_verified == 5


def test_watcher_behavior_and_llm_independence_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 9: Position Watcher operates deterministically in sub-50ms without LLM."""
    result = paper_validator.run_validation()
    wb = result.watcher_behavior

    assert isinstance(wb, WatcherBehaviorMetrics)
    assert wb.total_evaluations > 0
    assert wb.sub_50ms_compliance_rate_pct == 100.0
    assert wb.median_latency_us < 50000.0  # < 50ms (in reality < 50 µs)
    assert wb.hard_stops_executed == 2
    assert wb.profit_targets_executed == 2
    assert wb.trailing_stop_monotonicity_verified is True
    assert wb.emergency_exit_without_llm_verified is True


def test_crash_recovery_dimension(paper_validator: PaperTradingValidator) -> None:
    """Verify Dimension 11: Crash recovery rehydrates positions and verifies parity."""
    result = paper_validator.run_validation()
    rb = result.recovery_behavior

    assert isinstance(rb, RecoveryBehaviorMetrics)
    assert rb.crash_injected is True
    assert rb.positions_before_crash == 1
    assert rb.positions_rehydrated == 1
    assert rb.position_integrity_verified is True
    assert rb.stops_rehydrated_correctly is True
    assert rb.capital_parity_verified is True
    assert rb.unreconciled_orders_detected == 0


def test_validation_report_markdown_generation(paper_validator: PaperTradingValidator) -> None:
    """Verify that comprehensive markdown report contains all 11 dimensions and gate checkpoint."""
    result = paper_validator.run_validation()
    report = result.report_markdown

    assert "# Phase 18: Paper Trading Validation Report" in report
    assert "Dimension 1: Candidate Quality" in report
    assert "Dimension 2: Entry / Exit Behavior" in report
    assert "Dimension 3: Costs & Indian Statutory Levies" in report
    assert "Dimension 4: Slippage Assumptions & Sensitivity" in report
    assert "Dimension 5: Trade Frequency & Pacing" in report
    assert "Dimension 6: False Positives Analysis" in report
    assert "Dimension 7: False Exits & Whipsaw Analysis" in report
    assert "Dimension 8: Dual-Model Council Disagreement & Arbitration" in report
    assert "Dimension 9: Position Watcher Performance & LLM Independence" in report
    assert "Dimension 10: System Uptime, Telemetry & WAL Integrity" in report
    assert "Dimension 11: Crash Recovery & Reconciliation" in report
    assert "Identified Empirical Weaknesses" in report
    assert "HALT AT PHASE 18 GATE CHECKPOINT" in report
    assert "DO NOT PROCEED TO PHASE 19 OR ENABLE LIVE TRADING" in report


def test_runner_cli_execution(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that runner main function executes cleanly."""
    monkeypatch.chdir(tmp_path)
    exit_code = runner_main()
    assert exit_code == 0
    assert os.path.exists("PAPER_TRADING_VALIDATION_REPORT.md")
