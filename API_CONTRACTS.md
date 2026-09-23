# API Contracts & Interface Specification

This document defines the REST and WebSocket endpoints exposed by the FastAPI backend (`http://localhost:8000/api/v1`).

---

## 1. Security & Operational Segregation

- **Read / Query Endpoints**: Idempotent, read-only routes retrieving system state, telemetry, and history. Accessible without special gating.
- **Execution & Mutation Endpoints**: Guarded routes. Manual trade approvals, emergency kill switches, and configuration updates require verification.
- **Live Order Guard**: Direct order creation endpoints do NOT exist. All orders must originate from deterministic `TradePlan` objects evaluated by the Trade Gate.

---

## 2. REST Endpoints Overview

### System & Health
- `GET /health`: Basic liveness and readiness probe.
- `GET /system/status`: Returns status of market data feeds, DB WAL status, Ollama responsiveness, and Position Watcher heartbeat.

### Telemetry & Dashboard
- `GET /telemetry/summary`: High-level dashboard payload (Equity, daily P&L, active positions count, system mode).
- `GET /telemetry/capital`: Breakdown of total, available, and deployed capital, buying power, and drawdowns.

### Market Data & Scanning
- `GET /market/scanner`: Current universe candidates, price changes, and volume velocity.
- `GET /market/features/{symbol}`: Latest computed feature snapshot for a given ticker.

### Decision Pipeline & AI
- `GET /candidates`: Active candidates detected by Momentum and Early-Move strategies.
- `GET /ai/analyses/{candidate_id}`: Dual-model qualitative reports (`Qwen3` thesis + `DeepSeek-R1` challenge).
- `GET /trade-plans`: Recent trade plans evaluated by the Deterministic Trade Gate.

### Portfolio & Execution
- `GET /positions`: Active and historical positions with stop-loss and trailing levels.
- `GET /orders`: Status of submitted, filled, or cancelled orders.
- `GET /trades`: Executed trade fills and friction breakdowns (STT, GST, brokerage).

### Control & Manual Approval (Mutations)
- `POST /trades/approve/{plan_id}`: Approves a plan held in `MANUAL_PENDING` (trades > ₹300 or specific flagged setups).
- `POST /system/kill-switch`: Triggers an emergency stop. Liquidates open positions via Position Watcher and suspends new order generation.
- `POST /system/mode`: Switches system between `PAPER` and `LIVE` (requires confirmation token).

---

## 3. Real-Time WebSocket Streams

- `WS /ws/live-feed`: Broadcasts:
  - Ticks & Bar updates
  - Candidate discoveries
  - Order state updates (`SUBMITTED`, `FILLED`, etc.)
  - Position Watcher emergency events
