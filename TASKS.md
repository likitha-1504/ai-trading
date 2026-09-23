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
- [ ] Prepare Codex delegation spec for `BrokerAdapter` and `PaperAdapter`
- [ ] Codex: Implement order lifecycle state machine and reconciliation
- [ ] Antigravity: Verify broker abstraction purity and idempotency
- [!] Phase 08 Phase Gate Checkpoint

---

## Phase 09: Backtesting + Paper Trading Loop
- [ ] Prepare Codex delegation spec for event-driven backtesting
- [ ] Codex: Implement simulator, slippage model, and performance metrics
- [ ] Antigravity: Verify backtest/paper strategy interface symmetry
- [!] Phase 09 Phase Gate Checkpoint

---

## Phase 10: Qwen3 Analyst Integration
- [ ] Prepare Codex delegation spec for Qwen3 integration
- [ ] Codex: Implement structured JSON schema, prompt templates, and timeout handlers
- [ ] Antigravity: Verify AI output validation and fallback behavior
- [!] Phase 10 Phase Gate Checkpoint

---

## Phase 11: DeepSeek-R1 Challenger Layer
- [ ] Prepare Codex delegation spec for adversarial challenger
- [ ] Codex: Implement critique prompts, stress testing, and structured schema
- [ ] Antigravity: Verify deterministic gate retains final decision authority
- [!] Phase 11 Phase Gate Checkpoint

---

## Phase 12: Deterministic Trade Gate + AI Council
- [ ] Prepare Codex delegation spec for Trade Gate pipeline
- [ ] Codex: Assemble Candidate -> AI Council -> Risk Gate -> TradePlan pipeline
- [ ] Antigravity: Verify that AI models cannot directly trigger order submissions
- [!] Phase 12 Phase Gate Checkpoint

---

## Phase 13: Database, Journal & Performance
- [ ] Prepare Codex delegation spec for SQLite WAL schema and journaling
- [ ] Codex: Implement persistence, audit trails, and restart recovery
- [ ] Antigravity: Verify ACID compliance and decision reproducibility
- [!] Phase 13 Phase Gate Checkpoint

---

## Phase 14: FastAPI Backend + API Contracts
- [ ] Prepare Codex delegation spec for FastAPI endpoints
- [ ] Codex: Implement query/read endpoints and guarded command APIs
- [ ] Antigravity: Verify endpoint security and live-trading guardrails
- [!] Phase 14 Phase Gate Checkpoint

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
