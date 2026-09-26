---
name: implementation-task
description: Bounded scope, existing-pattern reuse, tests, minimal diffs, and no unrelated edits.
---

# Implementation Task Skill

This skill defines the governance and execution constraints for implementation workers (e.g., Cline, Kilo, subagents) operating on `ai-agent-trading`. Antigravity acts as Lead Architect and Reviewer, delegating bounded tasks to the implementation worker.

---

## 1. Operating Rules for Workers
1. **Bounded Scope**: Modify ONLY the exact files explicitly assigned by Antigravity in the task specification.
2. **Existing Pattern Reuse**: Study adjacent modules and reuse established conventions (Pydantic contracts, `Decimal` for financial math, SQLite WAL queries, structured loggers).
3. **Minimal Safe Diffs**: Produce the smallest surgical diff required to satisfy the requirement. Speculative refactorings, style churn, and cosmetic reformatting are prohibited.
4. **Mandatory Automated Tests**: Every new feature or bug fix must include dedicated unit or integration tests in `backend/tests/`.
5. **No Secret Commits**: Never introduce mock credentials, real API tokens, or hardcoded passwords into code.
6. **No Live Orders**: Implementation workers are strictly forbidden from placing real trades or connecting to live broker endpoints.

---

## 2. Delegation & Review Lifecycle
```
1. Antigravity defines task scope and assigns target files.
2. Implementation worker edits designated files and runs local tests.
3. Implementation worker reports:
   - Files changed
   - Tests executed and results
   - Assumptions made
   - Identified risks
4. Antigravity inspects Git diff:
   - Verifies architecture boundary adherence.
   - Verifies deterministic safety rules remain intact.
   - Runs full test suite regression (`pytest`).
   - Requests targeted fixes if necessary.
5. User provides approval for critical or architectural modifications.
```

---

## 3. Verification Commands Before Submitting Task
```bash
# 1. Run affected module tests
pytest backend/tests/<relevant_test>.py -v

# 2. Check type annotations
mypy backend/app

# 3. Check linting
ruff check backend/
```
