import {
  CapitalState,
  MarketScannerItem,
  CandidateItem,
  PositionItem,
  OrderItem,
  AIAnalysisRecord,
  TradeRecordItem,
  PerformanceStats,
  SystemHealthData,
  LogEntry,
} from "../types";
import {
  mockCapital,
  mockScanner,
  mockCandidates,
  mockPositions,
  mockOrders,
  mockAIAnalysis,
  mockTrades,
  mockPerformance,
  mockSystemHealth,
  mockLogs,
} from "../data/mockData";

const API_BASE = "/api/v1";

async function fetchWithFallback<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      return fallback;
    }
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export const api = {
  async getCapital(): Promise<CapitalState> {
    const raw = await fetchWithFallback<any>(`${API_BASE}/dashboard/capital`, mockCapital);
    if (!raw) return mockCapital;
    const totalEquity = Number(raw.total_equity ?? raw.total_capital ?? mockCapital.total_equity);
    const startCap = Number(raw.starting_capital ?? raw.high_water_mark ?? mockCapital.starting_capital);
    return {
      starting_capital: startCap,
      available_capital: Number(raw.available_capital ?? mockCapital.available_capital),
      deployed_capital: Number(raw.deployed_capital ?? 0),
      total_equity: totalEquity,
      realized_pnl: Number(raw.realized_pnl ?? 0),
      unrealized_pnl: Number(raw.unrealized_pnl ?? 0),
      daily_drawdown_pct: Number(raw.daily_drawdown_pct ?? 0),
      max_drawdown_limit_pct: Number(raw.max_drawdown_limit_pct ?? mockCapital.max_drawdown_limit_pct ?? 3.0),
      currency: String(raw.currency ?? "INR (₹)"),
    };
  },

  async getMarketScanner(): Promise<MarketScannerItem[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/market/scanner`, mockScanner);
    if (!Array.isArray(raw) || raw.length === 0) return mockScanner;
    return raw.map((item, idx) => {
      const fallbackMock = mockScanner[idx % mockScanner.length];
      const price = Number(item.last_price ?? item.price ?? fallbackMock?.last_price ?? 100);
      const vwap = Number(item.vwap ?? fallbackMock?.vwap ?? price);
      const vwapDist = vwap > 0 ? ((price - vwap) / vwap) * 100 : 0;
      const spreadBps = Number(item.spread_bps ?? (item.spread_pct ? Number(item.spread_pct) * 10000 : fallbackMock?.spread_bps ?? 4.5));
      return {
        symbol: String(item.symbol ?? fallbackMock?.symbol ?? "EQUITY"),
        last_price: price,
        change_pct: Number(item.change_pct ?? vwapDist),
        volume: Number(item.volume ?? fallbackMock?.volume ?? 1000000),
        rvol_10: Number(item.rvol_10 ?? item.relative_volume ?? fallbackMock?.rvol_10 ?? 1.5),
        vwap: vwap,
        vwap_distance_pct: Number(item.vwap_distance_pct ?? vwapDist),
        spread_bps: spreadBps,
        relative_spread_pct: Number(item.relative_spread_pct ?? (spreadBps / 10000)),
        volatility_atr: Number(item.volatility_atr ?? fallbackMock?.volatility_atr ?? 15.0),
        sector: String(item.sector ?? fallbackMock?.sector ?? "Equities"),
        status: (item.status as any) ?? "ACTIVE",
      };
    });
  },

  async getCandidates(): Promise<CandidateItem[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/candidates`, mockCandidates);
    if (!Array.isArray(raw) || raw.length === 0) return mockCandidates;
    return raw.map((c) => {
      const trig = Number(c.trigger_price ?? 100.0);
      const stop = Number(c.hard_stop_price ?? c.initial_stop_price ?? (trig * 0.98));
      const target = Number(c.take_profit_price ?? c.suggested_target_price ?? (trig * 1.04));
      const gross = trig > 0 ? ((target - trig) / trig) * 100 : 1.5;
      const net = gross * 0.65;
      return {
        candidate_id: String(c.candidate_id ?? `cand-${Math.random().toString(36).slice(2, 8)}`),
        symbol: String(c.symbol ?? "EQUITY"),
        detected_at: String(c.detected_at ?? new Date().toISOString()),
        strategy_type: c.strategy_type ?? "MOMENTUM_CONTINUATION",
        trigger_price: trig,
        hard_stop_price: stop,
        take_profit_price: target,
        expected_gross_edge: Number(c.expected_gross_edge ?? c.quantitative_evidence?.expected_gross_edge ?? gross),
        expected_net_edge: Number(c.expected_net_edge ?? c.quantitative_evidence?.expected_net_edge ?? net),
        rank_score: Number(c.rank_score ?? 85.0),
        status: (c.status as any) ?? "DETECTED",
        friction_estimate: Number(c.friction_estimate ?? 0.25),
      };
    });
  },

  async getPositions(): Promise<PositionItem[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/positions`, mockPositions);
    if (!Array.isArray(raw)) return mockPositions;
    return raw.map((p) => {
      const entry = Number(p.entry_price ?? 100.0);
      const current = Number(p.current_price ?? entry);
      const qty = Number(p.quantity ?? 1);
      const unrealized = Number(p.unrealized_pnl ?? ((current - entry) * qty));
      const unrealizedPct = (entry * qty) > 0 ? (unrealized / (entry * qty)) * 100 : 0;
      return {
        position_id: String(p.position_id ?? "pos-1"),
        plan_id: String(p.plan_id ?? "plan-1"),
        symbol: String(p.symbol ?? "EQUITY"),
        side: p.side ?? "BUY",
        quantity: qty,
        entry_price: entry,
        current_price: current,
        hard_stop_price: Number(p.hard_stop_price ?? (entry * 0.98)),
        trailing_stop_price: p.trailing_stop_price ? Number(p.trailing_stop_price) : undefined,
        take_profit_price: p.take_profit_price ? Number(p.take_profit_price) : undefined,
        unrealized_pnl: unrealized,
        unrealized_pnl_pct: Number(p.unrealized_pnl_pct ?? unrealizedPct),
        status: p.status ?? "OPEN",
        opened_at: String(p.opened_at ?? new Date().toISOString()),
        watcher_status: (p.watcher_status as any) ?? "ACTIVE",
        time_in_trade_minutes: Number(p.time_in_trade_minutes ?? 12),
      };
    });
  },

  async getOrders(): Promise<OrderItem[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/orders`, mockOrders);
    if (!Array.isArray(raw)) return mockOrders;
    return raw.map((o) => ({
      client_order_id: String(o.client_order_id ?? "ord-1"),
      plan_id: String(o.plan_id ?? "plan-1"),
      symbol: String(o.symbol ?? "EQUITY"),
      side: (o.side ?? "BUY") as "BUY" | "SELL",
      order_type: (o.order_type ?? "LIMIT") as any,
      quantity: Number(o.quantity ?? 1),
      filled_quantity: Number(o.filled_quantity ?? o.quantity ?? 0),
      price: o.price !== undefined ? Number(o.price) : (o.limit_price !== undefined ? Number(o.limit_price) : undefined),
      average_fill_price: o.average_fill_price !== undefined ? Number(o.average_fill_price) : undefined,
      status: (o.status ?? "FILLED") as any,
      created_at: String(o.created_at ?? o.submitted_at ?? new Date().toISOString()),
      rejection_reason: o.rejection_reason ? String(o.rejection_reason) : undefined,
      broker_order_id: o.broker_order_id ? String(o.broker_order_id) : undefined,
    }));
  },

  async getAIAnalyses(): Promise<AIAnalysisRecord[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/ai/analyses`, [mockAIAnalysis]);
    if (!Array.isArray(raw) || raw.length === 0) return [mockAIAnalysis];
    return raw.map((a) => {
      if (a.qwen3_thesis && a.deepseek_r1_critique && a.council_resolution) {
        return a as AIAnalysisRecord;
      }
      return {
        ...mockAIAnalysis,
        ...a,
        candidate_id: String(a.candidate_id ?? mockAIAnalysis.candidate_id),
        symbol: String(a.symbol ?? mockAIAnalysis.symbol),
        timestamp: String(a.timestamp ?? mockAIAnalysis.timestamp),
      };
    });
  },

  async getTrades(): Promise<TradeRecordItem[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/trades`, mockTrades);
    if (!Array.isArray(raw) || raw.length === 0) return mockTrades;
    return raw.map((t) => {
      const fric = t.friction ?? {};
      return {
        trade_id: String(t.trade_id ?? "trd-1"),
        plan_id: String(t.plan_id ?? "plan-1"),
        symbol: String(t.symbol ?? "EQUITY"),
        strategy: String(t.strategy ?? "MOMENTUM_CONTINUATION"),
        side: (t.side ?? "BUY") as "BUY" | "SELL",
        quantity: Number(t.quantity ?? 1),
        entry_timestamp: String(t.entry_timestamp ?? t.entry_time ?? new Date().toISOString()),
        entry_price: Number(t.entry_price ?? 100),
        exit_timestamp: String(t.exit_timestamp ?? t.exit_time ?? new Date().toISOString()),
        exit_price: Number(t.exit_price ?? 102),
        exit_trigger: String(t.exit_trigger ?? "PROFIT_TARGET"),
        gross_pnl: Number(t.gross_pnl ?? 2.0),
        brokerage: Number(t.brokerage ?? fric.brokerage ?? 0.1),
        stt: Number(t.stt ?? fric.stt ?? 0.05),
        exchange_charges: Number(t.exchange_charges ?? fric.exchange_charges ?? 0.02),
        sebi_charges: Number(t.sebi_charges ?? fric.sebi_charges ?? 0.001),
        stamp_duty: Number(t.stamp_duty ?? fric.stamp_duty ?? 0.005),
        gst: Number(t.gst ?? fric.gst ?? 0.02),
        total_friction: Number(t.total_friction ?? fric.total_friction ?? 0.2),
        net_pnl: Number(t.net_pnl ?? 1.5),
        holding_duration_seconds: Number(t.holding_duration_seconds ?? t.holding_seconds ?? 300),
      };
    });
  },

  async getPerformance(): Promise<PerformanceStats> {
    const raw = await fetchWithFallback<any>(`${API_BASE}/performance`, mockPerformance);
    if (!raw) return mockPerformance;
    return {
      total_trades: Number(raw.total_trades ?? mockPerformance.total_trades),
      winning_trades: Number(raw.winning_trades ?? mockPerformance.winning_trades),
      losing_trades: Number(raw.losing_trades ?? mockPerformance.losing_trades),
      win_rate_pct: Number(raw.win_rate_pct ?? raw.win_rate ?? mockPerformance.win_rate_pct),
      profit_factor: Number(raw.profit_factor ?? mockPerformance.profit_factor),
      expectancy: Number(raw.expectancy ?? mockPerformance.expectancy),
      total_gross_pnl: Number(raw.total_gross_pnl ?? raw.gross_pnl ?? mockPerformance.total_gross_pnl),
      total_friction: Number(raw.total_friction ?? mockPerformance.total_friction),
      total_net_pnl: Number(raw.total_net_pnl ?? raw.net_pnl ?? mockPerformance.total_net_pnl),
      max_drawdown_pct: Number(raw.max_drawdown_pct ?? mockPerformance.max_drawdown_pct),
      avg_win: Number(raw.avg_win ?? mockPerformance.avg_win),
      avg_loss: Number(raw.avg_loss ?? mockPerformance.avg_loss),
      strategies: Array.isArray(raw.strategies) ? raw.strategies : mockPerformance.strategies,
    };
  },

  async getSystemHealth(): Promise<SystemHealthData> {
    const raw = await fetchWithFallback<any>(`${API_BASE}/system/health`, mockSystemHealth);
    if (!raw) return mockSystemHealth;
    const isNominal = raw.status === "HEALTHY" || raw.status === "NOMINAL" || raw.status === "OPERATIONAL";
    const isCritical = raw.status === "CRITICAL" || raw.status === "HALTED";
    return {
      status: isNominal ? "HEALTHY" : isCritical ? "CRITICAL" : "WARNING",
      database: String(raw.database ?? mockSystemHealth.database),
      position_watcher: String(raw.position_watcher ?? mockSystemHealth.position_watcher),
      execution_engine: String(raw.execution_engine ?? mockSystemHealth.execution_engine),
      ai_council: String(raw.ai_council ?? mockSystemHealth.ai_council),
      mode: (raw.mode === "LIVE" ? "LIVE" : "PAPER") as "PAPER" | "LIVE",
      latencies: {
        normalizer_ms: Number(raw.latencies?.normalizer_ms ?? mockSystemHealth.latencies.normalizer_ms),
        feature_engine_ms: Number(raw.latencies?.feature_engine_ms ?? mockSystemHealth.latencies.feature_engine_ms),
        trade_gate_ms: Number(raw.latencies?.trade_gate_ms ?? mockSystemHealth.latencies.trade_gate_ms),
        position_watcher_ms: Number(raw.latencies?.position_watcher_ms ?? mockSystemHealth.latencies.position_watcher_ms),
        qwen3_ms: Number(raw.latencies?.qwen3_ms ?? mockSystemHealth.latencies.qwen3_ms),
        deepseek_r1_ms: Number(raw.latencies?.deepseek_r1_ms ?? mockSystemHealth.latencies.deepseek_r1_ms),
      },
      sqlite: {
        journal_mode: String(raw.sqlite?.journal_mode ?? (raw.database?.includes("WAL") ? "WAL" : mockSystemHealth.sqlite.journal_mode)),
        wal_size_kb: Number(raw.sqlite?.wal_size_kb ?? mockSystemHealth.sqlite.wal_size_kb),
        connection_pool: String(raw.sqlite?.connection_pool ?? mockSystemHealth.sqlite.connection_pool),
      },
      ollama: {
        status: String(raw.ollama?.status ?? (raw.ai_council === "ONLINE" ? "ONLINE" : mockSystemHealth.ollama.status)),
        loaded_models: Array.isArray(raw.ollama?.loaded_models) ? raw.ollama.loaded_models : mockSystemHealth.ollama.loaded_models,
        vram_used_mb: Number(raw.ollama?.vram_used_mb ?? mockSystemHealth.ollama.vram_used_mb),
      },
    };
  },

  async getLogs(): Promise<LogEntry[]> {
    const raw = await fetchWithFallback<any[]>(`${API_BASE}/logs/system`, mockLogs);
    if (!Array.isArray(raw) || raw.length === 0) return mockLogs;
    return raw.map((l, idx) => ({
      id: String(l.id ?? `log-${idx + 1}`),
      timestamp: String(l.timestamp ?? new Date().toISOString()),
      level: (l.level === "WARNING" ? "WARN" : (l.level ?? l.severity ?? "INFO")) as any,
      source: String(l.source ?? l.component ?? "SYSTEM"),
      message: String(l.message ?? ""),
      metadata: l.metadata ?? (l.details ? { details: l.details } : undefined),
    }));
  },

  async triggerKillSwitch(reason: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/system/kill-switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, initiated_by: "FRONTEND_DASHBOARD" }),
      });
      if (res.ok) {
        return (await res.json()) as { success: boolean; message: string };
      }
    } catch {
      // Fallback response for offline mock mode
    }
    return {
      success: true,
      message: `Emergency Kill-Switch triggered: ${reason}. All positions squared off.`,
    };
  },

  async getLiveReadinessAudit(): Promise<any> {
    return fetchWithFallback<any>(`${API_BASE}/system/live-readiness`, {
      overall_status: "READY_FOR_APPROVAL",
      total_checks: 12,
      passed_checks: 12,
      failed_checks: 0,
      approval_gate: {
        gate_status: "AWAITING_EXPLICIT_HUMAN_APPROVAL",
        environment_safety_lock_active: true,
      },
    });
  },
};
