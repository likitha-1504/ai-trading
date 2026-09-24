"""Trade Journal for audit trails, lifecycle tracking, and post-trade analytics.

Records all order executions, cost breakdowns, holding durations, exit triggers,
and market regimes with deterministic precision.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models.contracts import (
    FrictionBreakdown,
    MarketRegime,
    StrategyType,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)

logger = logging.getLogger(__name__)


@dataclass
class _ActiveEntry:
    trade_id: str
    plan_id: str
    symbol: str
    side: TradeSide
    strategy: StrategyType
    quantity: int
    entry_timestamp: datetime
    entry_price: Decimal
    entry_slippage: Decimal
    market_regime_at_entry: MarketRegime


class TradeJournal:
    """Maintains active trade records and produces completed TradeRecord items for audit and metrics."""

    def __init__(self) -> None:
        self._active_entries: dict[str, _ActiveEntry] = {}
        self._completed_trades: list[TradeRecord] = []

    def record_entry(
        self,
        plan_id: str,
        symbol: str,
        side: TradeSide,
        strategy: StrategyType,
        quantity: int,
        entry_timestamp: datetime,
        entry_price: Decimal,
        entry_slippage: Decimal,
        market_regime_at_entry: MarketRegime,
    ) -> str:
        """Register the open leg of a trade upon order fill."""
        trade_id = f"trd-{uuid.uuid4().hex[:10]}"
        entry = _ActiveEntry(
            trade_id=trade_id,
            plan_id=plan_id,
            symbol=symbol.upper(),
            side=side,
            strategy=strategy,
            quantity=quantity,
            entry_timestamp=entry_timestamp,
            entry_price=entry_price,
            entry_slippage=entry_slippage,
            market_regime_at_entry=market_regime_at_entry,
        )
        self._active_entries[trade_id] = entry
        logger.debug("Trade entry recorded: %s (%s %d @ %s)", trade_id, symbol, quantity, entry_price)
        return trade_id

    def record_exit(
        self,
        trade_id: str,
        exit_timestamp: datetime,
        exit_price: Decimal,
        exit_slippage: Decimal,
        exit_trigger: WatcherExitTrigger,
        friction: FrictionBreakdown,
        market_regime_at_exit: MarketRegime,
    ) -> TradeRecord:
        """Close an active trade, calculate gross and net P/L, and record final TradeRecord."""
        if trade_id not in self._active_entries:
            raise KeyError(f"Active trade {trade_id} not found in journal")

        entry = self._active_entries.pop(trade_id)
        qty_dec = Decimal(entry.quantity)

        # Financial P/L computation
        if entry.side == TradeSide.BUY:
            gross_pnl = (exit_price - entry.entry_price) * qty_dec
        else:
            gross_pnl = (entry.entry_price - exit_price) * qty_dec

        net_pnl = gross_pnl - friction.total_friction
        holding_seconds = max(0.0, (exit_timestamp - entry.entry_timestamp).total_seconds())

        record = TradeRecord(
            trade_id=trade_id,
            plan_id=entry.plan_id,
            symbol=entry.symbol,
            side=entry.side,
            strategy=entry.strategy,
            quantity=entry.quantity,
            entry_timestamp=entry.entry_timestamp,
            entry_price=entry.entry_price,
            entry_slippage=entry.entry_slippage,
            exit_timestamp=exit_timestamp,
            exit_price=exit_price,
            exit_slippage=exit_slippage,
            exit_trigger=exit_trigger,
            gross_pnl=gross_pnl.quantize(Decimal("0.01")),
            friction=friction,
            net_pnl=net_pnl.quantize(Decimal("0.01")),
            holding_duration_seconds=round(holding_seconds, 2),
            market_regime_at_entry=entry.market_regime_at_entry,
            market_regime_at_exit=market_regime_at_exit,
        )

        self._completed_trades.append(record)
        logger.debug(
            "Trade %s closed: gross=%s, friction=%s, net=%s via %s",
            trade_id,
            record.gross_pnl,
            friction.total_friction,
            record.net_pnl,
            exit_trigger.value,
        )
        return record

    def get_completed_trades(self) -> list[TradeRecord]:
        """Fetch all closed and audited trades."""
        return list(self._completed_trades)

    def get_active_count(self) -> int:
        """Count currently unclosed active trades."""
        return len(self._active_entries)

    def clear(self) -> None:
        """Clear all active and completed records."""
        self._active_entries.clear()
        self._completed_trades.clear()
