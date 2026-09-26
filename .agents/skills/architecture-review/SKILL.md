---
name: architecture-review
description: Compare changes with ARCHITECTURE.md, API contracts, schema, and trading rules.
---

# Architecture Review Skill

This skill governs architectural conformance checks for `ai-agent-trading`. Antigravity uses this skill to evaluate whether code modifications adhere to foundational system designs.

---

## 1. Conformance Matrix

| Specification | Source Document | Key Review Check |
| :--- | :--- | :--- |
| **System Topology** | `ARCHITECTURE.md` | Three-tier isolation: Presentation (React), Control Plane (FastAPI), Watchdog (Position Watcher). No direct UI-to-broker connections. |
| **API Contracts** | `API_CONTRACTS.md` | All endpoints conform to schemas in `backend/app/models/contracts.py`. `POST /orders` permanently blocked (405). |
| **Database Schema** | `DATABASE_SCHEMA.md` | All tables maintain foreign keys, indexed timestamps, and WAL ACID guarantees. |
| **Trading Rules** | `TRADING_RULES.md` | Risk per trade <= 1.5%, daily loss <= 3.0%, 15:15 IST auto-square-off intact. |
| **AI Roles** | `AI_ROLES.md` | Qwen3 Analyst and DeepSeek-R1 Challenger remain advisory; consensus score computed; zero LLM exit dependencies. |
| **Failure Handling** | `FAILURE_HANDLING.md` | Stale feed timeout (> 15s), broker reconnect exponential backoff, and crash recovery logic preserved. |

---

## 2. Review Protocol
1. **Compare Git Diff Against Contracts**:
   - Inspect Pydantic models in `backend/app/models/contracts.py`.
   - Verify `Decimal` is used for all prices, sizes, fees, and P/L calculations.
2. **Verify Threading & Concurrency Boundaries**:
   - Ensure Position Watcher loop remains free of asynchronous bottlenecks or blocking calls.
   - Verify SQLite write operations use appropriate transaction blocks.
3. **Record Architectural Decision Records (ADRs)**:
   - Any material architectural change, schema migration, or risk modification must be recorded as an ADR in `DECISIONS.md` and approved by the user.
