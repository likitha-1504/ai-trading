# GitHub Workflow & Development Agent Rules

Permanent repository workflow after V1.

---

## 1. Branch Hierarchy
- `main`: Permanent stable/releasable baseline. Direct commits for material changes are strictly forbidden.
- `feature/*`: Bounded feature implementations.
- `fix/*`: Targeted defect repairs.
- `research/*`: Isolated sandbox experiments and backtests.
- `release/*`: Release candidate stabilization and release preparation.

---

## 2. Development Lifecycle
```
Task
  ↓
Antigravity plan
  ↓
Implementation agent
  ↓
Tests
  ↓
Git diff review
  ↓
Antigravity review
  ↓
PR (with mandatory template)
  ↓
CI (full backend & frontend checks)
  ↓
User approval
  ↓
Merge
```

Every PR must explain:
1. What changed
2. Why
3. Tests & verification evidence
4. Trading and safety risks
5. Migrations & schema changes
6. Configuration changes
7. Rollback considerations

---

## 3. Commit & Security Discipline
- Use focused, semantic commits.
- Never mix unrelated refactors with trading or risk logic.
- Never commit secrets, broker credentials, model tokens, SQLite database files, or local environment files.

---

## 4. CI Integrity
All CI jobs must pass:
- Ruff formatting & linting.
- Mypy static type verification.
- Full pytest regression suite (251+ tests).
- 14-dimension operational preflight audit.
- Frontend TypeScript check and Vite production bundle.
- Secret scan verification.

---

## 5. Release Protocol
```
CHANGELOG
  ↓
Version bump
  ↓
Full tests
  ↓
Security/secret scan
  ↓
Docs verification
  ↓
Release commit
  ↓
Git tag
  ↓
GitHub release
  ↓
Deployment verification
```

---

## 6. Agent Governance
- Antigravity creates tasks, plans architecture, and reviews all diffs.
- The implementation agent modifies only necessary, bounded files.
- The user approves all architecture changes and live-trading changes.
