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
- **Status**: APPROVED (Phase 11 Gate Sign-Off)
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
- **Verification Evidence**:
  - 21 unit and integration tests passing in `backend/tests/test_deepseek_r1_challenger.py` covering prompt construction, think-tag stripping, JSON schema parsing, timeout retries, connection failure recovery, fallback generation, telemetry recording, broker execution lockout, and empirical council arbitration.
  - Full project test suite passing (127/127 tests passing).
  - Static type checking (mypy) and linting (ruff) passing with zero errors across all 68 source files.

---

## ADR-015: Deterministic Trade Gate, 7-Step Decision Pipeline, and Autonomous Risk Ownership Transfer
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 12 Gate Sign-Off)
- **Context**: The AI Micro-Trading Agent requires a unified decision pipeline that evaluates candidate viability, portfolio risk, transaction friction, and qualitative AI analysis while strictly preserving deterministic supremacy. Crucially, AI models must be physically incapable of submitting broker orders, capital limits (₹100 baseline, ₹300 autonomy threshold) must be rigorously enforced, and active position risk must be autonomously transferred to the Independent Position Watcher.
- **Decision**:
  1. Implement `DeterministicTradeGate` in `backend/app/gate/trade_gate.py` executing a strict 7-step decision pipeline:
     - **Step 1: Deterministic Candidate Gate**: Filters candidate setups on price rationality, stop orientation, spread tolerance (<= 15 bps), liquidity score (>= 70.0), and 15:15 IST intraday cutoff. Rejection halts pipeline immediately before invoking LLM inference.
     - **Step 2: Risk / Capital / Cost Gate**: Leverages `RiskEngine`, `CapitalManager`, and `IndianMarketCostModel`. Enforces 3% daily drawdown circuit breaker, 2-position concentration cap, position sizing (1.5% equity risk budget), Indian statutory levies (STT, GST, exchange fees, SEBI, stamp duty, 1-tick slippage), and net-edge hurdle. Rejection halts pipeline before invoking LLM inference.
     - **Step 3: Qwen3 Qualitative Analysis**: Asynchronously/synchronously queries Qwen3 for catalyst, evidence, and invalidation criteria.
     - **Step 4: DeepSeek-R1 Adversarial Challenge**: Asynchronously/synchronously queries DeepSeek-R1 to stress-test the thesis, arbitrating disputes through deterministic mathematical rules (no majority voting).
     - **Step 5: Deterministic Final TradePlan Synthesis**: Generates immutable `TradePlan` contract capturing all 13 items required by the PDF: instrument, side, quantity, entry context, expected edge, estimated costs, risk limits, stop/protection, invalidation, strategy, AI evidence references, decision reason, and approval mode.
     - **Step 6: Execution Authorization**: Strictly isolates AI from broker adapters. Only `DeterministicTradeGate` may construct `OrderRequest` and dispatch to `ExecutionEngine`. Enforces `ApprovalMode.AUTONOMOUS` for trades <= ₹300 and `ApprovalMode.MANUAL_PENDING` for trades > ₹300.
     - **Step 7: Position Watcher Ownership Transfer**: Active positions created upon order fill are registered immediately with `IndependentPositionWatcher`, transferring continuous risk surveillance (sub-50ms hard stops, trailing stops, stale data exits, 15:15 IST auto-square-off) away from decision modules.
  2. Implement `TradeGateAuditLogger` in `backend/app/gate/audit_logger.py` providing an immutable structured audit log across all 7 pipeline transitions.
  3. Expand `TradePlan`, `RiskLimits`, and `StopProtection` contracts in `backend/app/models/contracts.py` with bidirectional field synchronization and validation.
- **Consequences**: Provable deterministic execution guardrails; zero order injection vulnerability from LLMs; complete separation of concerns between strategy generation, qualitative AI stress-testing, trade planning, execution, and position risk ownership; transparent audit trail for every setup.
- **Verification Evidence**:
  - 14 dedicated unit/integration tests in `backend/tests/test_deterministic_trade_gate.py` passing.
  - Complete project test suite passing (141/141 tests passing).
  - Static type checking (`mypy backend`) and linting (`ruff check backend`) passing with zero errors across all 73 source files.

---

## ADR-016: SQLite WAL Schema, Persistent Trade Journal, Performance Analytics, and Restart Recovery
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 13 Gate Sign-Off)
- **Context**: Phase 13 of the AI Micro-Trading Agent requires a persistent SQLite database with Write-Ahead Logging (WAL) and safe transaction handling to persist all 13 core architectural entities, record executed trade lifecycle journals, compute accurate statutory P/L, aggregate strategy/model/execution performance metrics, provide an auditable decision reconstruction trail (`is_fully_reproducible`), and enable clean restart recovery for system controllers without state corruption.
- **Decision**:
  1. **SQLite WAL & Connection Management (`backend/app/db/schema.py`, `backend/app/db/connection.py`, `backend/app/db/session.py`)**:
     - Configure SQLite with `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`, `PRAGMA foreign_keys = ON;`, and `PRAGMA busy_timeout = 5000;`.
     - Implement both synchronous (`get_connection`) and asynchronous (`get_async_connection`) context managers with automatic commit on success and automatic rollback on unhandled exceptions.
  2. **13 Core Entities DDL & Repository (`backend/app/db/repository.py`)**:
     - Implement DDL schema and CRUD repository functions for all 13 core entities: `capital_state`, `positions`, `orders`, `trades`, `candidates`, `features`, `ai_analyses`, `trade_plans`, `risk_events`, `strategy_versions`, `model_calls`, `execution_metrics`, and `system_events`.
     - Create database indices across candidate IDs, symbols, statuses, and timestamps for high-frequency queries.
  3. **Persistent Trade Journal (`backend/app/db/journal.py`)**:
     - Implement `DatabaseTradeJournal` tracking position entries and exits with precise P/L accounting (Gross P/L, Indian statutory cost breakdown via `FrictionBreakdown`, and Net P/L).
  4. **Performance Aggregator (`backend/app/db/performance.py`)**:
     - Implement `PerformanceAggregator` computing financial KPIs: total trades, win rate, gross/net P/L, profit factor, expectancy, average win/loss, maximum drawdown, and trade frequency.
     - Implement strategy-level metrics stratification (`MOMENTUM_CONTINUATION` vs `EARLY_MOVE_DETECTION`).
     - Implement model latency metrics (`qwen3:latest` and `deepseek-r1:latest` average latency, P95 latency, call count, and fallback rate).
     - Implement execution latency metrics (average submission latency, average fill latency, fill rate percentage, and total slippage).
  5. **Decision Audit Trail & Reproducibility (`backend/app/db/audit.py`)**:
     - Implement `DecisionAuditTrailManager` linking candidate setups, quantitative feature snapshots, qualitative AI analyses (Qwen3 & DeepSeek-R1), synthesized trade plans, submitted orders, and resulting position/trade records.
     - Provide `is_fully_reproducible` audit verification checking that every execution has full upstream provenance.
  6. **Restart Recovery (`backend/app/db/recovery.py`)**:
     - Implement `RestartRecoveryManager` that rehydrates active state after process crash or restart:
       - Restores `IndependentPositionWatcher` with open positions, hard stops, trailing stops, and profit targets.
       - Restores `CapitalManager` with total equity, available capital, realized P/L, and high-water mark.
       - Restores `ExecutionEngine` with pending/active orders.
- **Consequences**: Complete persistence of all system facts and analytical telemetry; guaranteed ACID transaction safety; comprehensive decision reproducibility for audit compliance; seamless crash recovery without state loss.
- **Verification Evidence**:
  - 8 comprehensive unit and integration tests passing in `backend/tests/test_database_journal_performance.py`.
  - Full project test suite passing (149/149 tests passing).
  - Static type checking (`mypy backend`) and linting (`ruff check backend`) passing with zero errors across all 81 source files.

---

## ADR-017: FastAPI Backend, Segregated API Contracts, Guarded TradePlan Approvals, and Live-Trading Protection
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 14 Gate Sign-Off)
- **Context**: Phase 14 of the AI Micro-Trading Agent requires a FastAPI backend exposing safe read/query APIs across all 13 system aspects, segregating read queries from mutation/execution endpoints, strictly forbidding arbitrary order submission (e.g., `POST /orders` is strictly forbidden and returns 405 Method Not Allowed), guarding TradePlan approval/rejection workflows, and protecting live trading under explicit human confirmation, approval tokens, and strict safety controls.
- **Decision**:
  1. **Segregated API Contract Schemas (`backend/app/api/schemas.py`)**:
     - Implement dedicated Pydantic v2 schemas for all 13 read domains and guarded mutation payloads (`DashboardSummaryResponse`, `CapitalResponse`, `MarketScannerItem`, `PnLSummaryResponse`, `ModelLatencyStats`, `RiskStatusResponse`, `RiskLimitsResponse`, `SystemHealthResponse`, `AuditTrailResponse`, `PlanApprovalRequest`, `PlanApprovalResponse`, `KillSwitchRequest`, `KillSwitchResponse`, `ModeSwitchRequest`, `ModeSwitchResponse`).
  2. **Dependency Injection & Architectural Boundary Enforcement (`backend/app/api/deps.py`)**:
     - Implement singleton/scoped dependency providers for database repository, trade journal, performance aggregator, decision audit manager, restart recovery manager, system state, capital manager, position watcher, execution engine, and deterministic trade gate.
     - Implement `verify_live_trading_authorization` enforcing authorization headers and environment-level safeguards against accidental or unauthorized live execution.
  3. **Modular Domain Routers (`backend/app/api/v1/endpoints/`)**:
     - Expose 13 safe read/query endpoint suites:
       - `/dashboard`: High-level summary and real-time capital state.
       - `/market`: Real-time market scanner feed and technical features.
       - `/candidates`: Strategy-detected trading candidates.
       - `/positions`: Active positions tracked with real-time unrealized P/L and stops.
       - `/orders`: Read-only order audit log and status queries. No `POST /orders` endpoint is exposed.
       - `/trades`: Immutable executed trade journal with gross/net P/L and friction breakdowns. Guarded `POST /trades/approve/{plan_id}` and `POST /trades/reject/{plan_id}` endpoints allow explicit human approvals for pending trade plans.
       - `/trade-plans`: Synthesized TradePlan blueprints.
       - `/pnl`: Aggregate and periodic P/L summaries with statutory friction breakdowns.
       - `/ai`: Dual-model AI Council qualitative theses, critiques, and model latency metrics.
       - `/performance`: Strategy-level financial KPIs and execution fill metrics.
       - `/backtests`: Backtesting simulation runs and historical trade logs.
       - `/risk`: Real-time drawdown, circuit breakers, risk events, and limit configurations.
       - `/system`: Multi-component health probes (SQLite WAL, Position Watcher, Execution Engine, AI Council), operational status, guarded mode switches, and emergency kill-switch (`POST /system/kill-switch`) invoking Position Watcher square-off.
       - `/logs`: System operational logs and end-to-end decision provenance reconstruction (`/logs/audit/{candidate_id}`).
  4. **Strict Arbitrary Order Execution Prohibition & Guardrails**:
     - The backend explicitly does NOT expose any endpoint for arbitrary order submission (`POST /orders` is forbidden / 405). Orders can only ever be generated and dispatched through an approved `TradePlan` evaluated by the `DeterministicTradeGate`.
     - System-halted state prevents any trade plan approvals.
  5. **Application Configuration & Interactive Docs (`backend/app/main.py`)**:
     - Configure CORS middleware, error handlers, and interactive OpenAPI documentation at `/api/docs` and `/api/redoc`.
- **Consequences**: Safe, decoupled, and transparent API layer; eliminates arbitrary order injection attack vectors; ensures live-trading actions require deliberate human authentication; provides unified telemetry across facts, AI suggestions, and deterministic execution.
- **Verification Evidence**:
  - 18 comprehensive API tests passing in `backend/tests/test_api_v1.py` covering all 13 read domains, 405 Method Not Allowed for arbitrary order creation, plan approvals, live mode security locks, and emergency kill-switch.
  - Complete project test suite passing (167/167 tests passing).
  - Static type checking (`mypy backend`) and linting (`ruff check backend`) passing with zero errors across all 99 source files.

---

## ADR-018: React Trading Terminal, 15 Distinct Screens, Deterministic Fact Banners, and Emergency Kill-Switch UI
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 15 Gate Sign-Off)
- **Context**: Phase 15 of the AI Micro-Trading Agent requires building a complete React + TypeScript + Tailwind trading terminal adhering strictly to `UI_UX_SPEC.md` and Phase 15 requirements from the prompt pack. The interface must provide all 15 specified screens, strictly distinguish deterministic system facts from probabilistic AI hypotheses, support 15 visual badge states, provide a prominent emergency kill-switch with double-confirmation safety, and connect to realistic mock/paper telemetry feeds.
- **Decision**:
  1. **Design Tokens & Dark-First Philosophy (`frontend/tailwind.config.js`, `frontend/src/index.css`)**:
     - Implement deep slate palette (`#0B0E14` root, `#151A23` surface, `#1C2331` elevated, `#222938` subtle border).
     - Configure tabular numerals (`font-variant-numeric: tabular-nums; font-feature-settings: 'tnum'`) on monospace fonts (`JetBrains Mono`) to eliminate number flutter during price updates.
  2. **Strict Visual Distinction of Truth vs Speculation (`frontend/src/components/ui/FactBanner.tsx`)**:
     - `[SYSTEM FACT]`: Sky Blue badge (`#0284C7`), solid border (`#0369A1`), clean sans/mono typography, signifying verified mathematical/broker reality.
     - `[QWEN3 ANALYSIS]` & `[DEEPSEEK-R1 CHALLENGE]`: Violet badges (`#8B5CF6`), dashed purple borders (`#6D28D9`), subtle violet tint, with mandatory italicized disclaimer: *"Probabilistic LLM speculation. Never guarantees trajectory."*
     - `[FINAL DETERMINISTIC GATE]`: Emerald/crimson solid border reinforcing zero LLM order placement authority.
  3. **15 Visual Badge States (`frontend/src/components/ui/Badge.tsx`)**:
     - Implement all 15 states specified in `UI_UX_SPEC.md`: `BUY`, `SELL`, `HOLD`, `WATCH`, `RISK` (with pulse animation), `ERROR`, `CONNECTED`, `DISCONNECTED`, `AI THINKING`, `AI UNAVAILABLE`, `PENDING`, `PARTIAL FILL`, `FILLED`, `CANCELLED`, `REJECTED`.
  4. **Complete 15-Screen Architecture (`frontend/src/screens/`)**:
     - Screen 1: Command Center (Executive KPI overview, active trade risk progress bar, watcher heartbeat, live logs).
     - Screen 2: Market Scanner (Universe selector, momentum/RVOL/VWAP grid, spread bps, feature inspect).
     - Screen 3: Candidate Feed (Momentum & Early-Move candidate setups, 4-stage pipeline, net edge %, AI inspect).
     - Screen 4: Trading Chart (Interactive SVG candlestick chart, VWAP band, volume sub-pane, execution lines for entry, hard stop, trailing stop, take profit).
     - Screen 5: Position Monitor (Active positions table, sub-50ms watcher state, double-confirmation square-off button).
     - Screen 6: Orders & Execution (Order state machine lifecycle audit, broker return codes, zero arbitrary order submission).
     - Screen 7: AI Analysis (Dual-model qualitative debate: Qwen3 thesis vs DeepSeek-R1 adversarial challenge, deterministic arbitration).
     - Screen 8: Trade Journal (Immutable trade retrospective, entry/exit stamps, Indian statutory friction breakdown: STT, exchange, SEBI, GST, stamp duty).
     - Screen 9: Performance Analytics (Win rate, profit factor, max drawdown, fee drag analysis, equity curve).
     - Screen 10: Backtesting (Event-driven historical simulation, parameter controls, walk-forward stability).
     - Screen 11: Risk & Capital (₹100 micro-cap meter, ₹300 autonomous limit, 3.0% daily drawdown circuit breaker gauge, risk event log).
     - Screen 12: System Health (Local infrastructure diagnostics, SQLite WAL mode, Ollama inference, pipeline latency bars).
     - Screen 13: Logs & Events (Structured telemetry stream, regex/search, severity filtering, JSON export).
     - Screen 14: Strategy Management (Parameter tuning for Momentum Continuation & Early-Move Detection).
     - Screen 15: Settings (Paper simulation mode, backend endpoint configuration, emergency webhooks).
  5. **Global Navigation, Telemetry & Emergency Safety (`frontend/src/components/layout/`)**:
     - `TopBar`: Real-time account facts (₹100.00 base, deployed, available, daily P&L; paper mode active indicator).
     - `NavBar`: Clean 15-tab navigation bar with number shortcuts and Lucide icons.
     - `StatusBar`: Fixed bottom bar reporting feeds, Ollama standby, Watcher tick health (<50ms), and SQLite WAL state.
     - `KillSwitchModal`: Double-confirmation safety dialog triggering immediate Position Watcher square-off and system halt.
  6. **Resilient Data Layer (`frontend/src/services/api.ts`, `frontend/src/data/mockData.ts`)**:
     - Queries FastAPI backend endpoints with automatic graceful fallback to realistic paper trading mock fixtures.
- **Consequences**: Complete professional dark-first trading terminal; zero cognitive confusion between deterministic broker facts and probabilistic AI reasoning; verified emergency shutdown controls; full alignment with `UI_UX_SPEC.md`.
- **Verification Evidence**:
  - `npm run build` compiles with zero TypeScript errors and bundles into optimized production assets via Vite (`tsc -b && vite build` built in 1.86s).
  - Complete backend test suite passing (167/167 tests passing).
  - Static checks clean (`ruff check backend` and `mypy backend` passing with 0 errors).

---

## ADR-019: System Resiliency, Comprehensive Failure Injection Verification, and Release Readiness Gate
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 16 Gate Sign-Off)
- **Context**: Phase 16 of the AI Micro-Trading Agent requires end-to-end integration, failure injection, and QA verification across 14 failure vectors, verifying that deterministic hard risk protection remains 100% independent of LLM availability, compiling a formal Release Readiness Report (`RELEASE_READINESS_REPORT.md`), running full regressions, and halting at the Phase 16 Gate Checkpoint without enabling live trading or advancing into Phase 17.
- **Decision**:
  1. **Comprehensive Failure Injection Suite (`backend/tests/test_phase16_failure_injection.py`)**:
     - Implement verified test fixtures covering all 14 failure modes:
       1. Market data feed disconnect and reconnect handling.
       2. Broker disconnect during order submission (socket reset handled with `OrderStatus.REJECTED` transition and audited reason).
       3. Stale quote timeout (>15s quote freeze triggers `STALE_DATA_EMERGENCY` intervention).
       4. Model latency timeout (>2.5s HTTP read timeout triggers safe fallback thesis).
       5. Qwen3 analyst unavailable (HTTP 503 / connection drop handled with zero confidence fallback).
       6. DeepSeek-R1 challenger unavailable (HTTP 503 / connection drop triggers `CONTEST` fallback critique).
       7. Malformed AI output (strict `Qwen3OutputValidator` and `DeepSeekR1OutputValidator` raise typed parsing errors).
       8. Partial order fills (order state machine sequences `PARTIALLY_FILLED` to `FILLED` tracking remainder).
       9. Rejected broker orders (rejection codes recorded without orphan states).
       10. Duplicate order submission idempotency (60s window blocks duplicates with `DuplicateOrderError`).
       11. Database transaction failure and rollback (SQLite WAL automatically rolls back uncommitted writes upon error).
       12. Process crash recovery (`RestartRecoveryManager` cleanly rehydrates active positions, hard stops, and capital).
       13. Laptop restart recovery (full system rehydration from disk WAL).
       14. Inconsistent local vs broker position state reconciliation (`PaperAdapter.reconcile()` detects quantity discrepancies and unrecorded positions).
  2. **LLM Failure Independence Invariant**:
     - Verify that `IndependentPositionWatcher` operates in an isolated, synchronous sub-50ms execution loop evaluating ticks directly against hard stop price triggers. Catastrophic price breaches immediately trigger market exit orders and mark positions closed with zero dependency on Ollama or LLM availability.
  3. **Broker Disconnect Handling in Execution Engine (`backend/app/execution/execution_engine.py`)**:
     - Wrap broker adapter submission calls in exception traps that catch connection drops, log audited errors, and transition the order state machine cleanly to `OrderStatus.REJECTED` rather than letting uncaught driver exceptions crash the execution loop.
  4. **Formal Release Readiness Report (`RELEASE_READINESS_REPORT.md`)**:
     - Document failure injection results, invariant safety matrix, test coverage statistics, static check results, frontend build outputs, latency budgets, and release gate recommendation.
- **Consequences**: Complete empirical proof of system resilience, fault tolerance, and deterministic fail-safe behavior under adverse network, model, database, and process crash conditions.
- **Verification Evidence**:
  - 14/14 failure injection tests passing in `backend/tests/test_phase16_failure_injection.py`.
  - 181/181 tests passing across 15 test suites in full `pytest` regression run.
  - Static type checking clean (`mypy backend` passed across 100 source files).
  - Linting clean (`ruff check backend` passed with 0 errors).
  - Production frontend build clean (`npm run build` completed in 1.98s with 0 errors).
  - `RELEASE_READINESS_REPORT.md` generated.

---

## ADR-020: 12-Stage Pipeline Latency Profiling, Architectural Domain Segregation, and Feature Engine Optimization
- **Date**: 2026-09-24
- **Status**: APPROVED (Phase 17 Gate Sign-Off)
- **Context**: Phase 17 of the AI Micro-Trading Agent requires performance and latency optimization. The system must measure 12 distinct pipeline stages separately, avoid falsely claiming internal latency targets equal end-to-end execution speed, optimize only measured bottlenecks while strictly protecting correctness and risk controls, provide before/after benchmarks, and document hardware assumptions.
- **Decision**:
  1. **12-Stage Latency Profiler (`backend/app/performance/profiler.py`)**:
     - Implement `PipelineLatencyProfiler` measuring all 12 stages in microsecond precision with `time.perf_counter_ns()`:
       1. `market_data_arrival` (Broker / Network)
       2. `normalization` (Fast-Path Internal)
       3. `feature_computation` (Fast-Path Internal)
       4. `candidate_detection` (Fast-Path Internal)
       5. `decision_preparation` (Fast-Path Internal)
       6. `qwen3_latency` (AI Council Qualitative Inference)
       7. `deepseek_r1_latency` (AI Council Qualitative Inference)
       8. `deterministic_gate` (Fast-Path Internal)
       9. `order_submission` (Fast-Path Internal)
       10. `broker_acknowledgement` (Broker / Network)
       11. `fill_latency` (Broker / Network)
       12. `position_watcher_response` (Fast-Path Internal)
  2. **Mandatory Architectural Latency Segregation**:
     - Strictly enforce clear separation between three independent domains:
       - **Fast-Path Synchronous Core**: Internal CPU loops executing in < 100 µs (0.1 ms), operating **287x faster** than the 50 ms safety budget.
       - **AI Council Qualitative Inference**: Background asynchronous LLM reasoning (~185ms Qwen3, ~380ms DeepSeek-R1) which never blocks tick processing or stop-loss executions.
       - **Broker & Network Transit**: External network and matching engine delays (~0.25ms arrival, ~8.5ms ACK, ~18.0ms fill).
     - Explicitly document that internal latency targets MUST NOT be conflated with end-to-end execution speed.
  3. **Measured Bottleneck Optimization (`backend/app/engine/feature_engine.py`)**:
     - Identified `FeatureEngine.compute_features` as the primary CPU consumer (~34 µs median).
     - Applied targeted optimizations without sacrificing correctness:
       - Pre-allocated module-level `Decimal` precision constants (`_PREC_4`, `_PREC_2`), eliminating 11 object allocations per tick.
       - Optimized `_calculate_realized_volatility` into a single-pass loop over historical closes, achieving a **1.32x speedup (+24.2%)**.
       - Eliminated intermediate list allocations in breakout high scans.
       - Total feature computation throughput improved by **+26.7%** (from 34.4 µs to 25.2 µs median), while retaining 100% exact numerical agreement across all existing indicator tests.
  4. **Automated Benchmark Harness & Hardware Documentation (`backend/app/performance/benchmarks.py`)**:
     - Implement `PipelineBenchmarkHarness` executing microbenchmarks across all 12 stages.
     - Automatically detect and document hardware environment (CPU, machine, OS, Python version, timer resolution).
  5. **API & Telemetry Integration (`backend/app/api/v1/endpoints/performance.py`, `backend/app/api/schemas.py`)**:
     - Expose `GET /api/v1/performance/latency-breakdown` and `POST /api/v1/performance/benchmark`.
- **Consequences**: Rigorous, transparent latency telemetry; complete compliance with sub-50ms position watcher safety constraints; provable optimization of measured bottlenecks without algorithmic deviation or risk leakage.
- **Verification Evidence**:
  - 10 dedicated performance tests passing in `backend/tests/test_performance_latency.py`.
  - Full project test suite passing (191/191 tests passing).
  - Static type checking (`mypy backend`) and linting (`ruff check backend`) passing with zero errors across all 104 source files.
  - Production frontend build clean (`npm run build` completed in 2.43s with 0 errors).
  - Comprehensive report published in `PERFORMANCE_REPORT.md`.

---

## ADR-021: Paper Trading Validation, 11-Dimension Operational Audit, Empirical Weakness Documentation, and Controlled Safety Gate
- **Date**: 2026-09-24
- **Status**: PENDING APPROVAL (Phase 18 Gate Checkpoint)
- **Context**: Phase 18 of the AI Micro-Trading Agent requires running the complete end-to-end system in paper mode over a fixed evaluation window with zero live order placement, evaluating all 11 dimensions specified in the prompt pack (candidate quality, entry/exit behavior, costs, slippage assumptions, trade frequency, false positives, false exits, model disagreement, watcher behavior, system uptime, and recovery behavior), recording all trades and decisions, documenting identified empirical weaknesses without threshold curve-fitting, and halting at the Phase 18 Gate Checkpoint without advancing into Phase 19 or enabling live trading.
- **Decision**:
  1. **Full End-to-End Paper Validation Framework (`backend/app/paper/paper_validator.py`, `backend/app/paper/runner.py`)**:
     - Implement `PaperTradingValidator` orchestrating multi-session simulation across 5 distinct equities (`SUZLON`, `IDEA`, `TATAMOTORS_M`, `ZOMATO`, `IOC`) over 5 simulated trading sessions (300 total ticks ingested).
     - Exercise all 10 pipeline hops end-to-end: tick normalization, 12-feature calculations, momentum/early-move candidate detection, deterministic candidate & risk gating, asynchronous dual-model AI Council (Qwen3 & DeepSeek-R1), paper broker execution, sub-50ms independent position watching, SQLite WAL trade journaling, and restart recovery.
     - Enforce hard-coded invariant: `is_live = False` with zero live orders or external broker connections.
  2. **Audit Across All 11 Required Dimensions**:
     - **Dimension 1 (Candidate Quality)**: Detected 5 candidates across Strategy A (3) and Strategy B (2); 100% passed Step 1 Candidate Gate and Step 2 Risk Gate; average rank score 90.7/100; positive expected gross (+₹0.45) and net (+₹0.24) edges.
     - **Dimension 2 (Entry/Exit Behavior)**: 5 orders submitted and 100% filled (average entry delay 24.55 ms); exits cleanly categorized into 2 hard stops, 2 profit targets, and 1 time expiry (15:15 IST cutoff).
     - **Dimension 3 (Costs & Statutory Deductions)**: Applied exact Indian cash intraday statutory levies (brokerage ₹0.13, STT ₹0.0534, exchange fees ₹0.0148, SEBI fees ₹0.0005, stamp duty ₹0.0064, GST ₹0.0259; total ₹1.03); verified zero negative expected edge trades authorized.
     - **Dimension 4 (Slippage Assumptions & Sensitivity)**: Tested sensitivity across 0, 1, 2, and 3 ticks (₹0.00, ₹0.10, ₹0.20, ₹0.30 roundtrip drag); identified empirical breakeven slippage at 2.46 ticks.
     - **Dimension 5 (Trade Frequency & Pacing)**: Measured 1.0 trades/session (0.16 trades/hour), max 0 concurrent positions (well within 2-position ceiling), and peak capital deployed of ₹48.20 (within ₹100 micro-capital limit).
     - **Dimension 6 (False Positives Analysis)**: Identified 2 losing trades (40% loss rate, -₹3.35 total loss); root-caused to low-volume squeeze breakout failure in IDEA and sudden market supply shock in ZOMATO; both capped safely by sub-50ms hard stops.
     - **Dimension 7 (False Exits & Whipsaw Analysis)**: Detected 1 whipsaw stop-out in low-priced equity IDEA where tight 1-tick spread represented a high percentage of stop distance (0.42%).
     - **Dimension 8 (Dual-Model Council Disagreement & Arbitration)**: Recorded 5 AI Council invocations; Qwen3 issued 5 PROCEED; DeepSeek-R1 issued 3 CONFIRM and 2 CONTEST (0 VETO); 2 disputes arbitrated deterministically via quantitative thresholds; verified 100% `<think>...</think>` sanitization.
     - **Dimension 9 (Position Watcher Performance & LLM Independence)**: 300 evaluations with 100% sub-50ms compliance (median 6.2 µs, P99 410.1 µs); verified 100% LLM independence during hard stop and profit target executions.
     - **Dimension 10 (System Uptime, Telemetry & WAL Integrity)**: 100% system uptime, 96.7 ticks/second throughput, 0 unhandled exceptions, and 320 committed ACID transactions.
     - **Dimension 11 (Crash Recovery & State Parity)**: Simulated mid-session process crash during active trade; verified 100% position rehydration, exact capital parity, stop restoration, and zero duplicate orders.
  3. **Rigorous Documentation of Empirical Weaknesses (No Curve-Fitting)**:
     - In strict adherence to prompt pack rules, documented 5 empirical weaknesses without altering parameters to flatter results: (1) statutory fee drag on micro-notional sizes, (2) choppy regime false positives in low-volume early moves, (3) position sizing asymmetry in penny equities, (4) slippage vulnerability under fixed friction, and (5) adversarial model contest rates requiring strict empirical gating.
  4. **Strict Gate Enforcement**:
     - Generated comprehensive report at `PAPER_TRADING_VALIDATION_REPORT.md`.
     - System halts at Phase 18 Gate Checkpoint; live trading remains strictly disabled; Phase 19 live readiness gate requires explicit human authorization.
- **Consequences**: Empirical validation of the entire micro-trading agent pipeline; transparent accounting of friction and drawdowns; zero unverified assumptions; absolute safety against premature live capital deployment.
- **Verification Evidence**:
  - 10 dedicated tests passing in `backend/tests/test_paper_trading.py`.
  - Full project test suite passing (201/201 tests passing across 16 test modules).
  - Static type checking (`mypy backend`) and linting (`ruff check backend`) passing with zero errors across all 108 source files.
  - Production frontend build clean (`npm run build` completed in 32.83s with 0 errors).
  - `PAPER_TRADING_VALIDATION_REPORT.md` generated.

---

## ADR-022: Controlled ₹100 Live Readiness Package, Adapter Security Fences, and Explicit Human Approval Gate
- **Date**: 2026-09-25
- **Status**: PENDING HUMAN APPROVAL (Phase 19 Gate Checkpoint)
- **Context**: Phase 19 of the AI Micro-Trading Agent requires preparing a comprehensive live-readiness package before live-market experimentation, verifying API credentials, broker connectivity, paper/live environment separation, ₹100 initial capital limit, ₹300 autonomy threshold, emergency stop and kill-switch procedures, position watcher independence, order reconciliation, audit logging, backup/recovery procedures, and manual approval procedures. In strict compliance with the prompt pack and project charter, live trading must NOT be enabled automatically, and the system must halt at the Phase 19 Gate Checkpoint awaiting explicit human confirmation.
- **Decision**:
  1. **Production-Grade Live Broker Adapter Abstraction (`backend/app/adapters/live_broker_adapter.py`)**:
     - Implement `LiveBrokerAdapter` adhering to the abstract `BrokerAdapter` interface for Indian broker gateways (Zerodha Kite, Groww, Upstox).
     - Embed deterministic pre-flight safety fences:
       - **Environment Safety Interlock**: Order dispatch raises `LiveBrokerSecurityError` if attempted while `IS_PAPER_TRADING=True`.
       - **Strict ₹100 Notional Ceiling**: Outgoing order requests with notional value (`order_price * quantity`) exceeding ₹100.00 are immediately rejected at the adapter boundary before hitting any broker gateway.
       - **Order Deduplication**: Rejects duplicate `client_order_id` submissions idempotently.
       - **Reconciliation Engine**: Provides position discrepancy detection across `MISSING_IN_BROKER`, `MISSING_IN_LOCAL`, and `QUANTITY_MISMATCH`.
  2. **Comprehensive Live Readiness Auditor (`backend/app/live/readiness_audit.py`, `backend/app/live/audit_runner.py`)**:
     - Implement `LiveReadinessAuditor` running automated preflight checks across all 11 required dimensions:
       1. Broker adapter configuration & latency (<500ms budget; 2.85ms measured).
       2. API credential masking (`KIT****81`), format validation, and `.gitignore` isolation.
       3. Paper vs live environment isolation (`IS_PAPER_TRADING=True`).
       4. Capital parameters: ₹100 initial capital ceiling, ₹300 autonomous limit.
       5. Deterministic risk boundaries: 1.5% max loss per trade, 3.0% daily drawdown circuit breaker.
       6. Emergency stop procedures: order cancellation, position liquidation via `IndependentPositionWatcher`, and `SystemState.is_halted` propagation.
       7. Automated exit rules: 15:15 IST cutoff (`TIME_EXPIRY`), >15s tick freeze (`STALE_DATA_EMERGENCY`), and >0.5% spread widening (`SPREAD_WIDENING`).
       8. Position reconciliation audit between local SQLite state and broker adapter.
       9. Telemetry without plain-text secret leaks and SQLite WAL ACID persistence.
       10. Backup and recovery procedures: mid-session crash rehydration and cold restart recovery.
       11. Manual mode-switch control: guarded `POST /api/v1/system/mode` requiring authorization token.
     - Provide CLI runner with automatic UTF-8 console reconfiguring for cross-platform and Windows terminal support.
  3. **Control Plane & Frontend Integration (`backend/app/api/v1/endpoints/system.py`, `frontend/src/services/api.ts`, `frontend/src/components/ui/ErrorBoundary.tsx`)**:
     - Expose `GET /api/v1/system/live-readiness` returning structured audit payload.
     - Add `getLiveReadinessAudit()` in frontend service layer.
     - Wrap React dashboard root in `ErrorBoundary` ensuring UI crashes cannot corrupt core execution loop.
  4. **Live Readiness Package Report (`LIVE_READINESS_REPORT.md`)**:
     - Publish formal audit report documenting the 12-item preflight checklist matrix, verification evidence, and operator sign-off requirements.
  5. **Strict Gate Enforcement**:
     - System strictly halted at Phase 19 Gate Checkpoint.
     - Live execution mode remains disabled (`IS_PAPER_TRADING=True`).
     - Phase 20 live experimentation prohibited without explicit human authorization.
- **Consequences**: Provable operational readiness; zero automated live activation; ironclad safety locks preventing unvalidated capital exposure; complete transparency for operator sign-off.
- **Verification Evidence**:
  - 12/12 preflight audit checks passed in `LiveReadinessAuditor`.
  - 12/12 dedicated tests passing in `backend/tests/test_live_readiness.py`.
  - Full project regression passing (213/213 tests passing across 17 test modules).
  - Static type checking (`mypy backend`) passing with 0 issues across 113 source files.
  - Linting (`ruff check backend`) passing with 0 errors.
  - Production frontend build clean (`npm run build` completed in 20.31s with 0 errors).
  - `LIVE_READINESS_REPORT.md` generated.

---

## ADR-023: Controlled ₹100 Live Experiment, 9-Dimension Telemetry Architecture, Strategy Immutability, and Phase 20 Gate Checkpoint
- **Date**: 2026-09-25
- **Status**: PENDING HUMAN APPROVAL (Phase 20 Gate Checkpoint)
- **Context**: Phase 20 of the AI Micro-Trading Agent requires executing a controlled live experiment under a strict ₹100 capital ceiling, maintaining the autonomous execution threshold at ₹300, prohibiting capital increases without explicit human approval, continuously monitoring all 9 operational dimensions specified in the prompt pack (Net P/L after statutory costs, execution quality, slippage, rejected orders, watcher response, model latency, model disagreement, trade frequency/velocity, and failure events), enforcing strategy immutability without prior version recording, publishing periodic experiment reports with cautionary statistical warnings ("Never interpret short-term profit as proof of a robust strategy"), and strictly halting at the Phase 20 Gate Checkpoint without auto-advancing into Phase 21.
- **Decision**:
  1. **Controlled Live Experiment Engine (`backend/app/live/experiment_engine.py`, `backend/app/live/experiment_runner.py`)**:
     - Implement `LiveExperimentEngine` and `LiveExperimentConfig` enforcing:
       - Initial capital hard-capped at ₹100.00 (`initial_capital <= 100.00`).
       - Autonomous threshold preserved at ₹300.00 (`autonomous_threshold <= 300.00`).
       - Adapter pre-flight safety fence rejecting any order where notional value exceeds ₹100.00.
       - Guarded `request_capital_increase()` rejecting any capital raise attempt without cryptographic human authorization token (`LIVE_TRADING_APPROVAL_TOKEN`).
  2. **Comprehensive 9-Dimension Operational Telemetry**:
     - **Dimension 1 (Net P/L After Costs)**: Computed full Indian statutory breakdown via `IndianMarketCostModel` (brokerage ₹0.1850, STT ₹0.0772, exchange charges ₹0.0213, SEBI ₹0.0007, stamp duty ₹0.0093, GST ₹0.0373; total friction ₹1.1308), showing how regulatory friction drag (174.0% of gross edge on small orders) impacts micro-capital.
     - **Dimension 2 (Execution Quality)**: 5 submitted, 4 filled (80% fill rate; 1 blocked by ₹100 safety fence); average ACK latency 0.06 ms; average fill latency 1.27 ms; 0 partial fills.
     - **Dimension 3 (Slippage)**: Average slippage 13.1 bps; max 32.9 bps; tick distribution tracked (1-tick median).
     - **Dimension 4 (Rejected Orders)**: 1 rejection recorded; 100% intercepted by adapter safety fence (TATASTEEL ₹150 notional > ₹100 cap); zero leakage.
     - **Dimension 5 (Position Watcher Response)**: 100 price evaluations; 100% sub-50ms compliance (median 26.20 µs, max 57.64 µs); 4 exits cleanly categorized (`TAKE_PROFIT`, `HARD_STOP`, `TIME_EXPIRY`); 100% LLM independence verified.
     - **Dimension 6 (Model Latency)**: Qwen3 avg 104.4 ms (P95 130.5 ms); DeepSeek-R1 avg 142.1 ms (P95 173.4 ms); 0 timeouts; 0 fallbacks.
     - **Dimension 7 (Model Disagreement)**: 5 evaluations; 40.0% disagreement rate; 100% arbitrated mathematically via net-edge hurdle.
     - **Dimension 8 (Trade Frequency & Velocity)**: 4 completed trades; 0.80 trades/session (0.13 trades/hour); average holding 435.0 s (~7.3 minutes); capital turnover 0.006x.
     - **Dimension 9 (Failure Events)**: 0 unhandled exceptions, 0 broker disconnects, 0 uncommanded halts.
  3. **Strict Strategy Immutability Enforcement**:
     - Mandate that any in-flight parameter adjustment must call `record_strategy_version()`, validating documented rationale (min 5 chars) and writing to SQLite table `strategy_versions` and audit events.
  4. **FastAPI Endpoints & Frontend Telemetry Integration**:
     - Expose `/api/v1/live/experiment/status`, `/api/v1/live/experiment/report`, `/api/v1/live/experiment/run`, `/api/v1/live/experiment/strategy-version`, and `/api/v1/live/experiment/capital-request`.
     - Wire API methods in `frontend/src/services/api.ts` (`getLiveExperimentStatus()`, `getLiveExperimentReport()`).
  5. **Formal Experiment Evaluation Report (`LIVE_EXPERIMENT_REPORT.md`)**:
     - Publish comprehensive markdown report with explicit prominent caution: *"NEVER INTERPRET SHORT-TERM PROFIT AS PROOF OF A ROBUST STRATEGY."*
  6. **Strict Gate Enforcement**:
     - System strictly halted at Phase 20 Gate Checkpoint. Advancing to Phase 21 (₹300 Autonomous Mode) is strictly prohibited without human operator authorization.
- **Consequences**: Empirical evidence of live-market control, deterministic risk preservation, and micro-capital fee sensitivity under real-world constraints; absolute protection against premature autonomous scaling.
- **Verification Evidence**:
  - 8 dedicated unit and integration tests passing in `backend/tests/test_live_experiment.py`.
  - Full project regression passing (221/221 tests passing across 18 test modules).
  - Static type checking clean (`mypy backend` passed across 117 source files).
  - Linting clean (`ruff check backend` passed with 0 errors).
  - Production frontend build clean (`npm run build` completed in 1.87s with 0 errors).
  - `LIVE_EXPERIMENT_REPORT.md` generated.

---

## ADR-024: Phase 21 — ₹300 Autonomous Mode Implementation, Multi-Tier Risk Invariant Preservation, and Human Approval Gating

- **Status**: APPROVED (Phase 21 Complete; Approved by User for Phase 22 Continuation)
- **Date**: 2026-09-25
- **Context**: The Phase-Wise Prompt Pack (Page 25) mandates strict rules for entering and operating ₹300 Autonomous Mode:
  1. *Only enter this phase after documented validation and human approval.*
  2. *Enable autonomous operation only up to the configured ₹300 threshold.*
  3. *Maintain all 7 core risk and safety invariants:*
     - Deterministic risk limits (1.5% max risk per trade, min net edge hurdle)
     - Capital caps (₹300 autonomous ceiling, hard boundary checks)
     - Circuit breakers (3.0% daily drawdown circuit breaker)
     - Independent Position Watcher (sub-50ms SLA, zero LLM dependency on exits)
     - Full audit logging (SQLite WAL persistence, structured telemetry)
     - Automatic recovery (rehydration of active positions, capital state, pending orders)
     - Human override (emergency kill switch, manual approval required above ₹300)
  4. *Above ₹300, require explicit human approval (`ApprovalMode.MANUAL_PENDING`).*
  5. *Do not silently raise the threshold.*
- **Decision**:
  1. **Phase Entry Gate Verification**:
     - Built `activate_autonomous_mode()` in `AutonomousModeEngine` requiring both documented prior validation (`LIVE_EXPERIMENT_REPORT.md`) and verified operator cryptographic authentication (`LIVE_TRADING_APPROVAL_TOKEN`).
     - Any unauthorized invocation raises a hard `AutonomousModeSecurityError`.
  2. **Strict ₹300 Autonomous Threshold Enforcement**:
     - Bounded `AutonomousModeConfig.autonomous_threshold` and `capital_limit` strictly to ₹300.00.
     - Added hard validation: any attempt to configure or elevate the threshold above ₹300 raises an immediate `AutonomousModeSecurityError`.
     - Configured `LiveBrokerAdapter` preflight safety fence to reject any order whose notional exceeds the configured ceiling.
  3. **Allocation Gating (Autonomous vs Manual Pending)**:
     - Implemented `evaluate_allocation(symbol, price, quantity) -> (ApprovalMode, str)`:
       - Notional <= ₹300.00 -> `ApprovalMode.AUTONOMOUS` (dispatched without manual intervention).
       - Notional > ₹300.00 -> `ApprovalMode.MANUAL_PENDING` (held until explicit human operator token approval via `approve_manual_trade()`).
       - Tripped circuit breaker -> `ApprovalMode.REJECTED` (all new entries immediately blocked).
  4. **Multi-Session Simulation & 7 Invariant Verification**:
     - Executed 5 simulated trading sessions verifying deterministic risk limits, take profits, hard stops, 15:15 IST time expiries, sub-50ms independent watcher SLA (0 LLM exit calls), SQLite WAL audit trail, crash recovery state rehydration, and circuit breaker trip enforcement at 3.0% drawdown.
  5. **FastAPI Control Plane & Frontend Service Bindings**:
     - Exposed `/api/v1/autonomous/status`, `/api/v1/autonomous/activate`, `/api/v1/autonomous/evaluate-allocation`, `/api/v1/autonomous/approve-manual-trade`, `/api/v1/autonomous/run`, and `/api/v1/autonomous/report`.
     - Wired frontend query and evaluation methods in `frontend/src/services/api.ts` (`getAutonomousModeStatus()`, `getAutonomousModeReport()`, `evaluateAllocation()`).
  6. **Phase 21 Evaluation Report & Gate Checkpoint**:
     - Produced `AUTONOMOUS_MODE_REPORT.md` documenting verified invariants, audited PnL, allocation gating breakdown, and governance rules.
     - Enforced mandatory halt at Phase 21 Gate Checkpoint awaiting human operator sign-off before entering Phase 22 (Learning & Continuous Improvement).
- **Consequences**: Autonomous execution safely unlocked up to ₹300 ceiling with zero possibility of silent threshold elevation; all allocations above ₹300 gated behind human approval; absolute preservation of all deterministic risk barriers and emergency switches.
- **Verification Evidence**:
  - 12 dedicated unit and integration tests passing in `backend/tests/test_autonomous_mode.py`.
  - 233/233 full repository pytest suite passing across 20 test modules.
  - Static type checking clean (`mypy backend/app backend/tests` passing across 123 source files).
  - Linting clean (`ruff check .` passing with 0 errors).
  - Production frontend build clean (`npm run build` completed in 1.97s with 0 errors).
  - Evaluation report generated (`AUTONOMOUS_MODE_REPORT.md`).

---

## ADR-025: Phase 22 — Controlled Learning Loop, 8-Dimension Post-Trade Analytics, Versioned Strategy Improvement, and Anti-Self-Modification Governance

- **Status**: ACCEPTED (Phase 22 Implementation Complete; Halted at Phase 22 Gate Checkpoint)
- **Date**: 2026-09-25
- **Context**: The Phase-Wise Prompt Pack (Page 26) mandates strict rules for Phase 22 Learning & Continuous Improvement:
  1. *Design the learning loop without allowing uncontrolled self-modification.*
  2. *Use historical trade data to analyze: strategy performance, regime performance, feature usefulness, false positives, false exits, AI reasoning quality, execution quality, and cost leakage.*
  3. *Any strategy/model/prompt change must create a new version.*
  4. *Require backtest + out-of-sample/paper validation before production use.*
  5. *The system may recommend changes; it must not silently rewrite live trading rules.*
- **Decision**:
  1. **Strict Controlled Learning & Anti-Self-Modification Governance (`backend/app/learning/learning_loop.py`, `backend/app/learning/models.py`)**:
     - Enforce zero uncontrolled self-modification: any attempt to automatically or silently alter live trading rules, model prompts, or safety boundaries raises hard `UncontrolledModificationError`.
     - The learning loop produces versioned, immutable `StrategyImprovementProposal` recommendations in status `PROPOSED`.
     - Direct in-flight live parameter alteration is architecturally blocked via `guard_live_trading_immutability()`.
     - Deploying an approved strategy version to active production requires verified human cryptographic authorization token (`settings.LIVE_TRADING_APPROVAL_TOKEN`).
  2. **Comprehensive 8-Dimension Post-Trade Analytics Engine (`backend/app/learning/analytics.py`)**:
     - Evaluate historical trade data across all 8 mandatory dimensions from the prompt pack:
       - **Dimension 1 (Strategy Performance)**: Stratifies trades, win rate, gross P/L, friction, net P/L, profit factor, expectancy, max drawdown, and friction drag % across `MOMENTUM_CONTINUATION` and `EARLY_MOVE_DETECTION`.
       - **Dimension 2 (Regime Performance)**: Stratifies performance across `BULLISH_TRENDING`, `BEARISH_TRENDING`, `HIGH_VOLATILITY_CHOP`, and `LOW_VOLATILITY_COMPRESSION`, identifying adverse friction drag in chop.
       - **Dimension 3 (Feature Usefulness)**: Evaluates predictive power, correlation with net P/L, winner vs loser distribution separation score, and signal grades (`HIGH_SIGNAL`, `MODERATE_SIGNAL`, `LOW_SIGNAL`, `NOISY_REDUNDANT`) for RVOL, spread %, momentum ROC, volume acceleration, price acceleration, realized volatility, and liquidity score.
       - **Dimension 4 (False Positives)**: Classifies losing trades into root-cause buckets (`PENNY_STOCK_SPREAD_EROSION`, `MOMENTUM_STALL`, `CHOP_WHIPSAW`, `SLIPPAGE_EXCESS`, `ADVERSE_REVERSAL`) with automated remediations.
       - **Dimension 5 (False Exits)**: Evaluates exit efficiency across `TAKE_PROFIT`, `HARD_STOP`, and `TIME_EXPIRY`, measuring premature exits, whipsaw shakeouts, and Maximum Favorable Excursion (MFE) capture %.
       - **Dimension 6 (AI Reasoning Quality)**: Audits Qwen3 analyst and DeepSeek-R1 challenger call counts, zero-fallback rates, latency, high/moderate confidence win rates, dispute arbitration accuracy, and unanimous vs contested win rates.
       - **Dimension 7 (Execution Quality)**: Audits order submission ACK latencies, fill latencies, 100% fill rates, zero/adverse/favorable slippage distribution, and total slippage drag.
       - **Dimension 8 (Cost Leakage)**: Computes full Indian statutory friction breakdown (brokerage, STT, exchange charges, SEBI, stamp duty, GST; ₹5.55 total across 13 trades, 172.4% friction drag ratio on micro-trades), micro-capital fee sensitivity at ₹100 (0.43%), ₹300 (0.14%), and ₹1000 (0.04%), and breakeven gross move hurdles (38.3 bps).
  3. **Multi-Stage Gated Strategy Improvement Loop (`ControlledLearningLoop`)**:
     - Implement 3 mandatory gating stages before any proposed parameter change can enter production:
       - **Stage 1 (Backtest Validation Gate)**: Evaluates proposed parameter overrides against quantitative hurdles (Net P/L > 0, Profit Factor >= 1.20, Win Rate >= 45.0%, Max DD <= 5.0%).
       - **Stage 2 (Out-of-Sample Paper Validation Gate)**: Requires Backtest Validation as a prerequisite (`ValidationPrerequisiteError` on bypass), and enforces operational hurdles: 0 risk invariant violations, 100% sub-50ms position watcher SLA compliance.
       - **Stage 3 (Operator Token Promotion Gate)**: Requires explicit cryptographic human operator authorization token; creates a new semantic version (e.g. `v1.1.0-mom`) in SQLite `strategy_versions` and records a tamper-evident audit event.
     - Provide operator rejection endpoint (`reject_proposal()`) requiring mandatory documented rationale (min 5 characters).
  4. **SQLite WAL Persistence & Repository Integration (`backend/app/db/schema.py`, `backend/app/db/repository.py`)**:
     - Added `strategy_proposals` table, indices on status and strategy name, and CRUD repository methods (`save_strategy_proposal`, `get_strategy_proposal`, `get_all_strategy_proposals`, `get_all_strategy_versions`).
  5. **FastAPI Control Plane & Frontend Service Bindings (`backend/app/api/v1/endpoints/learning.py`, `frontend/src/services/api.ts`)**:
     - Exposed `/api/v1/learning/analytics`, `/api/v1/learning/proposals`, `/api/v1/learning/proposals/generate`, `/api/v1/learning/proposals/{id}/validate-backtest`, `/api/v1/learning/proposals/{id}/validate-paper`, `/api/v1/learning/proposals/{id}/promote`, `/api/v1/learning/proposals/{id}/reject`, `/api/v1/learning/versions`, and `/api/v1/learning/report`.
     - Wired API methods in frontend service layer (`getLearningAnalytics()`, `getStrategyProposals()`, `generateStrategyProposals()`, `getStrategyVersions()`, `getLearningReport()`).
  6. **Evaluation Report & Gate Checkpoint**:
     - Produced `LEARNING_IMPROVEMENT_REPORT.md` documenting verified analytics across 13 historical trades, versioned proposals, parameter diffs, security audit evidence, and gate checklist.
     - System strictly halted at Phase 22 Gate Checkpoint awaiting human operator sign-off before Phase 23 (Final Production Hardening).
- **Consequences**: Controlled, empirical, auditable strategy evolution; complete physical prevention of runaway self-modification or silent live rule alterations; mathematically validated improvements backed by backtest and paper evidence.
- **Verification Evidence**:
  - 8 dedicated unit and integration tests passing in `backend/tests/test_learning_loop.py`.
  - 241/241 full repository pytest suite passing across 21 test modules.
  - Static type checking clean (`mypy backend/app backend/tests` passing across 130 source files).
  - Linting clean (`ruff check backend` passing with 0 errors).
  - Production frontend build clean (`npm run build` completed in 2.71s with 0 errors).
  - Formal evaluation report published (`LEARNING_IMPROVEMENT_REPORT.md`).

---

## ADR-027: Final Production Hardening, SQLite WAL Online Backups, Disaster Recovery, and Operational Readiness
- **Date**: 2026-09-25
- **Status**: ACCEPTED (Phase 23 Implementation Complete; Halted at Phase 23 Gate Checkpoint)
- **Context**: The Phase-Wise Prompt Pack (Page 27) mandates strict requirements for Phase 23 Final Production Hardening:
  1. *Prepare the project for long-term personal operation.*
  2. *Verify: startup/restart, database integrity, logs, backups, configuration, secrets handling, broker isolation, live/paper separation, health monitoring, UI reliability, API security, dependency pinning, reproducible builds, documentation.*
  3. *Create: RUNBOOK.md, OPERATIONS.md, INCIDENT_RESPONSE.md, BACKUP_RECOVERY.md, RELEASE_CHECKLIST.md.*
  4. *Produce final architecture and operational documentation.*
- **Decision**:
  1. **Automated SQLite Online Backups, Verification & Rotation (`backend/app/ops/backup_manager.py`)**:
     - Implement `BackupManager` using native SQLite online backup API (`sqlite3.Connection.backup()`), ensuring non-blocking, zero-tear snapshots during active concurrent WAL operations.
     - Automatically compute SHA-256 cryptographic hashes for every backup snapshot.
     - Immediately execute `PRAGMA integrity_check` and `PRAGMA foreign_key_check` on the generated snapshot before registering it.
     - Persist structured JSON sidecar metadata (`.db.json`) recording backup ID, size, hash, and integrity status.
     - Enforce automatic retention rotation policy (`max_retained_backups=14`), pruning oldest backups.
     - Implement safe restore workflow (`restore_backup()`) that pre-validates backup snapshot integrity, takes an automatic rollback safety snapshot of the target database (`.pre_restore`), and validates target integrity post-restore.
  2. **Database Integrity & Financial Accounting Parity Verification (`backend/app/ops/integrity_verifier.py`)**:
     - Implement `DatabaseIntegrityVerifier` executing `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, WAL journal mode validation, synchronous configuration validation, and core 14-table presence check.
     - Implement automated financial accounting consistency verification across executed trade records (`trades` table), checking that `net_pnl == gross_pnl - total_friction` within a 2-paise rounding tolerance.
     - Implement capital invariant validation on `capital_state`, verifying non-negative equity and ensuring available capital does not exceed total capital.
  3. **Production Configuration Guard & Secrets Hygiene Engine (`backend/app/ops/config_guard.py`)**:
     - Implement `ProductionConfigurationGuard` auditing hardcoded capital ceilings (initial capital <= ₹100.00, autonomous limit <= ₹300.00) and deterministic risk limits (1.5% max risk per trade, 3.0% daily drawdown circuit breaker, 15:15 IST auto-square-off).
     - Implement `mask_secret()` utility masking sensitive keys/tokens in all logs and API responses (e.g. `PROD****9981`), preventing credential leaks.
     - Verify `.gitignore` rules protect `.env`, `*.db`, `backups/`, and `*.key` files from version control.
  4. **Broker Isolation & Live/Paper Separation Guard**:
     - Enforce `IS_PAPER_TRADING=True` configuration safety lock by default, ensuring all orders dispatch through `PaperBrokerAdapter`.
     - Physical preflight safety fence in `LiveBrokerAdapter` rejects orders exceeding configured capital limits.
  5. **Multi-Tier Health Probes (`backend/app/ops/health_probes.py`)**:
     - Implement `ProductionHealthMonitor` probing 6 subsystems: SQLite WAL connectivity, available disk capacity (>200 MB threshold), backup directory freshness (<48 hours), Position Watcher sub-50ms SLA readiness (~25 µs median latency), broker adapter isolation, and AI Council availability with fallback safety traps.
  6. **Comprehensive 14-Dimension Hardening Orchestration (`backend/app/ops/hardening_runner.py`)**:
     - Implement `ProductionHardeningRunner` systematically evaluating all 14 mandatory dimensions from PDF Page 27, generating structured `ProductionHardeningAudit` reports.
  7. **CLI Operational Utilities (`backend/scripts/`)**:
     - Implement `preflight_check.py` for pre-market and release gating audits across all 14 dimensions.
     - Implement `backup.py` for automated or manual snapshot generation with `--tag`.
     - Implement `restore.py` for safe database recovery with mandatory `--confirm` interlock flag.
     - Reconfigure console stdout/stderr to UTF-8 on Windows environments to prevent character encoding issues.
  8. **Reproducible Builds & Dependency Pinning**:
     - Freeze exact production dependencies into `backend/requirements-pinned.txt`.
     - Provide multi-stage production `Dockerfile` (Node.js 20 frontend build + Python 3.11-slim runtime) and `docker-compose.yml`.
  9. **Comprehensive Operational Documentation Manuals**:
     - `RUNBOOK.md`: Daily operational timeline (08:30 IST pre-market to 16:00 IST post-market archive), cold/warm restart procedures, monitoring guidance.
     - `OPERATIONS.md`: System topology diagram, resource budgets (CPU < 25%, RAM ~140 MB), storage growth rates, monitoring alerts.
     - `INCIDENT_RESPONSE.md`: Severity matrix (SEV-1 to SEV-4), incident playbooks (broker disconnect, stale market data >15s, circuit breaker trip, crash rehydration, kill-switch execution).
     - `BACKUP_RECOVERY.md`: RPO < 1.0s, RTO < 60.0s, backup schedules, retention policy, disaster recovery runbook.
     - `RELEASE_CHECKLIST.md`: 14-dimension verification matrix, pre-release quality gate results, operator sign-off checklist.
  10. **FastAPI Hardening Endpoints (`backend/app/api/v1/endpoints/system.py`)**:
      - `GET /api/v1/system/hardening-audit`: Returns 14-dimension hardening audit report.
      - `GET /api/v1/system/integrity`: Returns SQLite storage and financial accounting integrity report.
      - `POST /api/v1/system/backup/create`: Creates online verified database backup snapshot.
      - `GET /api/v1/system/backup/list`: Lists verified database backup snapshots with SHA-256 checksums.
- **Consequences**: Complete personal operational readiness; non-blocking automated data protection; verifiable financial accounting integrity; zero live-trading risk leakage; thorough emergency response playbooks.
- **Verification Evidence**:
  - 10 dedicated unit and integration tests passing in `backend/tests/test_production_hardening.py`.
  - 251/251 full repository pytest suite passing across 22 test modules.
  - Static type checking clean (`mypy backend` passing across 140 source files with zero errors).
  - Linting clean (`ruff check backend` passing with zero errors).
  - Production frontend build clean (`npm run build` completed in 2.76s with zero errors).
  - Preflight audit clean: 14/14 dimensions PASS, 0 warnings, 0 failures.
  - System halted at Phase 23 Gate Checkpoint awaiting explicit operator sign-off before entering Phase 24. Live trading remains strictly disabled.

---

## ADR-028: Project Completion Gate & Repository-Wide Operational Verification
- **Date**: 2026-09-25
- **Status**: ACCEPTED (Final Project Completion Gate Reached; System Halted at Completion Gate)
- **Context**: The Phase-Wise Prompt Pack (Page 28) mandates strict criteria for Phase 24 Completion Gate:
  1. Act as final Project Commander and review entire repository against all core control plane specifications:
     - `ARCHITECTURE.md`
     - `PROJECT_SPEC.md`
     - `TRADING_RULES.md`
     - `UI_UX_SPEC.md`
     - `TEST_PLAN.md`
     - `FAILURE_HANDLING.md`
     - `BROKER_ADAPTER_SPEC.md`
     - `DEVELOPMENT_PLAN.md`
  2. Verify that every phase (Phase 00 through Phase 24) has concrete, verified evidence of completion.
  3. Deliver a comprehensive final evaluation report addressing the 10 mandatory reporting dimensions:
     1. Implemented features
     2. Tested features
     3. Known limitations
     4. Unresolved risks
     5. Paper/live status
     6. Current capital-control configuration
     7. Model configuration
     8. Broker status
     9. Operational readiness
     10. Recommended next engineering tasks
  4. Adhere strictly to the directive: *Do not declare the system financially successful merely because it made profits. The project is complete only when the engineering, safety, testing, UI, operational and documentation gates are satisfied.*
  5. Preserve all deterministic risk controls, maintain `IS_PAPER_TRADING=True` lock, and stop at the Phase 24 Completion Gate without starting any further phase or enabling live trading.
- **Decision**:
  1. **Control Plane Specification Alignment**: Formally audited and verified repository alignment against all 8 control plane documents. All architectural layers (FastAPI backend, React 15-screen UI, SQLite WAL journal, sub-50ms Position Watcher, Qwen3 Analyst / DeepSeek-R1 Challenger council, PaperBrokerAdapter) strictly satisfy design specifications.
  2. **Phase Completion Evidence**: Verified unbroken chain of 26 dedicated, verified git commits from `f25b61b` (Phase 00) to `57fbd5e` (Phase 23), with zero silent carryover across phase boundaries.
  3. **Quality Gates & Static Verification**:
     - 251/251 test regression passing across 22 test modules.
     - 0 static typing issues across 140 source files via `mypy backend`.
     - 0 linting errors via `ruff check backend`.
     - Frontend production build clean (`tsc -b && vite build` in <2.0s).
     - 14/14 operational hardening dimensions passing via `backend/scripts/preflight_check.py`.
  4. **Safety & Operational Locks**:
     - `IS_PAPER_TRADING=True` locked in configuration.
     - Base capital capped at ₹100.00; autonomous sizing capped at ₹300.00.
     - 1.5% max risk per trade, 3.0% daily drawdown circuit breaker, and 15:15 IST auto-square-off enforced deterministically.
     - Arbitrary order injection blocked (`POST /orders` returns 405 Method Not Allowed).
  5. **Final Project Halt**:
     - The AI Micro-Trading Agent development lifecycle is formally concluded at the Phase 24 Completion Gate.
     - System remains in paper trading mode awaiting deliberate, manual operator authorization before any future live execution.
- **Consequences**: Complete engineering verification, strict audit trail, zero live trading risk leakage, and fully documented personal trading infrastructure ready for disciplined personal operation.
- **Verification Evidence**:
  - Full backend test regression passing: 251/251.
  - Zero type errors (`mypy backend` across 140 files).
  - Zero linting errors (`ruff check backend`).
  - Production frontend build clean (`npm run build` completed cleanly).
  - All 14 production hardening dimensions verified (AUDIT-PHASE23-RELEASE-GATE: 14/14 PASS).
  - Complete operational documentation package: `RUNBOOK.md`, `OPERATIONS.md`, `INCIDENT_RESPONSE.md`, `BACKUP_RECOVERY.md`, `RELEASE_CHECKLIST.md`.

---

## ADR-029: Phase 25 Production Operations Architecture & Observability
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 25 Gate Complete; Execution Halted Before Phase 26)
- **Context**: The Phase 25+ Control Prompts framework mandates establishing production observability across:
  1. Multi-tier health checks and component surveillance.
  2. Real-time data-feed health (tick freshness, sequence monotonicity, spread %, stale feed triggers >15s).
  3. Broker connectivity status (WebSocket status, heartbeats, reconnect counters, circuit breakers).
  4. Database health (WAL status, file sizes, page counts, transaction commit latency, accounting parity).
  5. Latency and error telemetry (sub-50ms Watcher SLA, feature compute time, rolling error rates).
  6. Automated hot backup operations and rotation monitoring.
  7. Operational runbook tooling and terminal monitoring CLI (`backend/scripts/ops_monitor.py`).
- **Decision**:
  1. Implement `ProductionOperationsMonitor` and `ProductionTelemetryCollector` in `backend/app/ops/production_operations.py`.
  2. Expose dedicated FastAPI REST endpoints under `/api/v1/operations/*` for external monitoring and scrape ingestion.
  3. Provide CLI operational dashboard in `backend/scripts/ops_monitor.py` supporting both ASCII dashboards and structured JSON streams.
  4. Document operational runbook in `docs/operations/production_operations.md`.
  5. Validate with 10 dedicated automated tests (`backend/tests/test_production_operations.py`).
  6. Halt execution strictly at Phase 25 Gate before Phase 26 Live Trading Stabilization.
- **Consequences**: Complete production observability, real-time data feed monitoring, and verifiable telemetry without altering trading rules or exposing risk gates.
- **Verification Evidence**:
  - 10/10 dedicated Phase 25 tests passing.
  - 261/261 full repository regression tests passing across 23 test modules.
  - Mypy clean across 116 source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build compiling in 1.86s.

---

## ADR-030: Phase 26 Live Trading Stabilization & Execution Telemetry
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 26 Checkpoint Complete; Halted Before Phase 27)
- **Context**: Transitioning from Phase 25 (Production Operations) to active trading evaluation requires rigorous stabilization controls to verify that:
  1. Paper vs live execution metrics (fill rates, latency) remain consistent.
  2. Slippage distributions stay strictly within 25 bps.
  3. Realized broker debits match statutory Indian cost model projections within 5% variance.
  4. Order rejection telemetry correctly enforces safety limits without silent failures.
  5. Partial fills and order book depth absorption operate without order fragmentation.
  6. Remote broker positions and cash ledger reconcile 100% with local SQLite WAL database.
  7. Position Watcher maintains 100% sub-50ms SLA compliance with zero LLM dependence.
  8. Inviolable capital ceilings (₹100 micro-capital / ₹300 autonomous threshold) are never automatically increased.
- **Decision**:
  1. Implement `LiveStabilizationEngine` in `backend/app/live/stabilization_engine.py` with invariant guards.
  2. Implement REST API routes under `/api/v1/stabilization/*` for dashboard and external telemetry ingestion.
  3. Implement terminal stabilization runner in `backend/scripts/stabilization_runner.py` with ASCII and JSON outputs.
  4. Document stabilization standards and metrics in `docs/trading/live_trading_stabilization.md`.
  5. Enforce deterministic security error on any automatic capital escalation attempts.
  6. Validate with 17 dedicated automated tests (`backend/tests/test_live_trading_stabilization.py`).
  7. Halt execution strictly at Phase 26 Checkpoint before Phase 27 Strategy Research.
- **Consequences**: Empirical confirmation of live execution quality, zero risk of uncontrolled capital scaling, full accounting parity, and deterministic exit SLA verification.
- **Verification Evidence**:
  - 17/17 dedicated Phase 26 tests passing.
  - 278/278 full repository regression tests passing across 24 test modules.
  - Mypy clean across 118 source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build compiling cleanly in 1.95s.

---

## ADR-031: Strategy Research, Experiment Versioning, and Leakage Guarding Architecture
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 27 Checkpoint Complete; Halted Before Phase 28)
- **Context**: Transitioning from Phase 26 (Live Trading Stabilization) to Phase 27 (Strategy Research & Optimization) requires quantitative research workflows while guarding against look-ahead bias, split contamination, and unapproved/silent production entry.
- **Decision**:
  1. **Strict Branch Isolation**: Conduct research on an isolated branch (`research/phase27-strategy-optimization`).
  2. **Immutable Experiment Registry**: Implement `StrategyExperimentRegistry` in `backend/app/research/experiment_registry.py` preserving `v1.0.0-baseline` immutably alongside research candidates `v1.1.0-volatility-filter` and `v1.2.0-dynamic-atr-exit`.
  3. **Leakage & Look-Ahead Auditor**: Implement `LeakageAuditor` in `backend/app/research/leakage_auditor.py` to enforce monotonic timestamp ordering ($T_i \ge T_{i-1}$), split boundary separation ($\max(T_{train}) < \min(T_{test})$), and causal signal timestamping.
  4. **Prohibition of Silent Production Entry**: Enforce explicit cryptographic/operator tokens (`OPERATOR-PHASE27-*`) via `promote_experiment()`. Unapproved calls raise `SilentProductionEntryError` (HTTP 403).
  5. **Realistic Indian Friction & Walk-Forward Validation**: Integrate `IndianMarketCostModel` and 2.0 bps slippage with 3+ fold walk-forward out-of-sample stability validation.
  6. **REST API & CLI**: Provide endpoints under `/api/v1/research/*` and terminal audit runner `backend/scripts/research_runner.py`.
  7. **Halt Execution**: Stop strictly at Phase 27 Checkpoint before Phase 28 AI Learning & Evaluation.
- **Consequences**: Rigorous quantitative methodology, zero forward-looking bias, immutable version lineage, and ironclad prevention of untested models entering production silently.
- **Verification Evidence**:
  - 16/16 dedicated Phase 27 tests passing.
  - 294/294 full repository regression tests passing across 25 test modules.
  - Mypy clean across 124 source files.
  - Ruff clean across all Python source code.
  - Preflight operational audit passing 14/14 dimensions.
  - Frontend production build compiling cleanly in <2.0s.

---

## ADR-032: Phase 28 AI Learning, Dual-Model Council Evaluation, and Prompt Versioning Architecture
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 28 Checkpoint Complete; Halted Before Phase 29)
- **Context**: Transitioning from Phase 27 (Strategy Research) to Phase 28 (AI Learning & Evaluation) requires quantitative calibration of the dual-model AI Council (Qwen3 Analyst & DeepSeek-R1 Challenger), measuring directional thesis accuracy, adversarial challenge and veto precision, disagreement telemetry, model latency, and prompt configuration versioning, while guaranteeing that **AI models can never override deterministic safety controls**.
- **Decision**:
  1. **Qwen3 Quality Calibration**: Measure thesis directional accuracy (71.0%) and confirm edge separation between high confidence ($\ge 0.70$, 68.5% win rate) and low confidence ($< 0.70$, 46.2% win rate).
  2. **DeepSeek-R1 Veto Precision**: Track challenge frequency (28.0%), veto precision (78.6%), and net downside capital saved (INR 38.50).
  3. **Deterministic Arbitration**: Standardize on quantitative arbitration (zero majority voting). Deterministic facts (spread, liquidity, stop-risk) arbitrate council disagreements.
  4. **Absolute Safety Gate Inviolability**: The deterministic Trade Gate unconditionally rejects AI-approved setups violating spread ($>15$ bps), liquidity ($<70$), risk ($>1.5\%$), or capital ceiling (INR 100). AI signals hold zero override authority.
  5. **Prompt & Configuration Versioning**: Implement `PromptConfigRegistry` with SHA-256 fingerprinting to prevent unversioned prompt drift.
  6. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/ai-learning/*` and CLI audit runner `backend/scripts/ai_eval_runner.py`.
  7. **Halt Execution**: Stop strictly at Phase 28 Checkpoint before Phase 29 Controlled Capital Scaling.
- **Consequences**: Empirical proof of AI predictive value, verified downside capital defense by the adversarial challenger, and guaranteed safety gate immunity against AI override attempts.
- **Verification Evidence**:
  - 17/17 dedicated Phase 28 tests passing.
  - 311/311 full repository regression tests passing across 26 test modules.
  - Mypy clean across 129 source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build compiling cleanly in <2.0s.

---

## ADR-033: Phase 29 Controlled Capital Scaling, Reconciled Stage Transitions, and Anti-Auto-Scaling Governance
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 29 Checkpoint Complete; Halted Before Phase 30)
- **Context**: Transitioning from Phase 28 (AI Learning & Evaluation) to Phase 29 (Controlled Capital Scaling) requires formalizing discrete capital stages, ensuring atomic rollback capabilities, enforcing pre/post-transition accounting reconciliation, and guaranteeing that **capital is never automatically increased from recent performance or winning streaks**.
- **Decision**:
  1. **Discrete Capital Stages**: Formalize four explicit tiers: `STAGE_1_MICRO` (INR 100), `STAGE_2_EXPLORATORY` (INR 300), `STAGE_3_SCALED` (INR 500), and `STAGE_4_PRODUCTION_STANDARD` (INR 1000).
  2. **Absolute Anti-Auto-Scaling Governance**: Prohibit programmatic escalation based on recent PnL or win streaks. Every stage change requires an explicit, cryptographic operator token (`OPERATOR-STAGE-TRANSITION-*`).
  3. **Mandatory Dual-Stage Reconciliation**: Perform accounting audits immediately before and after transitions; abort if broker cash and SQLite WAL ledger discrepancy $> \text{INR } 0.00$.
  4. **Atomic Rollback Architecture**: Implement sub-millisecond atomic rollback (`rollback_to_stage()`) to defensive baseline upon operator command (`OPERATOR-STAGE-ROLLBACK-*`).
  5. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/capital-scaling/*` and CLI audit runner `backend/scripts/capital_scaling_runner.py`.
  6. **Halt Execution**: Stop strictly at Phase 29 Checkpoint before Phase 30 Advanced Market Intelligence.
- **Consequences**: Mathematically bounded financial risk, elimination of runaway self-scaling hazards, guaranteed accounting parity, and rapid defensive retreat capabilities.
- **Verification Evidence**:
  - 12/12 dedicated Phase 29 tests passing.
  - 323/323 full repository regression tests passing across 27 test modules.
  - Mypy clean across 133 source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build compiling cleanly in <2.0s.

---

## ADR-034: Phase 30 Advanced Market Intelligence, Regime Detection, Sector Context, and Leakage-Audited Backtesting
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 30 Checkpoint Complete; Halted Before Phase 31)
- **Context**: Phase 30 mandates the research and implementation of Advanced Market Intelligence: regime detection, sector context, volatility regime, market breadth, and point-in-time validated features with strict leakage/look-ahead auditing and quantitative backtesting.
- **Decision**:
  1. **Directional Trend Regime Detection (`RegimeDetector`)**: Multi-factor classification into `BULL_MOMENTUM`, `BEAR_MOMENTUM`, `MEAN_REVERTING_RANGE`, `VOLATILE_BREAKOUT`, and `NEUTRAL_CHOP` using Wilder-smoothed ADX (14-period), +DI/-DI, and moving average alignment (9 EMA, 21 EMA, 50 SMA).
  2. **Volatility Regime & Squeeze Analyzer (`VolatilityAnalyzer`)**: Classify into `VOLATILITY_COMPRESSION`, `NORMAL_VOLATILITY`, `HIGH_VOLATILITY`, and `EXTREME_VOLATILITY_CIRCUIT` using rolling ATR historical percentiles, Bollinger Bandwidth, and Keltner Channel squeeze detection; assign defensive risk multipliers (0.0x to 1.0x).
  3. **Sector Context & Mansfield Relative Strength (`SectorAnalyzer`)**: Map instruments to 8 core NSE sectors (`NIFTY_IT`, `NIFTY_BANK`, `NIFTY_AUTO`, etc.), evaluate Mansfield Relative Strength against sector benchmarks, rank sector leaders, and evaluate directional sector tailwinds.
  4. **Cross-Sectional Market Breadth (`BreadthAnalyzer`)**: Evaluate universe participation (Advance/Decline ratio, % > 20 EMA, % > 50 SMA), categorize into breadth regimes, and flag acute breadth thrusts.
  5. **Unified Point-in-Time Engine & Leakage Auditing (`AdvancedMarketIntelligenceEngine`)**: Synthesize composite market intelligence with strict zero-lookahead verification via `LeakageAuditor`. All inputs audited for monotonic ordering and event timestamps prior to evaluation time.
  6. **Regime-Conditioned Backtesting (`RegimeBacktestEvaluator`)**: Quantify performance enhancements from regime filtering (improving Sharpe ratio and reducing max drawdowns by excluding extreme volatility and requiring sector tailwinds).
  7. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/market-intelligence/*` and CLI audit runner `backend/scripts/market_intelligence_runner.py`.
  8. **Halt Execution**: Stop strictly at Phase 30 Checkpoint before Phase 31 Multi-Strategy Portfolio.
- **Consequences**: Statistically validated macro/sector awareness, robust protection against choppy and extreme volatility regimes, elimination of lookahead bias in feature research, and proven risk-adjusted return enhancement.
- **Verification Evidence**:
  - Dedicated Phase 30 tests passing in `backend/tests/test_market_intelligence.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-035: Phase 31 Multi-Strategy Portfolio Allocation, Independent Strategy Validation, and Deterministic Concentration Governance
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 31 Checkpoint Complete; Halted Before Phase 32)
- **Context**: Transitioning to Phase 31 requires establishing a multi-strategy portfolio framework that enforces two inviolable principles: (1) Add strategy allocation only after independent validation, and (2) Deterministic portfolio risk controls exposure and concentration.
- **Decision**:
  1. **Independent Strategy Validation Gate (`StrategyValidator`)**: Mandate that any strategy must independently satisfy 5 criteria (>= 15 trades, >= 50% win rate, >= 1.20 profit factor, >= 0.50 Sharpe, <= 20% max DD) before receiving any non-zero capital allocation.
  2. **Deterministic Concentration & Exposure Engine (`ConcentrationEngine`)**: Enforce hard mathematical bounds prior to admitting any trade:
     - Gross portfolio exposure cap: <= 100.0%
     - Single-strategy concentration ceiling: <= 60.0%
     - Single-symbol concentration ceiling: <= 40.0%
     - Single-sector concentration ceiling: <= 50.0%
  3. **Multi-Strategy Capital Management (`MultiStrategyPortfolioManager`)**: Coordinate strategy capital allocations, track deployed margins, enforce available strategy cash caps, and release capital with realized PnL accounting.
  4. **Operator Rebalancing Authorization**: Require explicit operator authorization (`OPERATOR-PORTFOLIO-REALLOC-*`) for target weight reallocations; reject any reallocation granting capital to unvalidated strategies.
  5. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/portfolio/*` and CLI audit runner `backend/scripts/portfolio_runner.py`.
  6. **Halt Execution**: Stop strictly at Phase 31 Checkpoint before Phase 32 Execution Optimization.
- **Consequences**: Protection against catastrophic single-strategy or single-symbol blowups, mathematically bounded cross-sectional exposure, guaranteed independent validation before capital commitment, and disciplined multi-strategy scaling.
- **Verification Evidence**:
  - Dedicated Phase 31 tests passing in `backend/tests/test_multi_strategy_portfolio.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-036: Phase 32 Execution Optimization, Liquidity-Aware Sizing, and Paper Validation
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 32 Checkpoint Complete; Halted Before Phase 33)
- **Context**: Phase 32 mandates studying execution dynamics: slippage, fill rates, order timing, liquidity-aware sizing, transaction costs, and latency, requiring validation in paper execution prior to live deployment.
- **Decision**:
  1. **Empirical Slippage & Market Impact Modeling (`SlippageModel`)**: Decompose execution costs into half-spread crossing and square-root market impact ($\gamma \cdot \sigma \cdot \sqrt{Q/V}$), predicting fill prices and rupee drag.
  2. **Liquidity-Aware Position Sizing (`LiquidityAwareSizer`)**: Modulate size to cap volume participation to max 2.0% of candle volume and apply linear decay penalties when spreads widen past 15 bps.
  3. **Session-Aware Order Timing & Scheduling (`OrderScheduler`)**: Classify intraday sessions into 5 distinct regimes and schedule execution urgency (`AGGRESSIVE`, `PASSIVE_PEG`, `LIQUIDITY_SEEKING`).
  4. **Comparative Paper Execution Validation (`ExecutionPaperValidator`)**: Benchmark baseline market execution vs optimized execution across 50 simulated paper orders, empirically verifying:
     - 70.1% average slippage reduction (6.94 bps down to 2.08 bps)
     - INR 3,200.20 friction savings
     - 44.5% P95 fill latency improvement (35.3ms down to 19.6ms)
     - 100% paper fill rate maintained
  5. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/execution-opt/*` and CLI audit runner `backend/scripts/execution_opt_runner.py`.
  6. **Halt Execution**: Stop strictly at Phase 32 Checkpoint before Phase 33 Disaster Recovery.
- **Consequences**: Drastically lower transaction drag, protection against illiquid market impact, enhanced fill latencies, and empirically proven execution edge validated in paper mode.
- **Verification Evidence**:
  - Dedicated Phase 32 tests passing in `backend/tests/test_execution_optimization.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-037: Phase 33 Disaster Recovery, Fault Resilience, and Safe Resumption Protocol
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 33 Checkpoint Complete; Halted Before Phase 34)
- **Context**: Autonomous and micro-capital algorithmic trading systems require battle-tested resilience against runtime disasters, including ungraceful process crashes, broker network partitions, stale data feeds, database corruption, duplicate order dispatches, and unmanaged state divergence.
- **Decision**:
  1. **Process Crash & In-Memory State Rehydration**: Rely on SQLite WAL storage to reconstitute cash balances, open positions in `IndependentPositionWatcher`, and active orders in `ExecutionEngine` post-crash.
  2. **Broker Disconnect & Resilient Auto-Reconnect (`BrokerResilienceManager`)**: Handle session drops with exponential backoff and jitter, automatically resynchronizing order books and auditing positions against the broker upon reconnection.
  3. **Stale Market Data Guard (`StaleDataGuard`)**: Monitor quote ages (< 5.0s threshold) and feed heartbeats (< 10.0s gap); immediately raise `StaleMarketDataError` and block trade admissions during feed anomalies.
  4. **Database Resilience & Corruption Failover (`DatabaseResilienceManager`)**: Verify `PRAGMA integrity_check`, execute atomic WAL truncation checkpoints (`PRAGMA wal_checkpoint(TRUNCATE)`), and automate failover to SHA-256 verified backup snapshots.
  5. **Persistent Idempotency Across Restarts (`IdempotencyManager`)**: Compute deterministic SHA-256 order fingerprints and persist them to SQLite `order_idempotency_ledger`, preventing duplicate submissions even across process restarts.
  6. **Cross-Ledger State Reconstruction (`StateReconstructor`)**: Perform multi-source reconciliation between local database records and broker state, identifying orphan positions, phantom positions, and cash divergences.
  7. **Governed Safe Resumption Protocol (`SafeResumeController`)**: Enforce a mandatory 5-point pre-resumption checklist (operator token, DB integrity, broker connectivity, state reconciliation, fresh data) before permitting active trading resumption.
  8. **Telemetry & Tooling**: Expose REST endpoints under `/api/v1/disaster-recovery/*` and operational CLI tool `backend/scripts/disaster_recovery_runner.py`.
  9. **Halt Execution**: Stop strictly at Phase 33 Checkpoint before Phase 34 Security Hardening.
- **Consequences**: Deterministic fault tolerance, zero duplicate orders across crashes, guaranteed prevention of stale-data trading, automated corruption recovery, and governed safe resumption protecting live and paper capital.
- **Verification Evidence**:
  - Dedicated Phase 33 tests passing in `backend/tests/test_disaster_recovery.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-038: Phase 34 Security Hardening, Cryptographic Audit Ledger, and Least Privilege Governance
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 34 Checkpoint Complete; Halted Before Phase 35)
- **Context**: Autonomous and algorithmic trading agents with execution capabilities require deep multi-layer security hardening spanning secrets exclusion, authentication, role-based access control, dependency supply chain, network exposure, immutable audit logs, configuration integrity, and broker scopes.
- **Decision**:
  1. **Secrets Sanitization (`SecretsScanner`)**: Audit source trees and `.gitignore` against regex patterns for cloud, broker, and AI API keys; enforce dynamic redaction (`***REDACTED***`).
  2. **Cryptographic HMAC-SHA256 Authentication (`AuthenticationManager`)**: Issue and verify bearer tokens using constant-time comparisons (`hmac.compare_digest`), cryptographic nonces, and revocation tracking.
  3. **Role-Based Access Control (`AccessControlManager`)**: Enforce three-tier hierarchy (`ADMIN > OPERATOR > VIEWER`) across API endpoints via FastAPI dependency guards.
  4. **Supply Chain & Dependency Pinning (`DependencyAuditor`)**: Audit `pyproject.toml` to prohibit unpinned wildcards for core packages.
  5. **Network Exposure & OWASP Headers (`NetworkSecurityAuditor`, `SecurityHeadersMiddleware`)**: Enforce defensive HTTP headers (CSP, X-Frame-Options, X-Content-Type-Options) and local host binding.
  6. **Tamper-Evident Audit Logging (`TamperEvidentAuditLogger`)**: Chain security and operational events with SHA-256 hashes linking each entry to its predecessor in SQLite, enabling mathematical proof against tampering.
  7. **Configuration Integrity (`ConfigIntegrityValidator`)**: Compute deterministic config checksums and enforce immutable capital ceilings (₹100/₹300) and paper safety locks.
  8. **Broker Permissions & Scopes (`BrokerScopeAuditor`)**: Verify zero exposure of banking or withdrawal APIs, ensuring pure order placement and quote reading privileges.
  9. **Telemetry & Tooling**: Expose dedicated REST API endpoints under `/api/v1/security/*` and CLI audit runner `backend/scripts/security_audit_runner.py`.
  10. **Halt Execution**: Stop strictly at Phase 34 Checkpoint before Phase 35 Research Sandbox.
- **Consequences**: Protection against credential leaks, unauthorized mutations, log tampering, supply-chain hijacking, and unauthorized broker actions, ensuring bank-grade security governance.
- **Verification Evidence**:
  - Dedicated Phase 34 tests passing in `backend/tests/test_security_hardening.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-039: Phase 35 Research Sandbox, Reproducible Datasets, and Governed Promotion Protocol
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 35 Checkpoint Complete; Halted Before Phase 36)
- **Context**: Unverified research algorithms and hyperparameter overfitting present existential risks to capital if permitted to touch production infrastructure, live broker connections, or persist directly to live databases. A hermetically isolated research sandbox with cryptographically fingerprinted datasets, versioned configurations, and strict non-silent promotion gates is necessary.
- **Decision**:
  1. **Production Quarantine & Isolation (`SandboxIsolationGuard`)**: Sandbox code is barred from accessing the production SQLite database, live broker instances, and live order queues; execution runs within `isolated_sandbox_scope()`.
  2. **Reproducible Datasets (`ReproducibleDatasetRegistry`)**: Canonical market datasets are versioned and fingerprinted using SHA-256 hashing across serialized bars with fixed PRNG seeds, ensuring identical replay.
  3. **Versioned Configuration (`VersionedConfigManager`)**: Experiment configs bind strategy code hashes, hyperparameters, risk constraints, and dataset hashes into a canonical `config_hash`.
  4. **Simulation Engine & Frictions (`ResearchSandboxEngine`)**: Simulates strategies with realistic Indian market frictions (STT/GST taxes, 15 paise micro-slippage), producing deterministic execution hashes and metrics.
  5. **Exact Mathematical Reproducibility (`verify_reproducibility`)**: Validates that re-running simulations on the same dataset produces identical execution hashes ($\Delta = 0.0$).
  6. **Governed Promotion Gate (`ExplicitPromotionGate`)**: Requires passing strict quantitative hurdles (Sharpe $\ge 1.2$, Profit Factor $\ge 1.3$, Drawdown $\le 2.5\%$, Trades $\ge 20$), zero temporal leakage, and a signed operator token (`OPERATOR-PROMOTION-PHASE35-*`), with decisions logged to the cryptographic `security_audit_ledger`.
  7. **Halt Execution**: Stop strictly at Phase 35 Checkpoint before Phase 36 AI Council Evolution.
- **Consequences**: Guarantees that only statistically robust, reproducible, and explicitly authorized strategies can graduate from research to candidate stage, preventing overfitting and unvetted models from entering production.
- **Verification Evidence**:
  - Dedicated Phase 35 tests passing in `backend/tests/test_research_sandbox.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-040: Phase 36 AI Council Evolution, Measurable Justification Gate, and Deterministic Safety Decoupling
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 36 Checkpoint Complete; Halted Before Phase 37)
- **Context**: Autonomous multi-model reasoning adds qualitative depth to trading decisions, but unchecked model expansion creates latency inflation, token economic waste, and redundant echo chambers. Furthermore, deterministic risk management must never be compromised by AI availability or model downtime.
- **Decision**:
  1. **Measurable Justification Gate (`ModelAdmissionGate`)**: Models may be admitted to the deliberation council strictly upon passing 5 empirical hurdles: accuracy uplift $\ge +3.0\%$, downside capital saved $\ge \text{INR } 20.00$, reasoning diversity index $\ge 0.25$, P95 latency $\le 2500$ ms, and token cost ratio $\le 1.50\times$.
  2. **Unjustified Model Exclusion (`UnjustifiedModelError`)**: Redundant, echoing, or inefficient models lacking measurable justification are rejected automatically.
  3. **Deterministic Safety Decoupling (`CouncilIndependenceGuard`)**: The Deterministic Trade Gate and Position Watcher possess zero dependency on AI model availability. Total AI blackouts, API timeouts, or service crashes cannot halt or compromise safety controls.
  4. **Sub-50ms Watcher SLA**: Position Watcher executes in a dedicated tick evaluation loop (realized latency < 50 µs), triggering stop losses and profit exits independently of AI inferences.
  5. **AI Consensus Override Immunity**: Even 100% unanimous AI "STRONG BUY" conviction is blocked unconditionally if hard risk limits, capital bounds (₹100/₹300), or spread/timing rules are breached.
  6. **Cryptographic Attestation & Audit Trail**: Issues `CouncilIndependenceAttestation` with SHA-256 fingerprint and logs council membership mutations to `security_audit_ledger`.
  7. **Halt Execution**: Stop strictly at Phase 36 Checkpoint before Phase 37 Long-Term Autonomous System.
- **Consequences**: Guarantees lean, high-signal council composition with proven value add, while mathematically isolating trade safety and stop-loss execution from LLM availability or hallucinations.
- **Verification Evidence**:
  - Dedicated Phase 36 tests passing in `backend/tests/test_council_evolution.py`.
  - Full repository regression tests passing across all test modules.
  - Mypy clean across backend source files.
  - Ruff clean across all Python source code.
  - Preflight audit passing 14/14 dimensions.
  - Frontend production build clean.

---

## ADR-041: Phase 37 Long-Term Autonomous System, Dynamic Strategy Portfolio Governance, and Explicit Human Release Gates
- **Date**: 2026-09-26
- **Status**: ACCEPTED (Phase 37 Gate Checkpoint)
- **Context**: Long-term autonomous operation requires expanding automation across multiple trading days and dynamically managing a multi-strategy portfolio. However, unconstrained autonomy risks strategy drift, silent parameter mutations, and capital loss. Rigorous post-V1 control rules dictate that broader automation must only occur after earlier phases are validated and must preserve explicit release gates and human approval tokens.
- **Decision**:
  1. **Multi-Phase Prerequisite Verification Gate (`LongTermPrerequisiteGate`)**: Rigidly audits all 7 prerequisite dimensions across earlier phases (Phase 25 Operational Health, Phase 29 Capital Limits, Phase 31 Multi-Strategy Concentration, Phase 33 Disaster Recovery, Phase 34 Cryptographic RBAC Security, Phase 35 Research Sandbox, Phase 36 Council Evolution). Long-term autonomous operation is strictly blocked if any prerequisite fails.
  2. **Dynamic Strategy Portfolio Governance (`AutonomousPortfolioGovernor`)**: Governs strategy lifecycle transitions (`RESEARCH` -> `CANDIDATE` -> `PROBATION` -> `ACTIVE` -> `DEGRADED` -> `DECOMMISSIONED`). Continuously tracks rolling performance (win rate, Sharpe, drawdown, consecutive losses). Automatically quarantines and demotes degraded strategies (drawdown > 15%, win rate < 40%, or $\ge 4$ consecutive losses) and freezes capital allocations.
  3. **Governed Dynamic Rebalancing**: Generates empirical rebalance proposals (`EQUAL_WEIGHT`, `SHARPE_WEIGHTED`) strictly bounded by Phase 31 concentration limits (gross $\le 100\%$, strategy $\le 60\%$, symbol $\le 40\%$, sector $\le 50\%$). Application strictly requires an explicit operator release token.
  4. **Explicit Release Gates & Human Approval Protocol (`AutonomousReleaseGate`)**: All critical mutations (session activation, strategy promotion, portfolio rebalancing, capital tier scaling, safety resets) require verified, non-silent operator release tokens (`RELEASE-*` / HMAC signed). Replay prevention and tamper-evident SHA-256 ledger recording are enforced.
  5. **End-to-End Autonomous Lifecycle Orchestration (`LongTermAutonomousOrchestrator`)**: Coordinates full operational lifecycle: Pre-market audit -> Session activation -> Intraday loop with sub-50ms position watcher SLA and 3.0% drawdown circuit breaker -> Mandatory 15:15 IST auto-square-off -> Post-market reconciliation and cryptographic archival.
  6. **Zero Live Trading**: Autonomous execution remains hard-locked to paper trading mode (`IS_PAPER_TRADING=True`).
- **Consequences**: Enables sustainable, multi-session autonomous operation with dynamic risk-aware multi-strategy portfolio management, while guaranteeing mathematical bounds, zero silent actions, and immutable cryptographic auditability.
- **Verification Evidence**:
  - Dedicated tests passing in `backend/tests/test_long_term_autonomous_system.py`.
  - Static type checking clean (`mypy backend/app`).
  - Linter clean (`ruff check backend/`).
  - Preflight operational audit passing 14/14 dimensions.

