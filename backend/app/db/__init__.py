"""Database persistence, WAL transaction handling, trade journal, and performance package."""

from app.db.audit import DecisionAuditTrail, DecisionAuditTrailManager
from app.db.connection import (
    get_async_connection,
    get_connection,
    get_db_path,
    init_db,
)
from app.db.journal import DatabaseTradeJournal
from app.db.performance import (
    AggregatedPerformanceMetrics,
    PerformanceAggregator,
)
from app.db.recovery import RestartRecoveryManager, SystemRecoveryState
from app.db.repository import DatabaseRepository
from app.db.schema import DDL_STATEMENTS
from app.db.session import get_db_connection

__all__ = [
    "DDL_STATEMENTS",
    "AggregatedPerformanceMetrics",
    "DatabaseRepository",
    "DatabaseTradeJournal",
    "DecisionAuditTrail",
    "DecisionAuditTrailManager",
    "PerformanceAggregator",
    "RestartRecoveryManager",
    "SystemRecoveryState",
    "get_async_connection",
    "get_connection",
    "get_db_connection",
    "get_db_path",
    "init_db",
]
