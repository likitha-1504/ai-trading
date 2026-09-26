# End-to-End Data Flow & State Management

This document details the lifecycle of market ticks, candidate signals, AI deliberation records, order execution states, and position lifecycle updates across the system.

---

## 1. Trade Data Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Market as Market Feed / WebSocket
    participant MDN as Market Data Normalizer
    participant FE as Feature Engine
    participant Strat as Strategies (Early / Momentum)
    participant AI as AI Council (Qwen3 / R1)
    participant Gate as Deterministic Trade Gate
    participant Cost as Cost & Capital Sizer
    participant Exec as Execution Engine
    participant Broker as Broker Adapter
    participant PW as Position Watcher
    participant DB as SQLite WAL Store

    Market->>MDN: Ingest Raw Tick (LTP, Volume, Depth)
    MDN->>MDN: Validate Timestamp Monotonicity & Spread
    MDN->>FE: Forward Valid Tick
    FE->>FE: Compute EMA, VWAP, RSI, ATR
    FE->>Strat: Tick Slice & Indicator Snapshot
    Strat->>Strat: Evaluate Entry Rules
    Strat-->>AI: Generate Trade Candidate (Symbol, Side, Setup)
    AI->>AI: Qwen3 Hypothesis -> DeepSeek-R1 Challenge
    AI-->>Gate: Emit Advisory TradePlan with Confidence Score
    Gate->>Gate: Evaluate 100% Deterministic Rules
    Note over Gate: Max 1.5% Risk, 3% Daily Loss Stop, Market Cutoff
    alt Rule Fails
        Gate-->>DB: Record TradePlan REJECTED (Reason Code)
    else Rule Passes
        Gate->>Cost: Calculate Statutory Fees & Max Quantity
        Cost-->>Gate: Approved Sizing (<= Capital Limit)
        Gate->>Exec: Dispatch Approved TradePlan
        Exec->>Broker: Place Market / Limit Order
        Broker-->>Exec: Order ACK & Fill Event
        Exec->>DB: Persist Position & Order (ACID WAL)
        Exec->>PW: Register Active Position for Watching
    end

    loop Every Tick / Polling Interval (Sub-50ms SLA)
        Market->>PW: Live Tick Feed
        PW->>PW: Check Stop Loss, Target, Trailing Stop, 15:15 Cutoff
        alt Exit Condition Triggered
            PW->>Broker: Fire Fast-Path Market Exit Order
            Broker-->>PW: Order Filled
            PW->>DB: Record Position Closed & Realized P/L
            PW-->>Exec: Unregister Closed Position
        end
    end
```

---

## 2. Execution State Machine

Orders and positions progress strictly through deterministic states defined in `backend/app/models/contracts.py`:

```mermaid
stateDiagram-v2
    [*] --> PENDING_SUBMISSION
    PENDING_SUBMISSION --> SUBMITTED: Broker Dispatched
    PENDING_SUBMISSION --> REJECTED: Gate Violation / Invalid State
    SUBMITTED --> OPEN: Broker Fill ACK
    SUBMITTED --> REJECTED: Broker Rejection
    OPEN --> EXITING: Watcher Stop / Target / Emergency Exit
    EXITING --> CLOSED: Exit Order Filled
    OPEN --> CLOSED: Emergency Kill Switch
    CLOSED --> [*]
```

### State Definitions
1. **PENDING_SUBMISSION**: Created by Execution Engine, undergoing pre-submission lock.
2. **SUBMITTED**: Transmitted to broker adapter; awaiting exchange confirmation.
3. **OPEN**: Filled; active exposure monitored by Position Watcher thread.
4. **EXITING**: Exit trigger fired (Hard Stop, Take Profit, Time Expiry, or Cutoff); exit order in flight.
5. **CLOSED**: Completely exited, fees deducted, realized P/L locked to ledger.
6. **REJECTED**: Refused by Trade Gate risk limits or broker margin rejection.
7. **SYSTEM_HALTED**: Emergency kill-switch activated; all open positions forcefully closed.

---

## 3. Database Schema & WAL Persistence

The persistent layer is backed by SQLite with `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL`:
- **`positions`**: Open and closed positions with entry price, exit price, quantities, realized P/L, fees, and exit trigger tags.
- **`orders`**: Individual order execution events, broker order IDs, timestamps, and fill prices.
- **`trade_plans`**: Candidates evaluated by strategies and AI Council, including approval status and rejection reasons.
- **`capital_snapshots`**: Periodic and event-driven capital accounting snapshots (total capital, available cash, high water mark).
- **`council_records`**: Advisory deliberative text from Qwen3 and DeepSeek-R1 with agreement scores.
- **`system_audit_logs`**: Tamper-evident operational events, config validations, and error traces.
