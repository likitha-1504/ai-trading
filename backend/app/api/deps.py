"""FastAPI dependency injection providers.

Supplies database repositories, analytics aggregators, system controllers,
and strict authorization checks for the API layer.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, Header, HTTPException, status

from app.capital.capital_manager import CapitalManager
from app.capital.config import CapitalConfig
from app.capital.cost_model import IndianMarketCostModel
from app.capital.risk_engine import RiskEngine
from app.core.config import settings
from app.db.audit import DecisionAuditTrailManager
from app.db.journal import DatabaseTradeJournal
from app.db.performance import PerformanceAggregator
from app.db.recovery import RestartRecoveryManager
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import ExecutionEngine
from app.gate.trade_gate import DeterministicTradeGate
from app.watcher.position_watcher import IndependentPositionWatcher

# =====================================================================
# System State Management
# =====================================================================


class SystemState:
    """In-memory operational status container."""

    def __init__(self) -> None:
        self.mode: str = "PAPER"
        self.is_halted: bool = False
        self.start_time: datetime = datetime.now(timezone.utc)
        self.live_trading_allowed: bool = False
        self.live_approval_secret: str = "PROD-LIVE-APPROVAL-KEY-9981"
        self.kill_switch_triggered_at: datetime | None = None
        self.kill_switch_reason: str | None = None

    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


_system_state = SystemState()

# Singletons for memory controllers during application run
_capital_manager: CapitalManager | None = None
_position_watcher: IndependentPositionWatcher | None = None
_execution_engine: ExecutionEngine | None = None
_trade_gate: DeterministicTradeGate | None = None


def get_db_path() -> str:
    """Return active database file path."""
    return settings.DATABASE_PATH


def get_db_repo(db_path: str = Depends(get_db_path)) -> DatabaseRepository:
    """Provide DatabaseRepository instance."""
    return DatabaseRepository(db_path=db_path)


def get_journal(db_path: str = Depends(get_db_path)) -> DatabaseTradeJournal:
    """Provide DatabaseTradeJournal instance."""
    return DatabaseTradeJournal(db_path=db_path)


def get_performance_aggregator(
    db_path: str = Depends(get_db_path),
) -> PerformanceAggregator:
    """Provide PerformanceAggregator instance."""
    return PerformanceAggregator(db_path=db_path)


def get_audit_manager(
    repo: DatabaseRepository = Depends(get_db_repo),
    db_path: str = Depends(get_db_path),
) -> DecisionAuditTrailManager:
    """Provide DecisionAuditTrailManager instance."""
    return DecisionAuditTrailManager(repository=repo, db_path=db_path)


def get_recovery_manager(
    repo: DatabaseRepository = Depends(get_db_repo),
    db_path: str = Depends(get_db_path),
) -> RestartRecoveryManager:
    """Provide RestartRecoveryManager instance."""
    return RestartRecoveryManager(repository=repo, db_path=db_path)


def get_system_state() -> SystemState:
    """Provide operational system state."""
    return _system_state


def get_capital_manager() -> CapitalManager:
    """Provide CapitalManager singleton."""
    global _capital_manager
    if _capital_manager is None:
        cfg = CapitalConfig(
            starting_capital=Decimal(str(settings.INITIAL_CAPITAL)),
            autonomous_threshold=Decimal(
                str(settings.AUTONOMOUS_CAPITAL_THRESHOLD)
            ),
        )
        _capital_manager = CapitalManager(config=cfg)
    return _capital_manager


def get_position_watcher() -> IndependentPositionWatcher:
    """Provide IndependentPositionWatcher singleton."""
    global _position_watcher
    if _position_watcher is None:
        _position_watcher = IndependentPositionWatcher()
    return _position_watcher


def get_execution_engine() -> ExecutionEngine:
    """Provide ExecutionEngine singleton."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def get_trade_gate(
    cap_mgr: CapitalManager = Depends(get_capital_manager),
    pos_watcher: IndependentPositionWatcher = Depends(get_position_watcher),
    exec_engine: ExecutionEngine = Depends(get_execution_engine),
) -> DeterministicTradeGate:
    """Provide DeterministicTradeGate instance."""
    global _trade_gate
    if _trade_gate is None:
        cost_model = IndianMarketCostModel()
        risk_engine = RiskEngine(
            capital_manager=cap_mgr,
            cost_model=cost_model,
        )
        _trade_gate = DeterministicTradeGate(
            risk_engine=risk_engine,
            execution_engine=exec_engine,
            position_watcher=pos_watcher,
        )
    return _trade_gate


# =====================================================================
# Live Trading & Mutation Approval Guard
# =====================================================================


def verify_live_trading_authorization(
    x_approval_token: str | None = Header(default=None, alias="X-Approval-Token"),
    system_state: SystemState = Depends(get_system_state),
) -> None:
    """Enforce strict multi-layer security guard on live-trading endpoints.

    Fails with 403 if:
    1. System is configured in paper-only mode.
    2. Approval token is missing or invalid.
    3. Safety lockout is active.
    """
    if settings.IS_PAPER_TRADING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live trading is strictly disabled by environment safety policy.",
        )

    if not system_state.live_trading_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live trading is not permitted by current system state.",
        )

    if not x_approval_token or x_approval_token != system_state.live_approval_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid live trading approval credentials.",
        )
