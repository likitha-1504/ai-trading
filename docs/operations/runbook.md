# Daily Operational Runbook

This runbook outlines mandatory daily procedures for running the AI Micro-Trading Agent during trading sessions (Indian Equities: 09:15–15:30 IST).

---

## 1. Pre-Market Operations (08:30 – 09:00 IST)

1. **Verify Ollama LLM Service**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Ensure both `qwen2.5:7b` (or qwen3) and `deepseek-r1:7b` models are loaded.

2. **Execute Operational Preflight Audit**:
   ```bash
   python backend/scripts/preflight_check.py
   ```
   Must pass all 14 dimensions with 0 failures and 0 warnings.

3. **Check SQLite Database Integrity**:
   ```bash
   python -c "from app.ops.integrity_verifier import IntegrityVerifier; print(IntegrityVerifier().run_full_integrity_check())"
   ```
   Ensure integrity status is `ok` and accounting parity matches.

4. **Verify Paper Trading Lock**:
   Verify `.env` contains `IS_PAPER_TRADING=True`.

---

## 2. Market Open Operations (09:15 – 10:00 IST)

1. **Start System Services**:
   - Backend API: `uvicorn backend.app.main:app --port 8000`
   - Frontend Dashboard: `npm run dev` in `frontend/`
2. **Monitor Early Move Strategy**:
   - Verify WebSocket connection status is `CONNECTED` (green badge in UI).
   - Check Candidate Ranker tab for opening volatility breakout setups.
   - Verify Position Watcher thread status is `ACTIVE`.

---

## 3. Mid-Day Monitoring (10:00 – 15:00 IST)

- Monitor system resource usage (RAM, CPU).
- Inspect AI Council Deliberation log for Qwen3 vs DeepSeek-R1 consensus scores.
- Ensure daily drawdown does not exceed 3.0% circuit breaker.
- Trigger scheduled hot backup at 12:00 IST:
  ```bash
  python backend/scripts/backup.py --reason midday_scheduled
  ```

---

## 4. Market Close Operations (15:00 – 15:45 IST)

1. **15:00 IST**: Entry cutoff armed. System rejects all new trade entries.
2. **15:15 IST**: Mandatory Square-Off. Position Watcher automatically liquidates any lingering open positions at market price.
3. **15:30 IST**: Market closes. Verify zero open positions remain.
4. **15:45 IST**: Post-Market Reconciliation & Hot Backup:
   ```bash
   python backend/scripts/backup.py --reason eod_reconciliation
   ```
5. **Review Daily Performance & Learning Loop**:
   - Inspect post-trade analytics in `docs/` or API `/api/v1/learning/analytics`.
