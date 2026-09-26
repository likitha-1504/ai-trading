# Phase 30: Advanced Market Intelligence Technical Specification

## 1. Executive Summary & Architecture Overview

Phase 30 establishes the **Advanced Market Intelligence** framework for the AI Micro-Trading Agent. While early phases relied on single-asset microstructure indicators (VWAP distance, RVOL, realized volatility), Phase 30 equips the agent with holistic contextual market intelligence:
1. **Regime Detection**: Multi-factor trend identification via ADX, directional movement (+DI / -DI), and multi-horizon moving average stacks.
2. **Volatility Regime**: Squeeze identification via Bollinger Bandwidth and Keltner Channels, combined with rolling ATR percentile scoring and defensive capital risk scaling.
3. **Sector Context**: Mansfield Relative Strength (RS) tracking against benchmark Indian indices (NIFTY IT, NIFTY BANK, NIFTY AUTO, etc.), identifying sector leadership and directional tailwinds.
4. **Market Breadth**: Cross-sectional universe participation metrics including Advance/Decline ratios, moving average breadth (% above 20 EMA, % above 50 SMA), and acute breadth thrusts.
5. **Zero-Leakage Point-in-Time Engine**: Architectural enforcement ensuring every calculation is strictly point-in-time, audited against monotonic timestamps and future-data contamination via `LeakageAuditor`.
6. **Regime-Conditioned Backtesting**: Quantitative empirical backtesting validating that strategy performance improves significantly when conditioned on market regimes (elevating Sharpe and reducing drawdowns).

---

## 2. Core Subsystems & Mathematical Specifications

### 2.1 Trend Regime Detection (`regime_detector.py`)

The regime detector categorizes the prevailing market environment into one of five states:
- `BULL_MOMENTUM`: Strong upward directional trend.
- `BEAR_MOMENTUM`: Strong downward directional trend.
- `MEAN_REVERTING_RANGE`: Low directional momentum, oscillating between bounds.
- `VOLATILE_BREAKOUT`: Sudden expansion breaking multi-bar range.
- `NEUTRAL_CHOP`: Ambiguous or conflicting signals.

#### Mathematical Definitions:
1. **True Range ($TR$)**:
   $$\text{TR}_t = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$
2. **Directional Movement ($+DM$, $-DM$)**:
   $$\Delta H = H_t - H_{t-1}, \quad \Delta L = L_{t-1} - L_t$$
   $$+DM = \Delta H \text{ if } \Delta H > \Delta L \text{ and } \Delta H > 0 \text{ else } 0$$
   $$-DM = \Delta L \text{ if } \Delta L > \Delta H \text{ and } \Delta L > 0 \text{ else } 0$$
3. **Directional Indicators ($+DI_{14}$, $-DI_{14}$)**:
   $$+DI = \frac{\sum +DM}{\sum TR} \times 100, \quad -DI = \frac{\sum -DM}{\sum TR} \times 100$$
4. **Average Directional Index ($ADX_{14}$)**:
   $$DX = \frac{|+DI - -DI|}{+DI + -DI} \times 100, \quad ADX = \text{EMA}(DX, 14)$$

### 2.2 Volatility Regime & Squeeze Detection (`volatility_regime.py`)

Identifies volatility compression and expansion cycles to adjust position risk multipliers:
- **Bollinger Bands ($20, 2\sigma$)**:
  $$\text{Upper}_{BB} = \text{SMA}_{20} + 2\sigma, \quad \text{Lower}_{BB} = \text{SMA}_{20} - 2\sigma, \quad \text{Bandwidth} = \frac{\text{Upper}_{BB} - \text{Lower}_{BB}}{\text{SMA}_{20}}$$
- **Keltner Channels ($20, 1.5 \times ATR$)**:
  $$\text{Upper}_{KC} = \text{SMA}_{20} + 1.5 \times ATR_{14}, \quad \text{Lower}_{KC} = \text{SMA}_{20} - 1.5 \times ATR_{14}$$
- **Squeeze Condition**:
  $$\text{is\_squeeze} = (\text{Upper}_{BB} < \text{Upper}_{KC}) \land (\text{Lower}_{BB} > \text{Lower}_{KC})$$
- **Capital Risk Multiplier Matrix**:
  - `VOLATILITY_COMPRESSION`: $0.80\times$ (Prudent positioning before expansion).
  - `NORMAL_VOLATILITY`: $1.00\times$ (Full baseline size).
  - `HIGH_VOLATILITY`: $0.50\times$ (Defensive half-size).
  - `EXTREME_VOLATILITY_CIRCUIT`: $0.00\times$ (Trading halted immediately).

### 2.3 Sector Context & Relative Strength (`sector_context.py`)

Measures whether an individual stock has a macro tailwind from its sector:
1. **Instrument-to-Sector Mapping**: Maps symbols across 8 key sectors: `NIFTY_IT`, `NIFTY_BANK`, `NIFTY_AUTO`, `NIFTY_METAL`, `NIFTY_PHARMA`, `NIFTY_ENERGY`, `NIFTY_FMCG`, and `NIFTY_50`.
2. **Mansfield Relative Strength ($RS$)**:
   $$RS = \left( \frac{P_{t} / P_{t-N}}{B_{t} / B_{t-N}} - 1.0 \right) \times 100$$
3. **Sector Tailwind Condition**:
   $$\text{has\_sector\_tailwind} = (RS \ge 0.0) \land (\text{Sector\_Trend} == \text{BULLISH} \lor \text{Sector\_Is\_Leader})$$

### 2.4 Cross-Sectional Market Breadth (`market_breadth.py`)

Aggregates participation across the tracked universe:
- **Advance/Decline Ratio**:
  $$A/D = \frac{\text{Advancing Stocks}}{\max(1, \text{Declining Stocks})}$$
- **Moving Average Participation**:
  $$\% > 20 \text{ EMA} = \frac{N_{P \ge \text{EMA}_{20}}}{N_{\text{total}}} \times 100$$
  $$\% > 50 \text{ SMA} = \frac{N_{P \ge \text{SMA}_{50}}}{N_{\text{total}}} \times 100$$
- **Breadth Thrust**: $A/D \ge 2.5 \land \% > 20 \text{ EMA} \ge 70.0\%$.

---

## 3. Leakage & Look-Ahead Prevention Protocol

To guarantee mathematical integrity in quantitative research, Phase 30 enforces:
1. **Point-in-Time Invariant**: All input event timestamps $t_{bar} \le t_{eval}$.
2. **Monotonic Ordering**: Verified by `LeakageAuditor.audit_event_stream()` with zero timestamp inversions permitted.
3. **No Centered Smoothing**: All EMAs and indicators are strictly backward-looking.
4. **Cross-Partition Isolation**: Train/test or backtest splits are evaluated for zero future contamination.

---

## 4. REST API Reference

The following endpoints are registered under `/api/v1/market-intelligence/*`:

| Method | Path | Summary | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/snapshot` | Unified point-in-time snapshot for asset | `AdvancedMarketIntelligenceSnapshot` |
| `GET` | `/regimes` | Trend regime and ADX metrics | `RegimeClassification` |
| `GET` | `/volatility` | Volatility state and squeeze condition | `VolatilityClassification` |
| `GET` | `/sector-context` | Relative strength and sector rankings | `SectorContextSummary` |
| `GET` | `/breadth` | Cross-sectional market breadth | `MarketBreadthSummary` |
| `POST` | `/backtest` | Regime-conditioned backtesting run | `RegimeBacktestSummary` |
| `POST` | `/audit-leakage` | Point-in-time leakage audit | `LeakageAuditReport` |

---

## 5. Operational CLI Tooling

The operational runner provides an audit dashboard for real-time monitoring and automated CI/CD pipeline integration:

```bash
# Standard formatted ASCII report
python backend/scripts/market_intelligence_runner.py --symbol RELIANCE

# Structured JSON stream
python backend/scripts/market_intelligence_runner.py --symbol RELIANCE --json

# Standalone backtest validation
python backend/scripts/market_intelligence_runner.py --backtest

# Standalone leakage audit
python backend/scripts/market_intelligence_runner.py --audit-leakage
```
