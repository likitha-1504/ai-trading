# Architecture Decision Records (ADR Summary)

This log summarizes the foundational architectural choices established and ratified across Phases 00 through 24.

---

| ADR | Title | Decision & Rationale | Status |
| :--- | :--- | :--- | :---: |
| **ADR-001** | Local-First Architecture | Operate 100% on local hardware with ₹0 cloud recurring costs to guarantee zero infrastructure overhead. | Accepted |
| **ADR-002** | Deterministic Risk Supremacy | Isolate Trade Gate & Position Watcher from LLMs. Risk rules are pure deterministic Python functions. | Accepted |
| **ADR-003** | SQLite WAL Persistence | Use SQLite in Write-Ahead Logging (WAL) mode for lightweight, ACID-compliant local zero-ops persistence. | Accepted |
| **ADR-004** | Dual-LLM Advisory Council | Separate generative hypothesis generation (Qwen3) from adversarial stress testing (DeepSeek-R1). | Accepted |
| **ADR-005** | Three-Tier Process Boundaries | Strictly isolate UI (React), Control Plane (FastAPI), and Watchdog Execution (Threaded Watcher). | Accepted |
| **ADR-006** | Normalized Contract Schemas | Unify all inter-component payloads into Pydantic models with `Decimal` for financial quantities. | Accepted |
| **ADR-007** | Sub-50ms Watcher SLA | Run Position Watcher on an independent execution loop without network or disk bottlenecks. | Accepted |
| **ADR-008** | Statutory Indian Cost Modeling | Implement granular cost calculations (Brokerage, STT, Exchange fees, SEBI, GST, Stamp Duty). | Accepted |
| **ADR-009** | Blocked Arbitrary Order API | Exclude `POST /orders` from FastAPI routes (HTTP 405) to prevent accidental unvetted order injection. | Accepted |
| **ADR-010** | Paper Broker by Default | Default `IS_PAPER_TRADING = True` with multi-step authorization fences required for live trading. | Accepted |
| **ADR-011** | Staged Micro-Capital Limits | Limit initial live experiment to ₹100; autonomous operations strictly capped at ₹300. | Accepted |
| **ADR-012** | One-Writer Governance Rule | Enforce single-writer discipline for all autonomous code agents to eliminate merge conflicts. | Accepted |
| **ADR-013** | Online Hot Backups | Use SQLite online backup API (`sqlite3_backup`) with SHA-256 verification and atomic swap. | Accepted |
| **ADR-014** | Fact vs Hypothesis UI Segregation | UI explicitly colors and tags deterministic facts vs probabilistic AI reasoning to avoid bias. | Accepted |
| **ADR-015** | Post-Trade Learning Gate | Post-trade analytics generate versioned strategy recommendations without automatic live promotion. | Accepted |
| **ADR-016** | 15:15 IST Mandatory Square-Off | Automatically liquidate intraday equity positions prior to official exchange cutoff (15:30 IST). | Accepted |
| **ADR-017** | Daily Drawdown Circuit Breaker | Immediately halt trading session if cumulative daily realized + unrealized loss touches 3.0%. | Accepted |
| **ADR-018** | Stale Market Data Emergency Exit | Mark data feed stale if no tick received within 15 seconds; trigger fast-path position closure. | Accepted |
| **ADR-019** | Non-Committal of Secrets | Enforce strict Git exclusion of `.env`, `.db`, `backups/`, and runtime logs with regex log sanitization. | Accepted |
| **ADR-020** | Dual-Confirmation Kill Switch | Require explicit confirmation payload and operator token to trigger system-wide liquidation. | Accepted |
| **ADR-021** | Preflight Audit Gate | Require passing 14-dimension operational preflight check before enabling live engine. | Accepted |
| **ADR-022** | Pinned Dependencies | Pin exact production dependencies in `requirements-pinned.txt` to guarantee reproducible builds. | Accepted |
| **ADR-023** | Separation of BUY & SELL Engines | Entry signals pass through AI Council; exit signals are evaluated strictly by Position Watcher. | Accepted |
| **ADR-024** | Disagreement Arbitration Matrix | When Qwen3 and DeepSeek-R1 disagree, the trade is rejected unless consensus exceeds 0.70 threshold. | Accepted |
| **ADR-025** | Restart State Rehydration | On boot, reconstruct position, order, and capital state from SQLite WAL prior to tick ingestion. | Accepted |
| **ADR-026** | Mock vs Paper vs Live Isolation | Broker abstraction provides identical interface across Mock, Paper, and Live adapters. | Accepted |
| **ADR-027** | Multi-Stage Container Manifests | Provide Dockerfile and compose manifests for reproducible containerized deployments. | Accepted |
| **ADR-028** | V1 Project Completion Ratification | Formally ratify Phase 24 completion gate; freeze V1 release prior to Phase 25 operations. | Accepted |
