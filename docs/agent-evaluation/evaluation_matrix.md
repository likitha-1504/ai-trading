# Comparative Evaluation Matrix: Cline vs Kilo Code

This matrix tracks the performance of Cline and Kilo Code across the 10 benchmark dimensions.

---

## 1. System Readiness & Inspection Status

| Dimension | Cline Status | Kilo Code Status | Notes |
| :--- | :--- | :--- | :--- |
| **Installed Environment** | VS Code Extension (`saoudrizwan.claude-dev`) installed | VS Code Extension (`kilocode.kilo-code`) installed; CLI (`@kilocode/cli` v7.8.1) installed globally | Both agents are installed on the local system. |
| **CLI Availability** | NPM `@cline/cli` v0.0.13 (experimental); primarily VS Code UI extension | Full production CLI (`kilo` v7.8.1) with subcommands (`run`, `worktree`, `mcp`, `serve`) | Kilo has direct headless CLI invocation support. |
| **Prompt Delivery Mechanism**| VS Code chat window / system prompt input | CLI prompt flag `--prompt` / `--worktree` or VS Code interface | Kilo supports headless scripted orchestration via CLI. |
| **Branch / Worktree Support**| Git worktree or branch checkout via git | Native `kilo worktree` command and `.kilo/worktrees` structure | Existing `.kilo` directory detected in project from prior phase. |

---

## 2. Benchmark Scorecard (1–10 Scale)

*Note: Scores will be recorded upon completion of the benchmark task on isolated branches.*

| Evaluation Dimension | Weight | Cline Score | Kilo Code Score | Antigravity Observations |
| :--- | :---: | :---: | :---: | :--- |
| **1. Repository Comprehension** | 10% | — | — | Evaluates understanding of `backend/app` models and settings. |
| **2. Architecture Adherence** | 15% | — | — | Zero modifications to Trade Gate, Position Watcher, or risk caps. |
| **3. Minimal Diff Discipline** | 15% | — | — | Line diff count strictly bounded to assigned files. |
| **4. Test Execution & Coverage** | 15% | — | — | Adding and running automated pytest tests. |
| **5. Error Handling & Robustness** | 10% | — | — | Graceful exception handling and structured response. |
| **6. Documentation Accuracy** | 10% | — | — | Clarity and completeness of completion report. |
| **7. CLI & Tooling Reliability** | 10% | — | — | Absence of CLI freezes, crashes, or timeout hangs. |
| **8. Permissions & Safety Fences**| 10% | — | — | Least privilege compliance; zero secret leakage. |
| **9. MCP & Ecosystem Support** | 5% | — | — | Extensibility with Model Context Protocol. |
| **10. Ease of Orchestration** | 10% | — | — | Seamlessness of Antigravity commanding the worker. |
| **Composite Weighted Score** | **100%**| **TBD** | **TBD** | Awaiting empirical benchmark evidence. |

---

## 3. Decision Gate Criteria

Per Section 7 of the migration specification:
- Do not declare a winner before evidence is collected.
- After evaluating both agents, present evidence and wait for the user's explicit selection.
- Do not migrate the whole project automatically.
