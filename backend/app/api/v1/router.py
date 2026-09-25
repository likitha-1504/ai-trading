"""API v1 master router aggregating all domain endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    autonomous,
    backtests,
    candidates,
    dashboard,
    live_experiment,
    logs,
    market,
    orders,
    performance,
    pnl,
    positions,
    risk,
    system,
    trade_plans,
    trades,
    learning,
)

api_router = APIRouter()

# 1. Health & System
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(live_experiment.router, prefix="/live/experiment", tags=["live-experiment"])
api_router.include_router(autonomous.router, prefix="/autonomous", tags=["autonomous"])


@api_router.get("/health", tags=["system"], summary="Basic liveness probe")
def health_check():
    """Liveness probe for backend engine."""
    return {"status": "ok", "service": "AI Micro-Trading Agent"}


# 2. Dashboard & Telemetry
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(dashboard.router, prefix="/telemetry", tags=["telemetry"])

# 3. Market Scanner & Features
api_router.include_router(market.router, prefix="/market", tags=["market"])

# 4. Candidates
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])

# 5. Positions
api_router.include_router(positions.router, prefix="/positions", tags=["positions"])

# 6. Orders (Read-only, no generic arbitrary creation)
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

# 7. Trades & Guarded Approvals
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])

# 8. Trade Plans
api_router.include_router(trade_plans.router, prefix="/trade-plans", tags=["trade-plans"])

# 9. P/L & Friction Breakdown
api_router.include_router(pnl.router, prefix="/pnl", tags=["pnl"])

# 10. AI Council Analysis & Latency
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])

# 11. Performance Metrics
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])

# 12. Backtests
api_router.include_router(backtests.router, prefix="/backtests", tags=["backtests"])

# 13. Risk Governance & Limits
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])

# 14. Logs & Audit Trail Reconstruction
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])

# 15. Learning & Continuous Improvement (Phase 22)
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])

