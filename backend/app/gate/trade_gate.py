"""Deterministic Trade Gate and Decision Pipeline.

Fulfills Phase 12 requirements:
1. Deterministic candidate gate (technical validity, spreads, liquidity, cutoffs)
2. Risk/capital/cost gate (circuit breakers, position limits, sizing, Indian market fee hurdle)
3. Qwen3 qualitative analysis (primary evidence and invalidation conditions)
4. DeepSeek-R1 adversarial challenge (stress testing, flaw detection, council arbitration)
5. Deterministic final TradePlan synthesis (all 13 PDF items, immutable contract)
6. Execution authorization (strict lockout: AI cannot submit orders; autonomous vs manual gating)
7. Position Watcher ownership transfer (immediate handoff of active risk to IndependentPositionWatcher)
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.ai.challenger_client import DeepSeekR1ChallengerClient
from app.ai.client import Qwen3AnalystClient
from app.ai.council_evaluator import CouncilVerdict, evaluate_council_signals
from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig
from app.capital.cost_model import IndianMarketCostModel
from app.capital.risk_engine import RiskEngine
from app.execution.execution_engine import ExecutionEngine
from app.gate.audit_logger import TradeGateAuditLogger
from app.gate.config import TradeGateConfig
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    ChallengerCritique,
    FrictionBreakdown,
    MarketThesis,
    OrderEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    RiskEvaluationResult,
    RiskLimits,
    StopProtection,
    TradePlan,
    TradeSide,
)
from app.watcher.position_watcher import IndependentPositionWatcher

logger = logging.getLogger(__name__)


class DeterministicTradeGate:
    """Orchestrates the 7-step deterministic decision pipeline."""

    def __init__(
        self,
        config: TradeGateConfig | None = None,
        risk_engine: RiskEngine | None = None,
        qwen3_client: Qwen3AnalystClient | None = None,
        deepseek_client: DeepSeekR1ChallengerClient | None = None,
        execution_engine: ExecutionEngine | None = None,
        position_watcher: IndependentPositionWatcher | None = None,
        audit_logger: TradeGateAuditLogger | None = None,
    ) -> None:
        self.config = config or TradeGateConfig()
        self.risk_engine = risk_engine or RiskEngine(
            capital_manager=CapitalManager(
                config=CapitalConfig(starting_capital=self.config.max_capital_allocation)
            ),
            cost_model=IndianMarketCostModel(),
            autonomous_threshold=self.config.autonomous_threshold,
        )
        self.qwen3_client = qwen3_client or Qwen3AnalystClient()
        self.deepseek_client = deepseek_client or DeepSeekR1ChallengerClient()
        self.execution_engine = execution_engine or ExecutionEngine()
        self.position_watcher = position_watcher or IndependentPositionWatcher()
        self.audit_logger = audit_logger or TradeGateAuditLogger()

        # In-memory registry of evaluated trade plans: plan_id -> TradePlan
        self._plans: dict[str, TradePlan] = {}

    # -------------------------------------------------------------------------
    # Pipeline Step 1: Deterministic Candidate Gate
    # -------------------------------------------------------------------------

    def evaluate_candidate_gate(self, candidate: Candidate) -> tuple[bool, str]:
        """Evaluate pre-screened technical setup against deterministic viability criteria."""
        # 1. Price validity checks
        if candidate.trigger_price <= Decimal("0.00"):
            return False, f"Invalid trigger price {candidate.trigger_price} <= 0"
        if candidate.initial_stop_price <= Decimal("0.00"):
            return False, f"Invalid initial stop price {candidate.initial_stop_price} <= 0"

        # 2. Side-specific stop and target orientation
        if candidate.side == TradeSide.BUY:
            if candidate.initial_stop_price >= candidate.trigger_price:
                return (
                    False,
                    f"Stop price {candidate.initial_stop_price} must be strictly below trigger {candidate.trigger_price} for BUY",
                )
            if (
                candidate.suggested_target_price is not None
                and candidate.suggested_target_price <= candidate.trigger_price
            ):
                return (
                    False,
                    f"Target price {candidate.suggested_target_price} must be strictly above trigger {candidate.trigger_price} for BUY",
                )

        # 3. Market timing cutoff check (15:15 IST)
        det_time = candidate.detected_at
        if det_time is not None:
            # Check if time past 15:15 UTC/IST cutoff
            hh = det_time.hour
            mm = det_time.minute
            cutoff_parts = self.config.market_close_cutoff_time.split(":")
            c_hh, c_mm = int(cutoff_parts[0]), int(cutoff_parts[1])
            # If explicit IST hour in local comparison
            if (hh > c_hh or (hh == c_hh and mm >= c_mm)) and (
                det_time.tzinfo is not None and "IST" in str(det_time.tzinfo)
            ):
                return False, f"Candidate detected after market cutoff {self.config.market_close_cutoff_time} IST"

        # 4. Feature snapshot quantitative hurdles (spread & liquidity)
        fs = candidate.feature_snapshot
        if fs is not None:
            if fs.spread_pct > self.config.max_tolerable_spread_pct:
                return (
                    False,
                    f"Spread {fs.spread_pct} exceeds max tolerable {self.config.max_tolerable_spread_pct}",
                )
            if fs.liquidity_score < self.config.min_tolerable_liquidity:
                return (
                    False,
                    f"Liquidity score {fs.liquidity_score} below minimum hurdle {self.config.min_tolerable_liquidity}",
                )

        return True, "Candidate passed deterministic pre-screen validation"

    # -------------------------------------------------------------------------
    # Pipeline Step 2: Risk / Capital / Cost Gate
    # -------------------------------------------------------------------------

    def evaluate_risk_gate(
        self,
        candidate: Candidate,
        current_positions: list[PositionSnapshot] | None = None,
    ) -> RiskEvaluationResult:
        """Run comprehensive risk, sizing, Indian fee, and net-edge evaluation."""
        positions = (
            current_positions
            if current_positions is not None
            else self.position_watcher.get_all_open_positions()
        )
        return self.risk_engine.evaluate_candidate(candidate, current_positions=positions)

    # -------------------------------------------------------------------------
    # Pipeline Steps 3 & 4: AI Council (Qwen3 Analysis + DeepSeek-R1 Challenge)
    # -------------------------------------------------------------------------

    async def evaluate_ai_council(
        self, candidate: Candidate
    ) -> tuple[MarketThesis, ChallengerCritique, CouncilVerdict]:
        """Asynchronously invoke Qwen3 analyst, DeepSeek-R1 challenger, and arbitrate dispute."""
        # Step 3: Qwen3 qualitative market thesis
        thesis = await self.qwen3_client.analyze_candidate(candidate)
        self.audit_logger.record_stage(
            stage="QWEN3_ANALYSIS",
            candidate_id=candidate.candidate_id,
            decision=thesis.suggested_action.value,
            reason=thesis.thesis_summary,
            metadata={
                "confidence": str(thesis.confidence_score),
                "catalyst": thesis.catalyst_identified,
                "is_fallback": thesis.is_fallback,
                "latency_ms": thesis.latency_ms,
            },
        )

        # Step 4: DeepSeek-R1 adversarial challenge
        critique = await self.deepseek_client.critique_candidate(candidate, thesis)
        self.audit_logger.record_stage(
            stage="DEEPSEEK_CHALLENGE",
            candidate_id=candidate.candidate_id,
            decision=critique.recommendation_flag.value,
            reason=critique.critique_summary,
            metadata={
                "downside_severity": critique.downside_severity.value,
                "worst_case": critique.worst_case_scenario,
                "is_fallback": critique.is_fallback,
                "latency_ms": critique.latency_ms,
            },
        )

        # Deterministic arbitration
        verdict = evaluate_council_signals(
            candidate=candidate,
            thesis=thesis,
            critique=critique,
            min_qwen_confidence=self.config.min_qwen_confidence,
            max_tolerable_spread_pct=self.config.max_tolerable_spread_pct,
            min_tolerable_liquidity=self.config.min_tolerable_liquidity,
        )
        self.audit_logger.record_stage(
            stage="COUNCIL_ARBITRATION",
            candidate_id=candidate.candidate_id,
            decision=verdict.action.value,
            reason=verdict.decision_reason,
            metadata={"passed_filter": verdict.passed_filter, "risk_notes": verdict.risk_audit_notes},
        )

        return thesis, critique, verdict

    def evaluate_ai_council_sync(
        self, candidate: Candidate
    ) -> tuple[MarketThesis, ChallengerCritique, CouncilVerdict]:
        """Synchronously invoke Qwen3 analyst, DeepSeek-R1 challenger, and arbitrate dispute."""
        thesis = self.qwen3_client.analyze_candidate_sync(candidate)
        self.audit_logger.record_stage(
            stage="QWEN3_ANALYSIS",
            candidate_id=candidate.candidate_id,
            decision=thesis.suggested_action.value,
            reason=thesis.thesis_summary,
            metadata={
                "confidence": str(thesis.confidence_score),
                "catalyst": thesis.catalyst_identified,
                "is_fallback": thesis.is_fallback,
                "latency_ms": thesis.latency_ms,
            },
        )

        critique = self.deepseek_client.critique_candidate_sync(candidate, thesis)
        self.audit_logger.record_stage(
            stage="DEEPSEEK_CHALLENGE",
            candidate_id=candidate.candidate_id,
            decision=critique.recommendation_flag.value,
            reason=critique.critique_summary,
            metadata={
                "downside_severity": critique.downside_severity.value,
                "worst_case": critique.worst_case_scenario,
                "is_fallback": critique.is_fallback,
                "latency_ms": critique.latency_ms,
            },
        )

        verdict = evaluate_council_signals(
            candidate=candidate,
            thesis=thesis,
            critique=critique,
            min_qwen_confidence=self.config.min_qwen_confidence,
            max_tolerable_spread_pct=self.config.max_tolerable_spread_pct,
            min_tolerable_liquidity=self.config.min_tolerable_liquidity,
        )
        self.audit_logger.record_stage(
            stage="COUNCIL_ARBITRATION",
            candidate_id=candidate.candidate_id,
            decision=verdict.action.value,
            reason=verdict.decision_reason,
            metadata={"passed_filter": verdict.passed_filter, "risk_notes": verdict.risk_audit_notes},
        )

        return thesis, critique, verdict

    # -------------------------------------------------------------------------
    # Pipeline Step 5: Deterministic Final TradePlan Synthesis
    # -------------------------------------------------------------------------

    def synthesize_trade_plan(
        self,
        candidate: Candidate,
        risk_result: RiskEvaluationResult,
        council_verdict: CouncilVerdict | None = None,
        thesis: MarketThesis | None = None,
        critique: ChallengerCritique | None = None,
        rejection_reason: str | None = None,
    ) -> TradePlan:
        """Synthesize the immutable TradePlan containing all 13 items required by the PDF."""
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        fs = candidate.feature_snapshot

        # Determine approval mode
        if rejection_reason or not risk_result.approved or (council_verdict and not council_verdict.passed_filter):
            approval_mode = ApprovalMode.REJECTED
            final_reason = (
                rejection_reason
                or (council_verdict.decision_reason if council_verdict else None)
                or "; ".join(risk_result.rejection_reasons)
                or "Trade rejected by deterministic Trade Gate"
            )
        else:
            notional = Decimal(risk_result.approved_quantity) * candidate.trigger_price
            if notional <= self.config.autonomous_threshold:
                approval_mode = ApprovalMode.AUTONOMOUS
            else:
                approval_mode = ApprovalMode.MANUAL_PENDING
            final_reason = (
                council_verdict.decision_reason
                if council_verdict
                else "Trade approved by deterministic risk and fee evaluation"
            )

        # 1. Entry Context
        entry_context: dict[str, Any] = {
            "trigger_price": str(candidate.trigger_price),
            "rank_score": str(candidate.rank_score),
            "strategy": candidate.strategy_type.value,
            "evidence": candidate.quantitative_evidence,
        }
        if fs is not None:
            entry_context.update(
                {
                    "vwap": str(fs.vwap),
                    "momentum_score": str(fs.momentum_score),
                    "relative_volume_10": str(fs.relative_volume_10),
                    "spread_pct": str(fs.spread_pct),
                    "liquidity_score": str(fs.liquidity_score),
                    "regime": fs.regime.value,
                }
            )

        # 2. Risk Limits
        risk_limits = RiskLimits(
            max_loss_amount=risk_result.max_loss_potential,
            max_capital_allocation=risk_result.allocated_capital,
            max_position_size_pct=self.config.max_loss_per_trade_pct,
            max_daily_drawdown_pct=self.config.max_daily_drawdown_pct,
        )

        # 3. Stop / Protection
        stop_protection = StopProtection(
            hard_stop_price=candidate.initial_stop_price,
            take_profit_price=candidate.suggested_target_price,
            trailing_trigger_price=(
                candidate.trigger_price + ((candidate.trigger_price - candidate.initial_stop_price) * Decimal("1.5"))
            ),
            time_exit_time=f"{self.config.market_close_cutoff_time} IST",
        )

        # 4. Invalidation conditions
        invalidation: list[str] = [
            f"Breach of initial stop-loss price {candidate.initial_stop_price}",
            f"Market close time {self.config.market_close_cutoff_time} IST reached",
        ]
        if thesis:
            invalidation.extend(thesis.invalidation_conditions)
        if critique:
            invalidation.extend(critique.invalidation_conditions)

        # 5. AI Evidence References
        ai_evidence_refs: dict[str, Any] = {}
        if thesis:
            ai_evidence_refs["qwen3"] = {
                "catalyst": thesis.catalyst_identified,
                "bullish_evidence": thesis.bullish_evidence,
                "confidence": str(thesis.confidence_score),
                "suggested_action": thesis.suggested_action.value,
                "is_fallback": thesis.is_fallback,
            }
        if critique:
            ai_evidence_refs["deepseek_r1"] = {
                "recommendation": critique.recommendation_flag.value,
                "downside_severity": critique.downside_severity.value,
                "worst_case": critique.worst_case_scenario,
                "vulnerabilities": critique.identified_vulnerabilities,
                "is_fallback": critique.is_fallback,
            }

        trade_plan = TradePlan(
            plan_id=plan_id,
            candidate_id=candidate.candidate_id,
            created_at=now,
            instrument=candidate.symbol,
            symbol=candidate.symbol,
            side=candidate.side,
            quantity=max(1, risk_result.approved_quantity) if risk_result.approved else 1,
            entry_price_target=candidate.trigger_price,
            entry_context=entry_context,
            strategy=candidate.strategy_type,
            expected_edge=risk_result.expected_net_edge,
            expected_gross_edge=risk_result.expected_gross_edge,
            expected_net_edge=risk_result.expected_net_edge,
            estimated_costs=risk_result.friction,
            friction=risk_result.friction,
            risk_limits=risk_limits,
            stop_protection=stop_protection,
            hard_stop_price=candidate.initial_stop_price,
            take_profit_price=candidate.suggested_target_price,
            trailing_trigger_price=stop_protection.trailing_trigger_price,
            invalidation=invalidation,
            ai_evidence_references=ai_evidence_refs,
            decision_reason=final_reason,
            approval_mode=approval_mode,
            ai_thesis_ref=thesis,
            ai_critique_ref=critique,
        )

        self._plans[plan_id] = trade_plan
        self.audit_logger.record_stage(
            stage="TRADE_PLAN_SYNTHESIS",
            candidate_id=candidate.candidate_id,
            decision=approval_mode.value,
            reason=final_reason,
            plan_id=plan_id,
            metadata={
                "symbol": candidate.symbol,
                "quantity": trade_plan.quantity,
                "expected_edge": str(trade_plan.expected_edge),
                "total_friction": str(risk_result.friction.total_friction),
            },
        )
        return trade_plan

    # -------------------------------------------------------------------------
    # Pipeline Step 6: Execution Authorization
    # -------------------------------------------------------------------------

    def authorize_execution(self, trade_plan: TradePlan) -> OrderEvent | None:
        """Verify authorization and dispatch order to ExecutionEngine.
        
        Absolute Safety Invariant:
        AI models CANNOT directly submit an order or communicate with broker adapters.
        Only this deterministic method may authorize and dispatch orders.
        """
        if trade_plan.approval_mode not in (
            ApprovalMode.AUTONOMOUS,
            ApprovalMode.MANUAL_APPROVED,
        ):
            logger.info(
                "Execution authorization withheld for %s: mode is %s",
                trade_plan.plan_id,
                trade_plan.approval_mode.value,
            )
            return None

        client_order_id = f"order-{trade_plan.plan_id}"
        order_request = OrderRequest(
            client_order_id=client_order_id,
            plan_id=trade_plan.plan_id,
            symbol=trade_plan.instrument,
            side=trade_plan.side,
            order_type=OrderType.MARKET,
            quantity=trade_plan.quantity,
            price=trade_plan.entry_price_target,
            stop_price=trade_plan.hard_stop_price,
        )

        order_event = self.execution_engine.submit_order(order_request)
        self.audit_logger.record_stage(
            stage="EXECUTION_AUTHORIZATION",
            candidate_id=trade_plan.candidate_id,
            decision="AUTHORIZED",
            reason=f"Order submitted under {trade_plan.approval_mode.value}",
            plan_id=trade_plan.plan_id,
            order_id=order_event.client_order_id,
            metadata={
                "status": order_event.status.value,
                "filled_quantity": order_event.filled_quantity,
            },
        )
        return order_event

    # -------------------------------------------------------------------------
    # Pipeline Step 7: Position Watcher Ownership Transfer
    # -------------------------------------------------------------------------

    def transfer_to_position_watcher(
        self, trade_plan: TradePlan, order_event: OrderEvent
    ) -> PositionSnapshot | None:
        """Transfer active risk ownership directly to IndependentPositionWatcher."""
        # Only open position if order is filled or partially filled
        if order_event.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED, OrderStatus.ACKNOWLEDGED):
            logger.warning(
                "Cannot transfer to Position Watcher: order %s has status %s",
                order_event.client_order_id,
                order_event.status.value,
            )
            return None

        now = datetime.now(timezone.utc)
        position_id = f"pos-{trade_plan.plan_id}"
        fill_price = order_event.average_fill_price or trade_plan.entry_price_target
        fill_qty = order_event.filled_quantity if order_event.filled_quantity > 0 else trade_plan.quantity

        hard_stop = trade_plan.hard_stop_price
        if hard_stop is None and trade_plan.stop_protection is not None:
            hard_stop = trade_plan.stop_protection.hard_stop_price
        if hard_stop is None:
            hard_stop = trade_plan.entry_price_target * Decimal("0.98")

        position = PositionSnapshot(
            position_id=position_id,
            plan_id=trade_plan.plan_id,
            symbol=trade_plan.instrument,
            side=trade_plan.side,
            quantity=fill_qty,
            entry_price=fill_price,
            current_price=fill_price,
            hard_stop_price=hard_stop,
            trailing_stop_price=None,
            take_profit_price=trade_plan.take_profit_price,
            highest_price_seen=fill_price,
            unrealized_pnl=Decimal("0.00"),
            status=PositionStatus.OPEN,
            opened_at=now,
            last_evaluated_at=now,
        )

        # Autonomous ownership handover
        self.position_watcher.open_position(position)
        self.audit_logger.record_stage(
            stage="POSITION_WATCHER_OWNERSHIP",
            candidate_id=trade_plan.candidate_id,
            decision="TRANSFERRED",
            reason="Active risk ownership transferred to IndependentPositionWatcher",
            plan_id=trade_plan.plan_id,
            order_id=order_event.client_order_id,
            position_id=position_id,
            metadata={
                "hard_stop": str(position.hard_stop_price),
                "quantity": position.quantity,
                "entry_price": str(position.entry_price),
            },
        )
        return position

    # -------------------------------------------------------------------------
    # End-to-End Orchestration (Async & Sync)
    # -------------------------------------------------------------------------

    async def process_candidate(
        self,
        candidate: Candidate,
        current_positions: list[PositionSnapshot] | None = None,
    ) -> TradePlan:
        """Asynchronously execute all 7 pipeline steps for a candidate."""
        # 1. Candidate Gate
        c_passed, c_reason = self.evaluate_candidate_gate(candidate)
        self.audit_logger.record_stage(
            stage="CANDIDATE_GATE",
            candidate_id=candidate.candidate_id,
            decision="PASSED" if c_passed else "REJECTED",
            reason=c_reason,
        )
        if not c_passed:
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
            dummy_risk = RiskEvaluationResult(
                approved=False,
                approval_mode=ApprovalMode.REJECTED,
                symbol=candidate.symbol,
                approved_quantity=0,
                allocated_capital=Decimal("0.00"),
                max_loss_potential=Decimal("0.00"),
                friction=zero_friction,
                expected_gross_edge=Decimal("0.00"),
                expected_net_edge=Decimal("0.00"),
                is_circuit_breaker_tripped=False,
                rejection_reasons=[c_reason],
            )
            return self.synthesize_trade_plan(
                candidate=candidate,
                risk_result=dummy_risk,
                rejection_reason=c_reason,
            )

        # 2. Risk / Capital / Cost Gate
        risk_result = self.evaluate_risk_gate(candidate, current_positions=current_positions)
        self.audit_logger.record_stage(
            stage="RISK_GATE",
            candidate_id=candidate.candidate_id,
            decision="PASSED" if risk_result.approved else "REJECTED",
            reason="; ".join(risk_result.rejection_reasons) if not risk_result.approved else "Risk checks satisfied",
            metadata={
                "approved_qty": risk_result.approved_quantity,
                "net_edge": str(risk_result.expected_net_edge),
                "friction": str(risk_result.friction.total_friction),
            },
        )
        if not risk_result.approved:
            return self.synthesize_trade_plan(
                candidate=candidate,
                risk_result=risk_result,
            )

        # 3 & 4. AI Council (Qwen3 Analysis + DeepSeek-R1 Challenge)
        thesis, critique, council_verdict = await self.evaluate_ai_council(candidate)

        # 5. Deterministic Final TradePlan Synthesis
        trade_plan = self.synthesize_trade_plan(
            candidate=candidate,
            risk_result=risk_result,
            council_verdict=council_verdict,
            thesis=thesis,
            critique=critique,
        )

        # 6. Execution Authorization
        order_event = self.authorize_execution(trade_plan)

        # 7. Position Watcher Ownership Transfer
        if order_event is not None:
            self.transfer_to_position_watcher(trade_plan, order_event)

        return trade_plan

    def process_candidate_sync(
        self,
        candidate: Candidate,
        current_positions: list[PositionSnapshot] | None = None,
    ) -> TradePlan:
        """Synchronously execute all 7 pipeline steps for a candidate."""
        # 1. Candidate Gate
        c_passed, c_reason = self.evaluate_candidate_gate(candidate)
        self.audit_logger.record_stage(
            stage="CANDIDATE_GATE",
            candidate_id=candidate.candidate_id,
            decision="PASSED" if c_passed else "REJECTED",
            reason=c_reason,
        )
        if not c_passed:
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
            dummy_risk = RiskEvaluationResult(
                approved=False,
                approval_mode=ApprovalMode.REJECTED,
                symbol=candidate.symbol,
                approved_quantity=0,
                allocated_capital=Decimal("0.00"),
                max_loss_potential=Decimal("0.00"),
                friction=zero_friction,
                expected_gross_edge=Decimal("0.00"),
                expected_net_edge=Decimal("0.00"),
                is_circuit_breaker_tripped=False,
                rejection_reasons=[c_reason],
            )
            return self.synthesize_trade_plan(
                candidate=candidate,
                risk_result=dummy_risk,
                rejection_reason=c_reason,
            )

        # 2. Risk / Capital / Cost Gate
        risk_result = self.evaluate_risk_gate(candidate, current_positions=current_positions)
        self.audit_logger.record_stage(
            stage="RISK_GATE",
            candidate_id=candidate.candidate_id,
            decision="PASSED" if risk_result.approved else "REJECTED",
            reason="; ".join(risk_result.rejection_reasons) if not risk_result.approved else "Risk checks satisfied",
            metadata={
                "approved_qty": risk_result.approved_quantity,
                "net_edge": str(risk_result.expected_net_edge),
                "friction": str(risk_result.friction.total_friction),
            },
        )
        if not risk_result.approved:
            return self.synthesize_trade_plan(
                candidate=candidate,
                risk_result=risk_result,
            )

        # 3 & 4. AI Council (Sync)
        thesis, critique, council_verdict = self.evaluate_ai_council_sync(candidate)

        # 5. Deterministic Final TradePlan Synthesis
        trade_plan = self.synthesize_trade_plan(
            candidate=candidate,
            risk_result=risk_result,
            council_verdict=council_verdict,
            thesis=thesis,
            critique=critique,
        )

        # 6. Execution Authorization
        order_event = self.authorize_execution(trade_plan)

        # 7. Position Watcher Ownership Transfer
        if order_event is not None:
            self.transfer_to_position_watcher(trade_plan, order_event)

        return trade_plan

    # -------------------------------------------------------------------------
    # Manual Governance & Query APIs
    # -------------------------------------------------------------------------

    def approve_manual_plan(self, plan_id: str) -> OrderEvent:
        """Approve a trade plan held in MANUAL_PENDING (e.g. notional > ₹300)."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise KeyError(f"TradePlan {plan_id} not found in registry")

        if plan.approval_mode != ApprovalMode.MANUAL_PENDING:
            raise ValueError(
                f"Cannot manually approve plan {plan_id} with approval_mode {plan.approval_mode.value}"
            )

        # Mutate to MANUAL_APPROVED
        plan.approval_mode = ApprovalMode.MANUAL_APPROVED
        plan.decision_reason += " [Explicit Human Approval Granted]"
        self.audit_logger.record_stage(
            stage="MANUAL_APPROVAL",
            candidate_id=plan.candidate_id,
            decision="MANUAL_APPROVED",
            reason="Explicit human approval granted via control plane",
            plan_id=plan.plan_id,
        )

        order_event = self.authorize_execution(plan)
        if order_event is None:
            raise RuntimeError(f"Failed to dispatch order for approved plan {plan_id}")

        self.transfer_to_position_watcher(plan, order_event)
        return order_event

    def reject_manual_plan(self, plan_id: str, reason: str = "Rejected by human operator") -> TradePlan:
        """Explicitly reject a pending plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise KeyError(f"TradePlan {plan_id} not found in registry")

        plan.approval_mode = ApprovalMode.REJECTED
        plan.decision_reason = f"Manual Rejection: {reason}"
        self.audit_logger.record_stage(
            stage="MANUAL_APPROVAL",
            candidate_id=plan.candidate_id,
            decision="REJECTED",
            reason=reason,
            plan_id=plan.plan_id,
        )
        return plan

    def get_plan(self, plan_id: str) -> TradePlan | None:
        """Retrieve a TradePlan by plan_id."""
        return self._plans.get(plan_id)

    def get_all_plans(self) -> list[TradePlan]:
        """Return all evaluated trade plans in insertion order."""
        return list(self._plans.values())

    def get_audit_history(
        self,
        candidate_id: str | None = None,
        plan_id: str | None = None,
        stage: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve audit history."""
        return self.audit_logger.get_history(candidate_id=candidate_id, plan_id=plan_id, stage=stage)
