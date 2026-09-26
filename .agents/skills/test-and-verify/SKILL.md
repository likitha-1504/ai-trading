---
name: test-and-verify
description: Run relevant tests, record evidence, and never declare success without verification.
---

# Test and Verify Skill

This skill governs testing execution, evidence gathering, and verification gates across the `ai-agent-trading` lifecycle.

---

## 1. Prime Directive: Never Declare Success Without Verification
- No task, feature, bug fix, or release may be declared complete without executing automated tests and capturing the output evidence in task summaries.
- If a test fails, execution stops immediately. The failure must be diagnosed and resolved before any downstream phase begins.

---

## 2. Verification Levels

### Level 1: Unit & Component Verification
Run tests specific to modified modules:
```bash
pytest backend/tests/test_feature_engine.py -v
pytest backend/tests/test_strategies.py -v
```

### Level 2: Full Repository Regression (251 Tests)
Mandatory before creating commits or merging branches:
```bash
pytest
```
Expected output: `251 passed, 1 warning in <45s`

### Level 3: Static Code Quality Checks
Verify Python typing and PEP 8 conformance:
```bash
mypy backend/app
ruff check backend/
```
Expected output:
- `Success: no issues found in 114 source files`
- `All checks passed!`

### Level 4: Frontend Compilation Check
Verify TypeScript type checking and production bundling:
```bash
cd frontend
npm run build
```
Expected output: `✓ built in <3.0s` with zero TypeScript errors.

### Level 5: 14-Dimension Operational Preflight Audit
Verify database integrity, backup readiness, configuration hard caps, and health probes:
```bash
python backend/scripts/preflight_check.py
```
Expected output: `Status: ALL PASSED (14/14)` with 0 warnings and 0 failures.
