# Production Operational Runbook: AI Micro-Trading Agent

**Version**: `1.0.0-phase23`  
**System Classification**: Tier-1 Local-First Personal Trading System  
**Primary Execution Markets**: National Stock Exchange of India (NSE Cash Intraday)  
**Primary Trading Currency**: Indian Rupee (INR / ₹)  
**Safety Ceilings**: ₹100.00 Base Capital | ₹300.00 Autonomous Execution Threshold  
**Operational Timezone**: Indian Standard Time (IST, UTC+05:30)

---

## 1. System Overview & Core Operating Invariants

The AI Micro-Trading Agent is a local-first, low-capital autonomous trading agent designed for personal use. It enforces deterministic safety invariants at the code and adapter boundaries:

1. **Independent Position Watcher Supremacy**: Continuous synchronous price surveillance operates strictly sub-50ms with zero dependency on Ollama or LLM reasoning.
2. **Environment Separation**: `IS_PAPER_TRADING=True` safety lock prevents real broker orders from dispatching unless explicitly unlocked by cryptographic human authorization.
3. **Capital Ceilings**: Strict ₹100.00 base capital cap; autonomous order sizing strictly capped at ₹300.00 notional. Any allocation > ₹300.00 requires explicit operator token approval.
4. **Intraday Square-Off**: Hard 15:15:00 IST time cutoff liquidates all intraday positions to avoid broker penalty charges (auto-square-off fees + GST).
5. **Circuit Breakers**: 3.0% maximum daily drawdown limit immediately halts the trading pipeline and rejects all incoming candidate orders.

---

## 2. Daily Trading Routine & Operational Timeline (IST)

```
08:30 IST ───────── 08:45 IST ───────── 09:15 IST ───────── 15:15 IST ───────── 15:30 IST ───────── 16:00 IST
Host Boot         Pre-Flight Audit     Market Opens       Intraday Cutoff   Market Closes      Post-Market Run
& Ollama Init     & Backup Verified    Trading Active     100% Squaring-off Reconciliation     WAL Backup Archive
```

### 2.1 Pre-Market Protocol (08:30 – 09:00 IST)

1. **Host & Ollama Standby Verification**:
   - Ensure local Ollama inference service is operational:
     ```bash
     ollama list
     # Verify presence of qwen3:latest and deepseek-r1:latest
     curl http://localhost:11434/api/tags
     ```
2. **Database Integrity Pre-Check**:
   - Run SQLite integrity check using CLI:
     ```bash
     python backend/scripts/preflight_check.py
     ```
3. **Automated Pre-Market Snapshot Backup**:
   - Create a clean backup before market open:
     ```bash
     python backend/scripts/backup.py --tag pre_market
     ```
4. **Backend & Frontend Service Startup**:
   - Start the FastAPI backend server:
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
     ```
   - Start the React Trading Terminal (or run production preview):
     ```bash
     cd frontend && npm run preview -- --port 3000
     ```
5. **Verify Telemetry Endpoints**:
   - Open browser at `http://localhost:3000` (or `http://localhost:8000/api/docs`).
   - Check `GET /api/v1/system/health`: Verify `database: CONNECTED_WAL`, `position_watcher: ACTIVE`, `ai_council: ONLINE`.

---

### 2.2 Market Hours Surveillance (09:15 – 15:15 IST)

1. **Dashboard Monitoring**:
   - Observe **Screen 1 (Command Center)** and **Screen 5 (Position Monitor)**.
   - Verify tick ingestion rate (~50-100 ticks/sec during active sessions).
   - Ensure Watcher evaluation latency remains below 50ms (typical: 20-30 µs).
2. **Reviewing Candidate Setups & AI Council Debates**:
   - Strategy candidates appear in **Screen 3 (Candidate Feed)**.
   - Dual-model theses appear in **Screen 7 (AI Analysis)**: Qwen3 Bullish Thesis vs. DeepSeek-R1 Adversarial Critique.
   - Decisions are arbitrated deterministically by the 7-Step Trade Gate.
3. **Manual Approval Requests (Trades > ₹300)**:
   - If an allocation setup exceeds ₹300.00 notional, it enters `ApprovalMode.MANUAL_PENDING`.
   - The operator can inspect the plan and approve via `POST /api/v1/autonomous/approve-manual-trade` with authorization token.

---

### 2.3 Intraday Cutoff & Post-Market Protocol (15:15 – 16:00 IST)

1. **Automated 15:15 IST Square-Off**:
   - The Independent Position Watcher automatically triggers `TIME_EXPIRY` market exit orders for any active position at 15:15:00 IST.
   - Verify all positions transition to `CLOSED` in Screen 5.
2. **Trade Journal & P/L Reconciliation (15:30 IST)**:
   - Check **Screen 8 (Trade Journal)** and **Screen 9 (Performance Analytics)**.
   - Verify Gross P/L, exact statutory friction breakdown (STT, exchange fees, SEBI, stamp duty, GST), and Net P/L.
3. **Post-Market Automated Backup Archive (16:00 IST)**:
   ```bash
   python backend/scripts/backup.py --tag post_market
   ```

---

## 3. Cold Start & Warm Restart Procedures

### 3.1 Clean Cold Start
```bash
# 1. Activate Python virtual environment
.venv\Scripts\activate

# 2. Run preflight verification
python backend/scripts/preflight_check.py

# 3. Launch application
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

### 3.2 Mid-Session Crash Warm Restart (State Rehydration)
If the backend process terminates unexpectedly during market hours:
1. Re-launch the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. The `RestartRecoveryManager` immediately activates on startup:
   - Replays uncommitted SQLite WAL journal transactions.
   - Rehydrates active positions and stop-loss price triggers into `IndependentPositionWatcher`.
   - Re-establishes capital high-water mark and daily drawdown gauges in `CapitalManager`.
   - Re-checks order statuses with broker adapter.

---

## 4. Emergency Kill-Switch Activation

When market anomalies, exchange feed halts, or system errors occur:

### 4.1 UI Kill-Switch (Recommended)
1. Click the persistent **Red Kill-Switch Button** in the UI TopBar.
2. Type `HALT` in the double-confirmation modal.
3. Confirm: All pending orders are cancelled, open positions liquidated at market, and system state is set to `is_halted = True`.

### 4.2 API Emergency Override
```bash
curl -X POST http://localhost:8000/api/v1/system/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "reason": "Operator manual emergency shutdown"}'
```

---

## 5. Maintenance & Diagnostics Commands

| Task | Command | Frequency |
| :--- | :--- | :--- |
| **Integrity Audit** | `python backend/scripts/preflight_check.py` | Daily (Pre-Market) |
| **Create Snapshot** | `python backend/scripts/backup.py --tag daily` | Daily (Post-Market) |
| **List Backups** | `curl http://localhost:8000/api/v1/system/backup/list` | Weekly |
| **Restore Database** | `python backend/scripts/restore.py <backup_file> --confirm` | Disaster Recovery |
| **Run Regression** | `pytest` | Before Deployments |
| **Type Check** | `mypy backend/app backend/tests` | Before Deployments |
| **Code Lint** | `ruff check backend` | Before Deployments |
