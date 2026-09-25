"""Unified repository providing CRUD operations for all 13 core database entities."""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.db.connection import get_connection
from app.models.contracts import (
    ApprovalMode,
    Candidate,
    CapitalSnapshot,
    ChallengerCritique,
    ExecutionMetricsSnapshot,
    FeatureSnapshot,
    FrictionBreakdown,
    MarketRegime,
    MarketThesis,
    OrderRequest,
    OrderStatus,
    PositionSnapshot,
    PositionStatus,
    RiskLimits,
    StopProtection,
    StrategyType,
    TradePlan,
    TradeRecord,
    TradeSide,
    WatcherExitTrigger,
)

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Synchronous transactional repository for persisting and querying all 13 trading entities."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    # =========================================================================
    # 1. Capital State
    # =========================================================================

    def save_capital_state(
        self,
        snapshot: CapitalSnapshot,
        daily_drawdown: Decimal | None = None,
        high_water_mark: Decimal | None = None,
    ) -> int:
        """Persist account equity and capital allocation snapshot."""
        dd = (
            daily_drawdown
            if daily_drawdown is not None
            else getattr(snapshot, "daily_drawdown_amount", Decimal("0.00"))
        )
        hwm = (
            high_water_mark
            if high_water_mark is not None
            else getattr(snapshot, "high_water_mark", snapshot.total_capital)
        )
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO capital_state (
                    timestamp, total_capital, available_capital, deployed_capital,
                    buying_power, realized_pnl, unrealized_pnl, daily_drawdown,
                    high_water_mark, currency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp.isoformat(),
                    float(snapshot.total_capital),
                    float(snapshot.available_capital),
                    float(snapshot.deployed_capital),
                    float(snapshot.buying_power),
                    float(snapshot.realized_pnl),
                    float(snapshot.unrealized_pnl),
                    float(dd),
                    float(hwm),
                    "INR",
                ),
            )
            return cur.lastrowid or 0

    def get_latest_capital_state(self) -> dict[str, Any] | None:
        """Retrieve most recent capital snapshot."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM capital_state ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # 2. Positions
    # =========================================================================

    def save_position(self, pos: PositionSnapshot) -> None:
        """Save a new position record."""
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO positions (
                    id, plan_id, symbol, side, quantity, entry_price, current_price,
                    hard_stop_price, take_profit_price, trailing_stop_price,
                    highest_price_seen, unrealized_pnl, realized_pnl, status,
                    opened_at, closed_at, exit_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pos.position_id,
                    pos.plan_id,
                    pos.symbol,
                    pos.side.value,
                    pos.quantity,
                    float(pos.entry_price),
                    float(pos.current_price),
                    float(pos.hard_stop_price),
                    float(pos.take_profit_price) if pos.take_profit_price else None,
                    float(pos.trailing_stop_price) if pos.trailing_stop_price else None,
                    float(pos.highest_price_seen) if pos.highest_price_seen else None,
                    float(pos.unrealized_pnl),
                    0.0,
                    pos.status.value,
                    pos.opened_at.isoformat(),
                    None,
                    None,
                ),
            )

    def update_position_price(
        self,
        position_id: str,
        current_price: Decimal,
        unrealized_pnl: Decimal,
        trailing_stop_price: Decimal | None = None,
        highest_price_seen: Decimal | None = None,
    ) -> None:
        """Update floating price, trailing stop, and P/L for an open position."""
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE positions SET
                    current_price = ?,
                    unrealized_pnl = ?,
                    trailing_stop_price = COALESCE(?, trailing_stop_price),
                    highest_price_seen = COALESCE(?, highest_price_seen)
                WHERE id = ?
                """,
                (
                    float(current_price),
                    float(unrealized_pnl),
                    float(trailing_stop_price) if trailing_stop_price else None,
                    float(highest_price_seen) if highest_price_seen else None,
                    position_id,
                ),
            )

    def close_position(
        self,
        position_id: str,
        exit_price: Decimal,
        realized_pnl: Decimal,
        exit_reason: str,
        closed_at: datetime | None = None,
    ) -> None:
        """Mark position as CLOSED with exit metadata."""
        now = closed_at or datetime.now(timezone.utc)
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE positions SET
                    current_price = ?,
                    realized_pnl = ?,
                    unrealized_pnl = 0.0,
                    status = 'CLOSED',
                    closed_at = ?,
                    exit_reason = ?
                WHERE id = ?
                """,
                (
                    float(exit_price),
                    float(realized_pnl),
                    now.isoformat(),
                    exit_reason,
                    position_id,
                ),
            )

    def get_position(self, position_id: str) -> PositionSnapshot | None:
        """Retrieve PositionSnapshot by position_id."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_position(row)

    def get_open_positions(self) -> list[PositionSnapshot]:
        """Retrieve all currently OPEN positions."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM positions WHERE status = 'OPEN'")
            return [self._row_to_position(r) for r in cur.fetchall()]

    def get_all_positions(self, limit: int = 50) -> list[PositionSnapshot]:
        """Retrieve recent positions (open and closed)."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM positions ORDER BY opened_at DESC LIMIT ?", (limit,)
            )
            return [self._row_to_position(r) for r in cur.fetchall()]

    def _row_to_position(self, r: Any) -> PositionSnapshot:
        side_val = r["side"]
        if side_val in ("LONG", "BUY"):
            side = TradeSide.BUY
        else:
            side = TradeSide.SELL

        return PositionSnapshot(
            position_id=r["id"],
            plan_id=r["plan_id"] or "",
            symbol=r["symbol"],
            side=side,
            quantity=r["quantity"],
            entry_price=Decimal(str(r["entry_price"])),
            current_price=Decimal(str(r["current_price"])),
            hard_stop_price=Decimal(str(r["hard_stop_price"])),
            trailing_stop_price=(
                Decimal(str(r["trailing_stop_price"]))
                if r["trailing_stop_price"] is not None
                else None
            ),
            take_profit_price=(
                Decimal(str(r["take_profit_price"]))
                if r["take_profit_price"] is not None
                else None
            ),
            highest_price_seen=(
                Decimal(str(r["highest_price_seen"]))
                if r["highest_price_seen"] is not None
                else None
            ),
            unrealized_pnl=Decimal(str(r["unrealized_pnl"])),
            status=PositionStatus(r["status"]),
            opened_at=datetime.fromisoformat(r["opened_at"]),
            last_evaluated_at=datetime.now(timezone.utc),
        )

    # =========================================================================
    # 3. Orders
    # =========================================================================

    def save_order(
        self,
        order: OrderRequest,
        status: OrderStatus = OrderStatus.CREATED,
        position_id: str | None = None,
    ) -> None:
        """Insert or replace an order record."""
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO orders (
                    id, client_order_id, plan_id, position_id, symbol, side,
                    order_type, quantity, price, stop_price, filled_quantity,
                    average_fill_price, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.client_order_id,
                    order.client_order_id,
                    order.plan_id,
                    position_id,
                    order.symbol,
                    order.side.value,
                    order.order_type.value,
                    order.quantity,
                    float(order.price) if order.price else None,
                    float(order.stop_price) if order.stop_price else None,
                    0,
                    0.0,
                    status.value,
                    now,
                    now,
                ),
            )

    def update_order_status(
        self,
        client_order_id: str,
        status: OrderStatus,
        filled_quantity: int = 0,
        average_fill_price: Decimal = Decimal("0.00"),
        position_id: str | None = None,
    ) -> None:
        """Update lifecycle state and fill progress of an order."""
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE orders SET
                    status = ?,
                    filled_quantity = ?,
                    average_fill_price = ?,
                    position_id = COALESCE(?, position_id),
                    updated_at = ?
                WHERE client_order_id = ?
                """,
                (
                    status.value,
                    filled_quantity,
                    float(average_fill_price),
                    position_id,
                    now,
                    client_order_id,
                ),
            )

    def get_order(self, client_order_id: str) -> dict[str, Any] | None:
        """Retrieve order by client_order_id."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Retrieve active/non-terminal orders."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM orders
                WHERE status IN ('CREATED', 'SUBMITTED', 'ACKNOWLEDGED', 'PARTIALLY_FILLED')
                ORDER BY created_at ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def get_all_orders(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all recent orders."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # 4. Trades
    # =========================================================================

    def save_trade(self, trade: TradeRecord) -> str:
        """Persist an executed TradeRecord item into the journal."""
        f = trade.friction
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trades (
                    id, order_id, position_id, plan_id, symbol, side, strategy,
                    quantity, price, fee_brokerage, fee_stt, fee_exchange, fee_sebi,
                    fee_stamp_duty, fee_gst, slippage, total_friction, gross_pnl,
                    net_pnl, holding_duration_seconds, exit_trigger, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.trade_id,
                    trade.plan_id,  # foreign key / cross reference
                    f"pos-{trade.plan_id}",
                    trade.plan_id,
                    trade.symbol,
                    trade.side.value,
                    trade.strategy.value,
                    trade.quantity,
                    float(trade.exit_price),
                    float(f.brokerage),
                    float(f.stt),
                    float(f.exchange_charges),
                    float(f.sebi_charges),
                    float(f.stamp_duty),
                    float(f.gst),
                    float(f.expected_slippage),
                    float(f.total_friction),
                    float(trade.gross_pnl),
                    float(trade.net_pnl),
                    float(trade.holding_duration_seconds),
                    trade.exit_trigger.value,
                    trade.exit_timestamp.isoformat(),
                ),
            )
        return trade.trade_id

    def get_trade(self, trade_id: str) -> TradeRecord | None:
        """Retrieve TradeRecord by trade_id."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_trade(row)

    def get_trades(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        limit: int = 100,
    ) -> list[TradeRecord]:
        """Query historical trades with optional symbol and strategy filters."""
        query = "SELECT * FROM trades"
        params: list[Any] = []
        conds: list[str] = []

        if symbol:
            conds.append("symbol = ?")
            params.append(symbol)
        if strategy:
            conds.append("strategy = ?")
            params.append(strategy)

        if conds:
            query += " WHERE " + " AND ".join(conds)
        query += " ORDER BY executed_at DESC LIMIT ?"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            cur = conn.execute(query, params)
            return [self._row_to_trade(r) for r in cur.fetchall()]

    def get_recent_trades(self, limit: int = 50) -> list[TradeRecord]:
        """Retrieve recent executed trade records."""
        return self.get_trades(limit=limit)

    def _row_to_trade(self, r: Any) -> TradeRecord:
        friction = FrictionBreakdown(
            brokerage=Decimal(str(r["fee_brokerage"])),
            stt=Decimal(str(r["fee_stt"])),
            exchange_charges=Decimal(str(r["fee_exchange"])),
            sebi_charges=Decimal(str(r["fee_sebi"])),
            stamp_duty=Decimal(str(r["fee_stamp_duty"])),
            gst=Decimal(str(r["fee_gst"])),
            expected_slippage=Decimal(str(r["slippage"])),
            total_friction=Decimal(str(r["total_friction"])),
        )
        ts = datetime.fromisoformat(r["executed_at"])
        trigger_raw = dict(r).get("exit_trigger") or "TIME_EXPIRY"
        try:
            exit_trigger = WatcherExitTrigger(trigger_raw)
        except ValueError:
            exit_trigger = WatcherExitTrigger.TIME_EXPIRY

        return TradeRecord(
            trade_id=r["id"],
            plan_id=r["plan_id"] or "",
            symbol=r["symbol"],
            side=TradeSide(r["side"]),
            strategy=StrategyType(r["strategy"]),
            quantity=r["quantity"],
            entry_timestamp=ts,
            entry_price=Decimal(str(r["price"])),
            entry_slippage=Decimal("0.05"),
            exit_timestamp=ts,
            exit_price=Decimal(str(r["price"])),
            exit_slippage=Decimal(str(r["slippage"])),
            exit_trigger=exit_trigger,
            gross_pnl=Decimal(str(r["gross_pnl"])),
            friction=friction,
            net_pnl=Decimal(str(r["net_pnl"])),
            holding_duration_seconds=float(r["holding_duration_seconds"]),
            market_regime_at_entry=MarketRegime.BULLISH_TRENDING,
            market_regime_at_exit=MarketRegime.BULLISH_TRENDING,
        )

    # =========================================================================
    # 5. Candidates
    # =========================================================================

    def save_candidate(self, candidate: Candidate, status: str = "DETECTED") -> None:
        """Persist detected candidate setup."""
        fs_json = (
            candidate.feature_snapshot.model_dump_json()
            if candidate.feature_snapshot
            else None
        )
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO candidates (
                    id, timestamp, symbol, strategy_name, side, trigger_price,
                    initial_stop_price, target_price, score, evidence, feature_snapshot, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.detected_at.isoformat(),
                    candidate.symbol,
                    candidate.strategy_type.value,
                    candidate.side.value,
                    float(candidate.trigger_price),
                    float(candidate.initial_stop_price),
                    float(candidate.suggested_target_price)
                    if candidate.suggested_target_price
                    else None,
                    float(candidate.rank_score),
                    json.dumps(candidate.quantitative_evidence),
                    fs_json,
                    status,
                ),
            )

    def get_candidate(self, candidate_id: str) -> Candidate | None:
        """Retrieve Candidate by candidate_id."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            res = cur.fetchone()
            if not res:
                return None
            r = dict(res)
            fs_data: FeatureSnapshot | None = None
            if r.get("feature_snapshot"):
                try:
                    fs_data = FeatureSnapshot.model_validate_json(r["feature_snapshot"])
                except (ValueError, TypeError, KeyError):
                    fs_data = None

            if fs_data is None:
                # Fallback to feature table lookup or default snapshot
                fs_data = self.get_latest_feature(r["symbol"])
                if fs_data is None:
                    fs_data = FeatureSnapshot(
                        symbol=r["symbol"],
                        timestamp=datetime.fromisoformat(r["timestamp"]),
                        bar_timeframe="1m",
                        vwap=Decimal(str(r["trigger_price"])),
                        current_price=Decimal(str(r["trigger_price"])),
                        relative_volume_10=Decimal("1.0"),
                        volume_acceleration=Decimal("0.0"),
                        price_acceleration=Decimal("0.0"),
                        realized_volatility_15=Decimal("0.01"),
                        spread_pct=Decimal("0.001"),
                        liquidity_score=Decimal("80.0"),
                        market_index_direction="NEUTRAL",
                        regime=MarketRegime.BULLISH_TRENDING,
                    )

            return Candidate(
                candidate_id=r["id"],
                detected_at=datetime.fromisoformat(r["timestamp"]),
                symbol=r["symbol"],
                strategy_type=StrategyType(r["strategy_name"]),
                side=TradeSide(r["side"]),
                trigger_price=Decimal(str(r["trigger_price"])),
                initial_stop_price=Decimal(str(r["initial_stop_price"])),
                suggested_target_price=(
                    Decimal(str(r["target_price"]))
                    if r["target_price"] is not None
                    else Decimal(str(r["trigger_price"]))
                ),
                rank_score=Decimal(str(r["score"])),
                quantitative_evidence=json.loads(r["evidence"]),
                feature_snapshot=fs_data,
            )

    def get_recent_candidates(self, limit: int = 50) -> list[Candidate]:
        """Retrieve recent discovered candidates."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id FROM candidates ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            results: list[Candidate] = []
            for r in cur.fetchall():
                cand = self.get_candidate(r["id"])
                if cand:
                    results.append(cand)
            return results

    # =========================================================================
    # 6. Features
    # =========================================================================

    def save_feature_snapshot(self, fs: FeatureSnapshot) -> int:
        """Persist calculated quantitative features."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO features (
                    symbol, timestamp, timeframe, vwap, current_price, momentum_score,
                    relative_volume, volume_accel, price_accel, volatility,
                    spread, liquidity_score, regime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fs.symbol,
                    fs.timestamp.isoformat(),
                    fs.bar_timeframe,
                    float(fs.vwap),
                    float(fs.current_price),
                    float(fs.momentum_score),
                    float(fs.relative_volume_10),
                    float(fs.volume_acceleration),
                    float(fs.price_acceleration),
                    float(fs.realized_volatility_15),
                    float(fs.spread_pct),
                    float(fs.liquidity_score),
                    fs.regime.value,
                ),
            )
            return cur.lastrowid or 0

    def get_latest_feature(self, symbol: str) -> FeatureSnapshot | None:
        """Retrieve latest feature snapshot for symbol."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM features WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return self._row_to_feature(r)

    def _row_to_feature(self, r: Any) -> FeatureSnapshot:
        return FeatureSnapshot(
            symbol=r["symbol"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            bar_timeframe=r["timeframe"],
            vwap=Decimal(str(r["vwap"])),
            current_price=Decimal(str(r["current_price"])),
            vwap_distance_pct=Decimal("0.0"),
            momentum_score=Decimal(str(r["momentum_score"])),
            relative_volume_10=Decimal(str(r["relative_volume"])),
            volume_acceleration=Decimal(str(r["volume_accel"])),
            price_acceleration=Decimal(str(r["price_accel"])),
            realized_volatility_15=Decimal(str(r["volatility"])),
            spread_pct=Decimal(str(r["spread"])),
            liquidity_score=Decimal(str(r["liquidity_score"])),
            market_index_direction="NEUTRAL",
            price_structure="RANGE",
            regime=MarketRegime(r["regime"]),
        )

    def get_all_latest_features(self) -> list[FeatureSnapshot]:
        """Retrieve most recent FeatureSnapshot for each distinct symbol."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT f.* FROM features f
                INNER JOIN (
                    SELECT symbol, MAX(id) as max_id
                    FROM features
                    GROUP BY symbol
                ) latest ON f.id = latest.max_id
                """
            )
            return [self._row_to_feature(r) for r in cur.fetchall()]

    # =========================================================================
    # 7. AI Analyses
    # =========================================================================

    def save_ai_analysis(
        self,
        candidate_id: str,
        analysis: MarketThesis | ChallengerCritique,
    ) -> str:
        """Store qualitative thesis (Qwen3) or adversarial critique (DeepSeek-R1)."""
        now = datetime.now(timezone.utc).isoformat()
        analysis_id = f"ai-{analysis.candidate_id}-{analysis.model_name[:5]}"

        with get_connection(self.db_path) as conn:
            if isinstance(analysis, MarketThesis):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ai_analyses (
                        id, candidate_id, model_name, role, thesis_summary,
                        evidence, invalidation_conditions, risks, suggested_action,
                        confidence_score, worst_case_scenario, downside_severity,
                        recommendation_flag, latency_ms, token_count, is_fallback,
                        prompt_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis_id,
                        candidate_id,
                        analysis.model_name,
                        "ANALYST",
                        analysis.thesis_summary,
                        json.dumps(analysis.bullish_evidence),
                        json.dumps(analysis.invalidation_conditions),
                        json.dumps(analysis.perceived_risks),
                        analysis.suggested_action.value,
                        float(analysis.confidence_score),
                        None,
                        None,
                        None,
                        analysis.latency_ms,
                        analysis.token_count,
                        1 if analysis.is_fallback else 0,
                        analysis.prompt_version,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ai_analyses (
                        id, candidate_id, model_name, role, thesis_summary,
                        evidence, invalidation_conditions, risks, suggested_action,
                        confidence_score, worst_case_scenario, downside_severity,
                        recommendation_flag, latency_ms, token_count, is_fallback,
                        prompt_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis_id,
                        candidate_id,
                        analysis.model_name,
                        "CHALLENGER",
                        analysis.critique_summary,
                        json.dumps(analysis.identified_vulnerabilities),
                        json.dumps(analysis.invalidation_conditions),
                        json.dumps(analysis.contradictory_signals),
                        analysis.recommendation_flag.value,
                        None,
                        analysis.worst_case_scenario,
                        analysis.downside_severity.value,
                        analysis.recommendation_flag.value,
                        analysis.latency_ms,
                        analysis.token_count,
                        1 if analysis.is_fallback else 0,
                        analysis.prompt_version,
                        now,
                    ),
                )
        return analysis_id

    def get_ai_analyses_for_candidate(self, candidate_id: str) -> list[dict[str, Any]]:
        """Retrieve all AI analyses linked to a candidate."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM ai_analyses WHERE candidate_id = ? ORDER BY created_at ASC",
                (candidate_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_all_ai_analyses(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent AI analyses across all candidates."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM ai_analyses ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # 8. Trade Plans
    # =========================================================================

    def save_trade_plan(self, plan: TradePlan) -> str:
        """Persist synthesized immutable TradePlan."""
        hard_stop_val = (
            float(plan.hard_stop_price)
            if plan.hard_stop_price
            else (
                float(plan.stop_protection.hard_stop_price)
                if plan.stop_protection
                else 0.0
            )
        )
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trade_plans (
                    id, candidate_id, instrument, side, quantity, entry_price_target,
                    hard_stop, take_profit, trailing_trigger, expected_edge,
                    estimated_costs, risk_limits, stop_protection, invalidation,
                    strategy, ai_evidence_references, decision_reason, approval_mode,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.candidate_id,
                    plan.instrument,
                    plan.side.value,
                    plan.quantity,
                    float(plan.entry_price_target),
                    hard_stop_val,
                    float(plan.take_profit_price) if plan.take_profit_price else None,
                    float(plan.trailing_trigger_price) if plan.trailing_trigger_price else None,
                    float(plan.expected_edge),
                    float(plan.estimated_costs.total_friction) if plan.estimated_costs else 0.0,
                    plan.risk_limits.model_dump_json() if plan.risk_limits else "{}",
                    plan.stop_protection.model_dump_json() if plan.stop_protection else "{}",
                    json.dumps(plan.invalidation),
                    plan.strategy.value,
                    json.dumps(plan.ai_evidence_references),
                    plan.decision_reason,
                    plan.approval_mode.value,
                    plan.created_at.isoformat(),
                ),
            )
        return plan.plan_id

    def get_trade_plan(self, plan_id: str) -> TradePlan | None:
        """Retrieve TradePlan by plan_id."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM trade_plans WHERE id = ?", (plan_id,))
            r = cur.fetchone()
            if not r:
                return None
            return self._row_to_trade_plan(r)

    def _row_to_trade_plan(self, r: Any) -> TradePlan:
        risk_limits_dict = json.loads(r["risk_limits"]) if r["risk_limits"] else {}
        stop_protection_dict = json.loads(r["stop_protection"]) if r["stop_protection"] else {}

        risk_limits = RiskLimits(
            max_loss_amount=Decimal(str(risk_limits_dict.get("max_loss_amount", "1.50"))),
            max_capital_allocation=Decimal(str(risk_limits_dict.get("max_capital_allocation", "100.00"))),
            max_position_size_pct=Decimal(str(risk_limits_dict.get("max_position_size_pct", "0.015"))),
            max_daily_drawdown_pct=Decimal(str(risk_limits_dict.get("max_daily_drawdown_pct", "0.03"))),
        )

        stop_protection = StopProtection(
            hard_stop_price=Decimal(str(stop_protection_dict.get("hard_stop_price", r["hard_stop"]))),
            trailing_trigger_price=(
                Decimal(str(stop_protection_dict["trailing_trigger_price"]))
                if stop_protection_dict.get("trailing_trigger_price")
                else None
            ),
            take_profit_price=(
                Decimal(str(stop_protection_dict["take_profit_price"]))
                if stop_protection_dict.get("take_profit_price")
                else None
            ),
            time_exit_time=stop_protection_dict.get("time_exit_time", "15:15 IST"),
        )

        friction = FrictionBreakdown(
            brokerage=Decimal("0.05"),
            stt=Decimal("0.05"),
            exchange_charges=Decimal("0.01"),
            sebi_charges=Decimal("0.001"),
            stamp_duty=Decimal("0.01"),
            gst=Decimal("0.01"),
            expected_slippage=Decimal("0.05"),
            total_friction=Decimal(str(r["estimated_costs"])),
        )

        return TradePlan(
            plan_id=r["id"],
            candidate_id=r["candidate_id"],
            created_at=datetime.fromisoformat(r["created_at"]),
            instrument=r["instrument"],
            symbol=r["instrument"],
            side=TradeSide(r["side"]),
            quantity=r["quantity"],
            entry_price_target=Decimal(str(r["entry_price_target"])),
            strategy=StrategyType(r["strategy"]),
            expected_edge=Decimal(str(r["expected_edge"])),
            expected_gross_edge=Decimal(str(r["expected_edge"])),
            expected_net_edge=Decimal(str(r["expected_edge"])),
            estimated_costs=friction,
            friction=friction,
            risk_limits=risk_limits,
            stop_protection=stop_protection,
            hard_stop_price=Decimal(str(r["hard_stop"])),
            take_profit_price=(
                Decimal(str(r["take_profit"])) if r["take_profit"] is not None else None
            ),
            trailing_trigger_price=(
                Decimal(str(r["trailing_trigger"]))
                if r["trailing_trigger"] is not None
                else None
            ),
            invalidation=json.loads(r["invalidation"]) if r["invalidation"] else [],
            ai_evidence_references=(
                json.loads(r["ai_evidence_references"])
                if r["ai_evidence_references"]
                else {}
            ),
            decision_reason=r["decision_reason"],
            approval_mode=ApprovalMode(r["approval_mode"]),
        )

    def update_trade_plan_approval(self, plan_id: str, mode: ApprovalMode) -> None:
        """Update approval mode of a TradePlan."""
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE trade_plans SET approval_mode = ? WHERE id = ?",
                (mode.value, plan_id),
            )

    def get_recent_trade_plans(self, limit: int = 50) -> list[TradePlan]:
        """Retrieve recent trade plans."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM trade_plans ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            return [self._row_to_trade_plan(r) for r in cur.fetchall()]

    # =========================================================================
    # 9. Risk Events
    # =========================================================================

    def save_risk_event(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any],
        symbol: str | None = None,
        timestamp: datetime | None = None,
    ) -> int:
        """Log a risk event, circuit breaker trip, or watchdog intervention."""
        ts = timestamp or datetime.now(timezone.utc)
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO risk_events (timestamp, event_type, severity, symbol, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ts.isoformat(),
                    event_type,
                    severity,
                    symbol,
                    json.dumps(details),
                ),
            )
            return cur.lastrowid or 0

    def get_recent_risk_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent risk audit records."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM risk_events ORDER BY id DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # 10. Strategy Versions
    # =========================================================================

    def save_strategy_version(
        self,
        strategy_name: str,
        version: str,
        parameters: dict[str, Any],
        is_active: bool = True,
    ) -> str:
        """Register or update an immutable strategy version."""
        version_id = f"{strategy_name}-{version}"
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO strategy_versions (
                    id, strategy_name, version, parameters, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    strategy_name,
                    version,
                    json.dumps(parameters),
                    1 if is_active else 0,
                    now,
                ),
            )
        return version_id

    def get_active_strategy_version(self, strategy_name: str) -> dict[str, Any] | None:
        """Retrieve active configuration parameters for a strategy."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM strategy_versions
                WHERE strategy_name = ? AND is_active = 1
                ORDER BY created_at DESC LIMIT 1
                """,
                (strategy_name,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_strategy_versions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all strategy versions in reverse chronological order."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM strategy_versions
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def save_strategy_proposal(self, proposal: Any) -> str:
        """Persist or update a StrategyImprovementProposal."""
        now = datetime.now(timezone.utc).isoformat()
        status_val = (
            proposal.status.value
            if hasattr(proposal.status, "value")
            else str(proposal.status)
        )
        param_changes_raw = (
            [c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c) for c in proposal.parameter_changes]
            if hasattr(proposal, "parameter_changes")
            else []
        )
        backtest_raw = (
            proposal.backtest_evidence.model_dump(mode="json")
            if getattr(proposal, "backtest_evidence", None) and hasattr(proposal.backtest_evidence, "model_dump")
            else getattr(proposal, "backtest_evidence", None)
        )
        paper_raw = (
            proposal.paper_evidence.model_dump(mode="json")
            if getattr(proposal, "paper_evidence", None) and hasattr(proposal.paper_evidence, "model_dump")
            else getattr(proposal, "paper_evidence", None)
        )
        created_val = (
            proposal.created_at.isoformat()
            if hasattr(proposal, "created_at") and hasattr(proposal.created_at, "isoformat")
            else str(getattr(proposal, "created_at", now))
        )
        approved_val = (
            proposal.approved_at.isoformat()
            if getattr(proposal, "approved_at", None) and hasattr(proposal.approved_at, "isoformat")
            else str(proposal.approved_at) if getattr(proposal, "approved_at", None) else None
        )

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO strategy_proposals (
                    id, strategy_name, target_version, current_version, status,
                    title, empirical_weakness, parameter_changes, backtest_evidence,
                    paper_evidence, approved_by, approval_token_masked, approved_at,
                    rejection_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.id,
                    proposal.strategy_name,
                    proposal.target_version,
                    proposal.current_version,
                    status_val,
                    proposal.title,
                    proposal.empirical_weakness,
                    json.dumps(param_changes_raw, default=str),
                    json.dumps(backtest_raw, default=str) if backtest_raw else None,
                    json.dumps(paper_raw, default=str) if paper_raw else None,
                    getattr(proposal, "approved_by", None),
                    getattr(proposal, "approval_token_masked", None),
                    approved_val,
                    getattr(proposal, "rejection_reason", None),
                    created_val,
                ),
            )
        return proposal.id

    def get_strategy_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """Retrieve a specific strategy proposal by ID."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM strategy_proposals WHERE id = ?",
                (proposal_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_strategy_proposals(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all strategy improvement proposals."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM strategy_proposals
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # 11. Model Calls
    # =========================================================================

    def save_model_call(
        self,
        model_name: str,
        role: str,
        prompt_version: str,
        latency_ms: int,
        success: bool,
        token_count: int | None = None,
        candidate_id: str | None = None,
        is_fallback: bool = False,
        error_reason: str | None = None,
    ) -> int:
        """Record model inference latency, tokens, and outcome telemetry."""
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO model_calls (
                    timestamp, model_name, candidate_id, role, prompt_version,
                    latency_ms, token_count, success, is_fallback, error_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    model_name,
                    candidate_id,
                    role,
                    prompt_version,
                    latency_ms,
                    token_count,
                    1 if success else 0,
                    1 if is_fallback else 0,
                    error_reason,
                ),
            )
            return cur.lastrowid or 0

    # =========================================================================
    # 12. Execution Metrics
    # =========================================================================

    def save_execution_metrics(self, metrics: ExecutionMetricsSnapshot) -> int:
        """Persist aggregated broker execution latency and fill telemetry."""
        now = datetime.now(timezone.utc).isoformat()
        fill_rate = (
            (metrics.total_orders_filled / metrics.total_orders_submitted) * 100
            if metrics.total_orders_submitted > 0
            else 0.0
        )
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO execution_metrics (
                    timestamp, total_orders_submitted, total_orders_filled,
                    total_orders_rejected, avg_submission_latency_ms,
                    avg_fill_latency_ms, total_slippage, fill_rate_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    metrics.total_orders_submitted,
                    metrics.total_orders_filled,
                    metrics.total_orders_rejected,
                    metrics.avg_submission_latency_ms,
                    metrics.avg_fill_latency_ms,
                    float(metrics.total_slippage_incurred),
                    fill_rate,
                ),
            )
            return cur.lastrowid or 0

    # =========================================================================
    # 13. System Events
    # =========================================================================

    def save_system_event(
        self,
        source: str,
        level: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Record operational system log entry."""
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO system_events (timestamp, source, level, message, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    now,
                    source,
                    level,
                    message,
                    json.dumps(metadata, default=str) if metadata else None,
                ),
            )
            return cur.lastrowid or 0

    def get_recent_system_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent system operational events."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM system_events ORDER BY id DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cur.fetchall()]
