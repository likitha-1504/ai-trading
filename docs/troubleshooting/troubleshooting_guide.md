# Troubleshooting & Diagnostic Guide

This guide provides resolutions for common issues encountered during setup, testing, or operation of the AI Micro-Trading Agent.

---

## 1. Quick Diagnostic Checklist

| Check | Command | Expected Output |
| :--- | :--- | :--- |
| **Python Environment** | `python --version` | `Python 3.11.x` |
| **Test Suite** | `pytest` | `251 passed` |
| **Static Types** | `mypy backend/app` | `Success: no issues found in 114 source files` |
| **Code Formatting** | `ruff check backend/` | `All checks passed!` |
| **Operational Preflight** | `python backend/scripts/preflight_check.py` | `ALL PASSED (14/14)` |
| **Database Integrity** | `python backend/scripts/integrity_check.py` | `Integrity check: ok` |
| **Ollama Service** | `curl http://localhost:11434/api/tags` | JSON listing `qwen` and `deepseek` |

---

## 2. Common Issues & Solutions

### A. Database Issues

#### Symptom: `sqlite3.OperationalError: database is locked`
- **Cause**: Another process or unclosed SQLite connection is holding an exclusive write lock.
- **Resolution**:
  1. Ensure all connections use WAL mode: `PRAGMA journal_mode=WAL;`
  2. Increase busy timeout in connection string: `PRAGMA busy_timeout=5000;`
  3. Close any external database inspection tools (e.g., DB Browser for SQLite) that may hold locks during market operation.

#### Symptom: `Database integrity check failed`
- **Cause**: System unexpected power cut or hard disk write failure corrupted a WAL frame.
- **Resolution**:
  1. Quarantine current database: `mv trading_agent.db trading_agent.db.corrupt`
  2. Restore from the most recent verified backup:
     ```bash
     python backend/scripts/restore.py --backup-id <LATEST_BACKUP_ID>
     ```
  3. Re-run preflight check.

---

### B. AI Council & Ollama Issues

#### Symptom: `Council timeout: Ollama did not respond within 30.0s`
- **Cause**: Local GPU/CPU is overwhelmed, or models are swapping between system RAM and VRAM.
- **Resolution**:
  1. Inspect Ollama running processes: `ollama ps`
  2. Ensure GPU drivers (NVIDIA CUDA) are active if running on discrete GPU.
  3. Pre-warm both models prior to market open by sending a dummy prompt:
     ```bash
     curl http://localhost:11434/api/generate -d '{"model": "qwen2.5:7b", "prompt": "ping"}'
     ```
  4. Use 4-bit quantized model weights (e.g., `qwen2.5:7b-instruct-q4_K_M`) to reduce VRAM memory pressure.

#### Symptom: `Failed to parse AI Council JSON output`
- **Cause**: DeepSeek-R1 outputting raw `<think>` blocks before the JSON object.
- **Resolution**:
  - The adapter regex automatically filters `<think>...</think>` tags. If new token formats emerge, ensure `backend/app/ai/deepseek_r1_adapter.py` regex strips markdown backticks and reasoning tags before `json.loads()`.

---

### C. Frontend Dashboard Issues

#### Symptom: Frontend displays blank screen or "Network Error"
- **Cause**: Backend FastAPI server is not running on port 8000 or CORS is blocking the request.
- **Resolution**:
  1. Verify FastAPI server is running: `curl http://localhost:8000/`
  2. Verify backend CORS middleware in `backend/app/main.py` permits requests from `http://localhost:5173`.
  3. Open browser developer console (F12) to inspect network error codes.

#### Symptom: Vite build fails with `tsc -b` error
- **Cause**: TypeScript type mismatch in frontend contracts.
- **Resolution**:
  1. Run `npx tsc --noEmit` inside `frontend/` to locate the exact line.
  2. Ensure frontend interfaces match the Pydantic schemas defined in `backend/app/models/contracts.py`.

---

### D. Market Feed & Broker Issues

#### Symptom: `STALE_FEED_TRIGGERED: No tick received for 15.0 seconds`
- **Cause**: Broker WebSocket dropped or exchange feed has halted.
- **Resolution**:
  1. Check broker status or network connection.
  2. If using `SimulatedMarketDataAdapter`, ensure the generator thread is active.
  3. Position Watcher will automatically protect capital by triggering an exit on open positions.
