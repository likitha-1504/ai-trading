# Incident Response & Emergency Procedures: AI Micro-Trading Agent

**Version**: `1.0.0-phase23`  
**Classification**: Emergency Procedures, Failure Vectors & Disaster Mitigation  
**Primary On-Call Operator**: Personal Trading System Operator  
**Escalation Window**: Immediate (< 30 seconds for SEV-1 events)

---

## 1. Severity Classification Matrix

| Severity Level | Definition | Impact | Response SLA | Action Protocol |
| :--- | :--- | :--- | :---: | :--- |
| **SEV-1 (CRITICAL)** | Broker disconnect during active position; runaway order attempt; stop-loss execution failure; database corruption | Unprotected market risk | **Immediate (< 30s)** | Trigger Emergency Kill-Switch; manual broker terminal square-off |
| **SEV-2 (HIGH)** | Stale market data (>15s); 3.0% daily drawdown circuit breaker trip; AI council unavailable; process crash | Strategy impaired; risk active | **< 2 minutes** | Position Watcher emergency exit; automated crash rehydration |
| **SEV-3 (MEDIUM)** | Backup creation failure; disk space warning (<1 GB); non-WAL SQLite journal mode | Telemetry degraded; no open risk | **< 15 minutes** | Run database maintenance; disk cleanup; verify WAL mode |
| **SEV-4 (LOW)** | Minor UI display flutter; telemetry latency spike (<250ms) | Cosmetic UI impact | **Next routine maintenance** | UI refresh; log inspection |

---

## 2. Emergency Incident Playbooks

### Playbook 1: Broker Disconnection During Active Trade (SEV-1)
**Trigger**: WebSocket connection drops or REST order dispatch returns network socket error while an open position exists.
1. **Automated Safety Action**:
   - The engine flags `broker_connected = False` and logs a CRITICAL system event.
   - Active position risk surveillance continues locally against the last known price.
2. **Immediate Operator Steps**:
   - Check internet connectivity on workstation.
   - Open official broker mobile app (e.g. Zerodha Kite / Groww) on mobile device (independent network).
   - Verify open position status directly on broker portal.
   - If position is open and market is moving adversely, execute manual square-off via broker mobile app.
3. **Recovery**:
   - Restart backend server: `python -m uvicorn app.main:app --app-dir backend --port 8000`.
   - The `RestartRecoveryManager` will rehydrate state and reconcile with broker.

---

### Playbook 2: Stale Market Data Timeout (> 15 Seconds) (SEV-2)
**Trigger**: Feed latency exceeds 15.0 seconds without a fresh price tick for an active position.
1. **Automated Action**:
   - `IndependentPositionWatcher` detects tick timestamp staleness.
   - Triggers `STALE_DATA_EMERGENCY` exit trigger.
   - Immediately cancels pending limit orders and submits market liquidation order.
   - Sets system state halt flag to prevent new setup evaluations.
2. **Operator Steps**:
   - Verify market feed status on exchange or secondary news source.
   - Confirm position closed in SQLite audit log:
     ```sql
     SELECT * FROM positions WHERE exit_reason LIKE '%STALE%' ORDER BY created_at DESC LIMIT 1;
     ```

---

### Playbook 3: 3.0% Daily Drawdown Circuit Breaker Trip (SEV-2)
**Trigger**: Realized intraday loss plus unrealized loss exceeds 3.0% of capital ceiling (₹9.00 cumulative loss on ₹300 capital limit).
1. **Automated Action**:
   - `CapitalManager` trips circuit breaker flag `is_circuit_breaker_tripped = True`.
   - All subsequent candidate setups evaluate to `ApprovalMode.REJECTED`.
   - Existing open positions are strictly managed by `PositionWatcher` until natural stop or target exit.
2. **Operator Protocol**:
   - **DO NOT reset circuit breaker on the same trading day.**
   - Review trades in Screen 8 (Trade Journal) to analyze loss causes.
   - Allow market session to close normally; resume next trading day at 09:15 IST.

---

### Playbook 4: Sudden Process Crash & Cold Laptop Restart (SEV-2)
**Trigger**: Host machine power loss, operating system crash, or unhandled Python termination.
1. **Automated Action**:
   - Uncommitted data is safely preserved by SQLite Write-Ahead Logging (WAL).
2. **Operator Steps**:
   - Reboot machine and start Ollama service: `ollama run qwen3:latest` (or verify service).
   - Launch backend server: `python -m uvicorn app.main:app --app-dir backend --port 8000`.
   - `RestartRecoveryManager` executes automatically during startup sequence:
     ```
     [INFO] RestartRecoveryManager: Rehydrating state from trading_agent.db...
     [INFO] Restored 1 active position into IndependentPositionWatcher.
     [INFO] Restored CapitalManager: Equity ₹298.50, High-Water Mark ₹300.00.
     [INFO] State parity verified: 0 unreconciled orders.
     ```
   - Verify Screen 5 (Position Monitor) displays rehydrated position with active stop-loss.

---

## 3. Post-Mortem Incident Report Template

For any SEV-1 or SEV-2 incident, complete the following retrospective log:

```markdown
# Incident Post-Mortem: [INCIDENT-ID]

**Incident Date/Time**: 2026-XX-XX HH:MM:SS IST
**Severity**: SEV-1 / SEV-2
**Components Affected**: Position Watcher / Broker Adapter / Database / Ollama
**Financial Impact**: Net P/L Impact (₹X.XX)
**Incident Duration**: XX minutes

### 1. Incident Timeline
- **HH:MM:SS IST**: Anomaly first observed.
- **HH:MM:SS IST**: Automated safety trigger executed.
- **HH:MM:SS IST**: Operator intervention initiated.
- **HH:MM:SS IST**: System restored to normal operational state.

### 2. Root Cause Analysis (5 Whys)
1. Why did the issue occur?
2. Why was it not intercepted earlier?
3. Why did the recovery take XX minutes?

### 3. Preventative Actions & Code Adjustments
- [ ] Task 1: Code enhancement / fence addition
- [ ] Task 2: Automated test fixture added in test_phase16_failure_injection.py
```
