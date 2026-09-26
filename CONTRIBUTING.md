# Contributing to AI Micro-Trading Agent

Thank you for your interest in contributing to the AI Micro-Trading Agent project. This repository enforces strict engineering, testing, and trading safety standards.

---

## 1. Governance & Agent Model

This repository operates under a strict agentic hierarchy:
- **Project Commander & Reviewer**: Antigravity orchestrates development, ratifies plans, reviews diffs, and coordinates releases.
- **Implementation Worker**: Bounded implementation agents modify only assigned files.
- **One Writer Rule**: Exactly one writer touches the codebase at any given time. Concurrent multi-agent modifications are strictly prohibited.
- **User Approval Gate**: All architecture, risk ceiling, and live trading modifications require explicit human approval.

---

## 2. Branch Hierarchy

- `main`: Permanent stable, releasable baseline. Direct commits are strictly prohibited.
- `feature/*`: Bounded feature implementations.
- `fix/*`: Targeted defect repairs.
- `research/*`: Isolated strategy simulations, backtesting experiments, or market intelligence.
- `release/*`: Release candidate stabilization, documentation audits, and deployment verification.

---

## 3. Pull Request & Review Process

Every PR must satisfy the following checklist before merge:
1. **Bounded Scope**: Clean diff touching only necessary files. No unrelated refactoring.
2. **Deterministic Risk Protection**: No change may weaken the Trade Gate, Position Watcher, or risk limits.
3. **Test Suite Integrity**: Full test regression (`pytest`) must pass 100% (251+ tests).
4. **Static Type Safety**: `mypy backend` must pass with 0 errors across all source files.
5. **Linting Compliance**: `ruff check backend` must pass with 0 warnings/errors.
6. **Frontend Build**: `npm run build` in `frontend/` must compile with 0 TypeScript/Vite errors.
7. **Secrets Audit**: Zero API keys, database files, credentials, or personal tokens committed.
8. **Documentation**: Update relevant `docs/` and root specifications to reflect behavior changes.

---

## 4. Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd project

# Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Run backend test suite
pytest

# Frontend setup
cd frontend
npm install
npm run build
npm run dev
```

---

## 5. Coding Standards

- **Python**: PEP 8 compliance via Ruff. Strict type hints required on all function arguments and returns.
- **TypeScript**: Strict type checking (`tsc -b`), functional React components, and Tailwind CSS utility classes.
- **Financial Calculations**: Always use `Decimal` for currency, prices, quantities, and P/L calculations. Never use raw floating-point numbers for financial accounting.
- **Architecture Boundaries**: Maintain clear separation between Market Data, Technical Strategies, AI Council (Advisory only), Trade Gate (Deterministic), and Position Watcher (Independent Watchdog).
