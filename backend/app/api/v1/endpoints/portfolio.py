"""FastAPI REST API Endpoints for Phase 31 Multi-Strategy Portfolio.

Exposes endpoints for:
- Portfolio summary and allocations
- Independent strategy validation reports
- Cross-sectional concentration and gross exposure
- Operator-authorized strategy weight reallocation
- On-demand strategy validation evaluation
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from app.models.contracts import StrategyType
from app.portfolio.models import (
    ConcentrationMetrics,
    MultiStrategyPortfolioSummary,
    PortfolioAllocationError,
    ReallocationRequest,
    StrategyValidationReport,
)
from app.portfolio.portfolio_manager import MultiStrategyPortfolioManager
from app.portfolio.strategy_validator import StrategyValidator

router = APIRouter(prefix="/portfolio", tags=["Multi-Strategy Portfolio"])

# Shared portfolio manager instance
_portfolio_mgr = MultiStrategyPortfolioManager(total_capital=Decimal("100.00"))


@router.get("/summary", response_model=MultiStrategyPortfolioSummary)
def get_portfolio_summary() -> MultiStrategyPortfolioSummary:
    """Returns the unified multi-strategy portfolio summary."""
    return _portfolio_mgr.get_portfolio_summary()


@router.get("/strategies", response_model=list[StrategyValidationReport])
def list_strategy_validations() -> list[StrategyValidationReport]:
    """Returns independent validation reports for all known trading strategies."""
    reports = []
    for strat in StrategyType:
        rep = _portfolio_mgr.get_validation_report(strat)
        if rep:
            reports.append(rep)
    return reports


@router.get("/concentrations", response_model=ConcentrationMetrics)
def get_portfolio_concentrations() -> ConcentrationMetrics:
    """Returns cross-sectional concentration metrics across strategies, symbols, and sectors."""
    summary = _portfolio_mgr.get_portfolio_summary()
    return summary.concentrations


@router.post("/reallocate", response_model=MultiStrategyPortfolioSummary)
def reallocate_strategy_weights(req: ReallocationRequest) -> MultiStrategyPortfolioSummary:
    """Reallocates strategy capital weights with mandatory operator token authorization."""
    try:
        _portfolio_mgr.reallocate_weights(
            weights=req.weights,
            method=req.allocation_method,
            operator_token=req.operator_token,
            reason=req.reason,
        )
    except PortfolioAllocationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return _portfolio_mgr.get_portfolio_summary()


@router.post("/validate-strategy", response_model=StrategyValidationReport)
def validate_strategy_on_demand(
    strategy_type: StrategyType = Query(..., description="Strategy to validate"),
    trades_count: int = Query(..., ge=0),
    win_rate_pct: Decimal = Query(..., ge=0.0, le=100.0),
    profit_factor: Decimal = Query(..., ge=0.0),
    sharpe_ratio: Decimal = Query(...),
    max_drawdown_pct: Decimal = Query(..., ge=0.0, le=100.0),
) -> StrategyValidationReport:
    """Evaluates strategy metrics against independent validation rules."""
    report = StrategyValidator.validate_strategy(
        strategy_type=strategy_type,
        trades_count=trades_count,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct,
    )
    _portfolio_mgr.register_validation_report(report)
    return report
