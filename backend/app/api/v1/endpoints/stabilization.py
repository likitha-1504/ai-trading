"""FastAPI endpoints for Phase 26 Live Trading Stabilization."""


from fastapi import APIRouter, Depends

from app.api.deps import get_db_repo
from app.db.repository import DatabaseRepository
from app.live.stabilization_engine import (
    CostVarianceAnalysis,
    ExecutionMetricComparison,
    LiveStabilizationEngine,
    PositionWatcherSurveillance,
    ReconciliationAudit,
    SlippageAnalysis,
    StabilizationSummary,
)

router = APIRouter()


def get_stabilization_engine(
    repo: DatabaseRepository = Depends(get_db_repo),
) -> LiveStabilizationEngine:
    """Dependency provider for live stabilization engine."""
    return LiveStabilizationEngine(db_path=repo.db_path)


@router.get(
    "/report",
    response_model=StabilizationSummary,
    summary="Phase 26 Consolidated Live Trading Stabilization Report",
    description="Returns empirical evidence across paper/live comparison, slippage, costs, rejections, reconciliation, and Watcher behavior.",
)
def get_stabilization_report(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> StabilizationSummary:
    return engine.generate_stabilization_report()


@router.get(
    "/comparison",
    response_model=ExecutionMetricComparison,
    summary="Paper vs Live Execution Comparison",
    description="Compares fill rates, average fill latencies, P95 latencies, and ACK response times.",
)
def get_execution_comparison(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> ExecutionMetricComparison:
    return engine.compare_execution_metrics()


@router.get(
    "/slippage",
    response_model=SlippageAnalysis,
    summary="Slippage Distribution & Deviations",
    description="Evaluates tick and basis point slippage distributions under live execution.",
)
def get_slippage_analysis(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> SlippageAnalysis:
    return engine.evaluate_slippage()


@router.get(
    "/cost-variance",
    response_model=CostVarianceAnalysis,
    summary="Statutory Cost Modeling vs Realized Fees",
    description="Compares modeled Indian regulatory fees against realized clearing ledger deductions.",
)
def get_cost_variance(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> CostVarianceAnalysis:
    return engine.evaluate_cost_variance()


@router.get(
    "/reconciliation",
    response_model=ReconciliationAudit,
    summary="Broker vs SQLite Ledger Parity",
    description="Verifies zero desynchronization between remote broker positions and local database ledger.",
)
def get_reconciliation_audit(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> ReconciliationAudit:
    return engine.audit_reconciliation()


@router.get(
    "/watcher-behavior",
    response_model=PositionWatcherSurveillance,
    summary="Position Watcher Live SLA & Trigger Audit",
    description="Surveillance metrics for sub-50ms SLA compliance, evaluation latencies, and exit trigger breakdown.",
)
def get_watcher_surveillance(
    engine: LiveStabilizationEngine = Depends(get_stabilization_engine),
) -> PositionWatcherSurveillance:
    return engine.audit_watcher_surveillance()
