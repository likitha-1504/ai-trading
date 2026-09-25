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
- [!] Phase 21 Gate Checkpoint: ₹300 Autonomous Mode Sign-Off (MANDATORY GATE CHECKPOINT REACHED - System strictly halted awaiting explicit operator sign-off before entering Phase 22)

---

## Phase 22: Learning & Continuous Improvement
- [ ] Implement post-trade analytics and versioned strategy improvement loop
- [ ] Enforce immutability of live strategy rules without prior paper validation
- [!] Phase 22 Sign-Off

---

## Phase 23: Final Production Hardening
- [ ] Draft operational documentation (`RUNBOOK.md`, `OPERATIONS.md`, etc.)
- [ ] Verify automated backups and system recovery procedures
- [!] Phase 23 Sign-Off

---

## Phase 24: Completion Gate
- [ ] Full repository audit against control plane specifications
- [ ] Final Project Commander sign-off report
