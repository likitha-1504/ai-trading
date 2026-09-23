# UI/UX Specification: Professional Trading Terminal

## 1. Design Language & Dark-First Philosophy

The **AI Micro-Trading Terminal** is designed with a **dark-first professional aesthetics**, optimized for high visual density, rapid information hierarchy scanning, minimal eye fatigue during extended market hours, and immediate distinction between factual broker data and AI hypotheses.

### 1.1 Color Tokens & Theme System
```css
/* Core Dark Palette */
--bg-root: #0B0E14;              /* Deep slate background */
--bg-surface: #151A23;           /* Primary card / panel container */
--bg-surface-elevated: #1C2331;  /* Hovered cards, dropdowns, modals */
--border-subtle: #222938;        /* Panel dividers & table borders */
--border-highlight: #334155;     /* Active card focus / selections */

/* High-Contrast Typography */
--text-primary: #F1F5F9;         /* High-contrast crisp white headers & values */
--text-secondary: #94A3B8;       /* Muted labels & timestamps */
--text-muted: #64748B;           /* Inactive tabs, disabled hints */

/* Financial Status Tokens */
--color-bullish: #10B981;        /* Emerald green (profit, upward ticks) */
--color-bearish: #EF4444;        /* Crimson red (loss, downward ticks) */
--color-neutral: #64748B;        /* Neutral gray (sideways movement) */
--color-warning: #F59E0B;        /* Amber (risk threshold warning) */

/* Deterministic Facts vs. AI Distinctions */
--color-fact-badge: #0284C7;     /* Sky blue for DETERMINISTIC SYSTEM FACTS */
--color-fact-border: #0369A1;    /* Solid border for facts */
--color-ai-badge: #8B5CF6;       /* Violet / purple for AI ANALYSIS */
--color-ai-border: #6D28D9;      /* Dashed purple border for AI opinions */
```

### 1.2 Typography
- **Primary Interface**: Inter / Geist Sans (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`).
- **Data & Numbers**: JetBrains Mono (`'JetBrains Mono', 'Fira Code', monospace`) with tabular numerals (`font-feature-settings: 'tnum'`) to prevent number jitter during price flutters.
- **Scale**:
  - `Display / KPI`: 24px / 28px SemiBold
  - `Header 1`: 18px / 24px Bold
  - `Header 2`: 14px / 20px SemiBold
  - `Body / Tables`: 12px / 16px Regular
  - `Micro / Labels / Timestamps`: 10px / 14px Mono Medium

### 1.3 Spacing & Layout Grid
- Strict 4px/8px modular scale (`p-1`: 4px, `p-2`: 8px, `p-3`: 12px, `p-4`: 16px).
- Compact information density: Row height 32px for tables, 40px for active position widgets.

---

## 2. Navigation & Global Layout Architecture

```
+---------------------------------------------------------------------------------------------------+
|  [LOGO] AI MICRO-TRADER  |  [SYSTEM FACT] Cap: ₹100.00 | P&L: +₹2.40 | Paper: ACTIVE | [KILL SWITCH] |
+---------------------------------------------------------------------------------------------------+
| NAV: [1.Command] [2.Scanner] [3.Candidates] [4.Chart] [5.Positions] [6.Orders] [7.AI] [8.Journal] |
|      [9.Performance] [10.Backtest] [11.Risk] [12.Health] [13.Logs] [14.Strategies] [15.Settings] |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|                                       ACTIVE SCREEN VIEW                                          |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
| FOOTER: Feeds: CONNECTED (12ms) | Ollama: STANDBY | Watcher: ACTIVE (<50ms) | SQLite: WAL OK       |
+---------------------------------------------------------------------------------------------------+
```

- **Top Bar (Global Sticky)**:
  - System Identity and Mode (`PAPER` vs `LIVE`).
  - Real-Time Account Fact: Total Equity, Available Capital, Realized Daily P&L.
  - Emergency Kill-Switch: Prominent high-contrast red button with double-confirmation dialog.
- **Navigation Bar**: Tabbed horizontal or collapsible left rail providing instant 1-click access to all 15 screens.
- **Bottom Status Bar**: Connection heartbeats, latency meters, Position Watcher tick health.

---

## 3. Visual Separation: Deterministic Facts vs. AI Analysis

To prevent ambiguity between mathematical truth and probabilistic models:

| Visual Attribute | Deterministic System Fact | AI Model Analysis / Hypothesis |
| :--- | :--- | :--- |
| **Badge Tag** | `[SYSTEM FACT]` (Sky Blue / Solid) | `[QWEN3 THESIS]` / `[DEEPSEEK-R1 CHALLENGE]` |
| **Card Border** | Solid 1px `#0369A1` / `#222938` | Dashed 1.5px `#6D28D9` (Violet) |
| **Background Tint**| Dark Neutral `#151A23` | Subtle Violet Glow `rgba(139, 92, 246, 0.04)` |
| **Font Style** | Clean Monospace / Sans | Italicized body with explicit disclaimer |
| **Legal / Disclaimer**| None (Verified mathematical data) | *"Probabilistic LLM speculation. Never guarantees trajectory."* |

---

## 4. UI Visual States & Badges (15 Required States)

```css
/* Badge Styles */
.badge-buy         { background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #059669; }
.badge-sell        { background: rgba(239, 68, 68, 0.15);   color: #EF4444; border: 1px solid #DC2626; }
.badge-hold        { background: rgba(100, 116, 139, 0.15); color: #94A3B8; border: 1px solid #475569; }
.badge-watch       { background: rgba(6, 182, 212, 0.15);   color: #06B6D4; border: 1px solid #0891B2; }
.badge-risk        { background: rgba(245, 158, 11, 0.15);  color: #F59E0B; border: 1px solid #D97706; animation: pulse 2s infinite; }
.badge-error       { background: rgba(220, 38, 38, 0.25);   color: #FCA5A5; border: 1px solid #B91C1C; }
.badge-connected   { background: rgba(16, 185, 129, 0.2);  color: #34D399; }
.badge-disconnected{ background: rgba(239, 68, 68, 0.2);   color: #F87171; }
.badge-ai-thinking { background: rgba(139, 92, 246, 0.2);  color: #A78BFA; }
.badge-ai-unavail  { background: rgba(100, 116, 139, 0.2); color: #64748B; }
.badge-pending     { background: rgba(234, 179, 8, 0.15);   color: #EAB308; border: 1px solid #CA8A04; }
.badge-partial     { background: rgba(245, 158, 11, 0.15);  color: #FBBF24; border: 1px solid #D97706; }
.badge-filled      { background: rgba(16, 185, 129, 0.2);  color: #10B981; border: 1px solid #10B981; }
.badge-cancelled   { background: rgba(71, 85, 105, 0.2);   color: #94A3B8; border: 1px solid #475569; }
.badge-rejected    { background: rgba(220, 38, 38, 0.2);   color: #EF4444; border: 1px solid #DC2626; }
```

---

## 5. Detailed Specifications for All 15 Screens

### Screen 1: Command Center
- **Objective**: Executive overview of capital, active positions, system status, and live event ticker.
- **Widgets**:
  - `Capital KPI Tile`: ₹100.00 base, deployed amount, unrealized P&L.
  - `Active Trade Card`: Dynamic progress bar showing price distance between entry, stop-loss, and target.
  - `Watcher Heartbeat`: `<50ms` latency ticker showing autonomous watchdog health.
  - `Live Logs Stream`: Scrolling 1-line event feed with filterable severity tags.

### Screen 2: Market Scanner
- **Objective**: Real-time filtering of universe stocks based on momentum and volume velocity.
- **Widgets**:
  - Universe selector (Nifty 50, Micro-Cap Basket, Custom Watchlist).
  - Ticker grid displaying Last Price, Change %, RVOL 10, VWAP Distance %, and Spread %.
  - Quick action: "Inspect Features" button.

### Screen 3: Candidate Feed
- **Objective**: Displays setups generated by Momentum Continuation and Early-Move strategies.
- **Widgets**:
  - Candidate cards showing Rank Score, Strategy Origin, Trigger Price, and Net Edge %.
  - Status indicator: `DETECTED` → `IN_AI_REVIEW` → `PROMOTED` / `REJECTED`.

### Screen 4: Trading Chart
- **Objective**: High-definition, low-latency visual analysis.
- **Widgets**:
  - Candlestick chart (1m / 5m timeframes).
  - VWAP band overlay and volume sub-pane.
  - Interactive marker lines:
    - Entry Price (Cyan solid line).
    - Hard Stop-Loss (Red dashed line).
    - Trailing Stop Level (Amber dotted line).
    - Take Profit Target (Green solid line).

### Screen 5: Position Monitor
- **Objective**: Real-time inspection of open and closing positions.
- **Widgets**:
  - Table: Symbol, Side, Size, Entry, Current Price, Unrealized P&L, Stop Distance, Watcher State.
  - Manual Close Button (requires double click confirmation).

### Screen 6: Orders & Execution
- **Objective**: Complete order lifecycle audit.
- **Widgets**:
  - Lifecycle state tracker: `CREATED` → `SUBMITTED` → `ACKNOWLEDGED` → `PARTIALLY_FILLED` → `FILLED`.
  - Rejection and error logs with exact broker return codes.

### Screen 7: AI Analysis
- **Objective**: Dual-model qualitative debate inspector.
- **Widgets**:
  - Left Column: **Qwen3 Analyst** (Thesis, bullish catalysts, confidence score).
  - Right Column: **DeepSeek-R1 Challenger** (Adversarial counter-arguments, failure modes, critique).
  - Bottom Banner: Trade Gate deterministic synthesis outcome (`APPROVED` or `VETOED`).

### Screen 8: Trade Journal
- **Objective**: Post-trade retrospective and cognitive learning.
- **Widgets**:
  - Closed trade cards with entry/exit timestamps, net P&L, fees paid, and exit trigger reason.
  - User notes field and setup screenshot capture.

### Screen 9: Performance Analytics
- **Objective**: Statistical breakdown of trading edge.
- **Widgets**:
  - Equity curve line chart.
  - Key metrics: Win Rate %, Profit Factor, Max Drawdown %, Average R-Multiple, Expectancy.
  - Fee Drag Analysis: Total friction cost vs. Gross gains.

### Screen 10: Backtesting
- **Objective**: Event-driven historical simulation workbench.
- **Widgets**:
  - Parameter inputs: Lookback period, slippage estimate, transaction fee profile.
  - Monte Carlo simulation distributions and walk-forward stability score.

### Screen 11: Risk & Capital
- **Objective**: Real-time risk governance and circuit breaker monitoring.
- **Widgets**:
  - Capital allocation meters: ₹100 starting cap / ₹300 autonomous limit.
  - Daily Drawdown Gauge: Max 3.0% threshold before automatic daily shutdown.
  - Risk event log (spread spikes, liquidity thinnings, circuit alerts).

### Screen 12: System Health
- **Objective**: Diagnostics for local-first infrastructure.
- **Widgets**:
  - Latency bar charts for Normalizer, Feature Engine, Trade Gate, and Position Watcher.
  - Local Ollama status: VRAM usage, inference response time, queue depth.
  - SQLite WAL size and connection pool health.

### Screen 13: Logs & Events
- **Objective**: Real-time structured telemetry stream.
- **Widgets**:
  - Full-text search and regex filtering.
  - Severity level toggles: `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`.
  - Export to JSON / CSV.

### Screen 14: Strategy Management
- **Objective**: Parameter tuning for deterministic strategies.
- **Widgets**:
  - Strategy A (Momentum Continuation): RVOL threshold, minimum volume acceleration slope, VWAP max deviation.
  - Strategy B (Early-Move): Volatility compression lookback, ROC threshold, breakout volume multiplier.

### Screen 15: Settings
- **Objective**: System preferences, credentials, and environmental configuration.
- **Widgets**:
  - Broker configuration (Paper simulation toggle, API endpoint URLs).
  - Notification webhooks (Telegram / Discord alerts for hard stops).
  - Dark mode color theme adjustments and accessibility controls.

---

## 6. UI Implementation Task List for Codex CLI (Phase 15 Handoff)

When Phase 15 begins, Codex CLI will be delegated the following bounded implementation tasks:

1. **Task UI-01**: Setup Tailwind theme tokens and dark-mode root CSS matching `UI_UX_SPEC.md`.
2. **Task UI-02**: Implement reusable UI atoms in `frontend/src/components/ui/`:
   - `Badge.tsx` (15 visual states)
   - `FactBanner.tsx` (`[SYSTEM FACT]` vs `[AI ANALYSIS]`)
   - `MetricCard.tsx`
   - `TabularNum.tsx`
3. **Task UI-03**: Build the Top Bar with live capital telemetry and the emergency kill-switch modal.
4. **Task UI-04**: Build the navigation router supporting all 15 screens.
5. **Task UI-05**: Implement the primary 4 trading screens:
   - Command Center
   - Position Monitor
   - Candidate Feed
   - AI Analysis Dual-Pane
6. **Task UI-06**: Connect mock/paper WebSocket feeds with 250ms UI update throttling.
