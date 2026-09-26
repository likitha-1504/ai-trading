---
name: test-and-verify
description: Run relevant tests, record evidence, and never declare success without verification.
---

# Test and Verify Skill

This skill governs verification gates and test execution for `ai-agent-trading`.

## Principles
1. **Never Declare Success Without Verification**: Every modification must be validated by running tests and recording evidence.
2. **Full Regression Integrity**: Ensure all 251+ tests in `backend/tests/` pass with zero failures.
3. **Static Quality Verification**: Run `mypy backend/app` and `ruff check backend/`.
4. **Preflight Operational Check**: Execute `python backend/scripts/preflight_check.py` to ensure all 14 operational dimensions pass.
