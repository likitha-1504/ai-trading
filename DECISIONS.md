# Architecture Decision Records (ADRs)

This document tracks all critical architectural, design, and technical decisions made throughout the project lifecycle.

---

## ADR-001: Local-First Dual-Model LLM Council Architecture
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: The trading agent requires qualitative reasoning (identifying market catalysts, momentum context, and validating trade thesis) without incurring API recurring costs or risking latency/network failure dependencies during trade management.
- **Decision**: Use two local Ollama models with dedicated roles:
  1. `Qwen3`: Generates the market thesis and bullish/bearish rationales.
  2. `DeepSeek-R1`: Acts as an adversarial challenger, searching for counter-theses, false breakouts, and macro hazards.
- **Consequences**: Zero recurring API bills. Complete privacy of trading patterns. Strict requirement to keep LLM inferences off the emergency stop path.

---

## ADR-002: Deterministic Trade Gate & Absolute Watcher Independence
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: LLMs are probabilistic, can hallucinate, and are subject to latency spikes. Entrusting capital safety or emergency stop-loss execution to an LLM creates an unacceptable failure mode.
- **Decision**: 
  1. The final `TradePlan` authorization is strictly deterministic, evaluating liquidity, spread, capital, and risk limits.
  2. The `Position Watcher` runs as an isolated, independent daemon/task. It holds unilateral authority to trigger market exit orders on hard stops, timeout stops, or circuit breakers without querying any LLM.
- **Consequences**: Total immunity against LLM timeouts, malformed JSON outputs, or model crashes during active position management.

---

## ADR-003: One-Writer Rule for Agentic Collaboration
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: Operating multiple autonomous agents (Antigravity as Commander/Architect and Codex CLI as Coding Worker) risks file conflicts, race conditions, and divergent states.
- **Decision**: Enforce a strict single-writer policy. Antigravity prepares technical task definitions and reviews results. Codex CLI performs code generation and test execution in isolation. They never modify the same file concurrently.
- **Consequences**: Clean Git history, verifiable review checkpoints, and deterministic progress.

---

## ADR-004: SQLite with Write-Ahead Logging (WAL) Mode
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: The system needs a low-overhead, embedded persistence layer capable of handling high-frequency tick logging, real-time telemetry, and FastAPI read queries concurrently.
- **Decision**: Standardize on SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), synchronous NORMAL, and foreign keys enabled.
- **Consequences**: Zero external database infrastructure setup. Eliminates lock contention between the execution engine (writer) and the FastAPI/React dashboard (reader).

---

## ADR-005: Comprehensive Indian Market Cost Model & Net-Edge Hurdle
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: Micro-trading on small capital (₹100 to ₹300) is highly vulnerable to friction (STT, exchange fees, SEBI charges, stamp duty, GST, and slippage). A nominally winning trade can easily result in a net loss.
- **Decision**: Integrate a rigorous, configurable fee calculation engine directly into candidate scoring. No trade will be authorized unless the projected gross profit minus total friction satisfies a positive statistical expectancy threshold.
- **Consequences**: Protects micro-capital from attrition due to transaction costs.

---

## ADR-006: Formalization of Pipeline Boundary Contracts and Latency Budgets
- **Date**: 2026-09-23
- **Status**: APPROVED (Lead Architect Lock)
- **Context**: To ensure seamless handoffs and eliminate subtle type bugs across the 10-hop pipeline (`Market Data → Normalizer → Feature Engine → Strategies → Candidate Ranker → AI Queue → Trade Gate → Execution → Position Watcher → Journal`), explicit schema validation and latency budgets are required.
- **Decision**: 
  1. Implement strict Pydantic v2 schemas in `app.models.contracts` for every pipeline boundary.
  2. Mandate that the Position Watcher operates within a `< 50ms` internal evaluation budget.
  3. Decouple the AI Queue asynchronously so slow LLM inference (`1.5s - 4.0s`) never backpressures market tick processing or position monitoring.
- **Consequences**: Compile-time and runtime type safety; guaranteed non-blocking execution for deterministic safety paths.

---

## ADR-007: Deterministic Point-in-Time Feature Engine Architecture
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: Downstream momentum and early-move strategies (Phase 05) and the AI council (Phase 10-11) require multi-dimensional quantitative features (momentum, RVOL, volume/price acceleration, session VWAP, realized volatility, spread, liquidity, price structure, and regime classification) with strict point-in-time safety and guaranteed low latency.
- **Decision**:
  1. Aggregate ticks via `BarAggregator` with fixed epoch-aligned time buckets (e.g. 60s) to prevent timestamp drift and forward-looking data contamination.
  2. Maintain bounded per-symbol ring buffers (`deque(maxlen=100)`) and cumulative session counters for exact session VWAP calculations.
  3. Calculate all 12 quantitative features deterministically with `Decimal` precision and sample statistics, avoiding heavy numerical dependencies.
  4. Enforce sub-millisecond internal latency per feature evaluation, well within the 15ms architecture latency budget.
- **Consequences**: Provable zero look-ahead leakage, identical feature evaluation across live streaming and historical replay/backtesting, and deterministic reproducibility.

---

## ADR-008: Dual BUY Strategy Engine and Cooldown Deduplication Architecture
- **Date**: 2026-09-23
- **Status**: APPROVED
- **Context**: Candidate generation requires evaluating independent trading setups (Momentum Continuation and Early-Move Detection) with explainable evidence, strict rejection of false positives/deteriorating trends, zero order placement authority, and duplicate prevention.
- **Decision**:
  1. Implement `BaseStrategy` interface with `MomentumContinuationStrategy` and `EarlyMoveDetectionStrategy`.
  2. All thresholds (RVOL $\ge 1.80$, spread $\le 0.15\%$, compression volatility $\le 0.35\%$, etc.) are centralized in typed Pydantic models (`MomentumContinuationConfig`, `EarlyMoveDetectionConfig`, `CandidateRankerConfig`) to eliminate magic numbers.
  3. `CandidateRanker` enforces a per-symbol cooldown (default 300s) to suppress duplicate spam, allowing upgrades only when a subsequent candidate scores significantly higher (+15.0 pts).
  4. Candidates provide an explicit, human-readable `quantitative_evidence` dictionary explaining entry reasons and metrics.
  5. Strictly prohibit order placement in the strategy and ranker layer.
- **Consequences**: Clean separation of screening from order gating, predictable signal generation, zero duplicate candidate flooding.

---

## ADR-009: Autonomous Priority-Ordered Position Watcher & Emergency SELL Engine
- **Date**: 2026-09-23
- **Status**: PENDING APPROVAL (Phase 06 Gate Checkpoint)
- **Context**: Autonomous position holding on micro-capital (₹100 to ₹300) requires millisecond-level capital defense against market shocks, broker disconnects, liquidity flash crashes, and trend exhaustion without waiting on probabilistic or slow LLM responses.
- **Decision**:
  1. Implement `IndependentPositionWatcher` with zero dependency on Ollama/Qwen3/DeepSeek-R1 for emergency execution paths.
  2. Enforce a strict 7-level evaluation priority hierarchy:
     - Priority 1: Hard Stop-Loss (immediate market exit on breach)
     - Priority 2: Stale Data Emergency (feed dropped/frozen > 15s)
     - Priority 3: Catastrophic Liquidity Loss (spread >= 50 bps or liquidity score <= 15.0)
     - Priority 4: Daily Circuit Breaker (aggregate realized + unrealized drawdown >= 3.0% of equity)
     - Priority 5: Profit Targets & Monotonic Trailing Stop Ratchet (activation at 1.5R, trail at 1.0R behind peak)
     - Priority 6: Time Protection & Auto Square-Off (15:15 IST hard cutoff, max holding duration 3600s)
     - Priority 7: Technical Deterioration & Structure Breakdown (spread widening >= 25 bps, momentum collapse <= -0.50%, structure lower lows, market reversal)
  3. Treat qualitative AI thesis invalidation strictly as an auxiliary non-emergency signal via `ingest_ai_invalidation()`.
  4. Centralize all thresholds in typed `WatcherConfig` to eliminate magic numbers.
  5. Provide defensive handling for broker rejected orders (reset to OPEN for retry), partial fills, restart reconciliation, and operator manual kill-switch.
  6. Enforce a sub-50ms latency budget per evaluation cycle (measured < 0.2ms).
- **Consequences**: Guaranteed capital safety independent of external network or AI model state; deterministic, auditable exit rationale recorded in `WatcherInterventionEvent`.



