"""Deterministic Concentration and Exposure Risk Engine for Phase 31.

Enforces deterministic cross-sectional boundaries across:
- Gross portfolio exposure cap (default 100.0%)
- Single strategy concentration ceiling (default 60.0%)
- Single symbol concentration ceiling (default 40.0%)
- Single sector concentration ceiling (default 50.0%)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.market_intelligence.sector_context import SectorAnalyzer
from app.models.contracts import StrategyType
from app.portfolio.models import (
    ConcentrationLimits,
    ConcentrationMetrics,
)

_PREC_2 = Decimal("0.01")


class ConcentrationEngine:
    """Enforces deterministic concentration boundaries on portfolio allocations."""

    def __init__(self, limits: ConcentrationLimits | None = None) -> None:
        self.limits = limits or ConcentrationLimits()

    def evaluate_admission(
        self,
        strategy_type: StrategyType,
        symbol: str,
        proposed_capital: Decimal,
        total_equity: Decimal,
        current_strategy_deployed: Mapping[str, Decimal],
        current_symbol_deployed: Mapping[str, Decimal],
        current_sector_deployed: Mapping[str, Decimal],
    ) -> tuple[bool, str]:
        """Evaluates whether admitting a new trade breaches any concentration bounds.

        Args:
            strategy_type: Strategy initiating the trade.
            symbol: Ticker symbol.
            proposed_capital: Capital required for this trade.
            total_equity: Current total account equity.
            current_strategy_deployed: Map of strategy -> currently deployed INR.
            current_symbol_deployed: Map of symbol -> currently deployed INR.
            current_sector_deployed: Map of sector -> currently deployed INR.

        Returns:
            Tuple of (is_admitted, reason).
        """
        if total_equity <= Decimal("0.00"):
            return False, "Total portfolio equity must be positive."

        # 1. Check Gross Exposure Limit
        total_deployed = sum(current_strategy_deployed.values(), Decimal("0.00"))
        new_total_deployed = total_deployed + proposed_capital
        new_gross_pct = (new_total_deployed / total_equity) * Decimal("100.00")

        if new_gross_pct > self.limits.max_gross_exposure_pct:
            return False, (
                f"Gross exposure limit breached: {new_gross_pct:.1f}% > allowed "
                f"{self.limits.max_gross_exposure_pct:.1f}%."
            )

        # 2. Check Single Strategy Concentration Limit
        strat_key = strategy_type.value
        curr_strat = current_strategy_deployed.get(strat_key, Decimal("0.00"))
        new_strat_deployed = curr_strat + proposed_capital
        new_strat_pct = (new_strat_deployed / total_equity) * Decimal("100.00")

        if new_strat_pct > self.limits.max_single_strategy_pct:
            return False, (
                f"Strategy concentration limit breached for {strat_key}: {new_strat_pct:.1f}% > "
                f"allowed {self.limits.max_single_strategy_pct:.1f}%."
            )

        # 3. Check Single Symbol Concentration Limit
        curr_sym = current_symbol_deployed.get(symbol.upper(), Decimal("0.00"))
        new_sym_deployed = curr_sym + proposed_capital
        new_sym_pct = (new_sym_deployed / total_equity) * Decimal("100.00")

        if new_sym_pct > self.limits.max_single_symbol_pct:
            return False, (
                f"Symbol concentration limit breached for {symbol}: {new_sym_pct:.1f}% > "
                f"allowed {self.limits.max_single_symbol_pct:.1f}%."
            )

        # 4. Check Single Sector Concentration Limit
        sector = SectorAnalyzer.get_sector_for_symbol(symbol)
        curr_sector = current_sector_deployed.get(sector, Decimal("0.00"))
        new_sector_deployed = curr_sector + proposed_capital
        new_sector_pct = (new_sector_deployed / total_equity) * Decimal("100.00")

        if new_sector_pct > self.limits.max_single_sector_pct:
            return False, (
                f"Sector concentration limit breached for {sector}: {new_sector_pct:.1f}% > "
                f"allowed {self.limits.max_single_sector_pct:.1f}%."
            )

        return True, "Admission approved: within all exposure and concentration bounds."

    def calculate_metrics(
        self,
        total_equity: Decimal,
        strategy_deployed: Mapping[str, Decimal],
        symbol_deployed: Mapping[str, Decimal],
        sector_deployed: Mapping[str, Decimal],
    ) -> ConcentrationMetrics:
        """Computes current cross-sectional concentration telemetry vs limits."""
        denom = max(Decimal("0.01"), total_equity)

        strat_concentrations = {
            k: ((v / denom) * Decimal("100.00")).quantize(_PREC_2)
            for k, v in strategy_deployed.items()
        }

        sym_concentrations = {
            k: ((v / denom) * Decimal("100.00")).quantize(_PREC_2)
            for k, v in symbol_deployed.items()
        }

        sec_concentrations = {
            k: ((v / denom) * Decimal("100.00")).quantize(_PREC_2)
            for k, v in sector_deployed.items()
        }

        total_deployed = sum(strategy_deployed.values(), Decimal("0.00"))
        gross_pct = ((total_deployed / denom) * Decimal("100.00")).quantize(_PREC_2)

        violations: list[str] = []
        if gross_pct > self.limits.max_gross_exposure_pct:
            violations.append(f"Gross exposure {gross_pct}% > {self.limits.max_gross_exposure_pct}%")

        for k, v in strat_concentrations.items():
            if v > self.limits.max_single_strategy_pct:
                violations.append(f"Strategy {k} {v}% > {self.limits.max_single_strategy_pct}%")

        for k, v in sym_concentrations.items():
            if v > self.limits.max_single_symbol_pct:
                violations.append(f"Symbol {k} {v}% > {self.limits.max_single_symbol_pct}%")

        for k, v in sec_concentrations.items():
            if v > self.limits.max_single_sector_pct:
                violations.append(f"Sector {k} {v}% > {self.limits.max_single_sector_pct}%")

        return ConcentrationMetrics(
            strategy_concentrations=strat_concentrations,
            symbol_concentrations=sym_concentrations,
            sector_concentrations=sec_concentrations,
            gross_exposure_pct=gross_pct,
            is_within_limits=len(violations) == 0,
            violations=violations,
        )
