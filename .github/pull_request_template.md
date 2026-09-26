## Pull Request Summary

### 1. What Changed
<!-- High-level summary of the code, test, and documentation changes in this PR -->

### 2. Why
<!-- Rationale, user requirement, defect report, or architectural goal driving this change -->

### 3. Tests & Verification Evidence
<!-- Provide test commands run and exact outputs. Mandatory: never declare success without verification -->
- [ ] Unit / Integration Tests (`pytest`):
- [ ] Static Type Checking (`mypy backend/app`):
- [ ] Code Linting (`ruff check backend/`):
- [ ] Operational Preflight (`python backend/scripts/preflight_check.py`):
- [ ] Frontend Build (`npm run build` in `frontend/`):

### 4. Trading & Safety Risks
<!-- Deterministic risk implications, Position Watcher SLA impact, or broker interaction risks -->
- Deterministic Risk Core affected: [Yes / No]
- Position Watcher SLA (< 50ms) maintained: [Yes / No]
- Broker Adapter or order routing altered: [Yes / No]

### 5. Migrations & Schema Changes
<!-- Details of SQLite schema alterations, table additions, or index updates -->
- Database migration required: [None / Yes (detail below)]

### 6. Configuration Changes
<!-- New environment variables, config flags, or parameter default adjustments -->
- Environment variables modified: [None / Yes (detail below)]

### 7. Rollback Considerations
<!-- Exact operational rollback plan in the event of production regression -->
- Rollback steps:

---

## Agent Governance Sign-Off

- **Antigravity Plan Ratified**: [x]
- **Implementation Worker Scope Bounded**: [x]
- **One-Writer Rule Preserved**: [x]
- **User Approval Obtained (if architecture or live trading altered)**: [ ]
