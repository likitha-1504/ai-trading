# Chaos Engineering & Failure Injection Testing

To guarantee operational resilience in volatile markets, the AI Micro-Trading Agent undergoes systematic failure injection tests (`backend/tests/test_phase16_failure_injection.py`).

---

## 1. Simulated Failure Scenarios & Mitigations

### Scenario 1: Broker Connection Drop During Open Position
- **Simulation**: Injects socket disconnects or HTTP 500/504 errors from broker API during order submission or position holding.
- **System Response**:
  - The broker adapter attempts fast exponential backoff reconnection.
  - If disconnected > 10 seconds with an open position, the Position Watcher logs an urgent alert and arms the emergency fast-path exit.
  - Upon reconnection, `RestartRecoveryManager` immediately queries `get_positions()` to reconcile quantities.

### Scenario 2: Stale Market Data Feed
- **Simulation**: Market feed simulator stops broadcasting ticks or freezes LTP while a position is active.
- **System Response**:
  - The `MarketDataNormalizer` tracks elapsed time since last valid tick.
  - If elapsed time exceeds 15 seconds, the feed is flagged `STALE`.
  - The system triggers an immediate market exit for all open positions to prevent unmonitored market exposure.

### Scenario 3: Database WAL Lock Contention & Simulated Crash
- **Simulation**: Simulates process termination mid-transaction or locks SQLite DB file with exclusive file lock.
- **System Response**:
  - SQLite WAL (Write-Ahead Log) mode preserves committed transactions up to the crash point.
  - On restart, SQLite automatically recovers uncommitted journal frames.
  - `integrity_verifier.py` checks financial parity between cash ledger and trade history.

### Scenario 4: Extreme Outlier Tick / Bad Price Spike
- **Simulation**: Injects an anomalous tick with a 50% price gap caused by exchange feed glitch.
- **System Response**:
  - `MarketDataNormalizer` applies spread and circuit-filter sanity checks against the 5-minute rolling average.
  - Suspicious outlier ticks are quarantined and logged to prevent false stop-loss triggers.

### Scenario 5: Dual-LLM Ollama Timeout / Disconnect
- **Simulation**: Ollama API is killed or takes > 30 seconds to respond.
- **System Response**:
  - AI Council times out gracefully after configured threshold.
  - Candidate trade is **rejected** with reason `COUNCIL_TIMEOUT`.
  - The rest of the trading system (Position Watcher, existing positions, kill switch) continues operating without interruption.
