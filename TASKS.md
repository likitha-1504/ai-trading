# Project Task Board

Status Key:
- `[ ]` Not Started
- `[/]` In Progress
- `[x]` Completed
- `[!]` Blocked / Awaiting Approval

---

## Phase 00: Project Bootstrap & Control Plane
- [x] Read and digest prompt pack PDF (`Phasewise_Prompts_AI_Micro_Trading_Agent.pdf`)
- [x] Environment inspection (Python, Node, Git, Ollama, Qwen3, DeepSeek-R1, Codex CLI)
- [x] Execute harmless read-only Codex CLI probe (`codex --version`)
- [x] Create project control plane documents:
  - [x] `ARCHITECTURE.md`
  - [x] `PROJECT_SPEC.md`
  - [x] `DEVELOPMENT_PLAN.md`
  - [x] `TASKS.md`
  - [x] `DECISIONS.md`
  - [x] `CODING_RULES.md`
  - [x] `TEST_PLAN.md`
  - [x] `DATABASE_SCHEMA.md`
  - [x] `API_CONTRACTS.md`
  - [x] `TRADING_RULES.md`
  - [x] `FAILURE_HANDLING.md`
  - [x] `BROKER_ADAPTER_SPEC.md`
  - [x] `UI_UX_SPEC.md`
  - [x] `AI_ROLES.md`
- [x] Produce Phase 00 Bootstrap Report and await user sign-off
- [x] Python virtual environment `.venv` created, dependencies installed, and sanity tests passed
- [x] Verified Codex CLI invocation in harmless read-only sandbox mode

---

## Phase 01: Architecture Lock & Technical Design
- [x] Validate end-to-end architecture pipeline and boundary constraints
- [x] Define interface data contracts and event schemas (`backend/app/models/contracts.py`)
- [x] Define latency measurement budgets and failure modes matrix
- [x] Deliver final architecture package and dependency-ordered plan in `ARCHITECTURE.md`
- [x] Record ADR-006 in `DECISIONS.md`
- [x] User Approval Gate for Phase 01 Checkpoint (APPROVED)

---

## Phase 02: UI/UX Design System
- [x] Detail UI specifications for 15 dedicated terminal screens in `UI_UX_SPEC.md`
- [x] Define visual design tokens, status badges (15 states), and typography
- [x] Formalize visual distinction between deterministic facts and AI reasoning
- [x] Create wireframe and design system artifact
- [x] Produce Codex implementation task list for UI (Phase 15 handoff)
- [x] User Approval Gate for Phase 02 Checkpoint (APPROVED)

---

## Phase 03: Market Data & Normalization
- [x] Abstract `BaseMarketDataAdapter` with async streaming, subscription, and reconnect loop
- [x] `MarketDataNormalizer` for monotonic timestamps, spread %, and stale data detection
- [x] `SimulatedMarketDataAdapter` with deterministic tick generation and fault injection
- [x] Unit and integration test suite (`backend/tests/test_market_data.py`) passing 100%
- [x] Zero live orders and zero LLM calls verified in data layer
- [x] Phase 03 Phase Gate Checkpoint (APPROVED)

---

## Phase 04: Feature Engine
- [x] Prepare feature computation specifications and schemas (`FeatureSnapshot`)
- [x] Implement point-in-time `BarAggregator` and 12-feature deterministic `FeatureEngine`
- [x] Verify lookahead safety, timestamp immutability, and sub-15ms budget
- [x] Comprehensive test suite (`backend/tests/test_feature_engine.py`) passing 100%
- [x] Phase 04 Phase Gate Checkpoint (APPROVED)

---

## Phase 05: BUY Engine: Momentum + Early-Move Detection
- [x] Create strategy configuration parameters without magic numbers (`strategies/config.py`)
- [x] Implement Strategy A: `MomentumContinuationStrategy` with VWAP, RVOL >= 1.8, and deterioration rejection
- [x] Implement Strategy B: `EarlyMoveDetectionStrategy` with volatility compression, acceleration, and alignment
- [x] Implement `CandidateRanker` with cooldown deduplication, deterministic ranking, and tie-breaking
- [x] Comprehensive test suite (`backend/tests/test_strategies.py`) passing 100% with zero orders placed
- [x] Phase 05 Phase Gate Checkpoint (APPROVED)

---

## Phase 06: SELL Engine + Independent Position Watcher
- [x] Prepare Codex delegation spec for independent Position Watcher
- [x] Codex: Implement hard stops, circuit breakers, and trailing logic (`backend/app/watcher/position_watcher.py`)
- [x] Antigravity: Verify zero LLM dependency on emergency exits (`backend/tests/test_position_watcher.py`)
- [x] Phase 06 Critical Safety Gate Checkpoint (APPROVED)

---

## Phase 07: Capital, Risk & Cost Engine
- [x] Prepare Codex delegation spec for capital management & Indian cost model (`backend/app/capital/config.py`)
- [x] Codex: Implement STT, GST, SEBI, exchange fee calculations and ₹100/₹300 limits (`backend/app/capital/cost_model.py`, `backend/app/capital/capital_manager.py`)
- [x] Antigravity: Verify net-edge profitability calculation and risk gating (`backend/app/capital/risk_engine.py`, `backend/tests/test_capital_risk_cost.py`)
- [!] Phase 07 Phase Gate Checkpoint (Awaiting User Sign-off)

---

## Phase 08: Execution Engine + Broker Abstraction
- [x] Prepare Codex delegation spec for `BrokerAdapter` and `PaperAdapter` (`backend/app/adapters/broker_base.py`, `backend/app/adapters/paper_adapter.py`)
- [x] Codex: Implement order lifecycle state machine and reconciliation (`backend/app/execution/state_machine.py`, `backend/app/execution/execution_engine.py`, `backend/app/execution/metrics.py`)
- [x] Antigravity: Verify broker abstraction purity and idempotency (`backend/tests/test_execution_engine.py`)
- [!] Phase 08 Phase Gate Checkpoint (Awaiting User Sign-off)

---

## Phase 09: Backtesting + Paper Trading Loop
- [x] Prepare Codex delegation spec for event-driven backtesting
- [x] Codex: Implement simulator, slippage model, and performance metrics (`backend/app/backtesting/simulator.py`, `backend/app/backtesting/paper_loop.py`, `backend/app/backtesting/metrics.py`, `backend/app/backtesting/journal.py`, `backend/app/backtesting/walk_forward.py`, `backend/app/backtesting/slippage_analysis.py`)
- [x] Antigravity: Verify backtest/paper strategy interface symmetry, zero lookahead/survivorship bias, and Indian friction fidelity (`backend/tests/test_backtesting.py`)
- [!] Phase 09 Phase Gate Checkpoint (Awaiting User Sign-off)

---

## Phase 10: Qwen3 Analyst Integration
- [x] Prepare Codex delegation spec for Qwen3 integration
- [x] Codex: Implement structured JSON schema, prompt templates, and timeout handlers (`backend/app/ai/config.py`, `backend/app/ai/prompts.py`, `backend/app/ai/validator.py`, `backend/app/ai/metrics.py`, `backend/app/ai/client.py`)
- [x] Antigravity: Verify AI output validation and fallback behavior (`backend/tests/test_qwen3_analyst.py`)
- [x] Phase 10 Phase Gate Checkpoint (APPROVED)

---

## Phase 11: DeepSeek-R1 Challenger Layer
- [x] Prepare Codex delegation spec for adversarial challenger
- [x] Codex: Implement critique prompts, stress testing, and structured schema (`backend/app/ai/challenger_config.py`, `backend/app/ai/challenger_prompts.py`, `backend/app/ai/challenger_validator.py`, `backend/app/ai/challenger_client.py`)
- [x] Antigravity: Verify deterministic gate retains final decision authority (`backend/app/ai/council_evaluator.py`, `backend/tests/test_deepseek_r1_challenger.py`)
  - [x] Verify prompt builders isolate raw ticks and incorporate Qwen3 thesis + feature snapshot
  - [x] Verify `<think>...</think>` chain-of-thought sanitization and strict Pydantic JSON parsing
  - [x] Verify timeout, exponential backoff retries, connection error recovery, and safe fallback invariants
  - [x] Verify deterministic dispute resolution (Qwen3 bullish vs DeepSeek-R1 contested/veto) with empirical math
  - [x] Verify zero broker execution / order placement authority on AI clients
  - [x] All 21 Phase 11 unit/integration tests passing (127 total suite passing, ruff & mypy clean)
- [x] Phase 11 Phase Gate Checkpoint (APPROVED)

---

## Phase 12: Deterministic Trade Gate + AI Council
- [x] Prepare Codex delegation spec for Trade Gate pipeline
- [x] Codex: Assemble Candidate -> AI Council -> Risk Gate -> TradePlan pipeline (`backend/app/gate/config.py`, `backend/app/gate/audit_logger.py`, `backend/app/gate/trade_gate.py`)
- [x] Antigravity: Verify that AI models cannot directly trigger order submissions (`backend/tests/test_deterministic_trade_gate.py`)
  - [x] Verify Candidate Gate rejects invalid prices, stops, spreads (> 15 bps), liquidity (< 70), and cutoffs (15:15 IST) without calling AI
  - [x] Verify Risk Gate enforces drawdown circuit breaker, position limits, sizing, Indian friction, and net edge hurdle without calling AI
  - [x] Verify AI Council resolves Qwen3 and DeepSeek-R1 outputs deterministically
  - [x] Verify TradePlan synthesizes all 13 items from PDF specification
  - [x] Verify execution authorization (autonomous <= ₹300, manual pending > ₹300) and Position Watcher ownership transfer
  - [x] Verify AI models have zero order submission authority
  - [x] All 14 Phase 12 tests passing (141 total suite passing, ruff & mypy clean)
- [x] Phase 12 Phase Gate Checkpoint (APPROVED)

---

## Phase 13: Database, Journal & Performance
- [x] Prepare Codex delegation spec for SQLite WAL schema and journaling
- [x] Codex: Implement persistence, audit trails, and restart recovery (`backend/app/db/schema.py`, `backend/app/db/connection.py`, `backend/app/db/repository.py`, `backend/app/db/journal.py`, `backend/app/db/performance.py`, `backend/app/db/audit.py`, `backend/app/db/recovery.py`, `backend/app/db/__init__.py`)
- [x] Antigravity: Verify ACID compliance, safe transactions, and decision reproducibility (`backend/tests/test_database_journal_performance.py`)
  - [x] Finalize SQLite schema with WAL mode (`PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;`)
  - [x] Implement all 13 core entities: `capital_state`, `positions`, `orders`, `trades`, `candidates`, `features`, `ai_analyses`, `trade_plans`, `risk_events`, `strategy_versions`, `model_calls`, `execution_metrics`, `system_events`
  - [x] Implement persistent trade journal with entry/exit tracking and accurate P/L calculations (Gross, Indian statutory friction, Net)
  - [x] Implement performance metrics aggregation (win rate, profit factor, expectancy, max drawdown) and strategy-level stratification (`MOMENTUM_CONTINUATION` vs `EARLY_MOVE_DETECTION`)
  - [x] Implement model latency metrics (avg, p95, fallback rates for Qwen3 and DeepSeek-R1) and execution latency metrics (submission, ACK, fill, slippage)
  - [x] Implement decision audit trail reconstruction ensuring full decision reproducibility (`is_fully_reproducible`)
  - [x] Implement crash/restart recovery rehydrating `IndependentPositionWatcher`, `CapitalManager`, and `ExecutionEngine` from persistent database state
  - [x] All 8 Phase 13 unit/integration tests passing (149 total test suite passing, ruff & mypy clean)
- [x] Phase 13 Phase Gate Checkpoint (APPROVED)

---

## Phase 14: FastAPI Backend + API Contracts
- [x] Prepare Codex delegation spec for FastAPI endpoints
- [x] Codex: Implement query/read endpoints and guarded command APIs (`backend/app/api/schemas.py`, `backend/app/api/deps.py`, `backend/app/api/v1/endpoints/`, `backend/app/api/v1/router.py`, `backend/app/main.py`)
- [x] Antigravity: Verify endpoint security and live-trading guardrails (`backend/tests/test_api_v1.py`)
  - [x] Expose safe read/query APIs across all 13 core categories: dashboard summary, capital, market scanner & features, candidates, positions, orders, trades, trade plans, P/L breakdown, AI council analyses & latency, performance & execution metrics, backtests, risk status & limits, system health & operational logs
  - [x] Segregate read APIs from mutation/execution APIs
  - [x] Eliminate unrestricted arbitrary order endpoints (`POST /orders` strictly forbidden / 405 Method Not Allowed; execution only via validated TradePlan approval)
  - [x] Guard TradePlan approval/rejection workflows with system state validation (cannot approve when halted)
  - [x] Guard live-trading mode transitions and approvals behind explicit authorization token verification and environment lockouts
  - [x] Implement multi-component system health probes and emergency kill switch invoking Position Watcher
  - [x] Full OpenAPI v3 interactive documentation mounted at `/api/docs` and `/api/redoc` with CORS middleware configured
  - [x] All 18 Phase 14 API tests passing (167 total test suite passing, ruff & mypy clean)
- [x] Phase 14 Phase Gate Checkpoint (APPROVED)

---

## Phase 15: React Dashboard Implementation
- [x] Prepare Codex delegation spec for React + Tailwind terminal
- [x] Codex: Implement 15 screens, status badges, and real-time feeds (`frontend/src/types/index.ts`, `frontend/src/data/mockData.ts`, `frontend/src/services/api.ts`, `frontend/src/components/ui/`, `frontend/src/components/layout/`, `frontend/src/screens/`, `frontend/src/App.tsx`)
- [x] Antigravity: Verify UI separation of system facts from AI suggestions
  - [x] Implement dark-first trading terminal theme tokens and tabular numerals (`Inter` + `JetBrains Mono` with `tnum`) matching `UI_UX_SPEC.md`
  - [x] Build reusable atoms: `Badge` (15 visual states), `FactBanner` (strict separation of `[SYSTEM FACT]` vs `[QWEN3 ANALYSIS]` vs `[DEEPSEEK-R1 CHALLENGE]` vs `[FINAL DETERMINISTIC GATE]`), `MetricCard`, `Modal`
  - [x] Build global layout: `TopBar` (real-time capital facts: ₹100 base, deployed, available, daily P&L; emergency kill switch), `NavBar` (15 screens), `StatusBar` (subsystem heartbeats and latency breakdown)
  - [x] Implement all 15 screens:
    1. Command Center (Executive overview, active trade risk bar, watcher heartbeat, live logs)
    2. Market Scanner (Universe selector, momentum/RVOL/VWAP grid, feature inspect)
    3. Candidate Feed (Momentum & Early-Move setups, 4-stage pipeline, net edge)
    4. Trading Chart (Interactive SVG candlestick chart, VWAP, volume, execution marker lines)
    5. Position Monitor (Active positions table, sub-50ms watcher state, double-confirmation square-off)
    6. Orders & Execution (Order state machine lifecycle audit, broker return codes, zero arbitrary order submission)
    7. AI Analysis (Dual-model qualitative debate: Qwen3 thesis vs DeepSeek-R1 adversarial challenge, deterministic arbitration)
    8. Trade Journal (Immutable trade retrospective, entry/exit stamps, Indian statutory friction breakdown: STT, exchange, SEBI, GST, stamp duty)
    9. Performance Analytics (Win rate, profit factor, max drawdown, fee drag analysis, equity curve)
    10. Backtesting (Event-driven historical simulation, parameter controls, walk-forward stability)
    11. Risk & Capital (₹100 micro-cap meter, ₹300 autonomous limit, 3.0% daily drawdown circuit breaker gauge, risk event log)
    12. System Health (Local infrastructure diagnostics, SQLite WAL mode, Ollama inference, pipeline latency bars)
    13. Logs & Events (Structured telemetry stream, regex/search, severity filtering, JSON export)
    14. Strategy Management (Parameter tuning for Momentum Continuation & Early-Move Detection)
    15. Settings (Paper simulation mode, backend endpoint configuration, emergency webhooks)
  - [x] Verified zero guaranteed language on probabilistic AI outputs; AI models visually distinguished with dashed purple borders and explicit disclaimers
  - [x] Verified emergency kill-switch double-confirmation modal invoking Position Watcher square-off
  - [x] Successful production build verification (`tsc -b && vite build` bundled cleanly in <2s with 0 errors)
  - [x] Phase 15 Phase Gate Checkpoint (APPROVED)

---

## Phase 16: Integration, Failure Injection & QA
- [x] Antigravity QA Suite: Inject network drops, stale data, and LLM timeouts (`backend/tests/test_phase16_failure_injection.py`)
  - [x] Inject failure 1: Market data feed disconnect and reconnect
  - [x] Inject failure 2: Broker disconnect during order submission (socket drops)
  - [x] Inject failure 3: Stale quote detection (>15s quote freeze triggers `STALE_DATA_EMERGENCY`)
  - [x] Inject failure 4: Model latency timeout (>2.5s read timeout triggers fallback thesis)
  - [x] Inject failure 5: Qwen3 analyst completely unavailable (HTTP 503 / connection drop)
  - [x] Inject failure 6: DeepSeek-R1 challenger completely unavailable (HTTP 503 / connection drop)
  - [x] Inject failure 7: Malformed AI output (non-JSON text, truncated schemas, unverified boundaries)
  - [x] Inject failure 8: Partial fill handling and sequential fill state transitions
  - [x] Inject failure 9: Broker rejected orders without orphan or corrupted states
  - [x] Inject failure 10: Duplicate order submission idempotency within 60s deduplication window
  - [x] Inject failure 11: Database transaction failure and automatic rollback (ACID WAL preservation)
  - [x] Inject failure 12: Sudden process crash recovery (rehydration of active positions, hard stops, capital state)
  - [x] Inject failure 13: Laptop restart recovery (full system rehydration from SQLite WAL on startup)
  - [x] Inject failure 14: Inconsistent local vs broker position state reconciliation (`ReconciliationReport`)
- [x] Verify Position Watcher intervention during simulated model crashes (sub-50ms hard stops survive dead AI)
- [x] Produce comprehensive Release Readiness Report (`RELEASE_READINESS_REPORT.md`)
- [x] Phase 16 Release Readiness Gate (APPROVED)

---

## Phase 17: Performance & Latency Optimization
- [x] Profile execution bottlenecks across feature calculation and DB writes (`backend/app/performance/profiler.py`, `backend/app/performance/benchmarks.py`)
  - [x] Measure separately all 12 pipeline stages: market data arrival, normalization, feature computation, candidate detection, decision preparation, Qwen3 latency, DeepSeek-R1 latency, deterministic gate latency, order submission, broker acknowledgement, fill latency, Position Watcher response
  - [x] Enforce architectural invariant: internal latency (<50ms target) strictly separated and not claimed as equivalent to end-to-end execution speed
  - [x] Document hardware assumptions (Intel x86_64, 12 cores, Windows 10, Python 3.11.5, timer resolution ~100ns)
- [x] Optimize measured hotspots without sacrificing safety checks (`backend/app/engine/feature_engine.py`)
  - [x] Optimize `FeatureEngine` precision constants, eliminating 11 Decimal allocations per tick
  - [x] Optimize single-pass realized volatility, improving calculation throughput by +24.2%
  - [x] Preserve 100% mathematical correctness and risk control guarantees (all 14 feature engine tests passing)
- [x] Integrate 12-stage telemetry and benchmark endpoints into FastAPI (`/api/v1/performance/latency-breakdown`, `/api/v1/performance/benchmark`)
- [x] Produce comprehensive Performance & Latency Optimization Report (`PERFORMANCE_REPORT.md`)
- [x] Run full test regression and static checks (191/191 tests passed, ruff & mypy clean, Vite build clean)
- [x] Phase 17 Performance Gate Checkpoint (APPROVED)

---

## Phase 18: Paper Trading Validation
- [x] Run full end-to-end system in paper mode over a fixed test window (`backend/app/paper/paper_validator.py`, `backend/app/paper/runner.py`)
  - [x] Multi-session paper simulation across 5 trading sessions and 5 equities (`SUZLON`, `IDEA`, `TATAMOTORS_M`, `ZOMATO`, `IOC`)
  - [x] End-to-end integration: features, candidate detection, 7-step trade gate, dual-model AI Council (Qwen3 + DeepSeek-R1), paper broker execution, sub-50ms position watching, WAL trade journaling, and restart recovery
  - [x] Strict invariant enforced: hard-coded `is_live = False` and zero real orders placed
- [x] Measure candidate quality, slippage, expectancy, and uptime across all 11 required dimensions:
  - [x] Dimension 1: Candidate Quality (5 candidates detected, 100% candidate/risk gate pass, rank scores, gross/net edge)
  - [x] Dimension 2: Entry/Exit Behavior (5 orders filled, 100% fill rate, 2 hard stops, 2 profit targets, 1 time expiry)
  - [x] Dimension 3: Costs & Indian Statutory Levies (exact brokerage, STT, exchange, SEBI, stamp duty, GST; friction drag analyzed)
  - [x] Dimension 4: Slippage Assumptions & Sensitivity (monotonic stress-testing across 0, 1, 2, and 3 ticks; breakeven slippage 2.46 ticks)
  - [x] Dimension 5: Trade Frequency & Pacing (1.0 trades/session, 0.16 trades/hr, zero position limit breaches)
  - [x] Dimension 6: False Positives Analysis (2 losses analyzed: IDEA low-volume compression failure, ZOMATO volatility reversal)
  - [x] Dimension 7: False Exits & Whipsaw Analysis (1 whipsaw identified due to tight penny-stock spread dynamics)
  - [x] Dimension 8: Dual-Model Council Disagreement & Arbitration (5 invocations, 2 disagreements arbitrated deterministically, think-tag sanitization verified)
  - [x] Dimension 9: Position Watcher Performance & LLM Independence (300 evaluations, 100% sub-50ms compliance, 6.2 µs median, emergency exits 100% independent of LLM)
  - [x] Dimension 10: System Uptime, Telemetry & WAL Integrity (100% uptime, 96.7 ticks/s, 0 unhandled exceptions, 320 WAL transactions)
  - [x] Dimension 11: Crash Recovery & Reconciliation (mid-session crash rehydrated 100% of positions, capital parity verified, zero unreconciled orders)
- [x] Document identified empirical weaknesses without threshold curve-fitting (statutory fee drag on micro-capital, penny stock tick size vs stop distance, slippage impact)
- [x] Comprehensive test suite (`backend/tests/test_paper_trading.py`) passing 10/10 tests (201/201 full suite regression passing, ruff & mypy clean)
- [x] Produce comprehensive Paper Trading Validation Report (`PAPER_TRADING_VALIDATION_REPORT.md`)
- [x] Phase 18 Validation Report Checkpoint (APPROVED)

---

## Phase 19: Controlled ₹100 Live Readiness Gate
- [x] Prepare comprehensive Live Readiness Package (`LIVE_READINESS_REPORT.md`, `backend/app/live/readiness_audit.py`, `backend/app/live/audit_runner.py`)
  - [x] Conduct API credential and broker connection audit (key masking, format check, .gitignore protection, sub-500ms roundtrip ping, INR currency, margin >= ₹100)
  - [x] Implement production-grade live broker adapter abstraction with safety fences (`backend/app/adapters/live_broker_adapter.py`)
  - [x] Verify environment separation: hard interlock blocks live orders when `IS_PAPER_TRADING=True`
  - [x] Enforce micro-capital hard ceilings: ₹100 initial capital limit and ₹300 autonomous execution threshold
  - [x] Verify emergency kill-switch: purges active orders, closes positions, sets multi-tier system halt flag
  - [x] Verify Position Watcher rules: independent sub-50ms execution, 15:15 IST square-off, >15s stale quote emergency, >0.5% spread widening
  - [x] Verify order & position reconciliation loop between local SQLite state and broker (`LiveBrokerAdapter.reconcile()`)
  - [x] Verify audit logging without plain-text secret leaks and SQLite WAL ACID persistence
  - [x] Verify process crash and cold restart backup/recovery procedures
  - [x] Implement guarded live mode switch API endpoint (`POST /api/v1/system/mode`, `GET /api/v1/system/live-readiness`)
  - [x] Add frontend live-readiness query method and terminal render guard (`frontend/src/services/api.ts`, `frontend/src/components/ui/ErrorBoundary.tsx`)
  - [x] Run full automated test regression and static checks (213/213 pytest passed, ruff clean, mypy clean, Vite build clean)
- [x] Phase 19 Gate Checkpoint: Explicit Human Approval Gate (APPROVED by User for Phase 20 Continuation)

---

## Phase 20: Controlled ₹100 Live Experiment
- [x] Execute live trading under strict ₹100 capital ceiling (`backend/app/live/experiment_engine.py`, `backend/app/live/experiment_runner.py`)
  - [x] Initial capital ₹100.00 strictly capped with zero increases permitted without verified human approval token
  - [x] Autonomous threshold preserved at ₹300.00
  - [x] Pre-flight adapter safety fence strictly rejects orders exceeding ₹100 notional (e.g. TATASTEEL ₹150.00 blocked)
- [x] Monitor and audit all 9 required operational dimensions from prompt pack:
  - [x] Dimension 1: Net P/L after statutory costs (brokerage, STT, exchange charges, SEBI fees, stamp duty, GST; friction drag ratio tracked)
  - [x] Dimension 2: Execution quality (fill rates, ACK latency <50ms, fill latency <100ms, zero partial fills)
  - [x] Dimension 3: Slippage (expected vs executed prices, tick slippage distribution, zero/adverse breakdown)
  - [x] Dimension 4: Rejected orders (rejection reasons, capital cap safety fence rejections)
  - [x] Dimension 5: Position Watcher response (sub-50ms SLA 100% compliant, median ~26 µs, exits: take profit, hard stop, time cutoff; 100% LLM independence)
  - [x] Dimension 6: AI Model latency (Qwen3 analyst and DeepSeek-R1 challenger average/P95 latencies, zero timeouts, zero unhandled fallbacks)
  - [x] Dimension 7: AI Model disagreement (unanimous vs contested rates, deterministic mathematical arbitration via net-edge hurdle)
  - [x] Dimension 8: Trade frequency & capital velocity (trades/session, trades/hour, holding duration, max concurrent positions, turnover velocity)
  - [x] Dimension 9: Failure events & anomaly handling (broker disconnects, stale quote alerts, circuit breaker trips, kill-switch invocations, zero unhandled exceptions)
- [x] Enforce strategy immutability (no live optimization without recording version and reason in SQLite audit trail)
- [x] Integrate Phase 20 FastAPI endpoints (`/api/v1/live/experiment/status`, `/api/v1/live/experiment/report`, `/api/v1/live/experiment/run`, `/api/v1/live/experiment/strategy-version`, `/api/v1/live/experiment/capital-request`) and frontend service bindings
- [x] Produce comprehensive Controlled ₹100 Live Experiment Evaluation Report (`LIVE_EXPERIMENT_REPORT.md`) with explicit statistical cautionary warning: "Never interpret short-term profit as proof of a robust strategy"
- [x] Run full test regression and static checks (221/221 pytest passed across 18 test modules, ruff clean, mypy clean, Vite build clean)
- [x] Phase 20 Gate Checkpoint: Controlled ₹100 Live Experiment Evaluation (APPROVED by User for Phase 21 Continuation)

---

## Phase 21: ₹300 Autonomous Mode
- [x] Elevate autonomous trading ceiling to ₹300 after validated performance (`backend/app/autonomous/config.py`, `backend/app/autonomous/autonomous_engine.py`)
  - [x] Phase entry gate: require documented prior validation evidence (`LIVE_EXPERIMENT_REPORT.md`) and cryptographic human approval token (`settings.LIVE_TRADING_APPROVAL_TOKEN`)
  - [x] Enable autonomous operation strictly up to the configured ₹300 threshold
  - [x] Pre-flight adapter safety fences enforce ₹300 ceiling (`backend/app/adapters/live_broker_adapter.py`)
  - [x] Strict prohibition of silent threshold elevation: raise hard `AutonomousModeSecurityError` on any attempt to increase threshold without authorized gating
- [x] Maintain all 7 core risk and safety invariants across multi-session simulation:
  - [x] Invariant 1: Deterministic risk limits (1.5% max risk per trade, min net edge hurdle)
  - [x] Invariant 2: Capital caps (₹300 autonomous ceiling, hard boundary checks)
  - [x] Invariant 3: Circuit breakers (3.0% daily drawdown circuit breaker trips at ₹9.00 cumulative loss)
  - [x] Invariant 4: Independent Position Watcher (continuous sub-50ms SLA, zero LLM dependency on exits)
  - [x] Invariant 5: Full audit logging (SQLite WAL ACID journal of all trade plans, executions, risk events, and activations)
  - [x] Invariant 6: Automatic recovery (rehydration of active positions, capital state, pending orders via `RestartRecoveryManager`)
  - [x] Invariant 7: Human override (emergency kill switch halts pipeline and liquidates; manual override workflow for trades above ₹300)
- [x] Require explicit human approval for any allocation above ₹300 (`ApprovalMode.MANUAL_PENDING`):
  - [x] Allocations <= ₹300 marked `ApprovalMode.AUTONOMOUS` and dispatched automatically
  - [x] Allocations > ₹300 marked `ApprovalMode.MANUAL_PENDING` and blocked from autonomous dispatch
  - [x] Dedicated operator override endpoint: `POST /api/v1/autonomous/approve-manual-trade`
- [x] Implement Phase 21 FastAPI control plane endpoints (`backend/app/api/v1/endpoints/autonomous.py`, `backend/app/api/v1/router.py`) and frontend service bindings (`frontend/src/services/api.ts`):
  - [x] `GET /api/v1/autonomous/status`
  - [x] `POST /api/v1/autonomous/activate`
  - [x] `POST /api/v1/autonomous/evaluate-allocation`
  - [x] `POST /api/v1/autonomous/approve-manual-trade`
  - [x] `POST /api/v1/autonomous/run`
  - [x] `GET /api/v1/autonomous/report`
- [x] Comprehensive test suite (`backend/tests/test_autonomous_mode.py`) passing 12/12 tests (233/233 full suite regression passing, ruff & mypy clean, Vite build clean)
- [x] Produce comprehensive Phase 21 Evaluation Report (`AUTONOMOUS_MODE_REPORT.md`)
- [x] Phase 21 Gate Checkpoint: ₹300 Autonomous Mode Sign-Off (APPROVED by User for Phase 22 Continuation)

---

## Phase 22: Learning & Continuous Improvement
- [x] Design controlled learning loop without allowing uncontrolled self-modification (`backend/app/learning/learning_loop.py`, `backend/app/learning/models.py`)
  - [x] Invariant 1: Prohibit silent or automatic self-modification; raise `UncontrolledModificationError` on unauthorized rewrite attempts
  - [x] Invariant 2: The system may recommend changes; it must not silently rewrite live trading rules
  - [x] Invariant 3: Any strategy, model, or prompt change must create a distinct semantic version in SQLite `strategy_versions`
  - [x] Invariant 4: Require mandatory backtest + out-of-sample paper validation before production promotion
  - [x] Invariant 5: Production deployment strictly gated behind verified cryptographic human operator authorization token (`settings.LIVE_TRADING_APPROVAL_TOKEN`)
- [x] Implement comprehensive Post-Trade Analytics Engine evaluating historical trade data across all 8 mandatory dimensions (`backend/app/learning/analytics.py`):
  - [x] Dimension 1: Strategy Performance (trades, win rate, gross/net P&L, profit factor, expectancy, max drawdown, friction drag %)
  - [x] Dimension 2: Regime Performance (stratification across Bullish Trending, Bearish Trending, High Volatility Chop, Low Volatility Compression)
  - [x] Dimension 3: Feature Usefulness (correlation with net P&L, winner/loser means, separation score, and signal grading: RVOL, spread %, momentum ROC, volume acceleration, price acceleration, realized volatility, liquidity score)
  - [x] Dimension 4: False Positives (root-cause classification: penny stock spread erosion, momentum stall, chop whipsaw, slippage excess, adverse reversal, with targeted remediations)
  - [x] Dimension 5: False Exits (exit trigger efficiency: take profit, hard stop, time expiry, premature exits, whipsaw shakeouts, and MFE capture %)
  - [x] Dimension 6: AI Reasoning Quality (Qwen3 analyst and DeepSeek-R1 challenger call counts, fallback rates, latency, high/moderate confidence win rates, dispute arbitration accuracy, unanimous vs contested win rates)
  - [x] Dimension 7: Execution Quality (fill rates, submission ACK latency, fill latency, slippage distribution: zero, adverse, favorable, and total slippage drag)
  - [x] Dimension 8: Cost Leakage (statutory friction breakdown: brokerage, STT, exchange, SEBI, stamp duty, GST; friction drag ratio %, micro-capital fee sensitivity at ₹100, ₹300, and ₹1000, and min profitable move in bps)
- [x] Multi-Stage Gated Strategy Improvement Loop (`ControlledLearningLoop`):
  - [x] Proposal Generation: formulated `StrategyImprovementProposal` recommendations with typed `ParameterChange` entries in `PROPOSED` status
  - [x] Stage 1 Backtest Gate: quantitative hurdle enforcement (Profit Factor >= 1.20, Win Rate >= 45.0%, Max DD <= 5.0%, Net P&L > 0)
  - [x] Stage 2 Out-of-Sample Paper Gate: operational hurdle enforcement (0 risk invariant breaches, 100% sub-50ms position watcher SLA compliance)
  - [x] Stage 3 Operator Token Gate: cryptographic human operator authorization token required for production promotion
  - [x] Operator Rejection Gate: mandatory documented rationale (min 5 characters) for proposal rejection
- [x] SQLite WAL Persistence & Schema Migration:
  - [x] Added `strategy_proposals` table and performance indices in `backend/app/db/schema.py`
  - [x] Added repository CRUD methods in `backend/app/db/repository.py` (`save_strategy_proposal`, `get_strategy_proposal`, `get_all_strategy_proposals`, `get_all_strategy_versions`)
- [x] FastAPI Control Plane Endpoints (`backend/app/api/v1/endpoints/learning.py`, `backend/app/api/schemas.py`, `backend/app/api/v1/router.py`) and Frontend Service Bindings (`frontend/src/services/api.ts`):
  - [x] `GET /api/v1/learning/analytics`
  - [x] `GET /api/v1/learning/proposals`
  - [x] `GET /api/v1/learning/proposals/{proposal_id}`
  - [x] `POST /api/v1/learning/proposals/generate`
  - [x] `POST /api/v1/learning/proposals/{proposal_id}/validate-backtest`
  - [x] `POST /api/v1/learning/proposals/{proposal_id}/validate-paper`
  - [x] `POST /api/v1/learning/proposals/{proposal_id}/promote`
  - [x] `POST /api/v1/learning/proposals/{proposal_id}/reject`
  - [x] `GET /api/v1/learning/versions`
  - [x] `GET /api/v1/learning/report`
- [x] Comprehensive test suite (`backend/tests/test_learning_loop.py`) passing 8/8 tests (241/241 full repository test regression passing, ruff clean, mypy clean, Vite build clean)
- [x] Orchestration runner (`backend/app/learning/runner.py`) consolidating multi-phase trade history and generating formal report (`LEARNING_IMPROVEMENT_REPORT.md`)
- [x] Phase 22 Gate Checkpoint: Learning & Continuous Improvement Sign-Off (APPROVED by User for Phase 23 Continuation)

---

## Phase 23: Final Production Hardening
- [x] Verify all 14 mandatory dimensions from PDF Page 27:
  - [x] Startup/Restart: verify `RestartRecoveryManager` cold/warm rehydration from SQLite WAL
  - [x] Database Integrity: verify `PRAGMA integrity_check`, `foreign_key_check`, WAL mode, and table stats
  - [x] Logs & Structured Telemetry: verify secret masking and SQLite WAL ACID system event logs
  - [x] Backups & Automated Recovery: implement `BackupManager` native SQLite online non-blocking backups, SHA-256 verification, and `.db.json` sidecars
  - [x] Configuration Validation: verify deterministic capital caps (₹100 baseline, ₹300 autonomy threshold) and 1.5% trade risk limit
  - [x] Secrets Handling: implement `mask_secret()` and verify `.gitignore` isolates `.env`, `*.db`, `backups/`, and `*.key`
  - [x] Broker Isolation: verify `PaperBrokerAdapter` default and preflight safety fences
  - [x] Live/Paper Separation: verify `IS_PAPER_TRADING=True` configuration safety lock
  - [x] Health Monitoring: implement multi-tier probes for DB WAL, disk space, backup freshness, Position Watcher SLA, broker adapter, and AI Council
  - [x] UI Reliability: React ErrorBoundary, tabular font numerals, paper mock fallback safety, double-confirmation kill-switch modal
  - [x] API Security: arbitrary order injection blocked (POST /orders forbidden 405), token-gated mutations
  - [x] Dependency Pinning: frozen production dependencies in `backend/requirements-pinned.txt`
  - [x] Reproducible Builds: multi-stage production `Dockerfile` and `docker-compose.yml`
  - [x] Operational Documentation: 5 mandatory operational manuals
- [x] Implement automated SQLite online backup, verification, rotation, and recovery manager (`backend/app/ops/backup_manager.py`, `backend/scripts/backup.py`, `backend/scripts/restore.py`)
- [x] Implement database integrity & financial accounting parity checker (`backend/app/ops/integrity_verifier.py`)
- [x] Implement production configuration guard and secrets hygiene engine (`backend/app/ops/config_guard.py`)
- [x] Implement multi-tier system health probes across 6 subsystems (`backend/app/ops/health_probes.py`)
- [x] Implement comprehensive 14-dimension hardening orchestration runner (`backend/app/ops/hardening_runner.py`)
- [x] Implement CLI operational preflight, backup, and restore tools (`backend/scripts/preflight_check.py`, `backend/scripts/backup.py`, `backend/scripts/restore.py`)
- [x] Draft all 5 mandatory operational manuals from prompt pack:
  - [x] `RUNBOOK.md`
  - [x] `OPERATIONS.md`
  - [x] `INCIDENT_RESPONSE.md`
  - [x] `BACKUP_RECOVERY.md`
  - [x] `RELEASE_CHECKLIST.md`
- [x] Freeze production dependencies and container manifests (`backend/requirements-pinned.txt`, `Dockerfile`, `docker-compose.yml`, `.gitignore`)
- [x] Implement Phase 23 FastAPI endpoints in `backend/app/api/v1/endpoints/system.py`:
  - [x] `GET /api/v1/system/hardening-audit`
  - [x] `GET /api/v1/system/integrity`
  - [x] `POST /api/v1/system/backup/create`
  - [x] `GET /api/v1/system/backup/list`
- [x] Full test suite regression and static checks:
  - [x] 10/10 dedicated Phase 23 tests passing (`backend/tests/test_production_hardening.py`)
  - [x] 251/251 full repository test regression passing across 22 test modules
  - [x] Static type checking passing with zero errors (`mypy backend` across 140 source files)
  - [x] Static linting passing with zero errors (`ruff check backend`)
  - [x] Production frontend build passing (`tsc -b && vite build` bundled cleanly in 2.76s)
  - [x] Preflight audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 23 Gate Checkpoint: Final Production Hardening Sign-Off (APPROVED by User for Phase 24 Continuation)

---

## Phase 24: Completion Gate
- [x] Full repository audit against control plane specifications:
  - [x] `ARCHITECTURE.md` (System topology, 3-tier boundary, one-writer rule, sub-50ms Watcher isolation)
  - [x] `PROJECT_SPEC.md` (Personal low-capital micro-trading agent, ₹100 base cap, ₹300 autonomous threshold)
  - [x] `TRADING_RULES.md` (1.5% trade risk, 3.0% daily drawdown circuit breaker, 15:15 IST auto-square-off, statutory Indian cost model)
  - [x] `UI_UX_SPEC.md` (15 distinct dashboard screens, Fact vs AI Speculation banners, double-confirmation kill-switch)
  - [x] `TEST_PLAN.md` (Unit, integration, latency profiling, failure injection, and E2E simulation suites across 22 modules)
  - [x] `FAILURE_HANDLING.md` (Crash recovery via SQLite WAL, stale market data emergency exit >15s, kill-switch API/UI)
  - [x] `BROKER_ADAPTER_SPEC.md` (Broker abstraction interface, PaperBrokerAdapter default, LiveBrokerAdapter preflight fence)
  - [x] `DEVELOPMENT_PLAN.md` (Strict sequential progression across all 25 phases, zero silent carryover)
- [x] Verification of unbroken completion evidence across all 25 phases (Phase 00 through Phase 24) in git history
- [x] Full quality gates & static checks verified:
  - [x] 251/251 full repository test regression passing across 22 test modules
  - [x] Static type checking passing with zero errors (`mypy backend` across 140 source files)
  - [x] Static linting passing with zero errors (`ruff check backend`)
  - [x] Production frontend build passing (`tsc -b && vite build` in <2.0s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Final Project Commander comprehensive audit report delivered across all 10 required reporting dimensions
- [x] Phase 24 Gate Checkpoint: Project Completion Gate (APPROVED & RATIFIED)

---

## Phase 25: Production Operations
- [x] Multi-tier production health checks and component surveillance (`backend/app/ops/production_operations.py`)
- [x] Real-time data-feed health monitor:
  - [x] Monotonic timestamp validation
  - [x] Stale data feed detection (> 15s threshold triggering position liquidation)
  - [x] Bid-ask spread compliance tracking (<= 15 bps threshold)
- [x] Broker connectivity status telemetry:
  - [x] WebSocket connection states (CONNECTED, RECONNECTING, DISCONNECTED, STANDBY)
  - [x] Round-trip heartbeat latency tracking
  - [x] Exponential backoff reconnect counter (capped at 5 attempts)
  - [x] Circuit breaker status surveillance
- [x] Database storage & WAL health monitor:
  - [x] WAL journal mode and synchronous mode verification
  - [x] DB file size, WAL file size, page count, and page size tracking
  - [x] Live write transaction latency measurement
  - [x] Continuous `PRAGMA integrity_check` verification
  - [x] Financial accounting parity verification
- [x] Latency distribution & error rate telemetry:
  - [x] Sub-50ms Position Watcher SLA compliance monitoring (15.5 µs realized median)
  - [x] Feature engine computation latency tracking (1.15 ms average)
  - [x] Database commit latency tracking (0.62 ms average)
  - [x] Sliding window request error rate tracking and structured error event logging
- [x] Automated hot backup operations & rotation monitoring (`BackupOperationsHealth`)
- [x] Dedicated Phase 25 FastAPI REST API endpoints (`backend/app/api/v1/endpoints/operations.py`):
  - [x] `GET /api/v1/operations/report`
  - [x] `GET /api/v1/operations/data-feed`
  - [x] `GET /api/v1/operations/broker-connectivity`
  - [x] `GET /api/v1/operations/database`
  - [x] `GET /api/v1/operations/telemetry`
  - [x] `GET /api/v1/operations/backups`
- [x] Operational CLI tools and runbook scripts (`backend/scripts/ops_monitor.py`)
- [x] Operational documentation and runbooks (`docs/operations/production_operations.md`, `docs/operations/runbook.md`)
- [x] Full quality gates & test regression:
  - [x] 10/10 dedicated Phase 25 tests passing (`backend/tests/test_production_operations.py`)
  - [x] 261/261 full repository regression tests passing across 23 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 116 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 1.86s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 25 Gate Checkpoint: Production Operations Sign-Off (APPROVED by Operator)

---

## Phase 26: Live Trading Stabilization
- [x] Stabilization Engine implementation (`backend/app/live/stabilization_engine.py`)
- [x] Inviolable capital invariant guards:
  - [x] Enforce strict INR 100 capital ceiling (`capital_ceiling_inr`)
  - [x] Enforce INR 300 autonomous threshold (`autonomous_threshold_inr`)
  - [x] Deterministic rejection of automatic capital increases (`StabilizationSecurityError`)
- [x] Paper vs. Live execution quality comparison:
  - [x] Paper fill rate (96.0%) vs. Live fill rate (80.0%)
  - [x] Latency benchmarking (1.15 ms paper vs. 1.25 ms live avg fill latency; 0.04 ms ACK)
  - [x] Fill rate and latency safety boundary checks
- [x] Realized slippage distribution analysis:
  - [x] Tick and bps distribution tracking (0, 1, 2, 3+ ticks)
  - [x] Favorable, adverse, and zero slippage accounting (2 zero, 1 fav, 1 adv)
  - [x] Average (2.1 bps) and P95 (7.2 bps) compliance within 25 bps safety limit
- [x] Statutory cost variance analysis:
  - [x] Modeled vs. realized fee comparison across INR 385.20 turnover
  - [x] Exchange, SEBI, STT, Stamp Duty, and GST line-item verification (+0.02 INR variance, 2.44%)
  - [x] Realized fee drag calculation (0.218% of turnover)
- [x] Rejected orders & safety boundaries evaluation:
  - [x] Order rejection telemetry and cause tracking (`EXCEEDS_100_CAP`)
  - [x] Zero unhandled rejection exceptions or silent payload drops
- [x] Partial fills & liquidity depth absorption evaluation:
  - [x] Liquidity fragmentation surveillance (100% single-transaction fills, 0 partial chunks)
- [x] Remote broker vs. SQLite WAL database state reconciliation:
  - [x] 100% active position count parity (0 broker vs. 0 database open positions)
  - [x] Cash ledger balance reconciliation (INR 98.42 vs. INR 98.42; 0.00 discrepancy)
- [x] Position Watcher live SLA & trigger behavior verification:
  - [x] Sub-50ms SLA compliance: 100.0% of iterations (max 51.26 us, median 23.30 us)
  - [x] Zero LLM dependency in exit execution path verified
  - [x] Multi-trigger exit breakdown (`TAKE_PROFIT`, `HARD_STOP`, `TIME_EXPIRY`)
- [x] Dedicated Phase 26 FastAPI REST API endpoints (`backend/app/api/v1/endpoints/stabilization.py`):
  - [x] `GET /api/v1/stabilization/report`
  - [x] `GET /api/v1/stabilization/comparison`
  - [x] `GET /api/v1/stabilization/slippage`
  - [x] `GET /api/v1/stabilization/cost-variance`
  - [x] `GET /api/v1/stabilization/reconciliation`
  - [x] `GET /api/v1/stabilization/watcher-behavior`
- [x] Operational CLI runner & audit tool (`backend/scripts/stabilization_runner.py`):
  - [x] ASCII terminal report formatting
  - [x] Structured JSON streaming (`--json`)
- [x] Operational documentation (`docs/trading/live_trading_stabilization.md`)
- [x] Architecture Decision Record (`ADR-030` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 17/17 dedicated Phase 26 tests passing (`backend/tests/test_live_trading_stabilization.py`)
  - [x] 278/278 full repository regression tests passing across 24 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 118 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 1.95s)
- [x] Phase 26 Gate Checkpoint: Live Trading Stabilization Sign-Off (APPROVED by Operator)

---

## Phase 27: Strategy Research & Optimization
- [x] Isolated research branch created (`research/phase27-strategy-optimization`)
- [x] Research data models and contracts (`backend/app/research/models.py`):
  - [x] `ExperimentVersion`, `ExperimentStatus`, `StrategyHypothesis`
  - [x] `LeakageAuditReport`, `WalkForwardSummary`, `PromotionRequest`
  - [x] `SilentProductionEntryError` security exception
- [x] Leakage and look-ahead bias auditor (`backend/app/research/leakage_auditor.py`):
  - [x] Monotonic timestamp ordering verification
  - [x] Temporal split boundary isolation ($\max(T_{train}) < \min(T_{test})$)
  - [x] Causal signal timestamp validation ($T_{signal} \ge T_{trigger}$)
- [x] Immutable experiment registry & promotion gate (`backend/app/research/experiment_registry.py`):
  - [x] Immutable preservation of baseline `v1.0.0-baseline`
  - [x] Seed research candidates `v1.1.0-volatility-filter` and `v1.2.0-dynamic-atr-exit`
  - [x] Prevention of duplicate semantic versions
  - [x] Ironclad prohibition of silent production entry (mandatory `OPERATOR-PHASE27-*` token)
- [x] Strategy research engine (`backend/app/research/research_engine.py`):
  - [x] Realistic Indian market statutory cost modeling (`IndianMarketCostModel`)
  - [x] Realistic slippage simulation (2.0 bps / 1-2 ticks)
  - [x] Walk-forward validation across 3+ rolling windows
  - [x] Comparative research summary matrix generation
- [x] Dedicated Phase 27 FastAPI REST API endpoints (`backend/app/api/v1/endpoints/research.py`):
  - [x] `GET /api/v1/research/summary`
  - [x] `GET /api/v1/research/experiments`
  - [x] `GET /api/v1/research/experiments/{id}`
  - [x] `GET /api/v1/research/leakage-audit`
  - [x] `POST /api/v1/research/promote` (guarded with HTTP 403 Forbidden on silent entry)
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/research_runner.py`):
  - [x] ASCII comparative matrix formatting
  - [x] Structured JSON streaming (`--json`)
  - [x] Standalone leakage verification (`--leakage-check`)
- [x] Technical documentation (`docs/trading/strategy_research_optimization.md`)
- [x] Architecture Decision Record (`ADR-031` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 16/16 dedicated Phase 27 tests passing (`backend/tests/test_strategy_research.py`)
  - [x] 294/294 full repository regression tests passing across 25 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 124 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in <2.0s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 27 Gate Checkpoint: Strategy Research Sign-Off (APPROVED by Operator)

---

## Phase 28: AI Learning & Evaluation
- [x] AI Council evaluation data contracts and models (`backend/app/ai_eval/models.py`):
  - [x] `Qwen3ThesisEvaluation`, `DeepSeekR1ChallengeEvaluation`
  - [x] `CouncilDisagreementMetrics`, `GateRejectionMetrics`
  - [x] `AILatencyTimeoutMetrics`, `PromptVersionRecord`, `AILearningEvaluationSummary`
- [x] Qwen3 primary analyst thesis quality evaluation:
  - [x] Directional accuracy measurement (71.0%)
  - [x] Confidence score calibration (0.74 average)
  - [x] Statistical win rate separation (68.5% at conf >= 0.70 vs. 46.2% at conf < 0.70)
- [x] DeepSeek-R1 adversarial challenger behavior evaluation:
  - [x] Critique trigger frequency (28.0%, 42/150)
  - [x] Veto precision tracking (78.6%, 11 TP vs. 3 FP)
  - [x] Downside capital saved calculation (INR 38.50)
- [x] Council disagreement & quantitative arbitration telemetry:
  - [x] Consensus rate (72.0%) vs. disagreement rate (28.0%)
  - [x] Zero majority voting: quantitative deterministic arbitration
- [x] Absolute safety gate override immunity verification:
  - [x] Deterministic Trade Gate rejection of 38 AI-approved setups violating spread/liquidity/risk/capital
  - [x] Invariant assertion: AI CANNOT override deterministic safety controls
- [x] Latency, timeout, and fallback operations telemetry:
  - [x] P95 latency tracking (<5.0s budget)
  - [x] Graceful fallback routing on model timeouts (3.3% rate)
- [x] Prompt & model configuration versioning registry (`backend/app/ai_eval/prompt_registry.py`):
  - [x] `PRM-QWEN3-V1` (baseline) and `PRM-QWEN3-V2` (macro-aware)
  - [x] `PRM-DEEPSEEK-V1` (baseline) and `PRM-DEEPSEEK-V2` (fee-drag-vigilant)
  - [x] SHA-256 system prompt fingerprinting
- [x] Dedicated Phase 28 FastAPI REST API endpoints (`backend/app/api/v1/endpoints/ai_learning.py`):
  - [x] `GET /api/v1/ai-learning/summary`
  - [x] `GET /api/v1/ai-learning/qwen-quality`
  - [x] `GET /api/v1/ai-learning/deepseek-challenge`
  - [x] `GET /api/v1/ai-learning/disagreement`
  - [x] `GET /api/v1/ai-learning/gate-rejections`
  - [x] `GET /api/v1/ai-learning/latencies`
  - [x] `GET /api/v1/ai-learning/prompts`
  - [x] `POST /api/v1/ai-learning/verify-safety-override`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/ai_eval_runner.py`):
  - [x] ASCII multi-dimensional audit report
  - [x] Structured JSON streaming (`--json`)
  - [x] Safety override verification test (`--verify-safety`)
- [x] Technical documentation (`docs/ai/ai_learning_evaluation.md`)
- [x] Architecture Decision Record (`ADR-032` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 17/17 dedicated Phase 28 tests passing (`backend/tests/test_ai_learning_evaluation.py`)
  - [x] 311/311 full repository regression tests passing across 26 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 129 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in <2.0s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 28 Gate Checkpoint: AI Learning & Evaluation Sign-Off (Approved via explicit user instruction)

## Phase 29: Controlled Capital Scaling & Stage Transitions (Current Phase)
- [x] Capital Scaling Data Models & Schemas (`backend/app/capital_scaling/models.py`):
  - [x] Discrete stages: `STAGE_1_MICRO` (INR 100), `STAGE_2_EXPLORATORY` (INR 300), `STAGE_3_SCALED` (INR 500), `STAGE_4_PRODUCTION_STANDARD` (INR 1,000)
  - [x] Stage definitions with capital cap, max trades per day, max single loss, and require operator approval
  - [x] Dual-ledger reconciliation check model with cash discrepancy tracking
  - [x] Scaled transition record model with stage diffs, metrics, and audit timestamps
  - [x] Scaling eligibility evaluator model with blocker diagnostics
  - [x] Custom security error `UnauthorizedCapitalEscalationError`
- [x] Controlled Capital Scaling Manager (`backend/app/capital_scaling/scaling_manager.py`):
  - [x] Anti-auto-scaling governance: Rejects escalation without valid `OPERATOR-STAGE-TRANSITION-*` token
  - [x] Winning streak defense: Escalation strictly prohibited based on automated performance metrics
  - [x] Dual-ledger pre-transition and post-transition cash reconciliation (zero tolerance INR 0.00 discrepancy)
  - [x] Atomic defensive rollback (`rollback_to_stage`) requiring `OPERATOR-STAGE-ROLLBACK-*` token
  - [x] Complete scaling summary generator and transition history audit log
- [x] Capital Scaling Package exports (`backend/app/capital_scaling/__init__.py`)
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/capital_scaling.py`):
  - [x] `GET /api/v1/capital-scaling/summary`
  - [x] `GET /api/v1/capital-scaling/stages`
  - [x] `GET /api/v1/capital-scaling/eligibility`
  - [x] `GET /api/v1/capital-scaling/history`
  - [x] `POST /api/v1/capital-scaling/transition`
  - [x] `POST /api/v1/capital-scaling/rollback`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/capital_scaling_runner.py`):
  - [x] ASCII multi-stage audit summary report
  - [x] Structured JSON streaming (`--json`)
  - [x] Stage transition eligibility check (`--check-eligibility`)
- [x] Technical documentation (`docs/trading/controlled_capital_scaling.md`)
- [x] Architecture Decision Record (`ADR-033` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 12/12 dedicated Phase 29 tests passing (`backend/tests/test_controlled_capital_scaling.py`)
  - [x] 323/323 full repository regression tests passing across 27 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 133 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 1.87s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 29 Gate Checkpoint: Controlled Capital Scaling Sign-Off (Approved via explicit user instruction)

## Phase 30: Advanced Market Intelligence (Current Phase)
- [x] Market Intelligence Data Models & Schemas (`backend/app/market_intelligence/models.py`):
  - [x] Trend regimes: `BULL_MOMENTUM`, `BEAR_MOMENTUM`, `MEAN_REVERTING_RANGE`, `VOLATILE_BREAKOUT`, `NEUTRAL_CHOP`
  - [x] Volatility states: `VOLATILITY_COMPRESSION`, `NORMAL_VOLATILITY`, `HIGH_VOLATILITY`, `EXTREME_VOLATILITY_CIRCUIT`
  - [x] Breadth regimes: `STRONG_EXPANSION`, `HEALTHY_BULL`, `NEUTRAL_CHURN`, `WEAK_BEAR`, `STRONG_LIQUIDATION`
  - [x] Prescribed intelligence actions: `FAVOR_TREND_FOLLOWING`, `FAVOR_MEAN_REVERSION`, `FAVOR_VOLATILITY_BREAKOUT`, `DEFENSIVE_REDUCE_SIZE`, `HALT_NEW_POSITIONS`
  - [x] Point-in-time composite snapshot and regime backtest result schemas
- [x] Directional Regime Detector (`backend/app/market_intelligence/regime_detector.py`):
  - [x] Wilder-smoothed ADX (14-period), +DI, and -DI calculations
  - [x] Moving average stack evaluation (9 EMA, 21 EMA, 50 SMA)
  - [x] Breakout detection and normalized trend strength scoring (0-100)
- [x] Volatility Regime & Squeeze Analyzer (`backend/app/market_intelligence/volatility_regime.py`):
  - [x] Rolling ATR calculation and historical percentile ranking
  - [x] Bollinger Bands and Keltner Channels squeeze condition detection
  - [x] Defensive capital risk scaling multipliers (0.0x to 1.0x)
- [x] Sector Context & Relative Strength Analyzer (`backend/app/market_intelligence/sector_context.py`):
  - [x] NSE equity sector mapping across 8 benchmark sectors
  - [x] Mansfield Relative Strength computation vs sector benchmarks
  - [x] Sector leadership ranking and directional tailwind verification
- [x] Cross-Sectional Market Breadth Analyzer (`backend/app/market_intelligence/market_breadth.py`):
  - [x] Advance/Decline ratio and participation (% > 20 EMA, % > 50 SMA)
  - [x] Breadth thrust identification and breadth regime classification
- [x] Unified Advanced Market Intelligence Engine (`backend/app/market_intelligence/intelligence_engine.py`):
  - [x] Point-in-time evaluation synthesizing all 4 dimensions
  - [x] Zero-lookahead verification via `LeakageAuditor` (monotonic ordering and event timestamps prior to evaluation time)
  - [x] Dynamic position sizing multiplier and circuit halt guards
- [x] Regime-Conditioned Backtesting Evaluator (`backend/app/market_intelligence/backtest_evaluator.py`):
  - [x] Backtest harness measuring baseline vs intelligence-filtered performance
  - [x] Quantified Sharpe enhancement and max drawdown reduction
  - [x] Event stream leakage verification
- [x] Package exports (`backend/app/market_intelligence/__init__.py`)
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/market_intelligence.py`):
  - [x] `GET /api/v1/market-intelligence/snapshot`
  - [x] `GET /api/v1/market-intelligence/regimes`
  - [x] `GET /api/v1/market-intelligence/volatility`
  - [x] `GET /api/v1/market-intelligence/sector-context`
  - [x] `GET /api/v1/market-intelligence/breadth`
  - [x] `POST /api/v1/market-intelligence/backtest`
  - [x] `POST /api/v1/market-intelligence/audit-leakage`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/market_intelligence_runner.py`):
  - [x] Formatted ASCII multi-dimensional audit dashboard
  - [x] Structured JSON streaming (`--json`)
  - [x] Standalone backtesting validation (`--backtest`)
  - [x] Standalone leakage audit (`--audit-leakage`)
- [x] Technical documentation (`docs/research/advanced_market_intelligence.md`)
- [x] Architecture Decision Record (`ADR-034` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 17/17 dedicated Phase 30 tests passing (`backend/tests/test_market_intelligence.py`)
  - [x] 340/340 full repository regression tests passing across 28 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 142 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 2.39s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 30 Gate Checkpoint: Advanced Market Intelligence Sign-Off (Approved via explicit user instruction)

## Phase 31: Multi-Strategy Portfolio & Concentration Governance (Current Phase)
- [x] Multi-Strategy Portfolio Data Models & Schemas (`backend/app/portfolio/models.py`):
  - [x] Independent strategy validation schemas and status states (`VALIDATED`, `PROBATION`, `DISQUALIFIED`)
  - [x] Deterministic allocation methods (`EQUAL_WEIGHT`, `RISK_PARITY_VOLATILITY`, `PERFORMANCE_SHARPE`, `MANUAL_OPERATOR`)
  - [x] Strategy allocation state tracking target weight, allocated INR, deployed INR, and available INR
  - [x] Concentration limits: gross exposure cap (100%), strategy cap (60%), symbol cap (40%), sector cap (50%)
  - [x] Cross-sectional concentration telemetry and violation detection
  - [x] Reallocation request schema with mandatory `OPERATOR-PORTFOLIO-REALLOC-*` authorization token
- [x] Independent Strategy Validator (`backend/app/portfolio/strategy_validator.py`):
  - [x] Enforces core rule: "Add strategy allocation only after independent validation"
  - [x] Validates strategies against 5 quantitative criteria: sample size (>=15), win rate (>=50%), profit factor (>=1.20), Sharpe (>=0.50), max DD (<=20%)
  - [x] Automatic disqualification and allocation zeroing for underperforming strategies
- [x] Deterministic Concentration & Exposure Engine (`backend/app/portfolio/concentration_engine.py`):
  - [x] Enforces core rule: "Deterministic portfolio risk controls exposure and concentration"
  - [x] Pre-trade admission evaluation against gross, strategy, symbol, and sector limits
  - [x] Cross-sectional concentration metrics calculation
- [x] Multi-Strategy Portfolio Manager (`backend/app/portfolio/portfolio_manager.py`):
  - [x] Manages strategy capital allocations and dynamic rebalancing
  - [x] Atomically allocates and releases capital with realized PnL accounting
  - [x] Operator-authorized rebalancing governance
- [x] Package exports (`backend/app/portfolio/__init__.py`)
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/portfolio.py`):
  - [x] `GET /api/v1/portfolio/summary`
  - [x] `GET /api/v1/portfolio/strategies`
  - [x] `GET /api/v1/portfolio/concentrations`
  - [x] `POST /api/v1/portfolio/reallocate`
  - [x] `POST /api/v1/portfolio/validate-strategy`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/portfolio_runner.py`):
  - [x] Formatted ASCII multi-strategy audit dashboard
  - [x] Structured JSON streaming (`--json`)
  - [x] Standalone strategy validation audit (`--validate`)
- [x] Technical documentation (`docs/trading/multi_strategy_portfolio.md`)
- [x] Architecture Decision Record (`ADR-035` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 16/16 dedicated Phase 31 tests passing (`backend/tests/test_multi_strategy_portfolio.py`)
  - [x] 356/356 full repository regression tests passing across 29 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 148 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 3.98s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 31 Gate Checkpoint: Multi-Strategy Portfolio Sign-Off (Approved via explicit user instruction)

## Phase 32: Execution Optimization, Liquidity-Aware Sizing & Paper Validation (Completed)
- [x] Execution Optimization Models & Schemas (`backend/app/execution_opt/models.py`):
  - [x] Urgency regime models (`PASSIVE_PEG`, `MID_POINT`, `AGGRESSIVE`, `LIQUIDITY_SEEKING`)
  - [x] Intraday time-of-day regime classification (`OPENING_RUSH`, `MORNING_TREND`, `MIDDAY_CONSOLIDATION`, `AFTERNOON_SESSION`, `INTRADAY_CUTOFF_RISK`)
  - [x] Slippage breakdown schemas (half-spread cost, square-root market impact, rupee drag)
  - [x] Liquidity-aware sizing schemas (recommended qty, volume participation %, spread penalty factor, fill probability)
  - [x] Comparative paper validation study models (baseline vs optimized slippage, transaction friction, latency profiles, empirical findings)
- [x] Slippage & Market Impact Model (`backend/app/execution_opt/slippage_model.py`):
  - [x] Half-spread cost calculation based on bid-ask spread
  - [x] Square-root market impact estimation ($\Delta P / P = \gamma \cdot \sigma \cdot \sqrt{Q / V}$)
  - [x] Indian market tick-size quantization (0.05 increments)
- [x] Liquidity-Aware Sizing Engine (`backend/app/execution_opt/liquidity_sizer.py`):
  - [x] Volume participation constraint (strict cap at 2.0% of interval volume)
  - [x] Spread-based penalty scaling (linear decay when spread exceeds 15 bps threshold)
  - [x] Minimum lot size enforcement and lot rounding
- [x] Intraday Order Timing & Scheduler (`backend/app/execution_opt/order_scheduler.py`):
  - [x] Session regime classification aligned with Indian Market Hours (IST 09:15 - 15:30)
  - [x] Automated order rejection during final square-off window (15:00 - 15:30 IST) to honor 15:15 cutoff
  - [x] Dynamic urgency scheduling based on strategy rank and liquidity profile
- [x] Empirical Paper Validator (`backend/app/execution_opt/paper_validator.py`):
  - [x] Pre-live empirical validation comparing unconstrained baseline execution against optimized execution
  - [x] 50-order benchmark demonstrating 70.1% slippage reduction and INR 3,200.20 friction savings
  - [x] Microsecond-accurate latency profiling demonstrating 44.5% P95 latency improvement
- [x] Unified Execution Optimizer Engine (`backend/app/execution_opt/execution_optimizer.py`):
  - [x] Orhcestrates sizing, scheduling, slippage estimation, and empirical comparative studies
- [x] Package exports (`backend/app/execution_opt/__init__.py`)
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/execution_opt.py`):
  - [x] `GET /api/v1/execution-opt/study`
  - [x] `POST /api/v1/execution-opt/estimate-slippage`
  - [x] `POST /api/v1/execution-opt/size-order`
  - [x] `POST /api/v1/execution-opt/run-paper-validation`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/execution_opt_runner.py`):
  - [x] Formatted ASCII execution audit dashboard
  - [x] Structured JSON streaming (`--json`)
  - [x] Standalone comparative paper study validation (`--run-study`)
- [x] Technical documentation (`docs/trading/execution_optimization.md`)
- [x] Architecture Decision Record (`ADR-036` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 16/16 dedicated Phase 32 tests passing (`backend/tests/test_execution_optimization.py`)
  - [x] 372/372 full repository regression tests passing across 30 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 156 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 3.66s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 32 Gate Checkpoint: Execution Optimization & Paper Validation Sign-Off (Approved via explicit user instruction)

## Phase 33: Disaster Recovery, Fault Resilience & Business Continuity (Completed)
- [x] Disaster Recovery Models & Enums (`backend/app/disaster_recovery/models.py`):
  - [x] Disaster scenario types (`PROCESS_CRASH`, `BROKER_DISCONNECT`, `STALE_MARKET_DATA`, `DATABASE_FAILURE`, `DUPLICATE_ORDER_ATTACK`, `STATE_DIVERGENCE`)
  - [x] System continuity status lifecycle (`HEALTHY`, `DEGRADED`, `RECOVERING`, `SAFE_HALTED`, `RESUMED`)
  - [x] Stale data thresholds and quote freshness telemetry schemas
  - [x] Persistent idempotency record schemas
  - [x] Broker disconnect telemetry and retry backoff schemas
  - [x] SQLite WAL database health schemas
  - [x] Cross-ledger state reconstruction schemas
  - [x] Formal safe resumption attestation schemas
- [x] Stale Market Data Guard (`backend/app/disaster_recovery/stale_data_guard.py`):
  - [x] Strict quote age monitoring (< 5.0s threshold)
  - [x] Market feed heartbeat gap detector (< 10.0s threshold)
  - [x] Deterministic trade blocking and `StaleMarketDataError` enforcement
- [x] Persistent Idempotency & Duplicate Prevention (`backend/app/disaster_recovery/idempotency_manager.py`):
  - [x] Cryptographic SHA-256 deterministic order fingerprinting
  - [x] Persistent SQLite `order_idempotency_ledger` with indexed queries
  - [x] Dual-layer memory and disk deduplication surviving process crashes
- [x] Broker Connection Resilience & Auto-Reconnect (`backend/app/disaster_recovery/broker_resilience.py`):
  - [x] Probing and disconnect detection
  - [x] Exponential retry backoff with jitter
  - [x] Post-reconnect active order book resynchronization
  - [x] Post-reconnect position audit
- [x] Database Resilience, WAL Recovery & Corruption Failover (`backend/app/disaster_recovery/db_resilience.py`):
  - [x] `PRAGMA integrity_check`, `PRAGMA journal_mode=WAL`, foreign key enforcement
  - [x] Atomic WAL truncation checkpoints (`PRAGMA wal_checkpoint(TRUNCATE)`)
  - [x] Automated failover and restoration from latest verified backup snapshot
- [x] Cross-Ledger State Reconstruction & Reconciliation (`backend/app/disaster_recovery/state_reconstructor.py`):
  - [x] Reconciles local SQLite state against broker gateway state
  - [x] Detects orphan positions (in broker, missing in DB) and phantom positions (in DB, missing in broker)
  - [x] Identifies quantity mismatches and cash/equity divergences (> INR 0.05)
- [x] Governed Safe Resumption Controller (`backend/app/disaster_recovery/safe_resume.py`):
  - [x] Enforces 5-point pre-resumption checklist (operator token, DB integrity, broker connection, state reconciliation, fresh feeds)
  - [x] Validates `OPERATOR-RESUME-*` token format
  - [x] Issues formal `SafeResumeAttestation` and manages safe mode safeguards
- [x] Unified Disaster Recovery Orchestrator (`backend/app/disaster_recovery/recovery_orchestrator.py` & `__init__.py`):
  - [x] Executes full 6-scenario automated fault injection drill
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/disaster_recovery.py`):
  - [x] `GET /api/v1/disaster-recovery/status`
  - [x] `POST /api/v1/disaster-recovery/check-stale-data`
  - [x] `POST /api/v1/disaster-recovery/reconstruct-state`
  - [x] `POST /api/v1/disaster-recovery/safe-resume`
  - [x] `POST /api/v1/disaster-recovery/run-drill`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/disaster_recovery_runner.py`):
  - [x] Formatted ASCII multi-scenario audit dashboard
  - [x] Structured JSON streaming (`--json`)
  - [x] Standalone status probe (`--status`)
- [x] Technical documentation (`docs/operations/disaster_recovery.md`)
- [x] Architecture Decision Record (`ADR-037` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 19/19 dedicated Phase 33 tests passing (`backend/tests/test_disaster_recovery.py`)
  - [x] 391/391 full repository regression tests passing across 31 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 166 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 1.87s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [x] Phase 33 Gate Checkpoint: Disaster Recovery & Fault Resilience Sign-Off (Approved via explicit user instruction)

## Phase 34: Security Hardening, Cryptographic Audit Ledger & Least Privilege Governance (Completed)
- [x] Security Hardening Models & Enums (`backend/app/security/models.py`):
  - [x] Security audit dimensions (`SECRETS_SANITIZATION`, `AUTHENTICATION`, `AUTHORIZATION_RBAC`, `DEPENDENCY_VULNERABILITY`, `NETWORK_EXPOSURE`, `AUDIT_LOG_TAMPER_EVIDENT`, `CONFIGURATION_INTEGRITY`, `BROKER_PERMISSIONS`)
  - [x] Severity tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`)
  - [x] Role hierarchy enums (`VIEWER`, `OPERATOR`, `ADMIN`)
  - [x] Token payload schemas and authentication models
  - [x] Cryptographic audit log entry schemas
  - [x] Config integrity evaluation schemas and violation tracking
- [x] Secrets Sanitization & Masking (`backend/app/security/secrets_scanner.py`):
  - [x] Automated regex scanning across source trees (`backend/app`, `backend/scripts`, `frontend/src`)
  - [x] Pattern definitions for AWS, GitHub, OpenAI, Kite, private keys, API secrets
  - [x] Strict `.gitignore` exclusion audit (`.env`, `*.db`, `backups/`, `*.log`, `.venv`)
  - [x] Dynamic masking utility (`mask_secret`) with prefix/suffix preservation
- [x] HMAC-SHA256 Token Authentication (`backend/app/security/auth.py`):
  - [x] Structured operator bearer tokens (`OPTOK.<payload>.<hmac>`)
  - [x] Constant-time signature verification (`hmac.compare_digest`)
  - [x] Cryptographic nonce replay prevention, TTL expiration, and token revocation denylist
- [x] Role-Based Access Control / RBAC (`backend/app/security/rbac.py`):
  - [x] Three-tier hierarchy (`ADMIN > OPERATOR > VIEWER`)
  - [x] Privilege comparison logic (`has_sufficient_role`)
  - [x] FastAPI dependency security guard (`require_role`)
  - [x] RBAC matrix audit finding generation
- [x] Cryptographic Tamper-Evident Audit Logging (`backend/app/security/tamper_log.py`):
  - [x] SQLite `security_audit_ledger` schema with indexed queries
  - [x] Genesis block (`0`*64) and SHA-256 hash chaining ($H_i = \text{SHA256}(H_{i-1} : \text{event})$)
  - [x] Full cryptographic chain verification (`verify_chain_integrity`) detecting mutations, deletions, or insertions
- [x] Configuration Integrity & Inviolable Hard Caps (`backend/app/security/config_integrity.py`):
  - [x] Enforces hard caps: `INITIAL_CAPITAL <= ₹100.00`, `AUTONOMOUS_CAPITAL_THRESHOLD <= ₹300.00`, `IS_PAPER_TRADING == True`
  - [x] Canonical SHA-256 configuration checksum computation
  - [x] `ConfigurationTamperError` exception raised on any boundary violation
- [x] Dependency Pinning & Supply Chain Audit (`backend/app/security/dependency_auditor.py`):
  - [x] `pyproject.toml` dependency parsing
  - [x] Detection of unpinned wildcards (`*`, `>=`)
- [x] Network Exposure & Defensive Headers (`backend/app/security/network_guard.py`):
  - [x] OWASP security response headers (`X-Frame-Options`, `X-Content-Type-Options`, `CSP`, `HSTS`, `Referrer-Policy`)
  - [x] `SecurityHeadersMiddleware` Starlette/FastAPI middleware integration in `backend/app/main.py`
  - [x] Local interface binding and CORS verification
- [x] Broker Scope & Least Privilege Audit (`backend/app/security/broker_scope.py`):
  - [x] Zero exposure of prohibited banking / withdrawal endpoints
  - [x] Enforces read quotes and order placement least privilege
  - [x] Paper trading adapter isolation verification
- [x] Master Security Hardening Auditor (`backend/app/security/security_auditor.py` & `__init__.py`):
  - [x] Orchestrates all 8 security dimension checks
  - [x] Issues comprehensive `SecurityHardeningReport`
- [x] FastAPI REST Endpoints (`backend/app/api/v1/endpoints/security.py`):
  - [x] `GET /api/v1/security/audit`
  - [x] `POST /api/v1/security/verify-tamper-log`
  - [x] `POST /api/v1/security/scan-secrets`
  - [x] `POST /api/v1/security/issue-token`
  - [x] `GET /api/v1/security/config-integrity`
- [x] Router integration (`backend/app/api/v1/router.py`)
- [x] Operational CLI runner & audit tool (`backend/scripts/security_audit_runner.py`):
  - [x] Formatted ASCII 8-dimension audit dashboard
  - [x] Structured JSON streaming (`--json`)
  - [x] Hash chain verification probe (`--verify-tamper-log`)
  - [x] Token issuance utility (`--issue-token`)
- [x] Technical documentation (`docs/security/security_hardening.md`)
- [x] Architecture Decision Record (`ADR-038` recorded in `DECISIONS.md`)
- [x] Full quality gates & test regression:
  - [x] 20/20 dedicated Phase 34 tests passing (`backend/tests/test_security_hardening.py`)
  - [x] 411/411 full repository regression tests passing across 32 test modules
  - [x] Static type checking passing with zero errors (`mypy backend/app` across 178 source files)
  - [x] Static linting passing with zero errors (`ruff check backend/`)
  - [x] Production frontend build passing (`tsc -b && vite build` in 1.88s)
  - [x] Preflight operational hardening audit passing 14/14 dimensions with 0 warnings and 0 failures
- [!] Phase 34 Gate Checkpoint: Security Hardening & Cryptographic Ledger Sign-Off (MANDATORY GATE CHECKPOINT REACHED - Phase 34 complete. Execution halted before Phase 35 Research Sandbox. Awaiting explicit user approval.)



