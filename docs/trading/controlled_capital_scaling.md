# Phase 29: Controlled Capital Scaling Framework

## 1. Executive Summary & Purpose

Phase 29 (**Controlled Capital Scaling**) introduces formal, discrete capital stages and governance controls designed to prevent unearned capital escalation. It enforces three core safety principles:
1. **Configurable Discrete Stages**: Capital growth is bounded to explicitly defined tiers with rigorous prerequisites.
2. **Absolute Anti-Auto-Scaling Governance**: **Capital is NEVER scaled automatically from recent performance or winning streaks**. All escalations require explicit, cryptographic operator authorization tokens (`OPERATOR-STAGE-TRANSITION-*`).
3. **Mandatory Reconciliation & Atomic Rollback**: Every stage transition enforces pre- and post-transition accounting reconciliation (0 discrepancy) and can be atomically rolled back at any time via `OPERATOR-STAGE-ROLLBACK-*`.

---

## 2. Inviolable Governance & Safety Invariants

During Phase 29 and all operational scaling cycles:
- **Anti-Auto-Scaling Rule**: Even if a strategy experiences a 10-trade winning streak or exceptional PnL, programmatic auto-scaling is prohibited. Any unapproved scaling attempt raises `UnauthorizedCapitalEscalationError` (HTTP 403 Forbidden).
- **Risk Invariants**: Maximum risk per trade remains locked at **1.5%**; maximum daily drawdown stop remains at **3.0%**; intraday square-off remains at **15:15 IST**.
- **Accounting Parity**: Pre- and post-scaling reconciliation must confirm **INR 0.00 discrepancy** between remote broker cash and the local SQLite WAL ledger.
- **Safety Mode**: `IS_PAPER_TRADING=True` remains locked across all runtime configurations.

---

## 3. Discrete Capital Stages Specification

| Stage Identifier | Stage Name | Capital Ceiling (INR) | Autonomous Limit (INR) | Max Risk / Trade | Max Daily DD | Trade Count Prereq | Win Rate Prereq | Approval Req |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`STAGE_1_MICRO`** | Micro-Capital Baseline | **₹100.00** | **₹300.00** | 1.5% | 3.0% | 0 | 0.0% | **Yes** (Active) |
| **`STAGE_2_EXPLORATORY`** | Exploratory Capital | **₹300.00** | **₹500.00** | 1.5% | 3.0% | 50 | 60.0% | **Yes** (Mandatory) |
| **`STAGE_3_SCALED`** | Validated Scaled | **₹500.00** | **₹1,000.00** | 1.5% | 3.0% | 150 | 62.0% | **Yes** (Mandatory) |
| **`STAGE_4_PRODUCTION_STANDARD`** | Standard Production | **₹1,000.00** | **₹2,500.00** | 1.5% | 3.0% | 300 | 65.0% | **Yes** (Mandatory) |

---

## 4. Pre- and Post-Transition Accounting Reconciliation

Before any capital ceiling escalation or defensive rollback is committed:
1. **Pre-Transition Verification**:
   - The engine queries the remote broker adapter for cash balance and open positions.
   - The engine inspects local SQLite WAL tables (`trades`, `orders`, `positions`, `account_equity`).
   - If $|\text{Broker Cash} - \text{Ledger Cash}| > \text{INR } 0.00$, the transition is **aborted immediately**.
2. **Post-Transition Verification**:
   - Following ceiling adjustment, a second independent reconciliation audit is performed and recorded into the persistent `ScalingTransitionRecord`.

---

## 5. Defensive Atomic Rollback Procedure

If elevated market volatility, data-feed anomalies, or operator discretion warrant risk reduction:
```bash
# Example atomic rollback via API or CLI
curl -X POST http://localhost:8000/api/v1/capital-scaling/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "target_stage": "STAGE_1_MICRO",
    "operator_authorization_token": "OPERATOR-STAGE-ROLLBACK-TOKEN-...",
    "reason": "Defensive retreat to baseline micro-capital"
  }'
```
The rollback executes atomically in sub-millisecond time, immediately reinstating the INR 100 ceiling and conducting full reconciliation.

---

## 6. API Endpoints Reference

Phase 29 exposes dedicated REST endpoints under `/api/v1/capital-scaling`:

- `GET /api/v1/capital-scaling/summary`: Consolidated status report, active ceiling, and reconciliation integrity.
- `GET /api/v1/capital-scaling/stages`: Lists all 4 discrete capital stages and prerequisite thresholds.
- `GET /api/v1/capital-scaling/eligibility`: Audits current metrics against next stage prerequisites.
- `GET /api/v1/capital-scaling/history`: Returns chronologically ordered audit log of all transitions and rollbacks.
- `POST /api/v1/capital-scaling/transition`: Guarded escalation endpoint requiring operator token (`OPERATOR-STAGE-TRANSITION-*`).
- `POST /api/v1/capital-scaling/rollback`: Atomic rollback endpoint requiring rollback token (`OPERATOR-STAGE-ROLLBACK-*`).

---

## 7. CLI Verification Tooling

The capital scaling suite includes an operational terminal audit runner:

```bash
# Run terminal ASCII audit report
python backend/scripts/capital_scaling_runner.py

# Run with structured JSON stream output
python backend/scripts/capital_scaling_runner.py --json

# Run standalone eligibility audit
python backend/scripts/capital_scaling_runner.py --eligibility
```
