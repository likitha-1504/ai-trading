"""Dynamic Strategy Portfolio Governor for Phase 37 Long-Term Autonomous System.

Manages the long-term portfolio lifecycle across multiple trading strategies:
- Lifecycle tracking: RESEARCH -> CANDIDATE -> PROBATION -> ACTIVE -> DEGRADED -> DECOMMISSIONED
- Continuous performance attribution & rolling metric evaluation
- Automated probation demotion and capital freezing upon edge degradation
- Governed dynamic rebalancing constrained by Phase 31 concentration limits
- Strict requirement for human approval tokens on promotions and reallocations
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.long_term_autonomous.models import (
    DynamicRebalanceProposal,
    LongTermStrategyProfile,
    PortfolioBreachError,
    ReleaseGateType,
    StrategyLifecycleStage,
)
from app.long_term_autonomous.release_gate import AutonomousReleaseGate
from app.models.contracts import StrategyType
from app.portfolio.concentration_engine import ConcentrationEngine
from app.portfolio.models import ConcentrationLimits
from app.portfolio.portfolio_manager import MultiStrategyPortfolioManager
from app.security.tamper_log import TamperEvidentAuditLogger

logger = logging.getLogger(__name__)
_PREC_2 = Decimal("0.01")


class AutonomousPortfolioGovernor:
    """Oversees multi-strategy lifecycle, performance monitoring, and governed allocation."""

    def __init__(
        self,
        portfolio_manager: MultiStrategyPortfolioManager | None = None,
        release_gate: AutonomousReleaseGate | None = None,
        audit_logger: TamperEvidentAuditLogger | None = None,
    ) -> None:
        self.portfolio_manager = portfolio_manager or MultiStrategyPortfolioManager()
        self.audit_logger = audit_logger or TamperEvidentAuditLogger()
        self.release_gate = release_gate or AutonomousReleaseGate(audit_logger=self.audit_logger)
        self.limits: ConcentrationLimits = self.portfolio_manager.limits
        self.concentration_engine = ConcentrationEngine(self.limits)

        # Strategy profiles registry
        self._profiles: dict[str, LongTermStrategyProfile] = {}
        self._init_baseline_profiles()

    def _init_baseline_profiles(self) -> None:
        """Initializes default production strategies with verified baseline performance."""
        # Momentum Continuation
        self._profiles[StrategyType.MOMENTUM_CONTINUATION.value] = LongTermStrategyProfile(
            strategy_id="STRAT-MOM-01",
            strategy_name=StrategyType.MOMENTUM_CONTINUATION.value,
            lifecycle_stage=StrategyLifecycleStage.ACTIVE,
            target_weight_pct=Decimal("50.00"),
            allocated_capital=Decimal("50.00"),
            deployed_capital=Decimal("0.00"),
            rolling_win_rate_pct=Decimal("62.20"),
            rolling_profit_factor=Decimal("1.65"),
            rolling_sharpe=Decimal("1.85"),
            rolling_max_drawdown_pct=Decimal("8.50"),
            total_trades=45,
            consecutive_losses=0,
            is_active=True,
        )
        # Early Move Detection
        self._profiles[StrategyType.EARLY_MOVE_DETECTION.value] = LongTermStrategyProfile(
            strategy_id="STRAT-EMD-01",
            strategy_name=StrategyType.EARLY_MOVE_DETECTION.value,
            lifecycle_stage=StrategyLifecycleStage.ACTIVE,
            target_weight_pct=Decimal("50.00"),
            allocated_capital=Decimal("50.00"),
            deployed_capital=Decimal("0.00"),
            rolling_win_rate_pct=Decimal("57.10"),
            rolling_profit_factor=Decimal("1.42"),
            rolling_sharpe=Decimal("1.40"),
            rolling_max_drawdown_pct=Decimal("11.20"),
            total_trades=35,
            consecutive_losses=0,
            is_active=True,
        )

    def register_candidate_strategy(
        self,
        strategy_name: str,
        initial_profile: LongTermStrategyProfile,
    ) -> None:
        """Registers a candidate strategy emerging from Phase 35 research sandbox."""
        initial_profile.lifecycle_stage = StrategyLifecycleStage.CANDIDATE
        initial_profile.target_weight_pct = Decimal("0.00")
        initial_profile.allocated_capital = Decimal("0.00")
        initial_profile.is_active = False
        self._profiles[strategy_name] = initial_profile
        logger.info("Registered candidate strategy %s in CANDIDATE stage.", strategy_name)

    def update_strategy_performance(
        self,
        strategy_name: str,
        trade_pnl: Decimal,
        is_win: bool,
    ) -> LongTermStrategyProfile:
        """Updates rolling performance attribution and enforces automated edge degradation guards."""
        profile = self._profiles.get(strategy_name)
        if not profile:
            raise KeyError(f"Strategy {strategy_name} not found in portfolio governor.")

        profile.total_trades += 1
        if is_win:
            profile.consecutive_losses = 0
        else:
            profile.consecutive_losses += 1

        # Recompute estimated rolling win rate
        prior_wins = int(profile.rolling_win_rate_pct * Decimal(str(profile.total_trades - 1)) / Decimal("100.00"))
        new_wins = prior_wins + (1 if is_win else 0)
        profile.rolling_win_rate_pct = (
            (Decimal(str(new_wins)) / Decimal(str(profile.total_trades))) * Decimal("100.00")
        ).quantize(_PREC_2)

        # Automated Edge Degradation Guard:
        # If drawdown > 15.0% or win rate < 40.0% with at least 15 trades, or >= 4 consecutive losses
        demote_triggered = False
        reason = ""
        if profile.total_trades >= 15 and profile.rolling_win_rate_pct < Decimal("40.00"):
            demote_triggered = True
            reason = f"Win rate decayed to {profile.rolling_win_rate_pct:.2f}% (< 40.0%)"
        elif profile.rolling_max_drawdown_pct > Decimal("15.00"):
            demote_triggered = True
            reason = f"Max drawdown exceeded limit: {profile.rolling_max_drawdown_pct:.2f}% (> 15.0%)"
        elif profile.consecutive_losses >= 4:
            demote_triggered = True
            reason = f"Consecutive loss limit breached: {profile.consecutive_losses} consecutive losses"

        if demote_triggered and profile.lifecycle_stage == StrategyLifecycleStage.ACTIVE:
            profile.lifecycle_stage = StrategyLifecycleStage.DEGRADED
            profile.is_active = False
            profile.target_weight_pct = Decimal("0.00")
            profile.allocated_capital = Decimal("0.00")
            profile.quarantine_reason = reason
            logger.warning(
                "AUTOMATED DEMOTION: Strategy %s demoted to DEGRADED. Capital frozen. Reason: %s",
                strategy_name,
                reason,
            )
            self.audit_logger.log_event(
                event_type="STRATEGY_DEGRADATION_DEMOTION",
                operator_id="PORTFOLIO_GOVERNOR",
                role="ADMIN",
                action="DEMOTE_STRATEGY",
                resource=strategy_name,
                details={
                    "strategy_name": strategy_name,
                    "new_stage": profile.lifecycle_stage.value,
                    "reason": reason,
                    "metrics": {
                        "trades": profile.total_trades,
                        "win_rate": float(profile.rolling_win_rate_pct),
                        "consecutive_losses": profile.consecutive_losses,
                    },
                },
            )

        profile.last_evaluated_at = datetime.now(timezone.utc)
        return profile

    def promote_strategy(
        self,
        strategy_name: str,
        target_stage: StrategyLifecycleStage,
        operator_token: str,
        operator_id: str = "OPERATOR_ADMIN",
        target_weight: Decimal = Decimal("15.00"),
    ) -> LongTermStrategyProfile:
        """Promotes strategy lifecycle stage with mandatory operator release gate."""
        profile = self._profiles.get(strategy_name)
        if not profile:
            raise KeyError(f"Strategy {strategy_name} not found.")

        # Require explicit human release token
        decision = self.release_gate.enforce_release(
            release_type=ReleaseGateType.STRATEGY_PROMOTION,
            operator_id=operator_id,
            operator_token=operator_token,
            target_identifier=strategy_name,
            parameters={
                "current_stage": profile.lifecycle_stage.value,
                "target_stage": target_stage.value,
                "target_weight": float(target_weight),
            },
        )

        # Enforce lifecycle progression invariants
        if target_stage == StrategyLifecycleStage.PROBATION:
            if target_weight > Decimal("20.00"):
                raise PortfolioBreachError(
                    f"Probation strategy weight cap exceeded: {target_weight}% > max 20.00% allowed."
                )
        elif target_stage == StrategyLifecycleStage.ACTIVE and target_weight > self.limits.max_single_strategy_pct:
            raise PortfolioBreachError(
                f"Active strategy weight exceeds concentration limit: {target_weight}% > {self.limits.max_single_strategy_pct}%."
            )

        profile.lifecycle_stage = target_stage
        profile.target_weight_pct = target_weight
        profile.is_active = True
        profile.quarantine_reason = None
        profile.last_evaluated_at = datetime.now(timezone.utc)

        logger.info(
            "Strategy %s promoted to %s with weight %s%% (Release decision: %s)",
            strategy_name,
            target_stage.value,
            target_weight,
            decision.decision_id,
        )
        return profile

    def generate_rebalance_proposal(
        self,
        method: str = "SHARPE_WEIGHTED",
    ) -> DynamicRebalanceProposal:
        """Generates dynamic weight rebalance proposal based on empirical performance."""
        proposal_id = f"REBAL-PROP-{uuid.uuid4().hex[:8].upper()}"
        active_strats = {
            k: v for k, v in self._profiles.items()
            if v.is_active and v.lifecycle_stage in (StrategyLifecycleStage.ACTIVE, StrategyLifecycleStage.PROBATION)
        }

        if not active_strats:
            raise PortfolioBreachError("No active strategies available for rebalancing.")

        proposed_weights: dict[str, Decimal] = {}

        if method == "EQUAL_WEIGHT":
            equal_w = (Decimal("100.00") / Decimal(str(len(active_strats)))).quantize(_PREC_2)
            for k in active_strats:
                proposed_weights[k] = equal_w
            # Fix rounding remainder on first item
            diff = Decimal("100.00") - sum(proposed_weights.values())
            first_key = next(iter(proposed_weights))
            proposed_weights[first_key] += diff

        elif method == "SHARPE_WEIGHTED":
            # Weight proportional to Sharpe ratio, capped at concentration limit (60%)
            sharpe_sum = sum(max(Decimal("0.10"), v.rolling_sharpe) for v in active_strats.values())
            raw_weights: dict[str, Decimal] = {}
            for k, v in active_strats.items():
                s = max(Decimal("0.10"), v.rolling_sharpe)
                raw_weights[k] = ((s / sharpe_sum) * Decimal("100.00")).quantize(_PREC_2)

            # Cap individual strategy at max_strategy_allocation_pct (60%)
            max_cap = self.limits.max_single_strategy_pct
            for k, w in raw_weights.items():
                proposed_weights[k] = min(max_cap, w)

            # Normalize to 100%
            current_sum = sum(proposed_weights.values())
            if current_sum != Decimal("100.00") and current_sum > Decimal("0.00"):
                diff = Decimal("100.00") - current_sum
                # allocate diff to non-capped strategies
                non_capped = [k for k, w in proposed_weights.items() if w < max_cap]
                if non_capped:
                    proposed_weights[non_capped[0]] += diff
                else:
                    proposed_weights[next(iter(proposed_weights.keys()))] += diff

        else:
            raise ValueError(f"Unsupported rebalance method: {method}")

        return DynamicRebalanceProposal(
            proposal_id=proposal_id,
            timestamp=datetime.now(timezone.utc),
            method=method,
            proposed_weights=proposed_weights,
            rationale=f"Empirical dynamic rebalancing computed via {method} model.",
            approved=False,
        )

    def apply_rebalance_proposal(
        self,
        proposal: DynamicRebalanceProposal,
        operator_token: str,
        operator_id: str = "OPERATOR_ADMIN",
    ) -> dict[str, Decimal]:
        """Applies dynamic rebalancing proposal requiring operator release gate authorization."""
        # Enforce human release gate
        decision = self.release_gate.enforce_release(
            release_type=ReleaseGateType.PORTFOLIO_REBALANCE,
            operator_id=operator_id,
            operator_token=operator_token,
            target_identifier=proposal.proposal_id,
            parameters={"weights": {k: float(v) for k, v in proposal.proposed_weights.items()}},
        )

        # Enforce Phase 31 Concentration Limits
        for strat_name, weight in proposal.proposed_weights.items():
            if weight > self.limits.max_single_strategy_pct:
                raise PortfolioBreachError(
                    f"Proposed weight for {strat_name} ({weight}%) breaches concentration limit ({self.limits.max_single_strategy_pct}%)."
                )

        # Apply weights to profiles
        for strat_name, weight in proposal.proposed_weights.items():
            if strat_name in self._profiles:
                self._profiles[strat_name].target_weight_pct = weight
                self._profiles[strat_name].allocated_capital = (
                    self.portfolio_manager.total_capital * (weight / Decimal("100.00"))
                ).quantize(_PREC_2)

        proposal.approved = True
        proposal.rebalance_token = operator_token

        logger.info(
            "Portfolio rebalanced successfully via %s (Decision: %s). New weights: %s",
            proposal.method,
            decision.decision_id,
            proposal.proposed_weights,
        )
        return proposal.proposed_weights

    def get_portfolio_governance_summary(self) -> dict[str, Any]:
        """Compiles complete multi-strategy portfolio governance status."""
        return {
            "total_capital": float(self.portfolio_manager.total_capital),
            "limits": self.limits.model_dump(),
            "strategies": {k: v.model_dump() for k, v in self._profiles.items()},
            "active_strategy_count": sum(1 for v in self._profiles.values() if v.is_active),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
