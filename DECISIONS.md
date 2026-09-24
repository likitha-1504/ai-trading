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
- **Status**: APPROVED (User Gate Sign-Off)
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

---

## ADR-010: Configurable Indian Equity Cost Engine, Capital Tracking, and Deterministic Risk Gating
- **Date**: 2026-09-24
- **Status**: PENDING APPROVAL (Phase 07 Gate Checkpoint)
- **Context**: Micro-capital trading (₹100 to ₹300) in Indian equities is critically sensitive to transaction friction (brokerage, STT, exchange charges, SEBI turnover fees, stamp duty, GST, and bid-ask slippage). A system without exhaustive cost modeling and deterministic risk gating will suffer rapid capital attrition even with nominally winning trade signals.
- **Decision**:
  1. Implement `IndianMarketCostModel` in `backend/app/capital/cost_model.py` with 100% configurable statutory rates and zero hardcoded fees.
  2. Implement `CapitalManager` in `backend/app/capital/capital_manager.py` maintaining real-time equity, cash reserves, buying power, deployed allocations, high-water mark, and daily drawdowns.
  3. Implement `RiskEngine` in `backend/app/capital/risk_engine.py` enforcing:
     - 1.5% max risk per trade relative to current equity.
     - 3.0% max daily drawdown circuit breaker.
     - Max 2 concurrent open positions and zero duplicate symbol exposure.
     - Minimum economical trade size verification.
     - Expected Net Edge hurdle verification: $(\text{Target Gain} \times P(\text{Win})) - (\text{Stop Loss} \times (1 - P(\text{Win}))) - \text{Total Friction} \ge \text{Hurdle Rate}$.
     - Autonomy policy gating: trades $\le ₹300$ are categorized as `ApprovalMode.AUTONOMOUS`; trades or total allocations $> ₹300$ mandate `ApprovalMode.MANUAL_PENDING`.
- **Consequences**: Provable mathematical edge required before any trade plan can be authorized; deterministic capital defense and strict human-in-the-loop controls above the autonomous threshold.

---

## ADR-011: Broker Abstraction Layer, Order Lifecycle State Machine, and Portfolio Reconciliation
- **Date**: 2026-09-24
- **Status**: PENDING APPROVAL (Phase 08 Gate Checkpoint)
- **Context**: Interfacing with broker execution endpoints requires total decoupling of trading and risk core from external broker SDKs, strict state machine progression, idempotency to prevent duplicate orders during network latency/retries, comprehensive execution telemetry, realistic paper simulation, and automatic reconciliation with recovery procedures upon disconnects. Live trading must remain strictly disabled.
- **Decision**:
  1. Define abstract `BrokerAdapter` interface in `backend/app/adapters/broker_base.py` enforcing standard methods: `connect`, `disconnect`, `get_account_balance`, `get_positions`, `get_orders`, `submit_order`, `cancel_order`, and `reconcile`, with async event callback dispatch.
  2. Implement `PaperAdapter` in `backend/app/adapters/paper_adapter.py` providing realistic tick-based slippage, configurable latency, partial fill emulation, fault injection (broker offline, rejection symbols), and portfolio balance/margin tracking.
  3. Implement `OrderStateMachine` in `backend/app/execution/state_machine.py` enforcing strict transitions (`CREATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED / CANCELLED / REJECTED`) and immutable terminal states (`FILLED`, `CANCELLED`, `REJECTED`).
  4. Implement `ExecutionEngine` in `backend/app/execution/execution_engine.py` orchestrating:
     - 60-second client-order-id deduplication window rejecting duplicate submissions with `DuplicateOrderError`.
     - Delta-fill and cumulative telemetry updates, ignoring redundant exact-duplicate events.
     - Portfolio reconciliation comparing local active positions against broker snapshot and reporting `MISSING_IN_BROKER`, `MISSING_IN_LOCAL`, or `QUANTITY_MISMATCH`.
     - Reconnect recovery procedure reconnecting adapter and triggering immediate state audit.
     - Hard-coded `is_live = False` safety lock ensuring zero live market interaction in Phase 08.
  5. Implement `ExecutionMetricsTracker` in `backend/app/execution/metrics.py` recording order lifecycle counts, cumulative filled quantities, realized slippage, and average submission/acknowledgement/fill latencies in milliseconds.
- **Consequences**: Zero broker lock-in, mathematically sound idempotency, high-fidelity paper trading execution matching live constraints, auditable reconciliation and latency telemetry, and guaranteed lockout of real-money live execution.

---

## ADR-012: Event-Driven Backtester, Paper Trading Loop, and Quantitative Evaluation Metrics
- **Date**: 2026-09-24
- **Status**: PENDING APPROVAL (Phase 09 Gate Checkpoint)
- **Context**: Validating algorithmic strategies on micro-capital requires a simulation framework that eliminates lookahead and survivorship bias, models realistic transaction friction and slippage, shares 100% strategy and execution interfaces with live/paper pipelines, prevents overfitting via walk-forward analysis, and logs immutable trade journal audits without ever enabling real-money live order routing.
- **Decision**:
  1. Implement `BacktestEngine` in `backend/app/backtesting/simulator.py`:
     - Sequential event-driven processing enforcing strictly non-decreasing timestamps (`TimestampOrderError` on violation).
     - Point-in-time universe filtering to eliminate survivorship bias.
     - Integration with `FeatureEngine`, `CandidateRanker`, `RiskEngine`, `CapitalManager`, `PaperAdapter`, and `IndependentPositionWatcher`.
     - Zero lookahead bias: each feature and decision relies only on past/current events.
  2. Implement `PaperTradingLoop` in `backend/app/backtesting/paper_loop.py`:
     - Continuous market event consumption maintaining 100% strategy interface symmetry with backtesting.
     - Hard-coded `is_live = False` safety invariant guaranteeing live broker lockout.
  3. Implement `IndianMarketCostModel` integration:
     - Real-time deduction of statutory brokerage, STT, exchange charges, SEBI turnover fees, stamp duty, and GST on entry and exit fills.
  4. Implement `TradeJournal` in `backend/app/backtesting/journal.py`:
     - Detailed immutable `TradeRecord` items capturing trade lifecycle, prices, tick slippage, friction breakdowns, gross and net P/L, holding durations, and entry/exit market regimes.
  5. Implement `PerformanceCalculator` in `backend/app/backtesting/metrics.py`:
     - Computing net P/L, financial expectancy, profit factor, maximum drawdown amount/percentage, trade frequency per day, average trade, friction percentage of gross profit, and regime-stratified P/L.
  6. Implement `WalkForwardAnalyzer` in `backend/app/backtesting/walk_forward.py`:
     - Partitioning historical event streams into in-sample and out-of-sample segments to assess performance degradation and flag statistical overfitting.
  7. Implement `SlippageSensitivityAnalyzer` in `backend/app/backtesting/slippage_analysis.py`:
     - Stress-testing trading edge persistence across varying slippage tick increments (0, 1, 2, 3 ticks).
- **Consequences**: Provably unbiased historical and real-time paper evaluation; identical strategy execution across simulation and production; complete auditability through TradeJournal; zero risk of capital loss or accidental live order execution.

---

## ADR-013: Qwen3 Primary Market Analyst Integration, Structured Qualitative Evidence, and Deterministic Fallback Gating
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 10 Gate Sign-Off)
- **Context**: Autonomous micro-trading requires qualitative analysis of pre-screened technical setups (catalyst identification, bullish evidence, market context, perceived risks, invalidation criteria) while ensuring LLM latency, probabilistic hallucinations, network timeouts, or malformed JSON payloads cannot destabilize the system or bypass risk controls.
- **Decision**:
  1. Restrict Qwen3 inputs strictly to structured feature summaries (`FeatureSnapshot`) and candidate context (`Candidate`), completely eliminating raw tick stream leakage into the LLM prompt context (`backend/app/ai/prompts.py`).
  2. Define strict JSON schema with Pydantic contracts in `app.models.contracts.MarketThesis` and `MarketThesisAction` (`PROCEED`, `CAUTION`, `REJECT`), capturing thesis summary, catalyst, bullish evidence, invalidation conditions, perceived risks, bounded confidence score ([0.0, 1.0]), context summary, model metadata (`model_name`, `model_version`, `prompt_version`), latency in ms, and token metrics.
  3. Implement `Qwen3OutputValidator` in `backend/app/ai/validator.py` with markdown codeblock fence stripping, JSON structure verification, bounds checking, and deterministic parsing.
  4. Implement `Qwen3AnalystClient` in `backend/app/ai/client.py` supporting both asynchronous and synchronous invocation with per-request timeouts (default 3.0s), exponential backoff retries, and comprehensive error trapping.
  5. Enforce deterministic safe fallbacks on model unavailability, timeouts, or malformed outputs via `create_fallback_thesis()`, assigning confidence score `0.0`, `CAUTION` action, and `is_fallback=True`, ensuring zero trade execution authority or risk bypass.
  6. Collect runtime telemetry in `AIAnalystMetrics` (`backend/app/ai/metrics.py`) tracking request counts, successes, failures, timeouts, malformed responses, fallbacks, token counts, and average/P95 latencies.
- **Consequences**: Qualitative AI reasoning is cleanly integrated into the evidence-gathering pipeline; zero risk of LLM hallucinations triggering orders or bypassing risk rules; complete resilience against Ollama/network downtime.

---

## ADR-014: DeepSeek-R1 Adversarial Challenger Integration, Think-Tag Sanitization, and Deterministic Dispute Arbitration
- **Date**: 2026-09-24
- **Status**: PENDING APPROVAL (Phase 11 Gate Checkpoint)
- **Context**: Relying on a single qualitative AI analyst (Qwen3) introduces susceptibility to confirmation bias, overlooked structural risks, and unexamined assumptions. Adding an adversarial challenger (DeepSeek-R1) provides critical stress-testing, but simple majority voting or probabilistic resolution must never decide trade authorization. The deterministic Trade Gate must retain ultimate authority.
- **Decision**:
  1. Restrict DeepSeek-R1 inputs to structured candidate metrics (`FeatureSnapshot`, `Candidate`) AND Qwen3's qualitative analysis (`MarketThesis`), preserving complete isolation from raw tick streams (`backend/app/ai/challenger_prompts.py`).
  2. Implement strict Pydantic contract schemas in `app.models.contracts` (`ChallengerCritique`, `ChallengerSeverity`, `ChallengerRecommendation`), capturing critique summary, identified vulnerabilities, contradictory signals, missing evidence, invalidation conditions, worst-case scenario, downside severity (`LOW`, `MEDIUM`, `SEVERE`), and recommendation flag (`CONFIRM`, `CONTEST`, `VETO_CANDIDATE`).
  3. Implement `DeepSeekR1OutputValidator` in `backend/app/ai/challenger_validator.py` with special handling for DeepSeek-R1 `<think>...</think>` internal chain-of-thought blocks, markdown fences, and JSON boundary isolation.
  4. Implement `DeepSeekR1ChallengerClient` in `backend/app/ai/challenger_client.py` with asynchronous and synchronous interfaces, per-request timeouts (default 5.0s), exponential backoff retries, and comprehensive exception trapping with structured audit logging.
  5. Enforce deterministic safe fallbacks on model unavailability, timeouts, or malformed JSON via `create_fallback_critique()`, assigning `ChallengerRecommendation.CONTEST`, `ChallengerSeverity.MEDIUM`, and `is_fallback=True`, ensuring unverified trades never receive automatic clearance.
  6. Enforce deterministic council dispute arbitration in `backend/app/ai/council_evaluator.py`:
     - Reject immediately if Qwen3 rejects or confidence falls below minimum hurdle.
     - Reject immediately if DeepSeek-R1 issues `VETO_CANDIDATE` with `SEVERE` downside.
     - When Qwen3 is bullish (`PROCEED`) and DeepSeek-R1 contests (`CONTEST`), arbitrate using strictly empirical quantitative metrics (spread friction <= 15 bps, liquidity score >= 70.0, stop risk validation). Empirical compliance grants clearance with `CAUTION` and audited risk notes; empirical failure triggers immediate rejection.
     - Never use simple majority voting or probabilistic resolution.
- **Consequences**: Rigorous adversarial stress-testing without introducing deadlock or probabilistic risk leakage; guaranteed supremacy of empirical math and deterministic safety rules.

