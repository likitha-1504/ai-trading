# Indian Equities Statutory Cost Model

The AI Micro-Trading Agent embeds a mathematically exact cost engine reflecting the statutory regulatory fee structure of the Securities and Exchange Board of India (SEBI), National Stock Exchange (NSE), and Bombay Stock Exchange (BSE) for intraday equity trading.

---

## 1. Statutory Fee Schedule (Intraday Equities)

| Component | Rate / Formula | Application Basis |
| :--- | :--- | :--- |
| **Brokerage** | 0.03% or ₹20/order (whichever is lower) | Both Buy & Sell sides |
| **STT (Securities Transaction Tax)** | 0.025% | Sell side only |
| **Exchange Transaction Charges** | 0.00297% (NSE) / 0.00375% (BSE) | Both Buy & Sell turnover |
| **SEBI Turnover Charges** | ₹10 per crore (0.0001%) | Both Buy & Sell turnover |
| **Stamp Duty** | 0.003% (₹300 per crore) | Buy side only |
| **GST (Goods & Services Tax)** | 18.0% | Applied to (Brokerage + Exchange Charges + SEBI Charges) |
| **Investor Protection Fund (IPFT)**| 0.0001% | Both Buy & Sell turnover |

---

## 2. Mathematical Cost Calculation

Given:
- $P_{buy}$: Buy price per share
- $P_{sell}$: Sell price per share
- $Q$: Quantity of shares traded
- $\text{Turnover}_{buy} = P_{buy} \times Q$
- $\text{Turnover}_{sell} = P_{sell} \times Q$
- $\text{Turnover}_{total} = \text{Turnover}_{buy} + \text{Turnover}_{sell}$

$$\text{STT} = \text{round}(\text{Turnover}_{sell} \times 0.00025)$$

$$\text{Exchange Fee} = \text{Turnover}_{total} \times 0.0000297$$

$$\text{SEBI Fee} = \text{Turnover}_{total} \times 0.000001$$

$$\text{Stamp Duty} = \text{round}(\text{Turnover}_{buy} \times 0.00003)$$

$$\text{Taxable Services} = \text{Brokerage} + \text{Exchange Fee} + \text{SEBI Fee}$$

$$\text{GST} = \text{Taxable Services} \times 0.18$$

$$\text{Total Cost} = \text{Brokerage} + \text{STT} + \text{Exchange Fee} + \text{SEBI Fee} + \text{Stamp Duty} + \text{GST}$$

$$\text{Net PnL} = (\text{Turnover}_{sell} - \text{Turnover}_{buy}) - \text{Total Cost}$$

All calculations in `backend/app/engine/cost_calculator.py` use `decimal.Decimal` to eliminate rounding drift across thousands of simulated or live trades.
