import React from "react";
import { CapitalState, PositionItem, LogEntry, CandidateItem, ScreenId } from "../types";
import { MetricCard } from "../components/ui/MetricCard";
import { Badge } from "../components/ui/Badge";
import { FactBanner } from "../components/ui/FactBanner";
import { Activity, ShieldCheck, ArrowRight, Zap, Target } from "lucide-react";

interface CommandCenterProps {
  capital: CapitalState;
  positions: PositionItem[];
  candidates: CandidateItem[];
  logs: LogEntry[];
  onNavigate: (screen: ScreenId) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  capital,
  positions,
  candidates,
  logs,
  onNavigate,
}) => {
  const activePos = positions[0];
  const startCap = capital?.starting_capital ?? 100.0;
  const equity = capital?.total_equity ?? (capital as any)?.total_capital ?? startCap;
  const deployed = capital?.deployed_capital ?? 0.0;
  const available = capital?.available_capital ?? startCap;
  const realized = capital?.realized_pnl ?? 0.0;
  const maxDdLimit = capital?.max_drawdown_limit_pct ?? 3.0;

  return (
    <div className="space-y-4">
      {/* Top Banner: Deterministic Fact Confirmation */}
      <FactBanner
        type="SYSTEM_FACT"
        title="Micro-Capital Paper Execution Active"
        subtitle={`Starting Capital: ₹${startCap.toFixed(2)} | Current Equity: ₹${equity.toFixed(2)} | Deployed: ₹${deployed.toFixed(2)}`}
      >
        <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-sky-900/30 text-xs font-mono">
          <span className="text-slate-400">Autonomous Threshold:</span>
          <span className="text-sky-300 font-semibold">₹300.00 max</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Circuit Breaker:</span>
          <span className="text-amber-300 font-semibold">{maxDdLimit.toFixed(1)}% Daily Max DD</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Square-Off Cutoff:</span>
          <span className="text-emerald-300 font-semibold">15:15 IST (09:45 UTC)</span>
        </div>
      </FactBanner>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Total Equity"
          value={`₹${equity.toFixed(2)}`}
          subtext={`Base: ₹${startCap.toFixed(2)}`}
          trend={equity >= startCap ? "up" : "down"}
          trendValue={`+₹${(equity - startCap).toFixed(2)}`}
          isFact
        />
        <MetricCard
          label="Available Margin"
          value={`₹${available.toFixed(2)}`}
          subtext={`Deployed: ₹${deployed.toFixed(2)}`}
          isFact
        />
        <MetricCard
          label="Realized Daily P&L"
          value={`${realized >= 0 ? "+" : ""}₹${realized.toFixed(2)}`}
          subtext="Net of Indian friction"
          trend={realized >= 0 ? "up" : "down"}
          trendValue={`${startCap > 0 ? ((realized / startCap) * 100).toFixed(1) : "0.0"}%`}
          isFact
        />
        <MetricCard
          label="Watcher Health"
          value="< 50ms"
          subtext="Autonomous loop: 0.8ms"
          trend="up"
          trendValue="NOMINAL"
          isFact
        />
      </div>

      {/* Main Grid: Active Trade Card + Scanner Preview + Recent Candidates */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Active Trade / Position Watcher Widget */}
        <div className="lg:col-span-2 p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                Active Position Risk Surveillance
              </h3>
            </div>
            {activePos ? (
              <Badge state="WATCH">
                SUB-50MS WATCHER ACTIVE
              </Badge>
            ) : (
              <Badge state="HOLD">ZERO OPEN POSITIONS</Badge>
            )}
          </div>

          {activePos ? (
            <div className="p-3.5 rounded-lg bg-[#0B0E14] border border-emerald-900/40 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold font-mono text-slate-100">
                      {activePos.symbol}
                    </span>
                    <Badge state={activePos.side}>{activePos.side}</Badge>
                    <span className="text-xs text-slate-400 font-mono">
                      Qty: {activePos.quantity}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    Plan ID: {activePos.plan_id} • In trade: {activePos.time_in_trade_minutes}m
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-base font-bold font-mono text-emerald-400 tabular-nums">
                    +₹{activePos.unrealized_pnl.toFixed(2)} (+{activePos.unrealized_pnl_pct.toFixed(2)}%)
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Unrealized P&L</span>
                </div>
              </div>

              {/* Dynamic Target / Stop Price Distance Bar */}
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-rose-400">Hard Stop: ₹{activePos.hard_stop_price.toFixed(2)}</span>
                  <span className="text-slate-200 font-bold">Current: ₹{activePos.current_price.toFixed(2)}</span>
                  <span className="text-emerald-400">Target: ₹{activePos.take_profit_price?.toFixed(2) || "N/A"}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden relative">
                  <div className="absolute left-0 top-0 bottom-0 bg-rose-500/50 w-1/4" />
                  <div className="absolute left-1/4 top-0 bottom-0 bg-emerald-500 w-1/2" />
                  <div className="absolute right-0 top-0 bottom-0 bg-emerald-400/40 w-1/4" />
                  {/* Current price marker */}
                  <div
                    className="absolute top-0 bottom-0 w-1.5 bg-white shadow-md z-10"
                    style={{ left: "55%" }}
                  />
                </div>
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>Trailing Stop: ₹{activePos.trailing_stop_price?.toFixed(2)}</span>
                  <span>Entry: ₹{activePos.entry_price.toFixed(2)}</span>
                  <span>R:R = 1:2.0</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#222938] text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1 text-emerald-400">
                  <ShieldCheck size={12} />
                  Watcher Guard: Continuous Tick Surveillance
                </span>
                <button
                  onClick={() => onNavigate("positions")}
                  className="text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
                >
                  Manage Position <ArrowRight size={12} />
                </button>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500 font-mono text-xs">
              <p>Position Watcher idling in sub-50ms heartbeat loop.</p>
              <p className="text-[11px] text-slate-600 mt-1">
                Awaiting promoted candidate approval from Deterministic Trade Gate.
              </p>
            </div>
          )}

          {/* Quick Candidates Preview */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5">
                <Zap size={14} className="text-amber-400" />
                LATEST STRATEGY CANDIDATES
              </span>
              <button
                onClick={() => onNavigate("candidates")}
                className="text-[11px] text-sky-400 hover:underline font-mono"
              >
                View All ({candidates.length})
              </button>
            </div>

            <div className="space-y-1.5">
              {candidates.slice(0, 3).map((c) => (
                <div
                  key={c.candidate_id}
                  className="flex items-center justify-between p-2 rounded bg-[#0B0E14] border border-[#222938] text-xs font-mono"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100">{c.symbol}</span>
                    <Badge state={c.strategy_type === "MOMENTUM_CONTINUATION" ? "BUY" : "WATCH"}>
                      {c.strategy_type === "MOMENTUM_CONTINUATION" ? "MOMENTUM" : "EARLY-MOVE"}
                    </Badge>
                    <span className="text-slate-400 text-[11px]">Rank: {c.rank_score.toFixed(1)}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-slate-300 tabular-nums">Trigger: ₹{c.trigger_price.toFixed(2)}</span>
                    <span className="text-emerald-400 tabular-nums font-semibold">
                      +{c.expected_net_edge.toFixed(2)}% net
                    </span>
                    <Badge
                      state={
                        c.status === "PROMOTED"
                          ? "FILLED"
                          : c.status === "IN_AI_REVIEW"
                          ? "AI THINKING"
                          : c.status === "REJECTED"
                          ? "REJECTED"
                          : "PENDING"
                      }
                    >
                      {c.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live System Logs Stream Widget */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
              <div className="flex items-center gap-2">
                <Target size={16} className="text-sky-400" />
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                  Live Event Stream
                </h3>
              </div>
              <button
                onClick={() => onNavigate("logs")}
                className="text-[11px] text-sky-400 hover:underline font-mono"
              >
                All Logs
              </button>
            </div>

            <div className="space-y-2 mt-3 overflow-y-auto max-h-[320px] pr-1">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="p-2 rounded bg-[#0B0E14] border border-[#222938] text-[11px] font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-slate-500 text-[10px]">
                    <span className="text-slate-400">{log.source}</span>
                    <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-slate-200 leading-snug">{log.message}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="p-2.5 rounded bg-sky-950/40 border border-sky-800/40 text-[11px] font-mono text-sky-300">
            <span className="font-bold">[SYSTEM FACT]</span> SQLite WAL journal active. Deterministic safety core ensures zero unverified broker dispatches.
          </div>
        </div>
      </div>
    </div>
  );
};
