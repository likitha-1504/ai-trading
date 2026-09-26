---
name: trading-safety-review
description: Review trading safety, deterministic risk ownership, emergency exits, broker reconciliation, and no-LLM safety-critical dependencies.
---

# Trading Safety Review Skill

This skill provides comprehensive verification and review procedures for trading-critical operations in `ai-agent-trading`. Antigravity uses this skill to inspect proposed code changes, runtime telemetry, and broker interactions before permitting execution.

---

## 1. Deterministic Risk Ownership
- **Mandate**: All financial risk parameters are strictly owned and verified by deterministic Python functions in `backend/app/gate/trade_gate.py` and `backend/app/watcher/position_watcher.py`.
- **Hard Caps**:
  - Max risk per trade: <= 1.5% of total capital.
  - Max daily drawdown: <= 3.0% of high-water mark.
  - Max simultaneous open positions: 1 (under micro-capital limits).
  - Intraday entry cutoff: 15:00 IST.
  - Mandatory square-off: 15:15 IST.
- **Verification Rule**: Any pull request or modification touching risk thresholds, position sizing, or stop loss mechanics requires explicit user approval and a recorded Architecture Decision Record (ADR).

---

## 2. No-LLM Safety-Critical Dependencies
- **Mandate**: No Large Language Model (Qwen3, DeepSeek-R1, or external APIs) may participate in:
  - Exit order generation or stop-loss adjustments.
  - Real-time tick evaluation.
  - Risk gate approvals or limit overrides.
- **Architectural Boundary**: The AI Council operates strictly in an **advisory pre-trade capacity**. If Ollama or the models fail, timeout, or return invalid JSON, the Trade Gate defaults to rejecting the trade (`REJECT_TRADE`).

---

## 3. Position Watcher & Emergency Exits (Sub-50ms SLA)
- **Mandate**: The Position Watcher must run on an isolated execution thread with a strict sub-50ms SLA.
- **Exit Priority Sequence**:
  1. System Halt / Emergency Kill Switch (immediate market liquidation).
  2. Stale Feed Timeout (> 15 seconds without ticks -> market exit).
  3. Hard Stop Loss hit (LTP <= stop price).
  4. Trailing Stop hit (lock in profits with 1.0x ATR trail after +1.5x risk achieved).
  5. Profit Target hit (2.0x to 2.5x initial risk).
  6. 15:15 IST Mandatory Square-Off.
- **Verification Checklist**:
  ```bash
  pytest backend/tests/test_position_watcher.py
  pytest backend/tests/test_performance_latency.py
  ```

---

## 4. Broker Abstraction & State Reconciliation
- **Mandate**: On startup and reconnection, the system must reconcile local SQLite WAL state against remote broker positions via `RestartRecoveryManager`.
- **Desynchronization Handling**: If remote broker quantity != local database quantity, the system immediately halts trading (`SYSTEM_HALTED`) and triggers operator notification.
- **Isolation**: `IS_PAPER_TRADING` must default to `True`. Live broker credentials and endpoints must remain quarantined behind multi-tier configuration guards.
