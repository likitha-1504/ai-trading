"""Multi-Strategy Portfolio Manager for Phase 31.

Coordinates independent strategy validation, deterministic capital allocations,
concentration gating, and dynamic portfolio rebalancing with operator authorization.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping

from app.market_intelligence.sector_context import SectorAnalyzer
from app.models.contracts import StrategyType
from app.portfolio.concentration_engine import ConcentrationEngine
from app.portfolio.models import (
    AllocationMethod,
    ConcentrationLimits,
    MultiStrategyPortfolioSummary,
    PortfolioAllocationError,
    StrategyAllocation,
    StrategyValidationReport,
    StrategyValidationStatus,
)
from app.portfolio.strategy_validator import StrategyValidator

logger = logging.getLogger(__name__)
_PREC_2 = Decimal("0.01")


class MultiStrategyPortfolioManager:
    """Manages multi-strategy capital allocation and deterministic concentration limits."""

    def __init__(
        self,
        total_capital: Decimal = Decimal("100.00"),
        limits: ConcentrationLimits | None = None,
        allocation_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT,
    ) -> None:
        self.portfolio_id: str = f"PORT-{uuid.uuid4().hex[:8].upper()}"
        self.total_capital: Decimal = total_capital
        self.limits: ConcentrationLimits = limits or ConcentrationLimits()
        self.concentration_engine: ConcentrationEngine = ConcentrationEngine(self.limits)
        self.allocation_method: AllocationMethod = allocation_method

        # Independent validation registry: StrategyType -> Report
        self._validation_reports: dict[StrategyType, StrategyValidationReport] = {}

        # Target allocation weights (must sum to 100.0)
        self._target_weights: dict[StrategyType, Decimal] = {
            StrategyType.MOMENTUM_CONTINUATION: Decimal("50.00"),
            StrategyType.EARLY_MOVE_DETECTION: Decimal("50.00"),
        }

        # Real-time deployed capital tracking
        self._strategy_deployed: dict[str, Decimal] = {
            StrategyType.MOMENTUM_CONTINUATION.value: Decimal("0.00"),
            StrategyType.EARLY_MOVE_DETECTION.value: Decimal("0.00"),
        }
        self._symbol_deployed: dict[str, Decimal] = {}
        self._sector_deployed: dict[str, Decimal] = {}
        self._strategy_position_counts: dict[str, int] = {
            StrategyType.MOMENTUM_CONTINUATION.value: 0,
            StrategyType.EARLY_MOVE_DETECTION.value: 0,
        }

        # Initialize default validation for baseline strategies
        self._init_default_validations()

    def _init_default_validations(self) -> None:
        """Initializes independent validation records for standard strategies."""
        # Momentum Continuation: validated in Phase 27-28
        self._validation_reports[StrategyType.MOMENTUM_CONTINUATION] = (
            StrategyValidator.validate_strategy(
                strategy_type=StrategyType.MOMENTUM_CONTINUATION,
                trades_count=45,
                win_rate_pct=Decimal("62.20"),
                profit_factor=Decimal("1.65"),
                sharpe_ratio=Decimal("1.85"),
                max_drawdown_pct=Decimal("8.50"),
            )
        )
        # Early Move Detection: validated in Phase 27-28
        self._validation_reports[StrategyType.EARLY_MOVE_DETECTION] = (
            StrategyValidator.validate_strategy(
                strategy_type=StrategyType.EARLY_MOVE_DETECTION,
                trades_count=35,
                win_rate_pct=Decimal("57.10"),
                profit_factor=Decimal("1.42"),
                sharpe_ratio=Decimal("1.40"),
                max_drawdown_pct=Decimal("11.20"),
            )
        )

    def register_validation_report(self, report: StrategyValidationReport) -> None:
        """Registers an independent validation report for a strategy."""
        self._validation_reports[report.strategy_type] = report
        # If strategy is disqualified, zero out its target allocation
        if not report.is_validated:
            self._target_weights[report.strategy_type] = Decimal("0.00")
            logger.warning(
                "Strategy %s failed independent validation; allocation target set to 0.0%%",
                report.strategy_type.value,
            )

    def get_validation_report(self, strategy_type: StrategyType) -> StrategyValidationReport | None:
        """Retrieves validation report for a strategy."""
        return self._validation_reports.get(strategy_type)

    def evaluate_and_allocate(
        self,
        strategy_type: StrategyType,
        symbol: str,
        required_capital: Decimal,
    ) -> tuple[bool, str]:
        """Evaluates trade admission and allocates capital if all bounds are satisfied.

        Enforces:
        1. Independent validation requirement: Strategy must be validated.
        2. Strategy capital ceiling: Cannot exceed strategy's allocated capital.
        3. Cross-sectional concentration limits: Gross, strategy, symbol, and sector bounds.
        """
        # 1. Independent validation gate
        val = self._validation_reports.get(strategy_type)
        if not val or not val.is_validated:
            return False, f"Strategy {strategy_type.value} is not independently validated; allocation prohibited."

        # 2. Strategy available capital check
        strat_weight = self._target_weights.get(strategy_type, Decimal("0.00"))
        strat_cap = (self.total_capital * (strat_weight / Decimal("100.00"))).quantize(_PREC_2)
        currently_deployed = self._strategy_deployed.get(strategy_type.value, Decimal("0.00"))

        if currently_deployed + required_capital > strat_cap:
            return False, (
                f"Strategy {strategy_type.value} capital ceiling exceeded: "
                f"requested {required_capital:.2f} + current {currently_deployed:.2f} > cap {strat_cap:.2f} INR."
            )

        # 3. Cross-sectional concentration evaluation
        admitted, reason = self.concentration_engine.evaluate_admission(
            strategy_type=strategy_type,
            symbol=symbol,
            proposed_capital=required_capital,
            total_equity=self.total_capital,
            current_strategy_deployed=self._strategy_deployed,
            current_symbol_deployed=self._symbol_deployed,
            current_sector_deployed=self._sector_deployed,
        )

        if not admitted:
            return False, reason

        # Commit allocation
        self._strategy_deployed[strategy_type.value] = currently_deployed + required_capital
        sym_key = symbol.upper()
        self._symbol_deployed[sym_key] = self._symbol_deployed.get(sym_key, Decimal("0.00")) + required_capital
        sec_key = SectorAnalyzer.get_sector_for_symbol(symbol)
        self._sector_deployed[sec_key] = self._sector_deployed.get(sec_key, Decimal("0.00")) + required_capital
        self._strategy_position_counts[strategy_type.value] += 1

        return True, "Allocated successfully within portfolio boundaries."

    def release_allocation(
        self,
        strategy_type: StrategyType,
        symbol: str,
        returned_capital: Decimal,
        realized_pnl: Decimal = Decimal("0.00"),
    ) -> None:
        """Releases capital back to the strategy and portfolio upon position exit."""
        strat_key = strategy_type.value
        curr_strat = self._strategy_deployed.get(strat_key, Decimal("0.00"))
        self._strategy_deployed[strat_key] = max(Decimal("0.00"), curr_strat - returned_capital)

        sym_key = symbol.upper()
        curr_sym = self._symbol_deployed.get(sym_key, Decimal("0.00"))
        self._symbol_deployed[sym_key] = max(Decimal("0.00"), curr_sym - returned_capital)

        sec_key = SectorAnalyzer.get_sector_for_symbol(symbol)
        curr_sec = self._sector_deployed.get(sec_key, Decimal("0.00"))
        self._sector_deployed[sec_key] = max(Decimal("0.00"), curr_sec - returned_capital)

        self._strategy_position_counts[strat_key] = max(0, self._strategy_position_counts.get(strat_key, 0) - 1)
        self.total_capital += realized_pnl

    def reallocate_weights(
        self,
        weights: Mapping[StrategyType, Decimal],
        method: AllocationMethod,
        operator_token: str,
        reason: str,
    ) -> None:
        """Reallocates strategy target weights requiring valid operator authorization."""
        if not operator_token or not operator_token.startswith("OPERATOR-PORTFOLIO-REALLOC-"):
            raise PortfolioAllocationError(
                "Unauthorized portfolio reallocation: explicit token 'OPERATOR-PORTFOLIO-REALLOC-*' required."
            )

        total_weight = sum(weights.values(), Decimal("0.00"))
        if abs(total_weight - Decimal("100.00")) > Decimal("0.01"):
            raise PortfolioAllocationError(
                f"Invalid weights sum: target weights must sum to 100.00%, got {total_weight:.2f}%."
            )

        # Enforce that every strategy with weight > 0 must be validated
        for strat, w in weights.items():
            if w > Decimal("0.00"):
                report = self._validation_reports.get(strat)
                if not report or not report.is_validated:
                    raise PortfolioAllocationError(
                        f"Cannot allocate capital to unvalidated strategy {strat.value}."
                    )

        self._target_weights = dict(weights)
        self.allocation_method = method
        logger.info("Portfolio reallocated via %s: %s (Reason: %s)", method.value, self._target_weights, reason)

    def get_portfolio_summary(self) -> MultiStrategyPortfolioSummary:
        """Returns comprehensive multi-strategy portfolio summary."""
        total_deployed = sum(self._strategy_deployed.values(), Decimal("0.00"))
        available_cash = max(Decimal("0.00"), self.total_capital - total_deployed)

        strategy_allocations: list[StrategyAllocation] = []
        for strat in StrategyType:
            target_w = self._target_weights.get(strat, Decimal("0.00"))
            strat_cap = (self.total_capital * (target_w / Decimal("100.00"))).quantize(_PREC_2)
            deployed = self._strategy_deployed.get(strat.value, Decimal("0.00"))
            avail = max(Decimal("0.00"), strat_cap - deployed)
            val_status = (
                self._validation_reports[strat].status
                if strat in self._validation_reports
                else StrategyValidationStatus.DISQUALIFIED
            )
            strategy_allocations.append(
                StrategyAllocation(
                    strategy_type=strat,
                    target_weight_pct=target_w.quantize(_PREC_2),
                    allocated_capital=strat_cap,
                    deployed_capital=deployed.quantize(_PREC_2),
                    available_capital=avail.quantize(_PREC_2),
                    active_positions_count=self._strategy_position_counts.get(strat.value, 0),
                    validation_status=val_status,
                )
            )

        concentrations = self.concentration_engine.calculate_metrics(
            total_equity=self.total_capital,
            strategy_deployed=self._strategy_deployed,
            symbol_deployed=self._symbol_deployed,
            sector_deployed=self._sector_deployed,
        )

        total_positions = sum(self._strategy_position_counts.values())

        return MultiStrategyPortfolioSummary(
            portfolio_id=self.portfolio_id,
            timestamp=datetime.now(timezone.utc),
            total_capital=self.total_capital.quantize(_PREC_2),
            available_cash=available_cash.quantize(_PREC_2),
            deployed_capital=total_deployed.quantize(_PREC_2),
            allocation_method=self.allocation_method,
            allocations=strategy_allocations,
            concentrations=concentrations,
            limits=self.limits,
            active_positions_total=total_positions,
        )
