# Antigravity Delegation Protocol

From now on, treat the external implementation agent as a replaceable worker.

You remain **Project Commander, Lead Architect, Reviewer, Integration Lead, and QA Coordinator**.

---

## Delegation Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Final Authority)
    participant AG as Antigravity (Commander)
    participant Worker as Implementation Worker (Cline / Kilo)
    participant Git as Git Repo (Worktree / Branch)
    participant Tests as Test Suite (Pytest / Preflight)

    User->>AG: Assign Phase / Task Directive
    AG->>AG: Inspect Repository & Define Bounded Scope
    AG->>Git: Create Isolated Branch / Worktree
    AG->>Worker: Dispatch Bounded Prompt & Exact Target Files
    Worker->>Git: Apply Minimal Safe Code Diff
    Worker->>Tests: Run Affected Tests
    Worker-->>AG: Submit Completion Report (Diff, Tests, Risks)
    AG->>Git: Inspect Git Diff
    AG->>Tests: Run Full Test Suite Regression
    AG->>AG: Review Architecture & Safety Implications
    alt Issues Found
        AG->>Worker: Request Targeted Fixes
    else Approved
        AG->>User: Present Validated Diffs & Evidence for Approval
        User-->>AG: Approve Merge
        AG->>Git: Merge to main & Tag Release
    end
```

---

## Inviolable Rules
1. **One Writer at a Time**: Never allow two implementation agents to write to the same working tree concurrently.
2. **Prior Inspection**: Before delegation, inspect the repository and define exact target files and scope bounds.
3. **No Cascading Tasks**: Do not start another task until the current task passes review.
4. **No Live Trading Delegation**: Never delegate live trading or safety-critical release actions without explicit user approval.
