# Implementation-Agent Evaluation Protocol: Cline vs Kilo Code

This document outlines the comparative evaluation protocol to test **Cline** and **Kilo Code** on an identical, non-safety-critical benchmark task to determine suitability for post-V1 bounded implementation work.

---

## 1. Governance & Commander Role

- **Antigravity** remains permanent Project Commander, Lead Architect, Reviewer, and QA Coordinator.
- **Cline** and **Kilo Code** are treated as bounded, replaceable implementation workers.
- **Strict Isolation**: Both agents are evaluated on separate clean branches/worktrees. Neither agent is permitted to write to `main` or to each other's branch.
- **No Early Winner**: Neither agent will be declared the winner until empirical evidence is collected across all 10 evaluation dimensions.

---

## 2. Evaluation Dimensions

| Dimension | Description | Scoring Criteria |
| :--- | :--- | :--- |
| **1. Repository Comprehension** | Understanding of project topology, conventions, and existing contracts. | Does the agent accurately discover and reuse existing models, database helpers, and config? |
| **2. Architecture Adherence** | Respect for 3-tier boundary, Trade Gate isolation, and one-writer rules. | Does the agent avoid touching risk controls, Position Watcher, or unrelated modules? |
| **3. Minimal Diff Discipline** | Surgical precision of code edits without speculative churn. | Are lines touched minimal and strictly relevant to the task? |
| **4. Test Execution & Coverage** | Adding relevant tests and running test verification. | Does the agent add clean pytest cases and verify them before reporting completion? |
| **5. Error Handling & Robustness** | Graceful handling of invalid inputs and failure modes. | Does the implementation catch edge cases with appropriate HTTP exceptions and logs? |
| **6. Documentation Accuracy** | Explaining diffs, assumptions, and risks clearly. | Does the agent's report provide structured, accurate explanations? |
| **7. CLI & Tooling Reliability** | Stability of CLI or extension execution without crashing or stalling. | Does the tool run reliably and return structured output? |
| **8. Permissions & Safety Fences** | Compliance with least-privilege access and zero secret leaks. | Does the agent request only necessary file access? |
| **9. MCP & Ecosystem Support** | Support for Model Context Protocol servers and developer tool integrations. | How easily does the agent integrate with project tools? |
| **10. Ease of Antigravity Orchestration** | Simplicity for Antigravity to define scope, review diffs, and guide fixes. | How cleanly does Antigravity orchestrate the worker? |

---

## 3. Branch & Worktree Isolation Strategy

```bash
# Branch for Cline evaluation
git checkout -b eval/cline-benchmark main

# Branch for Kilo Code evaluation
git checkout -b eval/kilo-benchmark main
```
Each branch is independently tested, audited by Antigravity, and scored in `evaluation_matrix.md`.
