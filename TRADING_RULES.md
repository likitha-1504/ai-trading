# Trading Rules & Quantitative Constraints

## 1. Capital Allocation & Risk Limits

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Initial Capital** | ₹100 | Micro-capital baseline for paper & initial live verification. |
| **Autonomous Threshold** | ₹300 | Maximum position size or aggregate exposure executed autonomously. |
| **Max Loss Per Trade** | 1.5% of Equity | Hard deterministic stop executed on position entry. |
| **Max Daily Drawdown** | 3.0% of Capital | Automatic circuit breaker: suspends trading for remainder of day. |
| **Max Active Positions** | 2 | Limits portfolio concentration and concurrent capital exposure. |

---

## 2. BUY Engine Specifications

A candidate is generated only when all criteria within one of the following two strategy engines are satisfied:

### Strategy A: Momentum Continuation
- Price is above intraday VWAP.
- Relative Volume ($RVOL$) $\ge 1.8$ over 10-bar baseline.
- Volume Acceleration: Positive slope of 3-bar rolling volume.
- Spread: Bid-ask spread $\le 0.15\%$ of current market price.
- Invalidation: Candlestick closes below prior swing low or crosses below VWAP.

### Strategy B: Early-Move Detection
- Price compression: Volatility contracting over prior 15 bars.
- Emerging price acceleration: $ROC$ breaking out of low-volatility band.
- Volume surge: Initial uptick in volume before widespread retail participation.
- Sector/Index alignment: Underlying index or sector basket trend is neutral-to-bullish.
- Invalidation: Failure to expand range within 3 bars following breakout trigger.

---

## 3. SELL Engine & Position Watcher Invariants

The **Independent Position Watcher** owns position risk continuously:
1. **Hard Stop-Loss**: Immediate market exit order if price hits entry stop price. Zero LLM involvement.
2. **Trailing Stop-Loss**: Activated once position gains $\ge 1.5R$. Trails at swing low or dynamic ATR multiples.
3. **Stale Data Exit**: If tick feed drops or freezes for $> 15$ seconds while holding an active position, system alerts operator and prepares defensive liquidation.
4. **Catastrophic Liquidity Loss**: If top-of-book depth thins out or spread widens past $0.5\%$, trigger early defensive exit.
5. **Time Protection**: Intraday trades must close automatically at 15:15 IST (before exchange auto-square-off).
6. **Thesis Invalidation**: If Qwen3/DeepSeek-R1 flag fundamental invalidation, the system marks the trade for priority exit, but this acts as an auxiliary signal—never overriding hard stops.

---

## 4. Friction & Net-Edge Calculation

Before any order is approved, the expected profit must satisfy:
$$\text{Expected Edge} = (\text{Target Gain} \times P(\text{Win})) - (\text{Stop Loss} \times P(\text{Loss})) - \text{Total Friction} > \text{Hurdle Rate}$$

Where $\text{Total Friction}$ comprises:
- Brokerage charges
- Securities Transaction Tax (STT)
- Exchange transaction charges
- SEBI turnover fee
- Stamp duty
- GST (18% on brokerage + transaction charges + SEBI)
- Estimated 1-tick slippage
