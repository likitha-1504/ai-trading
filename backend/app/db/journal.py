"""Database-backed Trade Journal with persistent lifecycle tracking and P/L calculations."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.db.repository import DatabaseRepository
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


class DatabaseTradeJournal:
    """Manages active trades, settles exits, computes P/L, and stores immutable records in SQLite."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        db_path: str | None = None,
    ) -> None:
        self.repo = repository or DatabaseRepository(db_path=db_path)
        self._active_entries: dict[str, _ActiveEntry] = {}

    def record_entry(
        self,
        plan_id: str,
        symbol: str,
        side: TradeSide,
        strategy: StrategyType,
        quantity: int,
        entry_timestamp: datetime,
        entry_price: Decimal,
        entry_slippage: Decimal = Decimal("0.05"),
        market_regime_at_entry: MarketRegime = MarketRegime.BULLISH_TRENDING,
    ) -> str:
        """Register the opening leg of a trade."""
        trade_id = f"trd-{uuid.uuid4().hex[:10]}"
        entry = _ActiveEntry(
            trade_id=trade_id,
            plan_id=plan_id,
            symbol=symbol,
            side=side,
            strategy=strategy,
            quantity=quantity,
            entry_timestamp=entry_timestamp,
            entry_price=entry_price,
            entry_slippage=entry_slippage,
            market_regime_at_entry=market_regime_at_entry,
        )
        self._active_entries[trade_id] = entry
        logger.info(
            "Journal: Opened %s leg for %s (trade_id=%s, qty=%d, entry=%s)",
            side.value,
            symbol,
            trade_id,
            quantity,
            entry_price,
        )
        return trade_id

    def record_exit(
        self,
        trade_id: str,
        exit_price: Decimal,
        exit_timestamp: datetime,
        friction: FrictionBreakdown,
        exit_slippage: Decimal = Decimal("0.05"),
        exit_trigger: WatcherExitTrigger = WatcherExitTrigger.TIME_EXPIRY,
        market_regime_at_exit: MarketRegime = MarketRegime.BULLISH_TRENDING,
    ) -> TradeRecord:
        """Close an active trade, calculate gross & net P/L, and persist to database."""
        entry = self._active_entries.pop(trade_id, None)
        if entry is None:
            raise KeyError(f"Active trade {trade_id} not found in journal")

        qty = Decimal(entry.quantity)
        if entry.side == TradeSide.BUY:
            gross_pnl = (exit_price - entry.entry_price) * qty
        else:
            gross_pnl = (entry.entry_price - exit_price) * qty

        net_pnl = gross_pnl - friction.total_friction
        duration = max(0.0, (exit_timestamp - entry.entry_timestamp).total_seconds())

        record = TradeRecord(
            trade_id=entry.trade_id,
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
            gross_pnl=gross_pnl,
            friction=friction,
            net_pnl=net_pnl,
            holding_duration_seconds=duration,
            market_regime_at_entry=entry.market_regime_at_entry,
            market_regime_at_exit=market_regime_at_exit,
        )

        # Persist to database
        self.repo.save_trade(record)
        logger.info(
            "Journal: Settled %s (Gross: %s, Friction: %s, Net: %s INR)",
            trade_id,
            gross_pnl,
            friction.total_friction,
            net_pnl,
        )
        return record

    def record_completed_trade(self, trade: TradeRecord) -> str:
        """Directly insert a completed historical or paper trade record."""
        return self.repo.save_trade(trade)

    def get_trade(self, trade_id: str) -> TradeRecord | None:
        """Retrieve trade from repository."""
        return self.repo.get_trade(trade_id)

    def get_all_trades(self, limit: int = 200) -> list[TradeRecord]:
        """Retrieve all completed trades."""
        return self.repo.get_trades(limit=limit)

    def get_trades_by_symbol(self, symbol: str, limit: int = 100) -> list[TradeRecord]:
        """Retrieve trades filtered by ticker symbol."""
        return self.repo.get_trades(symbol=symbol, limit=limit)

    def get_trades_by_strategy(
        self, strategy: StrategyType, limit: int = 100
    ) -> list[TradeRecord]:
        """Retrieve trades filtered by strategy type."""
        return self.repo.get_trades(strategy=strategy.value, limit=limit)
