# Backup & Disaster Recovery Guide

This guide details the backup management, cryptographic verification, and disaster recovery processes implemented in `backend/app/ops/backup_manager.py`.

---

## 1. Hot Backup Architecture

The SQLite Write-Ahead Log (WAL) architecture allows live online hot backups without locking read/write transactions:
- **API**: Uses the official SQLite Online Backup API (`sqlite3_backup`).
- **Cryptographic Verification**: Every generated `.db` backup file is hashed via SHA-256. The hash, byte count, timestamp, and schema verification are recorded in an audit manifest.
- **Atomic Swap**: Backups are written to a temporary filename and atomically renamed once verified.
- **Rotation**: Automatically retains the latest 10 backup archives in `backups/` and purges older archives.

---

## 2. CLI Backup & Restore Operations

### Trigger an Immediate Hot Backup
```bash
python backend/scripts/backup.py --reason manual_pre_deployment
```
Output:
```
Backup successful: BKP-20260926_120000-manual_pre_deployment.db
Size: 196608 bytes | SHA-256: e3b0c44298fc1c149afbf4c8996fb924...
```

### List Verified Backups
```bash
python -c "from app.ops.backup_manager import BackupManager; print(BackupManager().list_backups())"
```

### Restore Database from a Specific Backup
```bash
# 1. Stop backend service
# 2. Execute restore tool
python backend/scripts/restore.py --backup-id BKP-20260926_120000-manual_pre_deployment.db

# 3. Verify integrity of restored database
python -c "from app.ops.integrity_verifier import IntegrityVerifier; print(IntegrityVerifier().run_full_integrity_check())"
```

---

## 3. Disaster Recovery Scenarios

| Failure Event | Recovery Procedure |
| :--- | :--- |
| **Corrupted SQLite DB** | 1. Stop API. 2. Quarantine corrupted `trading_agent.db`. 3. Run `backend/scripts/restore.py` pointing to latest valid backup. 4. Verify financial parity. 5. Restart API. |
| **Hardware Crash** | 1. Deploy code to backup hardware. 2. Restore latest verified backup from off-site storage. 3. Reconcile open positions with broker. 4. Run preflight audit. |
| **Accidental State Mutation** | 1. Identify point-in-time backup prior to mutation. 2. Restore backup into staging environment. 3. Export specific tables/records or perform full restore if market is closed. |
