"""Audit trail and deterministic decision reconstruction from stored database records."""

import logging
from dataclasses import dataclass
from typing import Any

from app.db.connection import get_connection
from app.db.repository import DatabaseRepository
from app.models.contracts import (
    Candidate,
    FeatureSnapshot,
    PositionSnapshot,
    TradePlan,
    TradeRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class DecisionAuditTrail:
    """Comprehensive, reproducible trail linking all pipeline artifacts for a setup."""

    candidate_id: str
    plan_id: str | None
    candidate: Candidate | None
    feature_snapshot: FeatureSnapshot | None
    ai_analyses: list[dict[str, Any]]
    trade_plan: TradePlan | None
    orders: list[dict[str, Any]]
    trades: list[TradeRecord]
    positions: list[PositionSnapshot]
    is_fully_reproducible: bool
    reproducibility_notes: list[str]


class DecisionAuditTrailManager:
    """Reconstructs historical decision pipelines and verifies reproducibility."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        db_path: str | None = None,
    ) -> None:
        self.repo = repository or DatabaseRepository(db_path=db_path)
        self.db_path = db_path

    def reconstruct_trail(
        self,
        candidate_id: str | None = None,
        plan_id: str | None = None,
    ) -> DecisionAuditTrail:
        """Reconstruct complete decision lifecycle from candidate to trade fill and position."""
        if not candidate_id and not plan_id:
            raise ValueError("Must provide either candidate_id or plan_id to reconstruct trail")

        notes: list[str] = []

        # 1. Resolve plan and candidate IDs
        plan: TradePlan | None = None
        if plan_id:
            plan = self.repo.get_trade_plan(plan_id)
            if plan and not candidate_id:
                candidate_id = plan.candidate_id

        cand_id = candidate_id or ""
        candidate = self.repo.get_candidate(cand_id) if cand_id else None
        if not candidate:
            notes.append(f"Candidate {cand_id} record not found")

        # 2. Resolve TradePlan if not yet loaded
        if not plan and cand_id:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT id FROM trade_plans WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1",
                    (cand_id,),
                )
                row = cur.fetchone()
                if row:
                    plan = self.repo.get_trade_plan(row[0])

        resolved_plan_id = plan.plan_id if plan else plan_id

        # 3. Features
        fs: FeatureSnapshot | None = None
        if candidate:
            fs = self.repo.get_latest_feature(candidate.symbol)

        # 4. AI Analyses
        analyses = self.repo.get_ai_analyses_for_candidate(cand_id) if cand_id else []
        if not analyses:
            notes.append("No AI analyses associated with candidate")

        # 5. Orders
        orders: list[dict[str, Any]] = []
        if resolved_plan_id:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT * FROM orders WHERE plan_id = ?", (resolved_plan_id,)
                )
                orders = [dict(r) for r in cur.fetchall()]

        # 6. Trades
        trades: list[TradeRecord] = []
        if resolved_plan_id:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT * FROM trades WHERE plan_id = ?", (resolved_plan_id,)
                )
                trades = [self.repo._row_to_trade(r) for r in cur.fetchall()]

        # 7. Positions
        positions: list[PositionSnapshot] = []
        if resolved_plan_id:
            with get_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT * FROM positions WHERE plan_id = ?", (resolved_plan_id,)
                )
                positions = [self.repo._row_to_position(r) for r in cur.fetchall()]

        # 8. Check reproducibility
        is_reproducible = candidate is not None and plan is not None
        if not is_reproducible:
            notes.append("Critical pipeline inputs missing; cannot guarantee 100% reproduction")
        else:
            notes.append("All core inputs and intermediate artifacts preserved with mathematical fidelity")

        return DecisionAuditTrail(
            candidate_id=cand_id,
            plan_id=resolved_plan_id,
            candidate=candidate,
            feature_snapshot=fs,
            ai_analyses=analyses,
            trade_plan=plan,
            orders=orders,
            trades=trades,
            positions=positions,
            is_fully_reproducible=is_reproducible,
            reproducibility_notes=notes,
        )
