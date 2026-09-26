"""Formal data contracts and schemas for Phase 31 Multi-Strategy Portfolio.

Defines models for:
- Independent Strategy Validation Reports
- Strategy Capital Allocations & Weights
- Deterministic Concentration Limits and Exposure Metrics
- Multi-Strategy Portfolio Summary
- Reallocation Requests & Security Errors
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.models.contracts import StrategyType


class StrategyValidationStatus(str, Enum):
    """Validation lifecycle status for individual strategies."""

    VALIDATED = "VALIDATED"
    PROBATION = "PROBATION"
    DISQUALIFIED = "DISQUALIFIED"


class AllocationMethod(str, Enum):
    """Deterministic allocation methodology."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    RISK_PARITY_VOLATILITY = "RISK_PARITY_VOLATILITY"
    PERFORMANCE_SHARPE = "PERFORMANCE_SHARPE"
    MANUAL_OPERATOR = "MANUAL_OPERATOR"


class StrategyValidationReport(BaseModel):
    """Independent quantitative validation report for a trading strategy."""

    strategy_type: StrategyType
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: StrategyValidationStatus
    trades_count: int
    win_rate_pct: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    is_validated: bool
    rejection_reasons: list[str] = Field(default_factory=list)
    details: str


class StrategyAllocation(BaseModel):
    """Capital allocation state for an individual trading strategy."""

    strategy_type: StrategyType
    target_weight_pct: Decimal = Field(..., description="Target allocation weight percentage (0 - 100)")
    allocated_capital: Decimal = Field(..., description="Absolute capital allocated in INR")
    deployed_capital: Decimal = Field(default=Decimal("0.00"), description="Capital currently engaged in open positions")
    available_capital: Decimal = Field(..., description="Remaining uncommitted capital for this strategy")
    active_positions_count: int = Field(default=0)
    max_concurrent_positions: int = Field(default=2)
    validation_status: StrategyValidationStatus = StrategyValidationStatus.VALIDATED


class ConcentrationLimits(BaseModel):
    """Deterministic concentration boundaries for portfolio safety."""

    max_single_strategy_pct: Decimal = Field(default=Decimal("60.00"), description="Max % capital in one strategy")
    max_single_symbol_pct: Decimal = Field(default=Decimal("40.00"), description="Max % capital in a single stock")
    max_single_sector_pct: Decimal = Field(default=Decimal("50.00"), description="Max % capital in a single sector")
    max_gross_exposure_pct: Decimal = Field(default=Decimal("100.00"), description="Max total deployed / total equity %")


class ConcentrationMetrics(BaseModel):
    """Current cross-sectional concentration and exposure telemetry."""

    strategy_concentrations: dict[str, Decimal] = Field(default_factory=dict)
    symbol_concentrations: dict[str, Decimal] = Field(default_factory=dict)
    sector_concentrations: dict[str, Decimal] = Field(default_factory=dict)
    gross_exposure_pct: Decimal
    is_within_limits: bool
    violations: list[str] = Field(default_factory=list)


class MultiStrategyPortfolioSummary(BaseModel):
    """Unified multi-strategy portfolio status and telemetry snapshot."""

    portfolio_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_capital: Decimal
    available_cash: Decimal
    deployed_capital: Decimal
    allocation_method: AllocationMethod
    allocations: list[StrategyAllocation]
    concentrations: ConcentrationMetrics
    limits: ConcentrationLimits
    active_positions_total: int
    unallocated_cash: Decimal = Decimal("0.00")


class ReallocationRequest(BaseModel):
    """Request to update strategy allocation weights."""

    weights: dict[StrategyType, Decimal] = Field(..., description="Target weights summing to 100.0")
    allocation_method: AllocationMethod = AllocationMethod.MANUAL_OPERATOR
    operator_token: str = Field(..., description="Authorization token matching OPERATOR-PORTFOLIO-REALLOC-*")
    reason: str = Field(..., description="Audit rationale for reallocation")


class PortfolioAllocationError(Exception):
    """Raised when portfolio exposure, concentration, or strategy validation limits are breached."""
