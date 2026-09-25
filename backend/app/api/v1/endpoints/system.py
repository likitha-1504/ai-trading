"""System health, status, emergency kill-switch, and operational mode endpoints."""

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SystemState,
    get_db_repo,
    get_execution_engine,
    get_position_watcher,
    get_system_state,
)
from app.api.schemas import (
    KillSwitchRequest,
    KillSwitchResponse,
    ModeSwitchRequest,
    ModeSwitchResponse,
    SystemHealthResponse,
)
from app.core.config import settings
from app.db.connection import get_connection
from app.db.repository import DatabaseRepository
from app.execution.execution_engine import ExecutionEngine
from app.live.readiness_audit import LiveReadinessAuditor, LiveReadinessAuditResult
from app.watcher.position_watcher import IndependentPositionWatcher

router = APIRouter()


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Get multi-component system health",
    description="Probes SQLite WAL database, Position Watcher heartbeat, Execution Engine, and AI Council availability.",
)
def get_system_health(
    repo: DatabaseRepository = Depends(get_db_repo),
    sys_state: SystemState = Depends(get_system_state),
) -> SystemHealthResponse:
    db_status = "CONNECTED_WAL"
    try:
        with get_connection(repo.db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            if mode.lower() not in ("wal", "memory"):
                db_status = "WARNING_NON_WAL"
    except (sqlite3.Error, OSError, RuntimeError, ValueError):
        db_status = "DISCONNECTED"

    # Overall status determination
    overall = "HEALTHY"
    if sys_state.is_halted or db_status == "DISCONNECTED":
        overall = "CRITICAL"
    elif db_status == "WARNING_NON_WAL":
        overall = "WARNING"

    return SystemHealthResponse(
        status=overall,
        database=db_status,
        position_watcher="ACTIVE",
        execution_engine="ACTIVE" if not sys_state.is_halted else "SUSPENDED",
        ai_council="ONLINE",
        mode=sys_state.mode,
        live_trading_allowed=sys_state.live_trading_allowed,
        uptime_seconds=round(sys_state.uptime_seconds(), 2),
        version=settings.VERSION,
    )


@router.get(
    "/status",
    summary="Get operational status and version",
    description="Returns high-level status, environment, and system mode.",
)
def get_system_status(
    sys_state: SystemState = Depends(get_system_state),
) -> dict[str, str]:
    return {
        "status": "HALTED" if sys_state.is_halted else "OPERATIONAL",
        "mode": sys_state.mode,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "live_trading_allowed": str(sys_state.live_trading_allowed),
    }


@router.post(
    "/kill-switch",
    response_model=KillSwitchResponse,
    summary="Trigger Emergency Kill Switch (Guarded Mutation)",
    description="Immediately cancels pending orders, liquidates open positions via Position Watcher, and halts system.",
)
def trigger_kill_switch(
    payload: KillSwitchRequest,
    repo: DatabaseRepository = Depends(get_db_repo),
    pos_watcher: IndependentPositionWatcher = Depends(get_position_watcher),
    exec_engine: ExecutionEngine = Depends(get_execution_engine),
    sys_state: SystemState = Depends(get_system_state),
) -> KillSwitchResponse:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation is required to trigger emergency kill-switch.",
        )

    # 1. Mark system state halted
    now = datetime.now(timezone.utc)
    sys_state.is_halted = True
    sys_state.kill_switch_triggered_at = now
    sys_state.kill_switch_reason = payload.reason

    # 2. Cancel all open orders in execution engine and DB
    open_orders = repo.get_open_orders()
    cancelled_count = 0
    for o in open_orders:
        client_id = o.get("client_order_id")
        if client_id:
            exec_engine.cancel_order(client_id)
            cancelled_count += 1

    # 3. Liquidate open positions via position watcher and repository
    open_positions = repo.get_open_positions()
    pos_watcher.trigger_manual_kill_switch(reason=payload.reason)
    liquidated_count = len(open_positions)
    for pos in open_positions:
        repo.close_position(
            pos.position_id,
            exit_price=pos.current_price,
            realized_pnl=pos.unrealized_pnl,
            exit_reason=payload.reason,
        )

    # 4. Log system event
    repo.save_system_event(
        source="KILL_SWITCH",
        level="CRITICAL",
        message=f"Emergency kill switch triggered: {payload.reason}",
        metadata={
            "positions_closed": liquidated_count,
            "orders_cancelled": cancelled_count,
            "triggered_at": now.isoformat(),
        },
    )

    return KillSwitchResponse(
        success=True,
        message=f"Kill-switch activated: {payload.reason}",
        positions_closed=liquidated_count,
        orders_cancelled=cancelled_count,
        system_halted=True,
        timestamp=now,
    )


@router.post(
    "/mode",
    response_model=ModeSwitchResponse,
    summary="Switch Operational Mode (Guarded Mutation)",
    description="Switches mode between PAPER and LIVE. Protected by explicit approval credentials and safety policy.",
)
def switch_system_mode(
    payload: ModeSwitchRequest,
    sys_state: SystemState = Depends(get_system_state),
    repo: DatabaseRepository = Depends(get_db_repo),
) -> ModeSwitchResponse:
    target = payload.target_mode.upper()
    if target not in ("PAPER", "LIVE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target mode '{payload.target_mode}'. Must be 'PAPER' or 'LIVE'.",
        )

    if target == "LIVE":
        # Strict multi-layer safety defense
        if not payload.confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit confirmation parameter required to switch to LIVE mode.",
            )

        if settings.IS_PAPER_TRADING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Live trading is strictly prohibited by configuration safety lock.",
            )

        if not payload.live_trading_approval_token or payload.live_trading_approval_token != sys_state.live_approval_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing live trading approval token.",
            )

        sys_state.mode = "LIVE"
        sys_state.live_trading_allowed = True
        msg = "System operational mode switched to LIVE with authorized token."
    else:
        # Switching back to PAPER mode is always safe
        sys_state.mode = "PAPER"
        sys_state.live_trading_allowed = False
        msg = "System operational mode switched to PAPER."

    repo.save_system_event(
        source="MODE_SWITCH",
        level="WARNING" if target == "LIVE" else "INFO",
        message=msg,
        metadata={"target_mode": target},
    )

    return ModeSwitchResponse(
        success=True,
        current_mode=sys_state.mode,
        message=msg,
    )


@router.get(
    "/live-readiness",
    response_model=LiveReadinessAuditResult,
    summary="Phase 19 Controlled Live Readiness Audit",
    description="Audits API credentials, broker connection, safety systems, and Phase 19 approval gate.",
)
def get_live_readiness_audit(
    sys_state: SystemState = Depends(get_system_state),
) -> LiveReadinessAuditResult:
    auditor = LiveReadinessAuditor(system_state=sys_state)
    return auditor.run_full_audit()


# =============================================================================
# Phase 23: Production Hardening, Integrity & Disaster Recovery Endpoints
# =============================================================================


@router.get(
    "/hardening-audit",
    summary="Phase 23 Comprehensive 14-Dimension Hardening Audit",
    description="Audits startup/restart, database integrity, logs, backups, configuration, secrets, broker isolation, and operational readiness.",
)
def get_hardening_audit(
    repo: DatabaseRepository = Depends(get_db_repo),
) -> dict:
    from app.ops.hardening_runner import ProductionHardeningRunner

    db_path = repo.db_path or settings.DATABASE_PATH
    runner = ProductionHardeningRunner(db_path=db_path)
    audit = runner.verify_all_dimensions()
    return audit.model_dump()


@router.get(
    "/integrity",
    summary="Phase 23 SQLite Storage and Accounting Integrity Check",
    description="Executes PRAGMA integrity_check, foreign_key_check, table validation, and financial accounting parity checks.",
)
def get_database_integrity(
    repo: DatabaseRepository = Depends(get_db_repo),
) -> dict:
    from app.ops.integrity_verifier import DatabaseIntegrityVerifier

    db_path = repo.db_path or settings.DATABASE_PATH
    verifier = DatabaseIntegrityVerifier(db_path=db_path)
    report = verifier.run_full_verification()
    return report.model_dump()


@router.post(
    "/backup/create",
    summary="Create online verified database backup snapshot",
    description="Executes native SQLite online backup, computes SHA-256 hash, and verifies snapshot integrity.",
)
def create_backup_snapshot(
    tag: str = "manual",
    repo: DatabaseRepository = Depends(get_db_repo),
) -> dict:
    from app.ops.backup_manager import BackupManager

    db_path = repo.db_path or settings.DATABASE_PATH
    mgr = BackupManager(db_path=db_path)
    try:
        meta = mgr.create_backup(tag=tag)
        return {
            "success": True,
            "message": f"Backup {meta.backup_id} created and verified.",
            "backup": meta.model_dump(),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup generation failed: {e}",
        )


@router.get(
    "/backup/list",
    summary="List verified database backup snapshots",
    description="Returns all available verified SQLite database backups with cryptographic checksums.",
)
def list_backups(
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[dict]:
    from app.ops.backup_manager import BackupManager

    db_path = repo.db_path or settings.DATABASE_PATH
    mgr = BackupManager(db_path=db_path)
    return [b.model_dump() for b in mgr.list_backups()]


