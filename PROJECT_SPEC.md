# Project Specification: AI Micro-Trading Agent

## 1. Project Mission & Objectives

The goal of the **AI Micro-Trading Agent** is to build a reliable, local-first, low-cost autonomous trading agent capable of operating on micro-capital allocations. 

### Key Constraints & Tenets
- **₹0 Development Spend**: Utilizes free, open-source local software, local Ollama LLM inferences, and self-hosted tooling.
- **Deterministic Capital Preservation**: Capital safety precedes profit generation. The agent will never risk more than allowed by hard-coded stop-loss and daily drawdown thresholds.
- **Local-First Execution**: The application runs entirely on the user's workstation without relying on third-party cloud orchestration or external paid SaaS APIs.
- **Explainability**: Every action taken by the system (screening, thesis generation, gating, order submission, exit) is recorded with full auditability and trace history.

---

## 2. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Execution Engine & Backend** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn | High performance, async I/O, rigorous type checking and data validation. |
| **Persistence Layer** | SQLite 3 (WAL mode, foreign keys enabled) | Embedded, zero-maintenance, ACID-compliant, fast sequential and concurrent reads. |
| **AI Reasoning Engine** | Local Ollama (`Qwen3` + `DeepSeek-R1`) | Dual qualitative debate: hypothesis generation vs adversarial stress-testing. |
| **Coding Worker** | Codex CLI | Automated task implementation under Antigravity orchestration. |
| **Frontend & Terminal** | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide Icons | Responsive, dark-first, low-latency trader dashboard with strict fact/AI visual separation. |
| **Data & Backtesting** | Pandas, NumPy, custom event-driven backtesting engine | No lookahead bias, point-in-time calculation correctness, walk-forward validation. |

---

## 3. Financial & Capital Rules

- **Initial Sandbox Capital**: ₹100.
- **Autonomous Ceiling**: ₹300.
- **Approval Escalation**: Any trade or cumulative portfolio size exceeding ₹300 mandates explicit human-in-the-loop approval.
- **Fee Model**: All trade projections must calculate full friction prior to execution:
  - Brokerage (fixed or %)
  - Securities Transaction Tax (STT)
  - Exchange transaction charges
  - SEBI turnover fees
  - Stamp duty
  - Goods and Services Tax (GST)
  - Dynamic slippage allowance
- **Net Edge Requirement**: No trade will be authorized unless the expected net profit after all frictional costs exceeds a configurable statistical hurdle rate.

---

## 4. Phased Lifecycle

The project adheres to a sequential 25-phase roadmap (Phase 00 through Phase 24):
1. **Phases 00–02**: Control Plane, Architecture Lock, UI/UX Design System.
2. **Phases 03–09**: Market Data, Feature Engineering, Strategy, Safety, Capital, Broker Abstraction, Backtesting.
3. **Phases 10–12**: Qwen3 Integration, DeepSeek-R1 Challenger, Deterministic Trade Gate.
4. **Phases 13–15**: Database WAL/Audit, FastAPI API Contracts, React Terminal.
5. **Phases 16–18**: Failure Injection, Latency Optimization, Paper Trading Validation.
6. **Phases 19–21**: Live Readiness Check, ₹100 Live Experiment, ₹300 Autonomous Operation.
7. **Phases 22–24**: Continuous Improvement, Production Hardening, Final Completion Gate.
