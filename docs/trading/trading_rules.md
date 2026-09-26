# Trading Rules & Risk Management

This document defines the deterministic rules enforced by the **Trade Gate** and **Position Watcher** (`backend/app/gate/trade_gate.py` and `backend/app/watcher/position_watcher.py`).

---

## 1. Hard Capital & Risk Limits

| Parameter | Value | Enforcement Mechanism | Failure Action |
| :--- | :--- | :--- | :--- |
| **Max Risk Per Trade** | **1.5%** of total capital | Trade Gate pre-trade check | Immediate rejection of TradePlan |
| **Max Daily Drawdown** | **3.0%** of high-water mark | Trade Gate pre-trade check | Session halt; no further trades |
| **Max Simultaneous Positions**| **1 Position** (micro-capital) | Trade Gate pre-trade check | Rejection of TradePlan |
| **Max Capital Allocation** | ₹100 (Live Phase 20) / ₹300 (Phase 21) | Trade Gate pre-trade check | Rejection of TradePlan |
| **Intraday Entry Cutoff** | **15:00 IST** | Trade Gate pre-trade check | Rejection of TradePlan |
| **Mandatory Square-Off** | **15:15 IST** | Position Watcher fast-path | Force-liquidate open positions at market |

---

## 2. Order Sizing Formula

Position sizing is mathematically bound by risk:

$$\text{Quantity} = \min\left( \left\lfloor \frac{\text{Capital} \times 0.015}{\text{Entry Price} - \text{Stop Loss Price}} \right\rfloor, \left\lfloor \frac{\text{Available Buying Power}}{\text{Entry Price} \times (1 + \text{Fee Buffer})} \right\rfloor \right)$$

- Risk is calculated against the exact stop-loss distance.
- If the calculated quantity is `< 1` share, the candidate trade is automatically rejected with code `INSUFFICIENT_CAPITAL_FOR_MIN_LOT`.

---

## 3. Position Watcher Exit Triggers

The Position Watcher runs continuously with sub-50ms SLA and evaluates the following triggers in order of priority:
1. **Emergency System Halt**: If kill switch or stale feed (> 15s) is active -> Exit at Market.
2. **Hard Stop Loss**: If LTP <= Hard Stop Price -> Exit at Market.
3. **Trailing Stop**: When unrealized gain reaches +1.5x risk, the trailing stop activates and locks in profits trailing by 1.0x ATR.
4. **Profit Target**: When LTP >= Target Price (typically 2.0x to 2.5x risk) -> Exit at Market/Limit.
5. **Time Expiry / 15:15 IST Cutoff**: Liquidate all open intraday positions prior to exchange closing.
