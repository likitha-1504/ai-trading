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
- [!] Phase 14 Phase Gate Checkpoint (Awaiting User Sign-off)

---

## Phase 15: React Dashboard Implementation
- [ ] Prepare Codex delegation spec for React + Tailwind terminal
- [ ] Codex: Implement 15 screens, status badges, and real-time feeds
- [ ] Antigravity: Verify UI separation of system facts from AI suggestions
- [!] Phase 15 Phase Gate Checkpoint

---

## Phase 16: Integration, Failure Injection & QA
- [ ] Antigravity QA Suite: Inject network drops, stale data, and LLM timeouts
- [ ] Verify Position Watcher intervention during simulated model crashes
- [!] Phase 16 Release Readiness Gate

---

## Phase 17: Performance & Latency Optimization
- [ ] Profile execution bottlenecks across feature calculation and DB writes
- [ ] Optimize measured hotspots without sacrificing safety checks
- [!] Phase 17 Performance Gate Checkpoint

---

## Phase 18: Paper Trading Validation
- [ ] Run full end-to-end system in paper mode over a fixed test window
- [ ] Measure candidate quality, slippage, expectancy, and uptime
- [!] Phase 18 Validation Report Checkpoint

---

## Phase 19: Controlled ₹100 Live Readiness Gate
- [ ] Conduct API credential and broker connection audit
- [ ] Verify kill-switch, capital caps, and emergency exit procedures
- [!] Explicit Human Approval Gate (Mandatory)

---

## Phase 20: ₹100 Controlled Live Experiment
- [ ] Execute live trading under strict ₹100 capital ceiling
- [ ] Monitor net P/L after taxes/brokerage and model latencies
- [!] Phase 20 Experiment Evaluation

---

## Phase 21: ₹300 Autonomous Mode
- [ ] Elevate autonomous trading ceiling to ₹300 after validated performance
- [ ] Require explicit human approval for any allocation above ₹300
- [!] Phase 21 Sign-Off

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
