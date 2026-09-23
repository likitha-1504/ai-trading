"""Deterministic Risk Engine and Capital Gate.

Enforces portfolio risk limits, position sizing, circuit breakers,
minimum economical trade sizes, Indian market fee hurdles, and autonomy ceilings.
"""

import logging
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.capital.capital_manager import CapitalManager
from app.capital.config import RiskLimitsConfig
from app.capital.cost_model import IndianMarketCostModel
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    FrictionBreakdown,
    PositionSnapshot,
    PositionStatus,
    RiskEvaluationResult,
)

logger = logging.getLogger(__name__)


class RiskEngine:
    """Evaluates candidates against strict risk bounds, transaction friction, and capital limits."""

    def __init__(
        self,
        capital_manager: CapitalManager | None = None,
        cost_model: IndianMarketCostModel | None = None,
        config: RiskLimitsConfig | None = None,
        autonomous_threshold: Decimal = Decimal("300.00"),
    ) -> None:
        self.capital_manager = capital_manager or CapitalManager()
        self.cost_model = cost_model or IndianMarketCostModel()
        self.config = config or RiskLimitsConfig()
        self.autonomous_threshold = autonomous_threshold

        self.is_circuit_breaker_tripped: bool = False

    def check_daily_circuit_breaker(self) -> bool:
        """Check if cumulative daily drawdown has breached the circuit breaker limit."""
        _dd_amt, dd_pct = self.capital_manager.get_daily_drawdown()
        if dd_pct >= self.config.max_daily_drawdown_pct:
            self.is_circuit_breaker_tripped = True
            logger.critical(
                "CIRCUIT BREAKER TRIPPED: Daily drawdown %s%% >= limit %s%%",
                dd_pct * 100,
                self.config.max_daily_drawdown_pct * 100,
            )
            return True
        return self.is_circuit_breaker_tripped

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker status (e.g. for a new trading day)."""
        self.is_circuit_breaker_tripped = False
        logger.info("Daily circuit breaker reset")

    def calculate_max_position_size(
        self,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> int:
        """Calculate maximum allowable share quantity across risk, capital, and concentration bounds.

        Constraints:
        1. Max Loss Per Trade: Risk * Qty <= Equity * max_loss_per_trade_pct (1.5%)
        2. Available Buying Power: Entry * Qty <= Buying Power
        3. Position Concentration: Entry * Qty <= Equity * max_position_concentration_pct (50%)
        """
        equity = self.capital_manager.total_capital
        risk_per_share = entry_price - stop_price
        if risk_per_share <= Decimal("0.00"):
            return 0

        # 1. Size by risk budget
        max_risk_budget = equity * self.config.max_loss_per_trade_pct
        shares_by_risk = int(
            (max_risk_budget / risk_per_share).quantize(Decimal(1), rounding=ROUND_DOWN)
        )

        # 2. Size by available buying power
        shares_by_capital = int(
            (self.capital_manager.buying_power / entry_price).quantize(
                Decimal(1), rounding=ROUND_DOWN
            )
        )

        # 3. Size by maximum position concentration
        max_concentration_capital = equity * self.config.max_position_concentration_pct
        shares_by_concentration = int(
            (max_concentration_capital / entry_price).quantize(
                Decimal(1), rounding=ROUND_DOWN
            )
        )

        return max(0, min(shares_by_risk, shares_by_capital, shares_by_concentration))

    def evaluate_candidate(
        self,
        candidate: Candidate,
        current_positions: list[PositionSnapshot] | None = None,
    ) -> RiskEvaluationResult:
        """Run comprehensive deterministic risk, cost, and capital evaluation for a Candidate.

        Returns an explicit RiskEvaluationResult with approval status, approval mode
        (AUTONOMOUS vs MANUAL_PENDING), approved quantity, friction breakdown, and net edge.
        """
        positions = current_positions or []
        open_positions = [p for p in positions if p.status == PositionStatus.OPEN]
        rejection_reasons: list[str] = []

        # 1. Circuit Breaker Check
        if self.check_daily_circuit_breaker():
            rejection_reasons.append(
                f"Daily circuit breaker active: maximum drawdown limit {self.config.max_daily_drawdown_pct * 100:.1f}% breached"
            )

        # 2. Portfolio Active Positions Limit Check
        if len(open_positions) >= self.config.max_active_positions:
            rejection_reasons.append(
                f"Active positions limit reached: {len(open_positions)} >= {self.config.max_active_positions}"
            )

        # 3. Duplicate Position Prevention Check
        sym_key = candidate.symbol.upper()
        if any(p.symbol.upper() == sym_key for p in open_positions):
            rejection_reasons.append(f"Position already open for symbol {sym_key}")

        # 4. Sizing Calculation
        entry_price = getattr(
            candidate,
            "entry_price",
            getattr(candidate, "trigger_price", Decimal("0.00")),
        )
        approved_qty = self.calculate_max_position_size(
            entry_price=entry_price,
            stop_price=candidate.initial_stop_price,
        )
        if approved_qty < 1:
            rejection_reasons.append(
                f"Insufficient capital or risk budget for minimum 1 share of {sym_key} at {entry_price}"
            )
            # Default zero fallback values for friction and net edge
            zero_friction = FrictionBreakdown(
                brokerage=Decimal("0.00"),
                stt=Decimal("0.00"),
                exchange_charges=Decimal("0.00"),
                sebi_charges=Decimal("0.00"),
                stamp_duty=Decimal("0.00"),
                gst=Decimal("0.00"),
                expected_slippage=Decimal("0.00"),
                total_friction=Decimal("0.00"),
            )
            return RiskEvaluationResult(
                approved=False,
                approval_mode=ApprovalMode.REJECTED,
                symbol=sym_key,
                approved_quantity=0,
                allocated_capital=Decimal("0.00"),
                max_loss_potential=Decimal("0.00"),
                friction=zero_friction,
                expected_gross_edge=Decimal("0.00"),
                expected_net_edge=Decimal("0.00"),
                is_circuit_breaker_tripped=self.is_circuit_breaker_tripped,
                rejection_reasons=rejection_reasons,
            )

        # 5. Minimum Economical Trade Size Check
        notional_value = (Decimal(approved_qty) * entry_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if notional_value < self.config.min_economical_trade_size:
            rejection_reasons.append(
                f"Trade notional {notional_value} INR is below minimum economical trade size {self.config.min_economical_trade_size} INR"
            )

        # 6. Comprehensive Friction & Net-Edge Calculation
        target_price = getattr(
            candidate,
            "target_price",
            getattr(candidate, "suggested_target_price", None),
        ) or (
            entry_price
            + ((entry_price - candidate.initial_stop_price) * Decimal("2.0"))
        )
        friction = self.cost_model.calculate_friction(
            quantity=approved_qty,
            buy_price=entry_price,
            sell_price=target_price,
        )

        gross_gain = (target_price - entry_price) * Decimal(approved_qty)
        max_loss = (entry_price - candidate.initial_stop_price) * Decimal(approved_qty)

        # Estimate win probability from candidate score or default baseline
        win_prob = self.config.default_win_probability

        gross_edge, net_edge, passes_hurdle = self.cost_model.evaluate_net_edge(
            expected_gross_gain=gross_gain,
            potential_loss=max_loss,
            p_win=win_prob,
            friction=friction,
            hurdle_rate=self.config.min_expected_net_edge,
        )

        if not passes_hurdle:
            rejection_reasons.append(
                f"Expected net edge {net_edge} INR does not meet required hurdle {self.config.min_expected_net_edge} INR after total friction {friction.total_friction} INR"
            )

        # 7. Autonomy Policy & Approval Mode Gating
        is_approved = len(rejection_reasons) == 0
        if not is_approved:
            approval_mode = ApprovalMode.REJECTED
        else:
            # Check autonomy threshold: starting/allocated equity <= ₹300 is AUTONOMOUS, > ₹300 requires MANUAL_PENDING
            total_equity = self.capital_manager.total_capital
            if (
                notional_value > self.autonomous_threshold
                or total_equity > self.autonomous_threshold
            ):
                approval_mode = ApprovalMode.MANUAL_PENDING
                logger.info(
                    "Trade for %s requires MANUAL approval: notional %s or equity %s exceeds autonomous ceiling %s",
                    sym_key,
                    notional_value,
                    total_equity,
                    self.autonomous_threshold,
                )
            else:
                approval_mode = ApprovalMode.AUTONOMOUS

        return RiskEvaluationResult(
            approved=is_approved,
            approval_mode=approval_mode,
            symbol=sym_key,
            approved_quantity=approved_qty if is_approved else 0,
            allocated_capital=notional_value if is_approved else Decimal("0.00"),
            max_loss_potential=max_loss if is_approved else Decimal("0.00"),
            friction=friction,
            expected_gross_edge=gross_edge,
            expected_net_edge=net_edge,
            is_circuit_breaker_tripped=self.is_circuit_breaker_tripped,
            rejection_reasons=rejection_reasons,
        )
