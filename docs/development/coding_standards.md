# Coding Standards & Guidelines

This document outlines the mandatory engineering conventions for contributing code to `ai-agent-trading`.

---

## 1. Core Principles

1. **Deterministic Safety Core**:
   - Risk calculation, stop orders, sizing, and position monitoring must never contain asynchronous network delays or external LLM dependencies.
2. **Financial Precision**:
   - Always use `decimal.Decimal` for currency amounts, asset prices, quantities, and profit/loss calculations.
   - **Never** use Python `float` or JavaScript floating-point numbers for financial accounting, as IEEE 754 precision errors accumulate.
3. **One-Writer Rule**:
   - Only one agent or developer touches the repository working tree at a time.
   - Every change must have a bounded scope, clean diffs, and corresponding automated tests.

---

## 2. Python Backend Standards

- **Python Version**: Strictly 3.11+.
- **Typing**: 100% type annotation coverage. Every function argument, return type, and class attribute must be typed. `mypy backend/app` must pass with 0 errors.
- **Linting & Formatting**: Follow PEP 8 guidelines enforced by Ruff (`ruff check backend/`).
- **Data Contracts**: Inter-module communication must use Pydantic models defined in `backend/app/models/contracts.py`.
- **Database Access**: All database queries must use parameterized SQL to prevent SQL injection. Connections must use SQLite WAL mode.
- **Exceptions**: Use custom application exceptions inheriting from base domain exceptions. Never catch generic `Exception` silently without structured logging.

---

## 3. Frontend Standards (React + TypeScript)

- **TypeScript**: Strict type checking (`tsc -b`). No `any` types permitted.
- **Component Isolation**: Presentation components must be decoupled from data fetchers.
- **Error Boundaries**: Every major dashboard tab must be wrapped in a React `ErrorBoundary` so a rendering error in one view does not crash the entire terminal.
- **Visual Segregation**: The UI must strictly distinguish deterministic system facts (realized P/L, open orders, hard stop prices) from probabilistic AI outputs (Qwen3 hypotheses, confidence scores, DeepSeek critiques). Facts must use tabular numerical fonts (`font-mono`) and distinct color badges.

---

## 4. Testing Mandate

- Every new feature, bug fix, or strategy modification must include automated pytest test cases in `backend/tests/`.
- Fast tests should be unit tests with mock brokers; integration tests must use temporary isolated SQLite databases (via pytest fixtures).
- Never modify or skip an existing safety assertion without explicit architectural review.
