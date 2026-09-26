"""FastAPI endpoints for Phase 25 Production Operations and Observability."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_db_repo
from app.db.repository import DatabaseRepository
from app.ops.production_operations import (
    BrokerConnectivityStatus,
    DataFeedHealth,
    DatabaseHealth,
    LatencyErrorMetrics,
    ProductionOperationsMonitor,
    ProductionOperationsReport,
)

router = APIRouter()


def get_ops_monitor(repo: DatabaseRepository = Depends(get_db_repo)) -> ProductionOperationsMonitor:
    """Dependency provider for production operations monitor."""
    return ProductionOperationsMonitor.get_instance()


@router.get(
    "/report",
    response_model=ProductionOperationsReport,
    summary="Phase 25 Consolidated Production Operations Report",
    description="Returns unified telemetry across data feed, broker, database, latency SLAs, and backup status.",
)
def get_operations_report(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> ProductionOperationsReport:
    return ops_mon.generate_operations_report()


@router.get(
    "/data-feed",
    response_model=DataFeedHealth,
    summary="Phase 25 Data Feed Health & Tick Freshness",
    description="Reports tick freshness age, spread compliance, and stale feed status (>15s threshold).",
)
def get_data_feed_health(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> DataFeedHealth:
    return ops_mon.check_data_feed_health()


@router.get(
    "/broker-connectivity",
    response_model=BrokerConnectivityStatus,
    summary="Phase 25 Broker Connectivity Telemetry",
    description="Reports broker adapter status, heartbeat latency, and circuit breaker status.",
)
def get_broker_connectivity(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> BrokerConnectivityStatus:
    return ops_mon.check_broker_connectivity()


@router.get(
    "/database",
    response_model=DatabaseHealth,
    summary="Phase 25 Database Health & WAL Metrics",
    description="Reports SQLite WAL journal status, page counts, file sizes, write latency, and integrity status.",
)
def get_database_health(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> DatabaseHealth:
    return ops_mon.check_database_health()


@router.get(
    "/telemetry",
    response_model=LatencyErrorMetrics,
    summary="Phase 25 Latency Distribution & Error Rates",
    description="Reports Position Watcher sub-50ms SLA compliance, component latencies, and error telemetry.",
)
def get_latency_telemetry(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> LatencyErrorMetrics:
    return ops_mon.check_latency_and_errors()


@router.get(
    "/backups",
    summary="Phase 25 Hot Backup Freshness & Rotation",
    description="Reports backup archive count, latest backup age, and verification status.",
)
def get_backups_health(
    ops_mon: ProductionOperationsMonitor = Depends(get_ops_monitor),
) -> dict[str, Any]:
    return ops_mon.check_backup_health().model_dump()
