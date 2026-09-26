# Incident Response & Emergency Procedures

This guide provides immediate action protocols for operational anomalies, extreme market conditions, or system failures.

---

## 1. Emergency Kill-Switch

The system provides a multi-channel emergency kill switch:
1. **Frontend Dashboard**: Click the prominent red **EMERGENCY KILL SWITCH** button in the header. Enter confirmation in the double-confirmation modal.
2. **REST API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/system/kill-switch \
     -H "Content-Type: application/json" \
     -d '{"confirm": true, "reason": "Emergency halt triggered by operator", "token": "LOCAL_DEV_KILL_TOKEN_SAFE_2026"}'
   ```

### Effects of Triggering Kill-Switch:
- System state immediately transitions to `SYSTEM_HALTED`.
- The Candidate Ranker, Strategies, and AI Council stop processing new entries.
- Position Watcher immediately fires market exit orders for all currently open positions.
- All pending submissions are canceled.
- System requires operator restart with valid preflight audit to resume.

---

## 2. Broker Connection Interruption

**Symptoms**: UI shows red `BROKER_DISCONNECTED` badge; logs show WebSocket disconnects.
- **Action**:
  1. Check broker status page and local internet connectivity.
  2. The adapter will automatically attempt reconnection using exponential backoff (1s, 2s, 4s, 8s, 16s).
  3. If connection is unrecoverable for > 60 seconds with active positions, log into broker web portal directly on mobile/browser to inspect orders.
  4. Once reconnected, the system automatically calls `reconcile_positions()`.

---

## 3. Position Desynchronization (Database vs Broker Mismatch)

**Symptoms**: UI displays `DESYNC_DETECTED` alert.
- **Action**:
  1. Trigger immediate emergency pause (`POST /api/v1/system/pause`).
  2. Inspect discrepancy via:
     ```bash
     python -c "from app.ops.integrity_verifier import IntegrityVerifier; print(IntegrityVerifier().reconcile_broker_positions())"
     ```
  3. Never place manual offsetting trades through the API while desync is unresolved.
  4. Resolve discrepancy via broker web interface. Run database balance reconciliation script to align ledger.
