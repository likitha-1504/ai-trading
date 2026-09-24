"""Real-time Paper Trading Loop.

Guarantees 100% strategy and execution interface symmetry with backtesting,
connecting the live/simulated market data stream with the Execution Engine,
Position Watcher, Risk Gate, and Trade Journal.
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
from app.execution.execution_engine import ExecutionEngine
from app.models.contracts import (
    EquityPoint,
    FeatureSnapshot,
    MarketRegime,
    NormalizedMarketEvent,
    OrderRequest,
    OrderStatus,
    OrderType,
    PerformanceMetrics,
    PositionSnapshot,
    PositionStatus,
    TradeSide,
)
from app.strategies.candidate_ranker import CandidateRanker
from app.watcher.position_watcher import IndependentPositionWatcher

logger = logging.getLogger(__name__)


class PaperTradingLoop:
    """Continuous paper trading controller maintaining strategy symmetry with backtesting."""

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
        execution_engine: ExecutionEngine | None = None,
        trade_journal: TradeJournal | None = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size

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
        self.execution_engine = execution_engine or ExecutionEngine(
            broker_adapter=self.paper_adapter
        )
        self.position_watcher = position_watcher or IndependentPositionWatcher(
            exit_order_dispatcher=self.execution_engine.submit_order
        )
        self.trade_journal = trade_journal or TradeJournal()

        # Active position management
        self._active_positions: dict[str, PositionSnapshot] = {}
        self._active_trade_ids: dict[str, str] = {}
        self._position_entry_regimes: dict[str, MarketRegime] = {}

        self.equity_curve: list[EquityPoint] = []
        self._start_time: datetime | None = None
        self._last_time: datetime | None = None

    @property
    def is_live(self) -> bool:
        """Safety invariant: Paper loop never engages live broker order routing."""
        return False

    def process_event(self, event: NormalizedMarketEvent) -> None:
        """Process a single incoming normalized market event through the full pipeline."""
        now = event.exchange_timestamp
        if self._start_time is None:
            self._start_time = now
        self._last_time = now

        # 1. Update adapter market price
        self.paper_adapter.update_market_price(event.symbol, event.last_price)

        # 2. Watcher evaluation for exits
        self._evaluate_exits(event)

        # 3. Calculate features
        snapshot = self.feature_engine.process_tick(event)

        # 4. Strategy candidate screening and risk gating
        self._evaluate_entries(event, snapshot)

        # 5. Record equity snapshot
        self._record_equity(now)

    def _evaluate_exits(self, event: NormalizedMarketEvent) -> None:
        """Evaluate open positions for emergency stops, profit targets, and trailing ratchets."""
        symbol_key = event.symbol.upper()
        matching = [p for p in self._active_positions.values() if p.symbol == symbol_key]
        if not matching:
            return

        interventions = self.position_watcher.evaluate_tick(event)
        for intervention in interventions:
            pid = intervention.position_id
            if pid not in self._active_positions:
                continue

            pos = self._active_positions.pop(pid)
            trade_id = self._active_trade_ids.pop(pid)
            entry_regime = self._position_entry_regimes.pop(pid, MarketRegime.LOW_VOLATILITY_COMPRESSION)

            slippage = self.tick_size * Decimal(self.slippage_ticks)
            exit_price = (event.last_price - slippage).quantize(Decimal("0.01"))

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
                exit_timestamp=event.exchange_timestamp,
                exit_price=exit_price,
                exit_slippage=slippage,
                exit_trigger=intervention.trigger,
                friction=friction,
                market_regime_at_exit=entry_regime,
            )

    def _evaluate_entries(self, event: NormalizedMarketEvent, snapshot: FeatureSnapshot) -> None:
        """Screen candidates, perform deterministic risk checks, and dispatch orders."""
        candidates = self.candidate_ranker.evaluate_snapshot(snapshot)
        if not candidates:
            return

        for cand in candidates:
            active_list = list(self._active_positions.values())
            risk_res = self.risk_engine.evaluate_candidate(cand, current_positions=active_list)

            if not risk_res.approved or risk_res.approved_quantity <= 0:
                continue

            qty = risk_res.approved_quantity
            notional = Decimal(qty) * cand.trigger_price

            if self.capital_manager.available_capital < notional:
                continue

            pos_id = f"pos-{uuid.uuid4().hex[:8]}"
            self.capital_manager.allocate_capital(
                position_id=pos_id,
                symbol=cand.symbol,
                quantity=qty,
                price=cand.trigger_price,
            )

            req = OrderRequest(
                client_order_id=f"ord-{uuid.uuid4().hex[:8]}",
                plan_id=cand.candidate_id,
                symbol=cand.symbol,
                side=TradeSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=qty,
                price=cand.trigger_price,
            )
            order_event = self.execution_engine.submit_order(req)

            if order_event.status == OrderStatus.FILLED:
                fill_price = order_event.average_fill_price or cand.trigger_price
                slippage_cost = abs(fill_price - cand.trigger_price)

                entry_regime = (
                    cand.feature_snapshot.regime
                    if cand.feature_snapshot is not None
                    else snapshot.regime
                )

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

    def _record_equity(self, timestamp: datetime) -> None:
        """Mark portfolio to market and record equity point."""
        active_list = list(self._active_positions.values())
        self.capital_manager.update_unrealized_pnl(active_list)
        dd_amt, dd_pct = self.capital_manager.get_daily_drawdown()

        self.equity_curve.append(
            EquityPoint(
                timestamp=timestamp,
                total_equity=self.capital_manager.total_capital,
                cash_balance=self.capital_manager.available_capital,
                unrealized_pnl=self.capital_manager.unrealized_pnl,
                drawdown_amount=dd_amt,
                drawdown_pct=float(dd_pct),
            )
        )

    def get_performance_summary(self) -> PerformanceMetrics:
        """Retrieve aggregated performance telemetry for current paper session."""
        completed = self.trade_journal.get_completed_trades()
        return PerformanceCalculator.calculate(
            trades=completed,
            equity_curve=self.equity_curve,
            start_time=self._start_time,
            end_time=self._last_time,
        )
