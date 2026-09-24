"""Independent Position Watcher and SELL Engine.

Operates with absolute autonomy, zero LLM dependency, and deterministic precedence.
Owns real-time risk evaluation, hard stop enforcement, trailing logic, and emergency liquidations.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.contracts import (
    FeatureSnapshot,
    NormalizedMarketEvent,
    OrderEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
    WatcherExitTrigger,
    WatcherInterventionEvent,
)
from app.watcher.config import WatcherConfig

logger = logging.getLogger(__name__)


class IndependentPositionWatcher:
    """Autonomous, deterministic watchdog that protects capital and executes exits instantly."""

    def __init__(
        self,
        config: WatcherConfig | None = None,
        exit_order_dispatcher: Callable[[OrderRequest], OrderEvent] | None = None,
    ) -> None:
        self.config = config or WatcherConfig()
        self.exit_order_dispatcher = exit_order_dispatcher

        # Active positions: position_id -> PositionSnapshot
        self._positions: dict[str, PositionSnapshot] = {}

        # Symbol to position_id lookup for fast tick dispatch: symbol -> set of position_ids
        self._symbol_positions: dict[str, set[str]] = {}

        # Daily performance tracking for circuit breaker
        self.realized_daily_pnl: Decimal = Decimal(0)
        self.is_circuit_breaker_tripped: bool = False

        # Last quote timestamps per symbol
        self._last_quote_timestamps: dict[str, datetime] = {}

        # Event audit log
        self._intervention_history: list[WatcherInterventionEvent] = []

    # -------------------------------------------------------------------------
    # Position Lifecycle & Reconciliation
    # -------------------------------------------------------------------------

    def open_position(self, position: PositionSnapshot) -> None:
        """Register a new active position under surveillance."""
        self._positions[position.position_id] = position
        sym = position.symbol.upper()
        if sym not in self._symbol_positions:
            self._symbol_positions[sym] = set()
        self._symbol_positions[sym].add(position.position_id)
        logger.info(
            "Position %s for %s registered with Watcher", position.position_id, sym
        )

    def register_position(self, position: PositionSnapshot) -> None:
        """Register a new active position under surveillance (alias for open_position)."""
        self.open_position(position)

    def deregister_position(self, position_id: str) -> None:
        """Remove a closed position from active surveillance."""
        pos = self._positions.pop(position_id, None)
        if pos is not None:
            sym = pos.symbol.upper()
            if sym in self._symbol_positions:
                self._symbol_positions[sym].discard(position_id)
                if not self._symbol_positions[sym]:
                    self._symbol_positions.pop(sym, None)

    def get_position(self, position_id: str) -> PositionSnapshot | None:
        """Retrieve an active position snapshot."""
        return self._positions.get(position_id)

    def get_all_open_positions(self) -> list[PositionSnapshot]:
        """Return a list of all currently open positions."""
        return [
            pos for pos in self._positions.values() if pos.status == PositionStatus.OPEN
        ]

    def update_partial_fill(
        self,
        position_id: str,
        filled_qty: int,
        fill_price: Decimal,
    ) -> None:
        """Update position quantity and entry price following a partial fill."""
        pos = self._positions.get(position_id)
        if pos is None:
            return

        pos.quantity = filled_qty
        pos.entry_price = fill_price
        pos.unrealized_pnl = (pos.current_price - pos.entry_price) * Decimal(
            pos.quantity
        )

    def handle_rejected_exit_order(
        self, position_id: str, rejection_reason: str
    ) -> None:
        """Handle rejection of an exit order defensively."""
        pos = self._positions.get(position_id)
        if pos is not None:
            logger.critical(
                "Exit order for position %s rejected by broker: %s. Retaining OPEN status for retry.",
                position_id,
                rejection_reason,
            )
            # Revert status from CLOSING to OPEN so watcher continues attempting exit
            pos.status = PositionStatus.OPEN

    def reconcile_positions(self, positions: list[PositionSnapshot]) -> None:
        """Reconcile and restore position surveillance state on system restart."""
        self._positions.clear()
        self._symbol_positions.clear()
        for pos in positions:
            if pos.status in (PositionStatus.OPEN, PositionStatus.CLOSING):
                self.open_position(pos)
        logger.info(
            "Watcher successfully reconciled %d active positions", len(self._positions)
        )

    # -------------------------------------------------------------------------
    # Real-Time Market Evaluation Paths
    # -------------------------------------------------------------------------

    def evaluate_tick(
        self, event: NormalizedMarketEvent
    ) -> list[WatcherInterventionEvent]:
        """Ingest a market tick and evaluate all active positions for that symbol.

        Execution budget: sub-50ms deterministic path.
        """
        symbol_key = event.symbol.upper()
        self._last_quote_timestamps[symbol_key] = event.exchange_timestamp
        position_ids = list(self._symbol_positions.get(symbol_key, set()))

        interventions: list[WatcherInterventionEvent] = []

        for pos_id in position_ids:
            pos = self._positions.get(pos_id)
            if pos is None or pos.status != PositionStatus.OPEN:
                continue

            intervention = self._evaluate_single_position(
                pos=pos,
                current_price=event.last_price,
                current_time=event.exchange_timestamp,
                spread_pct=event.spread_pct,
                is_quote_stale=event.is_stale,
                feature_snapshot=None,
            )
            if intervention is not None:
                interventions.append(intervention)

        return interventions

    def evaluate_feature_snapshot(
        self, snapshot: FeatureSnapshot
    ) -> list[WatcherInterventionEvent]:
        """Evaluate technical deterioration and structure breaks using a FeatureSnapshot."""
        symbol_key = snapshot.symbol.upper()
        self._last_quote_timestamps[symbol_key] = snapshot.timestamp
        position_ids = list(self._symbol_positions.get(symbol_key, set()))

        interventions: list[WatcherInterventionEvent] = []

        for pos_id in position_ids:
            pos = self._positions.get(pos_id)
            if pos is None or pos.status != PositionStatus.OPEN:
                continue

            intervention = self._evaluate_single_position(
                pos=pos,
                current_price=snapshot.current_price,
                current_time=snapshot.timestamp,
                spread_pct=snapshot.spread_pct,
                liquidity_score=snapshot.liquidity_score,
                is_quote_stale=False,
                feature_snapshot=snapshot,
            )
            if intervention is not None:
                interventions.append(intervention)

        return interventions

    def evaluate_heartbeat(
        self, current_time: datetime | None = None
    ) -> list[WatcherInterventionEvent]:
        """Periodic safety sweep: checks stale feeds, trade durations, and intraday square-off."""
        now = current_time or datetime.now(timezone.utc)
        interventions: list[WatcherInterventionEvent] = []

        for pos in list(self._positions.values()):
            if pos.status != PositionStatus.OPEN:
                continue

            # Check if quote feed for this symbol has frozen
            last_ts = self._last_quote_timestamps.get(
                pos.symbol.upper(), pos.last_evaluated_at
            )
            elapsed_sec = (now - last_ts).total_seconds()
            is_stale = elapsed_sec >= self.config.stale_quote_timeout_seconds

            intervention = self._evaluate_single_position(
                pos=pos,
                current_price=pos.current_price,
                current_time=now,
                is_quote_stale=is_stale,
                feature_snapshot=None,
            )
            if intervention is not None:
                interventions.append(intervention)

        return interventions

    # -------------------------------------------------------------------------
    # Core Deterministic Evaluation Logic
    # -------------------------------------------------------------------------

    def _evaluate_single_position(
        self,
        pos: PositionSnapshot,
        current_price: Decimal,
        current_time: datetime,
        spread_pct: Decimal | None = None,
        liquidity_score: Decimal | None = None,
        is_quote_stale: bool = False,
        feature_snapshot: FeatureSnapshot | None = None,
    ) -> WatcherInterventionEvent | None:
        """Evaluate a single open position against all safety triggers in strict priority order."""
        # Update position dynamic state
        pos.current_price = current_price
        pos.last_evaluated_at = current_time
        pos.unrealized_pnl = (current_price - pos.entry_price) * Decimal(pos.quantity)

        # Track peak price for trailing stop calculations
        if pos.highest_price_seen is None:
            pos.highest_price_seen = max(pos.entry_price, current_price)
        else:
            pos.highest_price_seen = max(pos.highest_price_seen, current_price)

        # Calculate initial risk unit R
        risk_r = pos.entry_price - pos.hard_stop_price

        # ---------------------------------------------------------------------
        # Priority 1: Hard Stop-Loss (Absolute Capital Protection)
        # ---------------------------------------------------------------------
        if current_price <= pos.hard_stop_price:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.HARD_STOP,
                trigger_price=current_price,
                details=f"Hard stop breached: price {current_price} <= stop {pos.hard_stop_price}",
            )

        # ---------------------------------------------------------------------
        # Priority 2: Stale Data Emergency
        # ---------------------------------------------------------------------
        if is_quote_stale:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.STALE_DATA_EMERGENCY,
                trigger_price=current_price,
                details="Market quote feed dropped or froze > 15s during active position",
            )

        # ---------------------------------------------------------------------
        # Priority 3: Catastrophic Liquidity Loss
        # ---------------------------------------------------------------------
        if spread_pct is not None and spread_pct >= self.config.catastrophic_spread_pct:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.CATASTROPHIC_LIQUIDITY_LOSS,
                trigger_price=current_price,
                details=f"Catastrophic spread blowout: {spread_pct * 100:.3f}% >= {self.config.catastrophic_spread_pct * 100:.3f}%",
            )

        if (
            liquidity_score is not None
            and liquidity_score <= self.config.catastrophic_liquidity_threshold
        ):
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.CATASTROPHIC_LIQUIDITY_LOSS,
                trigger_price=current_price,
                details=f"Catastrophic liquidity evaporation: score {liquidity_score} <= {self.config.catastrophic_liquidity_threshold}",
            )

        # ---------------------------------------------------------------------
        # Priority 4: Daily Circuit Breaker
        # ---------------------------------------------------------------------
        total_pnl = self.realized_daily_pnl + self._get_total_unrealized_pnl()
        daily_loss_limit = self.config.capital_base * self.config.max_daily_drawdown_pct
        if total_pnl <= -daily_loss_limit:
            self.is_circuit_breaker_tripped = True
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.DAILY_CIRCUIT_BREAKER,
                trigger_price=current_price,
                details=f"Daily circuit breaker tripped: total loss {total_pnl} breaches {daily_loss_limit} limit",
            )

        # ---------------------------------------------------------------------
        # Priority 5: Take Profit & Trailing Stop Ratchet
        # ---------------------------------------------------------------------
        # First, ratchet trailing stop if in profit
        if risk_r > Decimal(0):
            gain = pos.highest_price_seen - pos.entry_price
            activation_gain = risk_r * self.config.trailing_activation_multiple

            if gain >= activation_gain:
                trail_distance = risk_r * self.config.trailing_distance_multiple
                potential_trail_stop = pos.highest_price_seen - trail_distance

                # Monotonic ratchet: stop can only move upward
                if pos.trailing_stop_price is None:
                    pos.trailing_stop_price = max(
                        pos.hard_stop_price, potential_trail_stop
                    )
                else:
                    pos.trailing_stop_price = max(
                        pos.trailing_stop_price, potential_trail_stop
                    )

        if pos.take_profit_price is not None and current_price >= pos.take_profit_price:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.TAKE_PROFIT,
                trigger_price=current_price,
                details=f"Take-profit target hit: price {current_price} >= target {pos.take_profit_price}",
            )

        if (
            pos.trailing_stop_price is not None
            and current_price <= pos.trailing_stop_price
        ):
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.TRAILING_STOP,
                trigger_price=current_price,
                details=f"Trailing stop hit: price {current_price} <= trail {pos.trailing_stop_price}",
            )

        # ---------------------------------------------------------------------
        # Priority 6: Time Protection & Auto Square-Off
        # ---------------------------------------------------------------------
        # Intraday 15:15 IST auto square-off check (IST = UTC+5:30)
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        ist_dt = (
            current_time.astimezone(ist_tz)
            if current_time.tzinfo
            else current_time.replace(tzinfo=timezone.utc).astimezone(ist_tz)
        )
        ist_time_str = ist_dt.strftime("%H:%M")
        if ist_time_str >= self.config.auto_square_off_time_ist:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.TIME_EXPIRY,
                trigger_price=current_price,
                details=f"Intraday auto-square-off cutoff reached: {ist_time_str} >= {self.config.auto_square_off_time_ist}",
            )

        # Max duration check
        holding_seconds = (current_time - pos.opened_at).total_seconds()
        if holding_seconds >= self.config.max_holding_seconds:
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.TIME_EXPIRY,
                trigger_price=current_price,
                details=f"Max trade holding duration exceeded: {holding_seconds:.0f}s >= {self.config.max_holding_seconds}s",
            )

        # ---------------------------------------------------------------------
        # Priority 7: Technical Deterioration & Structure Breakdown
        # ---------------------------------------------------------------------
        if (
            spread_pct is not None
            and spread_pct >= self.config.spread_widening_threshold
        ):
            return self._execute_intervention(
                pos=pos,
                trigger=WatcherExitTrigger.SPREAD_WIDENING,
                trigger_price=current_price,
                details=f"Defensive exit on spread widening: {spread_pct * 100:.3f}% >= {self.config.spread_widening_threshold * 100:.3f}%",
            )

        if feature_snapshot is not None:
            # Momentum deterioration
            if (
                feature_snapshot.momentum_score
                <= self.config.momentum_deterioration_threshold
                or feature_snapshot.price_acceleration
                <= self.config.price_deceleration_threshold
            ):
                return self._execute_intervention(
                    pos=pos,
                    trigger=WatcherExitTrigger.MOMENTUM_DETERIORATION,
                    trigger_price=current_price,
                    details=f"Momentum collapsed: ROC={feature_snapshot.momentum_score}%, accel={feature_snapshot.price_acceleration}%",
                )

            # Structure break
            if (
                feature_snapshot.price_structure == "LOWER_LOWS"
                and current_price < pos.entry_price
            ):
                return self._execute_intervention(
                    pos=pos,
                    trigger=WatcherExitTrigger.STRUCTURE_BREAK,
                    trigger_price=current_price,
                    details="Market structure broke to LOWER_LOWS beneath entry price",
                )

            # Market/sector reversal
            if (
                feature_snapshot.market_index_direction == "BEARISH"
                and feature_snapshot.sector_strength < Decimal("-0.50")
            ):
                return self._execute_intervention(
                    pos=pos,
                    trigger=WatcherExitTrigger.MARKET_REVERSAL,
                    trigger_price=current_price,
                    details="Broad market turned BEARISH with negative sector momentum",
                )

        return None

    # -------------------------------------------------------------------------
    # Auxiliary Non-Emergency AI Signal Handling
    # -------------------------------------------------------------------------

    def ingest_ai_invalidation(
        self,
        position_id: str,
        thesis_summary: str,
        invalidation_reason: str,
    ) -> WatcherInterventionEvent | None:
        """Ingest qualitative AI invalidation as a non-emergency auxiliary exit signal.

        Note: Hard protection NEVER waits for this method.
        """
        pos = self._positions.get(position_id)
        if pos is None or pos.status != PositionStatus.OPEN:
            return None

        logger.info(
            "AI Council signaled thesis invalidation for position %s: %s",
            position_id,
            invalidation_reason,
        )
        return self._execute_intervention(
            pos=pos,
            trigger=WatcherExitTrigger.AI_THESIS_INVALIDATION,
            trigger_price=pos.current_price,
            details=f"AI Thesis Invalidated: {thesis_summary} - {invalidation_reason}",
        )

    # -------------------------------------------------------------------------
    # Manual Kill-Switch
    # -------------------------------------------------------------------------

    def trigger_manual_kill_switch(
        self, reason: str = "Operator emergency kill switch engaged"
    ) -> list[WatcherInterventionEvent]:
        """Emergency kill-switch: liquidates all open positions immediately."""
        interventions: list[WatcherInterventionEvent] = []
        for pos in list(self._positions.values()):
            if pos.status == PositionStatus.OPEN:
                intervention = self._execute_intervention(
                    pos=pos,
                    trigger=WatcherExitTrigger.MANUAL_KILL_SWITCH,
                    trigger_price=pos.current_price,
                    details=reason,
                )
                interventions.append(intervention)
        return interventions

    # -------------------------------------------------------------------------
    # Internal Execution Helper
    # -------------------------------------------------------------------------

    def _execute_intervention(
        self,
        pos: PositionSnapshot,
        trigger: WatcherExitTrigger,
        trigger_price: Decimal,
        details: str,
    ) -> WatcherInterventionEvent:
        """Construct market exit order, dispatch immediately, and archive event."""
        client_order_id = f"exit-{uuid.uuid4().hex[:12]}"
        pos.status = PositionStatus.CLOSING

        # Dispatch order via registered broker dispatcher if provided
        if self.exit_order_dispatcher is not None:
            order_req = OrderRequest(
                client_order_id=client_order_id,
                plan_id=pos.plan_id,
                symbol=pos.symbol,
                side=TradeSide.SELL,
                order_type=OrderType.MARKET,
                quantity=pos.quantity,
                price=None,
                stop_price=None,
            )
            try:
                order_event = self.exit_order_dispatcher(order_req)
                if order_event.status == OrderStatus.FILLED:
                    pos.status = PositionStatus.CLOSED
                    self.realized_daily_pnl += pos.unrealized_pnl
            except Exception as e:  # noqa: BLE001 - Protect watcher from external dispatcher crashes
                logger.error("Dispatcher failed during exit order: %s", e)
        else:
            # Synthetic fill for isolated watcher operation
            pos.status = PositionStatus.CLOSED
            self.realized_daily_pnl += pos.unrealized_pnl

        event = WatcherInterventionEvent(
            event_id=f"wiev-{uuid.uuid4().hex[:10]}",
            timestamp=datetime.now(timezone.utc),
            position_id=pos.position_id,
            symbol=pos.symbol,
            trigger=trigger,
            trigger_price=trigger_price,
            executed_exit_order_id=client_order_id,
            details=details,
        )

        self._intervention_history.append(event)
        logger.warning(
            "WATCHER INTERVENTION [%s]: Position %s (%s) exit dispatched at %s. Details: %s",
            trigger.value,
            pos.position_id,
            pos.symbol,
            trigger_price,
            details,
        )
        return event

    def _get_total_unrealized_pnl(self) -> Decimal:
        """Calculate aggregate unrealized P&L across all open positions."""
        return sum(
            (
                pos.unrealized_pnl
                for pos in self._positions.values()
                if pos.status == PositionStatus.OPEN
            ),
            Decimal(0),
        )
