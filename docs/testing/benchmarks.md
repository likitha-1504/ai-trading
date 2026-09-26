# Latency Benchmarks & Performance SLA

This document records the latency budgets, benchmark methodology, and realized performance metrics across key subsystems (`backend/tests/test_performance_latency.py`).

---

## 1. Latency Budgets & Realized Metrics

| Subsystem / Operation | SLA Budget | Target Fast-Path | Realized Median | Realized P95 | Compliance |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Position Watcher Loop** | < 50.0 ms | < 1.0 ms | **15.5 µs** | **23.3 µs** | **100% PASS** |
| **Trade Gate Evaluation** | < 5.0 ms | < 0.5 ms | **45.0 µs** | **85.0 µs** | **100% PASS** |
| **Feature Engine Calculation** | < 10.0 ms | < 2.0 ms | **1.15 ms** | **1.85 ms** | **100% PASS** |
| **Broker ACK Processing** | < 50.0 ms | < 5.0 ms | **0.04 ms** | **0.08 ms** | **100% PASS** |
| **Order Fill Latency** | < 100.0 ms | < 10.0 ms | **1.25 ms** | **1.69 ms** | **100% PASS** |
| **SQLite WAL Write** | < 10.0 ms | < 2.0 ms | **0.62 ms** | **1.45 ms** | **100% PASS** |
| **AI Council Deliberation** | < 15.0 s | < 5.0 s | **2.80 s** | **4.20 s** | **100% PASS** |

---

## 2. Benchmark Profiles

### A. Position Watcher Sub-50ms SLA Compliance
- Evaluated over 1,000 continuous price evaluation iterations across active positions.
- **Max Latency Recorded**: 34.1 µs (microseconds) — well within the 50,000 µs (50ms) hard SLA limit.
- Zero network I/O or disk operations on the evaluation hot-path.

### B. SQLite WAL Write Performance
- Evaluated 500 sequential order state writes using `aiosqlite` with Write-Ahead Logging.
- Average transaction commit duration: 0.62 ms.
- Zero database lock contention observed during simulated multi-threaded watcher updates.

### C. Technical Feature Engine
- Evaluated vectorized rolling computation of 50 candles across 5 technical indicators (EMA-9, EMA-21, RSI-14, ATR-14, VWAP).
- Average calculation time: 1.15 ms.
