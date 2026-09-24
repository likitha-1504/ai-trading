"""Deterministic Event-Driven Backtesting Simulator.

Simulates historical execution with realistic Indian market friction, configurable slippage,
strict timestamp monotonicity, zero lookahead bias, and independent position protection.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal

from app.adapters.paper_adapter import PaperAdapter
from app.backtesting.journal import TradeJournal
from app.backtesting.metrics import PerformanceCalculator
from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig
from app.capital.cost_model import IndianMarketCostModel
from app.capital.risk_engine import RiskEngine
from app.engine.feature_engine import FeatureEngine
from app.models.contracts import (
    BacktestReport,
    EquityPoint,
    FeatureSnapshot,
    MarketRegime,
    NormalizedMarketEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
    WatcherExitTrigger,
)
from app.strategies.candidate_ranker import CandidateRanker
from app.watcher.position_watcher import IndependentPositionWatcher

logger = logging.getLogger(__name__)


class TimestampOrderError(ValueError):
    """Raised when an out-of-order event is encountered in the historical stream."""


class BacktestEngine:
    """Event-driven backtesting engine ensuring 100% strategy parity with live/paper loops."""

    def __init__(
        self,
        initial_capital: Decimal = Decimal("100.00"),
        slippage_ticks: int = 1,
        tick_size: Decimal = Decimal("0.05"),
        cost_model: IndianMarketCostModel | None = None,
        capital_manager: CapitalManager | None = None,
        risk_engine: RiskEngine | None = None,
        candidate_ranker: CandidateRanker | None = None,
        feature_engine: FeatureEngine | None = None,
        position_watcher: IndependentPositionWatcher | None = None,
        paper_adapter: PaperAdapter | None = None,
        trade_journal: TradeJournal | None = None,
        point_in_time_universe: set[str] | list[str] | None = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size
        self.point_in_time_universe = point_in_time_universe
        self._universe_set: set[str] | None = (
            {s.upper() for s in point_in_time_universe}
            if point_in_time_universe is not None
            else None
        )

        # Models and engines
        self.cost_model = cost_model or IndianMarketCostModel()
        self.capital_manager = capital_manager or CapitalManager(
            CapitalConfig(starting_capital=initial_capital)
        )
        self.risk_engine = risk_engine or RiskEngine(
            capital_manager=self.capital_manager,
            cost_model=self.cost_model,
        )
        self.candidate_ranker = candidate_ranker or CandidateRanker()
        self.feature_engine = feature_engine or FeatureEngine()
        self.paper_adapter = paper_adapter or PaperAdapter(
            initial_cash=initial_capital,
            slippage_ticks=slippage_ticks,
            tick_size=tick_size,
        )
        self.position_watcher = position_watcher or IndependentPositionWatcher(
            exit_order_dispatcher=self.paper_adapter.submit_order
        )
        self.trade_journal = trade_journal or TradeJournal()

        # Internal simulation tracking: position_id -> PositionSnapshot
        self._active_positions: dict[str, PositionSnapshot] = {}
        self._active_trade_ids: dict[str, str] = {}
        self._position_entry_regimes: dict[str, MarketRegime] = {}

    def run(self, events: list[NormalizedMarketEvent]) -> BacktestReport:
        """Execute event-driven simulation across sequential historical ticks.

        Guarantees:
        - Strictly non-decreasing timestamps (TimestampOrderError on violation)
        - Zero look-ahead bias: each feature and decision relies only on past/current events
        - Realistic costs and configurable tick slippage on all orders
        """
        if not events:
            raise ValueError("Cannot run backtest on empty event sequence")

        run_id = f"bkt-{uuid.uuid4().hex[:8]}"
        equity_curve: list[EquityPoint] = []
        last_timestamp: datetime | None = None

        logger.info(
            "Starting backtest %s with %d events (Initial Capital: %s INR, Slippage: %d ticks)",
            run_id,
            len(events),
            self.initial_capital,
            self.slippage_ticks,
        )

        for event in events:
            # 1. Monotonic Timestamp Verification
            if last_timestamp is not None and event.exchange_timestamp < last_timestamp:
                raise TimestampOrderError(
                    f"Timestamp monotonicity violation: tick timestamp {event.exchange_timestamp} "
                    f"is prior to previous {last_timestamp}. Look-ahead bias prohibited."
                )
            last_timestamp = event.exchange_timestamp

            # 2. Point-in-Time Universe Check (survivorship bias prevention)
            if self._universe_set is not None and event.symbol.upper() not in self._universe_set:
                continue

            # 3. Update paper adapter market price
            self.paper_adapter.update_market_price(event.symbol, event.last_price)

            # 4. Position Evaluation and Emergency Watcher Exits
            self._evaluate_positions(event)

            # 4. Point-in-Time Feature Calculation
            snapshot = self.feature_engine.process_tick(event)

            # 5. Candidate Screening and Risk Gating
            self._evaluate_entries(event, snapshot)

            # 6. Mark-to-Market & Equity Tracking
            self._record_equity_point(event.exchange_timestamp, equity_curve)

        # 7. End of simulation auto-square off for remaining open positions
        if self._active_positions and last_timestamp is not None:
            self._square_off_remaining_positions(last_timestamp, events[-1].last_price)
            self._record_equity_point(last_timestamp, equity_curve)

        # 8. Compile Performance Metrics
        completed_trades = self.trade_journal.get_completed_trades()
        metrics = PerformanceCalculator.calculate(
            trades=completed_trades,
            equity_curve=equity_curve,
            start_time=events[0].exchange_timestamp,
            end_time=events[-1].exchange_timestamp,
        )

        return BacktestReport(
            run_id=run_id,
            start_time=events[0].exchange_timestamp,
            end_time=events[-1].exchange_timestamp,
            initial_capital=self.initial_capital,
            final_equity=self.capital_manager.total_capital,
            slippage_ticks=self.slippage_ticks,
            metrics=metrics,
            trades=completed_trades,
            equity_curve=equity_curve,
        )

    def _evaluate_positions(self, event: NormalizedMarketEvent) -> None:
        """Check active positions for exit triggers via IndependentPositionWatcher."""
        symbol_key = event.symbol.upper()
        matching_pos_ids = [
            pid for pid, pos in self._active_positions.items() if pos.symbol == symbol_key
        ]

        if not matching_pos_ids:
            return

        interventions = self.position_watcher.evaluate_tick(event)
        for intervention in interventions:
            pid = intervention.position_id
            if pid not in self._active_positions:
                continue

            pos = self._active_positions.pop(pid)
            trade_id = self._active_trade_ids.pop(pid)
            entry_regime = self._position_entry_regimes.pop(pid, MarketRegime.LOW_VOLATILITY_COMPRESSION)

            # Exit execution fill with realistic slippage
            slippage_amount = self.tick_size * Decimal(self.slippage_ticks)
            exit_price = (event.last_price - slippage_amount).quantize(Decimal("0.01"))

            # Calculate statutory Indian market friction
            friction = self.cost_model.calculate_friction(
                quantity=pos.quantity,
                buy_price=pos.entry_price,
                sell_price=exit_price,
                is_intraday=True,
            )

            # Calculate gross P/L and release capital
            gross_pnl = (exit_price - pos.entry_price) * Decimal(pos.quantity)
            self.capital_manager.release_capital(
                position_id=pid,
                symbol=pos.symbol,
                quantity=pos.quantity,
                exit_price=exit_price,
                gross_realized_pnl=gross_pnl,
                friction=friction.total_friction,
            )

            # Audit record in trade journal
            self.trade_journal.record_exit(
                trade_id=trade_id,
                exit_timestamp=event.exchange_timestamp,
                exit_price=exit_price,
                exit_slippage=slippage_amount,
                exit_trigger=intervention.trigger,
                friction=friction,
                market_regime_at_exit=entry_regime,
            )

    def _evaluate_entries(
        self, event: NormalizedMarketEvent, snapshot: FeatureSnapshot
    ) -> None:
        """Evaluate strategy candidate generation, risk gating, and order dispatch."""
        candidates = self.candidate_ranker.evaluate_snapshot(snapshot)
        if not candidates:
            return

        for cand in candidates:
            # Risk Engine evaluation
            active_list = list(self._active_positions.values())
            risk_res = self.risk_engine.evaluate_candidate(cand, current_positions=active_list)

            if not risk_res.approved or risk_res.approved_quantity <= 0:
                continue

            qty = risk_res.approved_quantity
            notional = Decimal(qty) * cand.trigger_price

            if self.capital_manager.available_capital < notional:
                continue

            # Allocate capital
            pos_id = f"pos-{uuid.uuid4().hex[:8]}"
            self.capital_manager.allocate_capital(
                position_id=pos_id,
                symbol=cand.symbol,
                quantity=qty,
                price=cand.trigger_price,
            )

            # Dispatch order through PaperAdapter
            req = OrderRequest(
                client_order_id=f"ord-{uuid.uuid4().hex[:8]}",
                plan_id=cand.candidate_id,
                symbol=cand.symbol,
                side=TradeSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=qty,
                price=cand.trigger_price,
            )
            order_event = self.paper_adapter.submit_order(req)

            if order_event.status == OrderStatus.FILLED:
                fill_price = order_event.average_fill_price or cand.trigger_price
                slippage_cost = abs(fill_price - cand.trigger_price)

                entry_regime = (
                    cand.feature_snapshot.regime
                    if cand.feature_snapshot is not None
                    else snapshot.regime
                )

                # Record trade journal entry
                trade_id = self.trade_journal.record_entry(
                    plan_id=cand.candidate_id,
                    symbol=cand.symbol,
                    side=TradeSide.BUY,
                    strategy=cand.strategy_type,
                    quantity=qty,
                    entry_timestamp=event.exchange_timestamp,
                    entry_price=fill_price,
                    entry_slippage=slippage_cost,
                    market_regime_at_entry=entry_regime,
                )

                # Track position
                pos = PositionSnapshot(
                    position_id=pos_id,
                    plan_id=cand.candidate_id,
                    symbol=cand.symbol,
                    side=TradeSide.BUY,
                    quantity=qty,
                    entry_price=fill_price,
                    current_price=fill_price,
                    hard_stop_price=cand.initial_stop_price,
                    trailing_stop_price=None,
                    take_profit_price=cand.suggested_target_price,
                    highest_price_seen=fill_price,
                    unrealized_pnl=Decimal("0.00"),
                    status=PositionStatus.OPEN,
                    opened_at=event.exchange_timestamp,
                    last_evaluated_at=event.exchange_timestamp,
                )
                self.position_watcher.open_position(pos)
                self._active_positions[pos_id] = pos
                self._active_trade_ids[pos_id] = trade_id
                self._position_entry_regimes[pos_id] = entry_regime

    def _record_equity_point(
        self, timestamp: datetime, curve: list[EquityPoint]
    ) -> None:
        """Mark unrealized P&L and record equity point."""
        active_list = list(self._active_positions.values())
        self.capital_manager.update_unrealized_pnl(active_list)
        dd_amt, dd_pct = self.capital_manager.get_daily_drawdown()

        curve.append(
            EquityPoint(
                timestamp=timestamp,
                total_equity=self.capital_manager.total_capital,
                cash_balance=self.capital_manager.available_capital,
                unrealized_pnl=self.capital_manager.unrealized_pnl,
                drawdown_amount=dd_amt,
                drawdown_pct=float(dd_pct),
            )
        )

    def _square_off_remaining_positions(
        self, timestamp: datetime, final_price: Decimal
    ) -> None:
        """Square off any open positions at the end of the simulation."""
        remaining_ids = list(self._active_positions.keys())
        for pid in remaining_ids:
            pos = self._active_positions.pop(pid)
            trade_id = self._active_trade_ids.pop(pid)
            entry_regime = self._position_entry_regimes.pop(pid, MarketRegime.LOW_VOLATILITY_COMPRESSION)

            slippage_amount = self.tick_size * Decimal(self.slippage_ticks)
            exit_price = (final_price - slippage_amount).quantize(Decimal("0.01"))

            friction = self.cost_model.calculate_friction(
                quantity=pos.quantity,
                buy_price=pos.entry_price,
                sell_price=exit_price,
                is_intraday=True,
            )

            gross_pnl = (exit_price - pos.entry_price) * Decimal(pos.quantity)
            self.capital_manager.release_capital(
                position_id=pid,
                symbol=pos.symbol,
                quantity=pos.quantity,
                exit_price=exit_price,
                gross_realized_pnl=gross_pnl,
                friction=friction.total_friction,
            )

            self.trade_journal.record_exit(
                trade_id=trade_id,
                exit_timestamp=timestamp,
                exit_price=exit_price,
                exit_slippage=slippage_amount,
                exit_trigger=WatcherExitTrigger.TIME_EXPIRY,
                friction=friction,
                market_regime_at_exit=entry_regime,
            )
            self.position_watcher.deregister_position(pid)
