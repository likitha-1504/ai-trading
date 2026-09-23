# UI/UX Specification: Professional Trading Terminal

## 1. Design Language & Visual Tokens

The terminal is designed with a **dark-first professional aesthetics**, optimized for density, readability during extended market sessions, and low cognitive fatigue.

### Color Palette
- **Background**: `#0B0E14` (Deep Slate / Pitch)
- **Card / Surface**: `#151A23` (Charcoal Surface)
- **Borders**: `#222938` (Subtle Grid Border)
- **Primary Text**: `#F1F5F9` (High Contrast White)
- **Muted Text**: `#94A3B8` (Slate Neutral)
- **Bullish / Profit**: `#10B981` (Emerald 500)
- **Bearish / Loss**: `#EF4444` (Rose 500)
- **Warning / Risk Alert**: `#F59E0B` (Amber 500)
- **AI Hypothesis / Thinking**: `#8B5CF6` (Violet 500)
- **System Fact Indicator**: `#0284C7` (Sky Blue)

---

## 2. Fact vs. AI Visual Separation Standard

To avoid confusion between mathematical reality and probabilistic AI speculation:
- **DETERMINISTIC SYSTEM FACTS**: Solid border, clean Sans typography, Sky Blue / White badge indicator with the label `[SYSTEM FACT]`. Used for live broker equity, confirmed filled trades, active hard-stop price, and current tick quotes.
- **AI REASONING / OPINION**: Muted purple dashed border, subtle italics, with tag `[QWEN3 THESIS]` or `[DEEPSEEK-R1 CHALLENGE]`. Includes disclaimer footer: *"Probabilistic model output. Does not guarantee market trajectory."*

---

## 3. Dedicated Terminal Screens (15 Screens)

1. **Command Center**: High-level telemetry, active positions, kill-switch status, and system logs ticker.
2. **Market Scanner**: Live universe filtering, volume anomalies, and momentum scores.
3. **Candidate Feed**: Real-time cards showing detected setups, entry triggers, and calculated net edge.
4. **Trading Chart**: Lightweight candlestick chart with overlay markers for entry, stop, and trailing levels.
5. **Position Monitor**: Open trades, real-time unrealized P&L, distance to stop-loss, and duration timer.
6. **Orders & Execution**: Complete order lifecycle table (`CREATED`, `SUBMITTED`, `ACKNOWLEDGED`, `FILLED`).
7. **AI Analysis**: Dual-pane comparison between Qwen3 thesis and DeepSeek-R1 adversarial critique.
8. **Trade Journal**: Post-trade logging, screenshots, thesis review, and notes.
9. **Performance Analytics**: Win rate, profit factor, Sharpe ratio, and drawdown curve.
10. **Backtesting**: Strategy simulation dashboard with walk-forward testing metrics.
11. **Risk & Capital**: Capital allocation breakdown, circuit breaker thresholds, and ₹100/₹300 limit meters.
12. **System Health**: Ollama latency, WebSocket connection status, database WAL metrics, and memory utilization.
13. **Logs / Events**: Live structured log streaming with severity filters (`INFO`, `WARN`, `ERROR`, `CRITICAL`).
14. **Strategy Management**: Parameter configuration for Momentum Continuation and Early-Move modules.
15. **Settings**: Broker credentials, simulation speed, notification webhooks, and theme preferences.

---

## 4. UI Visual States

| State | Badge / Color Indicator | Meaning |
| :--- | :--- | :--- |
| `BUY` | Emerald Green Badge | Buy candidate confirmed by Trade Gate |
| `SELL` | Rose Red Badge | Exit signal triggered |
| `HOLD` | Slate Neutral Badge | Position within normal operating parameters |
| `WATCH` | Cyan Outline Badge | Setup monitored for entry breakout |
| `RISK` | Pulsing Amber Alert | Risk limit or drawdown warning threshold breached |
| `ERROR` | Red Alert Box | System failure or unhandled exception |
| `CONNECTED` | Solid Emerald Dot | Feeds and broker active |
| `DISCONNECTED` | Solid Rose Dot | Feed loss or broker outage |
| `AI THINKING` | Pulsing Violet Spinner | Ollama model inference in progress |
| `AI UNAVAILABLE` | Muted Violet Cross | Model offline; quantitative fallback active |
| `PENDING` | Yellow Badge | Order awaiting broker acknowledgment |
| `PARTIAL FILL` | Half-filled Yellow/Green Badge | Partial order execution recorded |
| `FILLED` | Solid Green Check | Order executed in full |
| `CANCELLED` | Muted Grey Cross | Order cancelled |
| `REJECTED` | Bright Red Cross | Broker or gate rejected order |
