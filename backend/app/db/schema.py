"""SQLite database schema and DDL definitions for all 13 core entities.

Entities:
1. capital_state
2. positions
3. orders
4. trades
5. candidates
6. features
7. ai_analyses
8. trade_plans
9. risk_events
10. strategy_versions
11. model_calls
12. execution_metrics
13. system_events
"""

DDL_STATEMENTS = """
-- 1. Capital State
CREATE TABLE IF NOT EXISTS capital_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_capital REAL NOT NULL,
    available_capital REAL NOT NULL,
    deployed_capital REAL NOT NULL,
    buying_power REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    daily_drawdown REAL NOT NULL,
    high_water_mark REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR'
);

-- 2. Positions
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    plan_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL', 'LONG', 'SHORT')),
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    hard_stop_price REAL NOT NULL,
    take_profit_price REAL,
    trailing_stop_price REAL,
    highest_price_seen REAL,
    unrealized_pnl REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSING', 'CLOSED')),
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    exit_reason TEXT
);

-- 3. Orders
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    client_order_id TEXT UNIQUE NOT NULL,
    plan_id TEXT,
    position_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL CHECK(order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LOSS')),
    quantity INTEGER NOT NULL,
    price REAL,
    stop_price REAL,
    filled_quantity INTEGER DEFAULT 0,
    average_fill_price REAL DEFAULT 0.0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 4. Trades
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    order_id TEXT,
    position_id TEXT,
    plan_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    strategy TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    fee_brokerage REAL NOT NULL,
    fee_stt REAL NOT NULL,
    fee_exchange REAL NOT NULL,
    fee_sebi REAL NOT NULL,
    fee_stamp_duty REAL NOT NULL,
    fee_gst REAL NOT NULL,
    slippage REAL NOT NULL,
    total_friction REAL NOT NULL,
    gross_pnl REAL DEFAULT 0.0,
    net_pnl REAL DEFAULT 0.0,
    holding_duration_seconds REAL DEFAULT 0.0,
    exit_trigger TEXT DEFAULT 'TIME_EXPIRY',
    executed_at TEXT NOT NULL
);

-- 5. Candidates
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    side TEXT NOT NULL,
    trigger_price REAL NOT NULL,
    initial_stop_price REAL NOT NULL,
    target_price REAL,
    score REAL NOT NULL,
    evidence JSON NOT NULL,
    feature_snapshot JSON,
    status TEXT NOT NULL CHECK(status IN ('DETECTED', 'REJECTED', 'PROMOTED'))
);

-- 6. Features
CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    vwap REAL NOT NULL,
    current_price REAL NOT NULL,
    momentum_score REAL NOT NULL,
    relative_volume REAL NOT NULL,
    volume_accel REAL NOT NULL,
    price_accel REAL NOT NULL,
    volatility REAL NOT NULL,
    spread REAL NOT NULL,
    liquidity_score REAL NOT NULL,
    regime TEXT NOT NULL
);

-- 7. AI Analyses
CREATE TABLE IF NOT EXISTS ai_analyses (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ANALYST', 'CHALLENGER')),
    thesis_summary TEXT NOT NULL,
    evidence JSON NOT NULL,
    invalidation_conditions JSON NOT NULL,
    risks JSON NOT NULL,
    suggested_action TEXT NOT NULL,
    confidence_score REAL,
    worst_case_scenario TEXT,
    downside_severity TEXT,
    recommendation_flag TEXT,
    latency_ms INTEGER NOT NULL,
    token_count INTEGER,
    is_fallback INTEGER NOT NULL DEFAULT 0,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 8. Trade Plans
CREATE TABLE IF NOT EXISTS trade_plans (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price_target REAL NOT NULL,
    hard_stop REAL NOT NULL,
    take_profit REAL,
    trailing_trigger REAL,
    expected_edge REAL NOT NULL,
    estimated_costs REAL NOT NULL,
    risk_limits JSON NOT NULL,
    stop_protection JSON NOT NULL,
    invalidation JSON NOT NULL,
    strategy TEXT NOT NULL,
    ai_evidence_references JSON NOT NULL,
    decision_reason TEXT NOT NULL,
    approval_mode TEXT NOT NULL CHECK(approval_mode IN ('AUTONOMOUS', 'MANUAL_PENDING', 'MANUAL_APPROVED', 'REJECTED')),
    created_at TEXT NOT NULL
);

-- 9. Risk Events
CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('INFO', 'WARNING', 'CRITICAL')),
    symbol TEXT,
    details JSON NOT NULL
);

-- 10. Strategy Versions
CREATE TABLE IF NOT EXISTS strategy_versions (
    id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    version TEXT NOT NULL,
    parameters JSON NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 11. Model Calls
CREATE TABLE IF NOT EXISTS model_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model_name TEXT NOT NULL,
    candidate_id TEXT,
    role TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    token_count INTEGER,
    success INTEGER NOT NULL,
    is_fallback INTEGER NOT NULL DEFAULT 0,
    error_reason TEXT
);

-- 12. Execution Metrics
CREATE TABLE IF NOT EXISTS execution_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_orders_submitted INTEGER NOT NULL,
    total_orders_filled INTEGER NOT NULL,
    total_orders_rejected INTEGER NOT NULL,
    avg_submission_latency_ms REAL NOT NULL,
    avg_fill_latency_ms REAL NOT NULL,
    total_slippage REAL NOT NULL,
    fill_rate_pct REAL NOT NULL
);

-- 13. System Events
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSON
);

-- 14. Strategy Proposals (Phase 22 Learning & Continuous Improvement)
CREATE TABLE IF NOT EXISTS strategy_proposals (
    id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    target_version TEXT NOT NULL,
    current_version TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    empirical_weakness TEXT NOT NULL,
    parameter_changes JSON NOT NULL,
    backtest_evidence JSON,
    paper_evidence JSON,
    approved_by TEXT,
    approval_token_masked TEXT,
    approved_at TEXT,
    rejection_reason TEXT,
    created_at TEXT NOT NULL
);

-- Indices for performance and query optimization
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_plan_id ON orders(plan_id);
CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(order_id);
CREATE INDEX IF NOT EXISTS idx_trades_position_id ON trades(position_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
CREATE INDEX IF NOT EXISTS idx_candidates_symbol ON candidates(symbol);
CREATE INDEX IF NOT EXISTS idx_features_symbol_ts ON features(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_candidate ON ai_analyses(candidate_id);
CREATE INDEX IF NOT EXISTS idx_trade_plans_candidate ON trade_plans(candidate_id);
CREATE INDEX IF NOT EXISTS idx_model_calls_model_ts ON model_calls(model_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON strategy_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_strat ON strategy_proposals(strategy_name);
"""
