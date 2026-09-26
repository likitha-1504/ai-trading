# Phase 31: Multi-Strategy Portfolio Allocation & Concentration Governance

## 1. Executive Summary & Architecture Overview

Phase 31 implements the **Multi-Strategy Portfolio** management and risk control framework. In quantitative multi-strategy trading, capital allocation across disparate alphas introduces cross-sectional concentration hazards and correlation risks. Phase 31 enforces two foundational architectural rules:
1. **Independent Strategy Validation Rule**: *"Add strategy allocation only after independent validation."* Capital is strictly never allocated to an unvalidated, speculative, or probation strategy.
2. **Deterministic Portfolio Risk Controls**: *"Deterministic portfolio risk controls exposure and concentration."* Hardcoded mathematical boundaries govern single-strategy, single-symbol, single-sector, and total portfolio gross exposures.

---

## 2. Independent Strategy Validation Gate (`strategy_validator.py`)

Every trading strategy (`MOMENTUM_CONTINUATION`, `EARLY_MOVE_DETECTION`, etc.) must independently satisfy five quantitative criteria before receiving non-zero capital allocation:

| Validation Criterion | Required Hurdle | Rationale |
| :--- | :---: | :--- |
| **Minimum Sample Size** | $\ge 15$ closed trades | Prevents small-sample variance from granting premature capital. |
| **Realized Win Rate** | $\ge 50.0\%$ | Eliminates losing strategies from portfolio inclusion. |
| **Profit Factor** | $\ge 1.20$ | Ensures gross gains exceed losses after transaction costs. |
| **Risk-Adjusted Return (Sharpe)** | $\ge 0.50$ | Verifies excess return over volatility. |
| **Maximum Drawdown Floor** | $\le 20.0\%$ | Bounds worst-case equity deterioration. |

### Validation Lifecycle States:
- `VALIDATED`: Strategy meets all 5 hurdles. Target allocation weight $> 0.0\%$ allowed.
- `PROBATION`: Sample size $< 15$ trades. Target allocation locked at $0.0\%$.
- `DISQUALIFIED`: Strategy breached win rate, profit factor, Sharpe, or drawdown limits. Target allocation immediately zeroed out.

---

## 3. Deterministic Portfolio Risk & Concentration Limits (`concentration_engine.py`)

To prevent catastrophic single-point-of-failure exposure, `ConcentrationEngine` enforces four invariant boundary checks prior to admitting any trade:

1. **Gross Portfolio Exposure Cap ($\le 100.0\%$)**:
   $$\text{Gross Exposure} = \frac{\sum \text{Deployed Capital}}{\text{Total Portfolio Equity}} \times 100 \le 100.0\%$$
2. **Single-Strategy Concentration Ceiling ($\le 60.0\%$)**:
   $$\text{Strategy Concentration}_s = \frac{\text{Deployed}_s + \text{Proposed}}{\text{Total Portfolio Equity}} \times 100 \le 60.0\%$$
3. **Single-Symbol Concentration Ceiling ($\le 40.0\%$)**:
   $$\text{Symbol Concentration}_i = \frac{\text{Deployed}_i + \text{Proposed}}{\text{Total Portfolio Equity}} \times 100 \le 40.0\%$$
4. **Single-Sector Concentration Ceiling ($\le 50.0\%$)**:
   $$\text{Sector Concentration}_k = \frac{\text{Deployed}_k + \text{Proposed}}{\text{Total Portfolio Equity}} \times 100 \le 50.0\%$$

If a trade candidate breaches any of these four constraints, `evaluate_admission()` returns `(False, reason)` and the order is deterministically rejected at the portfolio gate.

---

## 4. Multi-Strategy Capital Manager (`portfolio_manager.py`)

`MultiStrategyPortfolioManager` coordinates:
- **Baseline Allocation**: Default equal-weighting (50% Momentum, 50% Early Move) scaled to current account equity.
- **Trade Capital Locking**: Atomically records capital committed by a strategy upon trade entry.
- **Capital Release & PnL Accounting**: Releases capital and books realized PnL back into portfolio equity upon trade exit.
- **Operator-Authorized Rebalancing**: Strategy target weight changes require an explicit operator token starting with `OPERATOR-PORTFOLIO-REALLOC-*`. Unauthorized attempts raise `PortfolioAllocationError` (HTTP 403 Forbidden).

---

## 5. REST API Reference

The following endpoints are registered under `/api/v1/portfolio/*`:

| Method | Path | Summary | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/summary` | Unified portfolio status, allocations, and exposure | `MultiStrategyPortfolioSummary` |
| `GET` | `/strategies` | Independent validation reports for all strategies | `list[StrategyValidationReport]` |
| `GET` | `/concentrations` | Real-time concentration metrics vs limits | `ConcentrationMetrics` |
| `POST` | `/reallocate` | Reallocate strategy target weights (Operator token required) | `MultiStrategyPortfolioSummary` |
| `POST` | `/validate-strategy` | Run on-demand independent strategy validation | `StrategyValidationReport` |

---

## 6. Operational CLI Tooling

The operational runner provides interactive inspection and automated CI/CD validation:

```bash
# Standard formatted ASCII report
python backend/scripts/portfolio_runner.py

# Structured JSON stream
python backend/scripts/portfolio_runner.py --json

# Standalone strategy validation audit
python backend/scripts/portfolio_runner.py --validate
```
