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
- **Status**: PENDING APPROVAL (Phase 16 Release Readiness Gate)
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





