// Comprehensive data types for AI Micro-Trading Terminal

export type ScreenId =
  | "command"
  | "scanner"
  | "candidates"
  | "chart"
  | "positions"
  | "orders"
  | "ai"
  | "journal"
  | "performance"
  | "backtesting"
  | "risk"
  | "health"
  | "logs"
  | "strategies"
  | "settings";

export type BadgeState =
  | "BUY"
  | "SELL"
  | "HOLD"
  | "WATCH"
  | "RISK"
  | "ERROR"
  | "CONNECTED"
  | "DISCONNECTED"
  | "AI THINKING"
  | "AI UNAVAILABLE"
  | "PENDING"
  | "PARTIAL FILL"
  | "FILLED"
  | "CANCELLED"
  | "REJECTED";

export interface CapitalState {
  starting_capital: number;
  available_capital: number;
  deployed_capital: number;
  total_equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_drawdown_pct: number;
  max_drawdown_limit_pct: number;
  currency: string;
}

export interface MarketScannerItem {
  symbol: string;
  last_price: number;
  change_pct: number;
  volume: number;
  rvol_10: number;
  vwap: number;
  vwap_distance_pct: number;
  spread_bps: number;
  relative_spread_pct: number;
  volatility_atr: number;
  sector: string;
  status: "ACTIVE" | "WATCHING" | "COOLDOWN";
}

export interface CandidateItem {
  candidate_id: string;
  symbol: string;
  detected_at: string;
  strategy_type: "MOMENTUM_CONTINUATION" | "EARLY_MOVE_DETECTION";
  trigger_price: number;
  hard_stop_price: number;
  take_profit_price: number;
  expected_gross_edge: number;
  expected_net_edge: number;
  rank_score: number;
  status: "DETECTED" | "IN_AI_REVIEW" | "PROMOTED" | "REJECTED";
  friction_estimate: number;
}

export interface PositionItem {
  position_id: string;
  plan_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  entry_price: number;
  current_price: number;
  hard_stop_price: number;
  trailing_stop_price?: number;
  take_profit_price?: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  status: "OPEN" | "CLOSING" | "CLOSED";
  opened_at: string;
  watcher_status: "ACTIVE" | "TRIGGERED" | "STANDBY";
  time_in_trade_minutes: number;
}

export interface OrderItem {
  client_order_id: string;
  plan_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT" | "STOP_LOSS";
  quantity: number;
  filled_quantity: number;
  price?: number;
  average_fill_price?: number;
  status: "CREATED" | "SUBMITTED" | "ACKNOWLEDGED" | "PARTIALLY_FILLED" | "FILLED" | "CANCELLED" | "REJECTED";
  created_at: string;
  rejection_reason?: string;
  broker_order_id?: string;
}

export interface AIAnalysisRecord {
  candidate_id: string;
  symbol: string;
  timestamp: string;
  qwen3_thesis: {
    model_name: string;
    thesis_summary: string;
    catalyst_identified?: string;
    bullish_evidence: string[];
    invalidation_conditions: string[];
    perceived_risks: string[];
    confidence_score: number;
    suggested_action: "PROCEED" | "REJECT" | "MORE_INFO";
    latency_ms: number;
    token_count?: number;
  };
  deepseek_r1_critique: {
    model_name: string;
    critique_summary: string;
    blind_spots_identified: string[];
    downside_scenarios: string[];
    risk_severity: "LOW" | "MEDIUM" | "SEVERE";
    recommendation: "CONFIRM" | "CONTEST" | "VETO";
    adjusted_confidence_multiplier: number;
    latency_ms: number;
  };
  council_resolution: {
    final_verdict: "APPROVED" | "VETOED" | "DOWNSIZED";
    effective_confidence: number;
    reasoning: string;
    deterministic_gate_passed: boolean;
  };
}

export interface TradeRecordItem {
  trade_id: string;
  plan_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  strategy: string;
  quantity: number;
  entry_timestamp: string;
  entry_price: number;
  exit_timestamp: string;
  exit_price: number;
  exit_trigger: string;
  gross_pnl: number;
  brokerage: number;
  stt: number;
  exchange_charges: number;
  sebi_charges: number;
  stamp_duty: number;
  gst: number;
  total_friction: number;
  net_pnl: number;
  holding_duration_seconds: number;
}

export interface PerformanceStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  expectancy: number;
  total_gross_pnl: number;
  total_friction: number;
  total_net_pnl: number;
  max_drawdown_pct: number;
  avg_win: number;
  avg_loss: number;
  strategies: {
    name: string;
    trades: number;
    win_rate_pct: number;
    net_pnl: number;
    profit_factor: number;
  }[];
}

export interface SystemHealthData {
  status: "HEALTHY" | "WARNING" | "CRITICAL";
  database: string;
  position_watcher: string;
  execution_engine: string;
  ai_council: string;
  mode: "PAPER" | "LIVE";
  latencies: {
    normalizer_ms: number;
    feature_engine_ms: number;
    trade_gate_ms: number;
    position_watcher_ms: number;
    qwen3_ms: number;
    deepseek_r1_ms: number;
  };
  sqlite: {
    journal_mode: string;
    wal_size_kb: number;
    connection_pool: string;
  };
  ollama: {
    status: string;
    loaded_models: string[];
    vram_used_mb: number;
  };
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR" | "CRITICAL";
  source: string;
  message: string;
  metadata?: Record<string, unknown>;
}
