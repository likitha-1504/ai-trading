"""Comprehensive test suite for Phase 31 Multi-Strategy Portfolio.

Tests cover:
- Independent Strategy Validation (Validated, Probation, Disqualified)
- Deterministic Concentration Engine (Gross, Strategy, Symbol, Sector bounds)
- Multi-Strategy Portfolio Manager (Allocations, Capital Release, PnL accounting)
- Operator-Authorized Rebalancing & Anti-Unvalidated Allocation Governance
- FastAPI REST API Endpoints & Schemas
- Operational CLI Runner Execution
"""

from __future__ import annotations

import subprocess
import sys
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.contracts import StrategyType
from app.portfolio.concentration_engine import ConcentrationEngine
from app.portfolio.models import (
    AllocationMethod,
    PortfolioAllocationError,
    StrategyValidationStatus,
)
from app.portfolio.portfolio_manager import MultiStrategyPortfolioManager
from app.portfolio.strategy_validator import StrategyValidator


def test_strategy_validator_valid_strategy() -> None:
    """Tests that a strategy satisfying all 5 criteria is VALIDATED."""
    report = StrategyValidator.validate_strategy(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        trades_count=25,
        win_rate_pct=Decimal("60.00"),
        profit_factor=Decimal("1.50"),
        sharpe_ratio=Decimal("1.20"),
        max_drawdown_pct=Decimal("10.00"),
    )
    assert report.is_validated is True
    assert report.status == StrategyValidationStatus.VALIDATED
    assert len(report.rejection_reasons) == 0


def test_strategy_validator_probation() -> None:
    """Tests that a strategy with insufficient sample size is placed on PROBATION."""
    report = StrategyValidator.validate_strategy(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trades_count=10,  # Below 15
        win_rate_pct=Decimal("60.00"),
        profit_factor=Decimal("1.50"),
        sharpe_ratio=Decimal("1.20"),
        max_drawdown_pct=Decimal("10.00"),
    )
    assert report.is_validated is False
    assert report.status == StrategyValidationStatus.PROBATION
    assert "Sample size insufficient" in report.rejection_reasons[0]


def test_strategy_validator_disqualified() -> None:
    """Tests that a strategy breaching performance thresholds is DISQUALIFIED."""
    report = StrategyValidator.validate_strategy(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trades_count=30,
        win_rate_pct=Decimal("42.00"),  # Below 50%
        profit_factor=Decimal("0.90"),   # Below 1.20
        sharpe_ratio=Decimal("0.10"),    # Below 0.50
        max_drawdown_pct=Decimal("25.00"),  # Above 20%
    )
    assert report.is_validated is False
    assert report.status == StrategyValidationStatus.DISQUALIFIED
    assert len(report.rejection_reasons) >= 4


def test_concentration_engine_within_limits() -> None:
    """Tests that a standard trade well within limits is admitted."""
    engine = ConcentrationEngine()
    admitted, reason = engine.evaluate_admission(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="RELIANCE",
        proposed_capital=Decimal("25.00"),
        total_equity=Decimal("100.00"),
        current_strategy_deployed={"MOMENTUM_CONTINUATION": Decimal("10.00")},
        current_symbol_deployed={"RELIANCE": Decimal("10.00")},
        current_sector_deployed={"NIFTY_ENERGY": Decimal("10.00")},
    )
    assert admitted is True
    assert "within all exposure and concentration bounds" in reason


def test_concentration_engine_gross_exposure_breach() -> None:
    """Tests rejection when proposed trade breaches 100% gross exposure."""
    engine = ConcentrationEngine()
    admitted, reason = engine.evaluate_admission(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="INFY",
        proposed_capital=Decimal("30.00"),
        total_equity=Decimal("100.00"),
        current_strategy_deployed={"MOMENTUM_CONTINUATION": Decimal("80.00")},
        current_symbol_deployed={},
        current_sector_deployed={},
    )
    assert admitted is False
    assert "Gross exposure limit breached" in reason


def test_concentration_engine_strategy_concentration_breach() -> None:
    """Tests rejection when a single strategy exceeds 60% concentration."""
    engine = ConcentrationEngine()
    admitted, reason = engine.evaluate_admission(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="INFY",
        proposed_capital=Decimal("25.00"),
        total_equity=Decimal("100.00"),
        current_strategy_deployed={"MOMENTUM_CONTINUATION": Decimal("40.00")},
        current_symbol_deployed={},
        current_sector_deployed={},
    )
    assert admitted is False
    assert "Strategy concentration limit breached" in reason


def test_concentration_engine_symbol_concentration_breach() -> None:
    """Tests rejection when a single symbol exceeds 40% concentration."""
    engine = ConcentrationEngine()
    admitted, reason = engine.evaluate_admission(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        symbol="TCS",
        proposed_capital=Decimal("20.00"),
        total_equity=Decimal("100.00"),
        current_strategy_deployed={"EARLY_MOVE_DETECTION": Decimal("25.00")},
        current_symbol_deployed={"TCS": Decimal("25.00")},
        current_sector_deployed={"NIFTY_IT": Decimal("25.00")},
    )
    assert admitted is False
    assert "Symbol concentration limit breached" in reason


def test_concentration_engine_sector_concentration_breach() -> None:
    """Tests rejection when a single sector exceeds 50% concentration."""
    engine = ConcentrationEngine()
    # INFY is in NIFTY_IT
    admitted, reason = engine.evaluate_admission(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="INFY",
        proposed_capital=Decimal("15.00"),
        total_equity=Decimal("100.00"),
        current_strategy_deployed={"MOMENTUM_CONTINUATION": Decimal("40.00")},
        current_symbol_deployed={"TCS": Decimal("40.00")},
        current_sector_deployed={"NIFTY_IT": Decimal("40.00")},
    )
    assert admitted is False
    assert "Sector concentration limit breached" in reason


def test_portfolio_manager_initialization() -> None:
    """Tests default portfolio allocations and strategy validation state."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))
    summary = mgr.get_portfolio_summary()

    assert summary.total_capital == Decimal("100.00")
    assert summary.available_cash == Decimal("100.00")
    assert summary.deployed_capital == Decimal("0.00")
    assert len(summary.allocations) == 2

    # Momentum: 50%, ₹50 allocated
    mom = next(a for a in summary.allocations if a.strategy_type == StrategyType.MOMENTUM_CONTINUATION)
    assert mom.target_weight_pct == Decimal("50.00")
    assert mom.allocated_capital == Decimal("50.00")
    assert mom.validation_status == StrategyValidationStatus.VALIDATED


def test_portfolio_manager_unvalidated_strategy_rejection() -> None:
    """Tests that unvalidated or disqualified strategies are barred from allocation."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    # Register disqualified report for Early Move
    disq_report = StrategyValidator.validate_strategy(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trades_count=5,  # Probation/invalid
        win_rate_pct=Decimal("40.00"),
        profit_factor=Decimal("0.80"),
        sharpe_ratio=Decimal("0.10"),
        max_drawdown_pct=Decimal("30.00"),
    )
    mgr.register_validation_report(disq_report)

    ok, reason = mgr.evaluate_and_allocate(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        symbol="INFY",
        required_capital=Decimal("10.00"),
    )
    assert ok is False
    assert "is not independently validated" in reason


def test_portfolio_manager_allocate_and_release() -> None:
    """Tests full lifecycle: allocation locks capital, release restores capital with PnL."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    ok, _reason = mgr.evaluate_and_allocate(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="RELIANCE",
        required_capital=Decimal("30.00"),
    )
    assert ok is True

    summary = mgr.get_portfolio_summary()
    assert summary.deployed_capital == Decimal("30.00")
    assert summary.available_cash == Decimal("70.00")
    assert summary.active_positions_total == 1

    # Release capital with ₹1.50 profit
    mgr.release_allocation(
        strategy_type=StrategyType.MOMENTUM_CONTINUATION,
        symbol="RELIANCE",
        returned_capital=Decimal("30.00"),
        realized_pnl=Decimal("1.50"),
    )

    summary_after = mgr.get_portfolio_summary()
    assert summary_after.deployed_capital == Decimal("0.00")
    assert summary_after.total_capital == Decimal("101.50")
    assert summary_after.available_cash == Decimal("101.50")
    assert summary_after.active_positions_total == 0


def test_portfolio_manager_reallocate_authorized() -> None:
    """Tests valid operator reallocation changes target weights."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    mgr.reallocate_weights(
        weights={
            StrategyType.MOMENTUM_CONTINUATION: Decimal("60.00"),
            StrategyType.EARLY_MOVE_DETECTION: Decimal("40.00"),
        },
        method=AllocationMethod.MANUAL_OPERATOR,
        operator_token="OPERATOR-PORTFOLIO-REALLOC-20260926-TEST",
        reason="Performance skew towards Momentum",
    )

    summary = mgr.get_portfolio_summary()
    mom = next(a for a in summary.allocations if a.strategy_type == StrategyType.MOMENTUM_CONTINUATION)
    assert mom.target_weight_pct == Decimal("60.00")
    assert mom.allocated_capital == Decimal("60.00")


def test_portfolio_manager_reallocate_unauthorized() -> None:
    """Tests that missing or invalid operator token raises PortfolioAllocationError."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    with pytest.raises(PortfolioAllocationError, match="Unauthorized portfolio reallocation"):
        mgr.reallocate_weights(
            weights={
                StrategyType.MOMENTUM_CONTINUATION: Decimal("60.00"),
                StrategyType.EARLY_MOVE_DETECTION: Decimal("40.00"),
            },
            method=AllocationMethod.MANUAL_OPERATOR,
            operator_token="INVALID-TOKEN",
            reason="Unauthorized attempt",
        )


def test_portfolio_manager_reallocate_unvalidated_strategy() -> None:
    """Tests that attempting to allocate weight to an unvalidated strategy is blocked."""
    mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))

    # Disqualify Early Move
    disq = StrategyValidator.validate_strategy(
        strategy_type=StrategyType.EARLY_MOVE_DETECTION,
        trades_count=5,
        win_rate_pct=Decimal("30.00"),
        profit_factor=Decimal("0.50"),
        sharpe_ratio=Decimal("0.00"),
        max_drawdown_pct=Decimal("35.00"),
    )
    mgr.register_validation_report(disq)

    with pytest.raises(PortfolioAllocationError, match="Cannot allocate capital to unvalidated strategy"):
        mgr.reallocate_weights(
            weights={
                StrategyType.MOMENTUM_CONTINUATION: Decimal("50.00"),
                StrategyType.EARLY_MOVE_DETECTION: Decimal("50.00"),
            },
            method=AllocationMethod.MANUAL_OPERATOR,
            operator_token="OPERATOR-PORTFOLIO-REALLOC-20260926-TEST",
            reason="Invalid allocation attempt",
        )


def test_fastapi_portfolio_endpoints() -> None:
    """Tests all FastAPI portfolio endpoints."""
    client = TestClient(app)

    # 1. Summary
    res_sum = client.get("/api/v1/portfolio/summary")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert "total_capital" in data_sum
    assert "allocations" in data_sum
    assert "concentrations" in data_sum

    # 2. Strategies
    res_strats = client.get("/api/v1/portfolio/strategies")
    assert res_strats.status_code == 200
    assert len(res_strats.json()) >= 2

    # 3. Concentrations
    res_conc = client.get("/api/v1/portfolio/concentrations")
    assert res_conc.status_code == 200
    assert "gross_exposure_pct" in res_conc.json()

    # 4. Reallocate with valid token
    realloc_payload = {
        "weights": {
            "MOMENTUM_CONTINUATION": "60.00",
            "EARLY_MOVE_DETECTION": "40.00",
        },
        "allocation_method": "MANUAL_OPERATOR",
        "operator_token": "OPERATOR-PORTFOLIO-REALLOC-20260926-API",
        "reason": "API rebalance test",
    }
    res_real = client.post("/api/v1/portfolio/reallocate", json=realloc_payload)
    assert res_real.status_code == 200

    # 5. Reallocate with invalid token (403)
    realloc_bad = dict(realloc_payload)
    realloc_bad["operator_token"] = "BAD-TOKEN"
    res_bad = client.post("/api/v1/portfolio/reallocate", json=realloc_bad)
    assert res_bad.status_code == 403

    # 6. Validate strategy on-demand
    res_val = client.post(
        "/api/v1/portfolio/validate-strategy?strategy_type=MOMENTUM_CONTINUATION&trades_count=30&win_rate_pct=65.0&profit_factor=1.8&sharpe_ratio=2.1&max_drawdown_pct=5.0"
    )
    assert res_val.status_code == 200
    assert res_val.json()["is_validated"] is True


def test_cli_portfolio_runner() -> None:
    """Tests portfolio CLI runner under standard and flag executions."""
    # Standard ASCII dashboard
    res_ascii = subprocess.run(
        [sys.executable, "backend/scripts/portfolio_runner.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_ascii.returncode == 0
    assert "PHASE 31 MULTI-STRATEGY PORTFOLIO AUDIT DASHBOARD" in res_ascii.stdout

    # JSON streaming
    res_json = subprocess.run(
        [sys.executable, "backend/scripts/portfolio_runner.py", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_json.returncode == 0
    assert '"total_capital":' in res_json.stdout

    # Validate flag
    res_val = subprocess.run(
        [sys.executable, "backend/scripts/portfolio_runner.py", "--validate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_val.returncode == 0
    assert "Strategy MOMENTUM_CONTINUATION: Validated=True" in res_val.stdout
