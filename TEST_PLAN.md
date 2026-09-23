# Test Plan & Quality Assurance Strategy

## 1. Testing Pyramid

Our quality assurance strategy incorporates automated testing at every layer, prioritizing safety, determinism, and financial correctness.

```
       / \
      /   \      Phase 18: Paper Trading Validation
     /  E2E \    Phase 16: Failure Injection & Recovery
    /---------\
   /   Integ   \  Phase 14: API & DB Integration Tests
  /-------------\ Phase 08: Broker & Order Lifecycle Tests
 /     Unit      \ Phase 03-07: Math, Features, Risk, Costs
-------------------
```

---

## 2. Test Suites by Module

### A. Math & Cost Calculations
- Decimal precision of transaction taxes (STT, GST, SEBI charges, stamp duty).
- Net-edge formula validation across various spread and slippage scenarios.
- Prevention of negative or zero trade sizes.

### B. Feature & Strategy Engine
- Lookahead bias tests: Verify that bar $T$ calculations never access bars $T+1$ or later.
- Monotonic timestamp validation.
- Handling of missing ticks, NaN indicators, and flatline volume.

### C. Execution & Order State Machine
- Lifecycle transition tests: `CREATED` → `SUBMITTED` → `ACKNOWLEDGED` → `PARTIALLY_FILLED` → `FILLED`.
- Idempotency test: Re-submitting identical client order IDs must not create duplicate orders.
- Order rejection handling and state recovery.

### D. Position Watcher & Emergency Exits
- Independent emergency stop: Verify position exit occurs within `< 50ms` of stop breach.
- Simulated model crash test: Verify that taking Ollama offline does not block or delay stop-loss execution.
- Stale-data freeze: System triggers safe exit or cancellation if quotes stall beyond configured timeout.

### E. AI Council Validation
- Pydantic schema validation for Qwen3 output (thesis, invalidation, confidence).
- DeepSeek-R1 adversarial challenge parsing and fallback on malformed JSON.
- Timeout handling: If an LLM call exceeds `N` seconds, fall back gracefully to purely deterministic evaluation or bypass AI gating.

---

## 3. Failure Injection Matrix (Phase 16)

| Failure Scenario | Injected Condition | Expected Behavior |
| :--- | :--- | :--- |
| **Market Data Drop** | Abruptly disconnect WebSocket feed | Tag quotes stale; cancel open speculative orders; alert operator. |
| **Broker API Outage** | Inject HTTP 500 / timeout on broker | Retry according to backoff; halt new entries; retry exit with highest priority. |
| **Ollama Hang / OOM** | Terminate Ollama process mid-trade | Position Watcher continues operating unaffected; Trade Gate holds entries. |
| **Partial Fill Trap** | Broker reports only 40% filled, then cancels | Adjust position record to exact filled quantity; update risk limits. |
| **Process Crash** | Hard kill of Python process (`SIGKILL`) | On restart, reconcile active positions with broker snapshot before resuming. |

---

## 4. Phase Verification Gates
Each phase must pass 100% of its designated unit and integration tests before proceeding to the subsequent phase.
