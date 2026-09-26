---
name: deployment-review
description: Environment variables, dependencies, persistence, health checks, and free-tier constraints.
---

# Deployment Review Skill

This skill governs deployment readiness reviews, environment validation, and infrastructure safety checks for `ai-agent-trading`.

---

## 1. Free-Tier Cloud Constraints & Safety Interlock

> [!CAUTION]
> **CRITICAL WARNING**: Safety-critical live trading must NEVER run on sleeping, throttled, or ephemeral free cloud services (Render free tier, Fly free tier, burstable shared micro-VMs).
>
> If a provider suspends container execution during 15 minutes of inactivity or throttles CPU credits during market spikes:
> - The Position Watcher's sub-50ms SLA fails.
> - Outbound stop loss orders are delayed or never transmitted.
> - Ephemeral filesystems wipe the local SQLite WAL ledger on restart.

---

## 2. Infrastructure Verification Dimensions

1. **Environment Variables**:
   - Verify `.env` is populated from `.env.example`.
   - Verify `IS_PAPER_TRADING=True` unless live experiment has received formal human authorization.
   - Verify operator security tokens (`OPERATOR_APPROVAL_KEY`, `KILL_SWITCH_TOKEN`) are configured.
2. **Dependency Pinning**:
   - Ensure all production dependencies are locked in `backend/requirements-pinned.txt`.
3. **Database Persistence & Hot Backups**:
   - Ensure `DATABASE_PATH` points to a persistent NVMe/SSD volume.
   - Verify SQLite WAL mode is enabled (`PRAGMA journal_mode=WAL`).
   - Verify automated hot backups run periodically via `backend/app/ops/backup_manager.py`.
4. **Health Probes**:
   - Query `/api/v1/system/health` to confirm all 6 internal subsystems report `HEALTHY`.
