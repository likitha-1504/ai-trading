# Production Operations Manual: AI Micro-Trading Agent

**Document Classification**: Operational Architecture & Systems Engineering  
**Version**: `1.0.0-phase23`  
**Host Architecture**: Local Laptop / Workstation (Windows 11 / Linux x86_64)  
**Target Availability**: 99.9% uptime during active market hours (09:15 - 15:30 IST)

---

## 1. System Topology & Architecture

The AI Micro-Trading Agent is engineered as a decoupled, local-first service architecture with strictly isolated execution and inference paths:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Local Host (Workstation)                        │
│                                                                        │
│  ┌──────────────────────┐             ┌─────────────────────────────┐  │
│  │ React Trading UI     │             │ Local Ollama Service        │  │
│  │ (Vite / Port 3000)   │             │ (Port 11434)                │  │
│  │ - 15 Dashboards      │             │ - Qwen3 Analyst (4-bit)     │  │
│  │ - Fact vs Speculation│             │ - DeepSeek-R1 (4-bit)       │  │
│  └──────────┬───────────┘             └──────────────┬──────────────┘  │
│             │ HTTP / WebSocket                       │ Async HTTP      │
│             ▼                                        ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Backend Controller (Uvicorn / Port 8000)                 │  │
│  │                                                                  │  │
│  │  ┌──────────────────────┐  Zero LLM  ┌────────────────────────┐  │  │
│  │  │ 7-Step Decision Gate │  Orders    │ Position Watcher       │  │  │
│  │  │ - Risk Budgeting     ├───────────►│ - Sub-50ms Synchronous │  │  │
│  │  │ - Friction Hurdles   │            │ - Hard Stop / Trailing │  │  │
│  │  │ - AI Disagreements   │            │ - 15:15 IST Cutoff     │  │  │
│  │  └──────────────────────┘            └────────────┬───────────┘  │  │
│  │                                                   │ Order Exit   │  │
│  │                                                   ▼              │  │
│  │  ┌──────────────────────┐            ┌────────────────────────┐  │  │
│  │  │ SQLite WAL Journal   │            │ Broker Adapter Layer   │  │  │
│  │  │ - 14 Core Tables     │            │ - Paper Adapter        │  │  │
│  │  │ - ACID Transactions  │            │ - Live Preflight Fence │  │  │
│  │  └──────────────────────┘            └────────────┬───────────┘  │  │
│  └───────────────────────────────────────────────────┼──────────────┘  │
└──────────────────────────────────────────────────────┼─────────────────┘
                                                       │ HTTPS (Mock / Live)
                                                       ▼
                                          ┌─────────────────────────────┐
                                          │ Indian Broker / Exchange    │
                                          │ (Zerodha Kite / NSE)        │
                                          └─────────────────────────────┘
```

---

## 2. Resource Budgets & Hardware Constraints

| Resource | Target Budget | Monitored Peak | Enforcement Mechanism |
| :--- | :---: | :---: | :--- |
| **CPU Utilization** | < 25% average | < 15% measured | Event-driven tick loops; non-busy polling; sub-30µs fast-path |
| **RAM Footprint (Backend)** | < 300 MB | ~140 MB | Python process garbage collection; Decimal preallocation |
| **RAM Footprint (Ollama)** | 6.0 GB – 10.0 GB | ~7.2 GB | Q4_K_M quantized weights; 4K context windows |
| **Disk Storage (Database)**| < 500 MB / year | ~50 MB initial | SQLite WAL mode; auto-checkpoint at 1,000 pages |
| **Watcher Latency Budget**| **Sub-50.0 ms** | **21.0 µs** | Pure CPU price comparison; zero background I/O or LLM calls |
| **Decision Preparation** | < 1.0 ms | 0.08 ms | Optimized single-pass technical feature engine |

---

## 3. Database Management & SQLite WAL Maintenance

### 3.1 SQLite WAL Configuration
The persistent storage engine operates in Write-Ahead Logging mode:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA auto_vacuum = INCREMENTAL;
```

### 3.2 WAL Checkpointing Protocol
- **Automatic Checkpointing**: SQLite automatically truncates the `-wal` file when it reaches 1,000 pages (~4 MB).
- **Manual Checkpoint**: To force a complete WAL checkpoint into the primary `.db` file:
  ```bash
  python -c "import sqlite3; conn = sqlite3.connect('trading_agent.db'); conn.execute('PRAGMA wal_checkpoint(TRUNCATE);'); conn.close(); print('WAL Checkpoint complete.')"
  ```
- **Weekly Compaction & VACUUM**:
  ```bash
  python -c "import sqlite3; conn = sqlite3.connect('trading_agent.db'); conn.execute('VACUUM;'); conn.close(); print('Database vacuum complete.')"
  ```

---

## 4. Telemetry, Logging & Secret Sanitization

### 4.1 Structured Log Event Pipeline
1. All operational transitions (orders, fills, risk events, health probes) write to SQLite table `system_events`.
2. Standard output streams structured format:
   `%(asctime)s [%(levelname)s] [%(name)s] %(message)s`
3. **Secret Sanitization Invariant**:
   Any log record containing broker passwords, API secret keys, or cryptographic approval tokens is automatically intercepted and masked:
   `KIT****81` or `PROD****9981`.

---

## 5. Security & Network Hardening

1. **Loopback Address Binding**:
   - Backend Uvicorn server binds to `127.0.0.1` (or local Docker network bridge), prohibiting external internet ingress.
2. **Strict HTTP Method Restrictions**:
   - Arbitrary order endpoints (`POST /orders`) are strictly forbidden and return `405 Method Not Allowed`.
   - Orders can only be originated through approved `TradePlan` contracts evaluated by the deterministic trade gate.
3. **Guarded Mutations**:
   - System mode switching (`POST /api/v1/system/mode`) and proposal promotion (`POST /api/v1/learning/proposals/{id}/promote`) require cryptographic token authentication.
4. **Adapter Safety Fences**:
   - Physical code fence in `LiveBrokerAdapter` rejects orders if `IS_PAPER_TRADING=True` or notional > ₹300.00.

---

## 6. Service Management (Systemd / Windows Startup)

### 6.1 Windows PowerShell Startup Script (`start_trading_agent.ps1`)
```powershell
# Set project directory
Set-Location "C:\Users\likit\Desktop\project"

# Activate Virtualenv
& ".\.venv\Scripts\Activate.ps1"

# Verify preflight audit
python backend\scripts\preflight_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Preflight hardening checks failed. Aborting startup."
    exit 1
}

# Start backend server
Start-Process python -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
Write-Host "AI Micro-Trading Agent running on http://127.0.0.1:8000"
```
