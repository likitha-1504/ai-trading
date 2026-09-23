# Failure Handling & Fault Tolerance Guide

This document specifies the autonomous defensive behaviors and manual recovery protocols for critical failure modes.

---

## 1. System Resilience Matrix

| Failure Mode | Detection Mechanism | Autonomous Mitigation | Recovery Action |
| :--- | :--- | :--- | :--- |
| **Market Data Disconnect** | Heartbeat missed for $> 5\text{s}$ | Flag quotes stale; block all new entries; start exponential backoff reconnect. | Log warning; resume scanning on reconnect. |
| **Broker API Disconnect** | REST timeout or WebSocket drop | Queue active requests; Position Watcher enters emergency offline monitoring. | Re-authenticate, query open positions, reconcile balances. |
| **Stale Data (>15s)** | Monotonic clock vs quote timestamp | Prevent new orders; trigger safe exit evaluation if holding exposed positions. | Notify operator; verify feed integrity. |
| **Ollama / LLM Timeout** | HTTP timeout on model inference ($> 4\text{s}$) | Fall back immediately to purely quantitative criteria; do not stall execution. | Mark candidate as `AI_SKIPPED`; continue pipeline. |
| **Malformed AI JSON** | Pydantic validation failure | Discard LLM recommendation; treat as unconfirmed; block autonomous entry. | Log raw payload for offline prompt fine-tuning. |
| **Partial Order Fill** | Broker reports partial quantity | Update position with filled quantity; adjust remaining order or cancel remainder. | Re-evaluate risk with partial sizing. |
| **Rejected Order** | Broker returns rejection code | Log error; flag instrument; prevent re-submission for configured cooldown period. | Operator review of margin or regulatory reasons. |
| **Duplicate Order Attempt** | Idempotency key collision check | Engine drops duplicate request before network submission. | Log warning with client order ID. |
| **Database Lock / Error** | SQLite `BUSY` / `LOCKED` exception | Auto-retry with jitter using WAL busy-timeout ($5000\text{ms}$). | If unresolved, dump transaction log to emergency crash file. |
| **Process Crash / Restart** | Process restart / OS boot | On startup, run state reconciliation with broker before trading starts. | Restore position records, sync orders, resume watcher. |

---

## 2. Emergency Kill-Switch Protocol

If an unrecoverable state or runaway loss occurs:
1. Operator triggers `POST /system/kill-switch` or CLI emergency stop.
2. System immediately cancels all pending unfilled orders.
3. Position Watcher submits market exit orders for all open positions.
4. Engine sets trading mode to `SUSPENDED` and disengages autonomous triggers.
