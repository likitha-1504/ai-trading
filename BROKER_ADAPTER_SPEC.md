# Broker Adapter Specification & Abstraction

## 1. Architectural Abstraction

The trading core remains completely decoupled from specific broker SDKs or proprietary APIs. All communication passes through the abstract `BrokerAdapter` interface.

```mermaid
classDiagram
    class BrokerAdapter {
        <<interface>>
        +connect() bool
        +disconnect() void
        +get_account_balance() AccountBalance
        +get_positions() List[Position]
        +get_orders() List[Order]
        +submit_order(OrderRequest) OrderResponse
        +cancel_order(order_id) bool
        +reconcile() ReconciliationReport
    }

    class PaperAdapter {
        -simulated_slippage: float
        -simulated_latencies: int
        -orders_table: Dict
        +submit_order(OrderRequest)
        +simulate_fill()
    }

    class LiveBrokerAdapter {
        -api_key: str
        -access_token: str
        +submit_order(OrderRequest)
        +handle_websocket_ticks()
    }

    BrokerAdapter <|-- PaperAdapter
    BrokerAdapter <|-- LiveBrokerAdapter
```

---

## 2. Order Lifecycle State Machine

Orders must transition strictly through the following sequence:

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> SUBMITTED : Dispatched to Broker
    SUBMITTED --> ACKNOWLEDGED : Broker Accepted
    SUBMITTED --> REJECTED : Insufficient Margin / Invalid
    ACKNOWLEDGED --> PARTIALLY_FILLED : Partial Execution
    PARTIALLY_FILLED --> FILLED : Full Execution
    ACKNOWLEDGED --> FILLED : Single Fill Execution
    ACKNOWLEDGED --> CANCELLED : Cancel Requested
    PARTIALLY_FILLED --> CANCELLED : Cancel Remainder
    FILLED --> [*]
    CANCELLED --> [*]
    REJECTED --> [*]
```

---

## 3. Invariants & Implementation Requirements

1. **Idempotency & Duplicate Order Prevention**:
   - Every order submission requires a client-generated UUID `client_order_id`.
   - The adapter checks local history; duplicate attempts within a 60-second window are rejected immediately.
2. **Reconciliation Loop**:
   - Every 60 seconds (or after connection recovery), the adapter queries broker positions and compares them against the local database.
   - Any mismatch generates a `CRITICAL` risk event and halts new entries.
3. **PaperAdapter Fidelity**:
   - `PaperAdapter` must accurately simulate order submission latency (50–150ms), partial fills, and realistic slippage based on bid-ask spreads.
