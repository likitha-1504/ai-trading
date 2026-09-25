# Disaster Recovery & Automated Backup Manual: AI Micro-Trading Agent

**Version**: `1.0.0-phase23`  
**Classification**: Storage Reliability, Business Continuity & Data Protection  
**Target RPO (Recovery Point Objective)**: **< 1.0 second** (Guaranteed by SQLite WAL ACID journal)  
**Target RTO (Recovery Time Objective)**: **< 60.0 seconds** (Automated snapshot restore & state rehydration)

---

## 1. Backup Strategy & Architecture

The AI Micro-Trading Agent leverages SQLite's native C-level Online Backup API (`sqlite3_backup_*`), encapsulated in [`BackupManager`](file:///C:/Users/likit/Desktop/project/backend/app/ops/backup_manager.py):

```
┌─────────────────────────────────────────────────────────────┐
│                 Live Operational Database                   │
│   trading_agent.db (Primary) + trading_agent.db-wal (WAL)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ SQLite Native Backup API
                               │ (Zero table locks, non-blocking)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Verified Backup Snapshot in backups/            │
│   trading_agent_backup_YYYYMMDD_HHMMSS_<tag>.db             │
├─────────────────────────────────────────────────────────────┤
│ 1. Cryptographic SHA-256 Checksum Calculation               │
│ 2. Automated PRAGMA integrity_check validation              │
│ 3. Automated PRAGMA foreign_key_check validation            │
│ 4. Sidecar JSON Metadata (.db.json) Generation              │
│ 5. Automated Retention Policy Rotation (Retain Last 14)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Automated Backup Schedules & Retention Policy

### 2.1 Standard Backup Schedules
| Snapshot Trigger | Tag | Execution Time | Purpose |
| :--- | :--- | :--- | :--- |
| **Pre-Market Snapshot** | `pre_market` | 08:45 IST Daily | Clean baseline state before opening bell |
| **Post-Market Snapshot** | `post_market`| 16:00 IST Daily | Preserves finalized day's P/L, trade journal, and telemetry |
| **Pre-Deployment Tag** | `pre_deploy` | Ad-hoc | Prior to schema migrations, code updates, or strategy upgrades |
| **Disaster Recovery Pre-Snapshot** | `pre_restore` | Automated | Taken immediately before any restore operation begins |

### 2.2 Retention & Rotation Policy
- **Maximum Retention**: 14 snapshots.
- **Rotation Engine**: When snapshot count exceeds 14, [`_rotate_backups()`](file:///C:/Users/likit/Desktop/project/backend/app/ops/backup_manager.py) automatically prunes the oldest database file and its `.json` sidecar.

---

## 3. Step-by-Step Disaster Recovery Runbook

### Scenario: Database Corruption or Host Hardware Failure

#### Step 1: Assess Database Status
Run the automated integrity verifier to confirm failure state:
```bash
python backend/scripts/preflight_check.py
```
If output displays `[FAIL   ] Dim 02: Database Integrity & WAL Mode`, proceed immediately with restoration.

#### Step 2: Select and Inspect Latest Verified Backup
List available backups sorted by date:
```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from app.ops.backup_manager import BackupManager
mgr = BackupManager()
for b in mgr.list_backups()[:5]:
    print(f'{b.backup_id} | {b.created_at} | Size: {b.size_bytes}B | SHA: {b.sha256_hash[:12]}... | Status: {b.integrity_status}')
"
```

#### Step 3: Execute Restoration Safety Workflow
Execute the restore CLI with the `--confirm` flag:
```bash
python backend/scripts/restore.py backups/trading_agent_backup_YYYYMMDD_HHMMSS_post_market.db --confirm
```
*Note: The restore script automatically creates a `.pre_restore` backup of the damaged database before applying changes.*

#### Step 4: Validate Restored Database
Run the integrity verifier to verify clean state:
```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from app.ops.integrity_verifier import DatabaseIntegrityVerifier
rep = DatabaseIntegrityVerifier().run_full_verification()
print('Restored DB Status:', 'HEALTHY' if rep.is_healthy else 'FAILED')
print('Integrity check:', rep.integrity_check_output)
print('Tables count:', len(rep.tables))
print('Accounting Reconciled:', rep.accounting_reconciled)
"
```

#### Step 5: Restart Trading Agent & Verify State Rehydration
Launch the server and inspect logs to confirm state recovery:
```bash
cd backend && uvicorn app.main:app --port 8000
```
Verify `GET http://localhost:8000/api/v1/system/health` reports:
`"database": "CONNECTED_WAL"`, `"status": "HEALTHY"`.

---

## 4. Offsite & Secondary Backup Recommendations

For personal long-term peace of mind:
1. **Encrypted Archive Export**:
   Copy the `backups/` directory weekly to an encrypted USB drive or secondary cloud folder.
2. **Exclusion from Git**:
   `.gitignore` strictly isolates all `*.db`, `*.db-wal`, `*.db-shm`, and `backups/` directories to prevent sensitive financial logs from leaking into version control.
