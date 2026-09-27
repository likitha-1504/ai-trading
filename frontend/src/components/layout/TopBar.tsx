import React from "react";
import { AlertOctagon, ShieldCheck, Activity } from "lucide-react";
import { CapitalState } from "../../types";

interface TopBarProps {
  capital: CapitalState;
  onOpenKillSwitch: () => void;
  isHalted: boolean;
}

const formatINR = (value: number): string =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(isFinite(value) ? value : 0);

export const TopBar: React.FC<TopBarProps> = ({
  capital,
  onOpenKillSwitch,
  isHalted,
}) => {
  const equity = capital?.total_equity ?? (capital as any)?.total_capital ?? 100;
  const available = capital?.available_capital ?? 100;
  const deployed = capital?.deployed_capital ?? 0;
  const pnl = capital?.realized_pnl ?? 0;
  const isProfit = pnl >= 0;

  return (
    <header
      className="sticky top-0 z-40 flex items-center justify-between px-4 py-2.5 bg-[#0B101D]/70 backdrop-blur-md border-b border-indigo-500/20 shadow-[0_4px_24px_-8px_rgba(99,102,241,0.15)]"
      role="banner"
      aria-label="Global trading header"
    >
      {/* Brand & Mode Identification */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div
            className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"
            aria-hidden="true"
          />
          <h1 className="text-sm font-bold tracking-tight text-slate-100 uppercase">
            AI Micro-Trader
          </h1>
        </div>

        <span
          className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/80 font-mono font-medium flex items-center gap-1"
          aria-label="Paper trading mode active"
        >
          <ShieldCheck size={12} aria-hidden="true" />
          PAPER: ACTIVE
        </span>

        {isHalted && (
          <span
            className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-600 font-mono font-bold animate-pulse flex items-center gap-1"
            role="status"
            aria-live="polite"
            aria-label="System halted"
          >
            <AlertOctagon size={12} aria-hidden="true" />
            SYSTEM HALTED
          </span>
        )}
      </div>

      {/* Global Real-Time Capital Facts */}
      <div
        className="hidden lg:flex items-center gap-3"
        aria-label="System capital facts"
      >
        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-sky-950/20 border border-sky-500/30 font-mono text-xs backdrop-blur-sm shadow-[0_0_18px_-6px_rgba(14,165,233,0.25)]">
          <span
            className="text-[10px] text-sky-300 font-bold bg-sky-950/90 px-1.5 rounded border border-sky-700/70"
            aria-label="Deterministic system fact"
          >
            SYSTEM FACT
          </span>
          <span className="text-slate-400">Equity:</span>
          <span className="text-slate-100 font-bold tabular-nums">
            {formatINR(equity)}
          </span>
          <span className="text-slate-600" aria-hidden="true">
            |
          </span>
          <span className="text-slate-400">Avail:</span>
          <span className="text-slate-200 tabular-nums">
            {formatINR(available)}
          </span>
          <span className="text-slate-600" aria-hidden="true">
            |
          </span>
          <span className="text-slate-400">Deployed:</span>
          <span className="text-slate-200 tabular-nums">
            {formatINR(deployed)}
          </span>
          <span className="text-slate-600" aria-hidden="true">
            |
          </span>
          <span className="text-slate-400">P&L:</span>
          <span
            className={`font-bold tabular-nums ${
              isProfit ? "text-emerald-400" : "text-rose-400"
            }`}
            aria-label={`${isProfit ? "Profit" : "Loss"}: ${formatINR(pnl)}`}
          >
            {isProfit ? "+" : ""}
            {formatINR(pnl)}
          </span>
        </div>

        <div
          className="flex items-center gap-1 text-[11px] font-mono text-slate-400 px-2 py-1 bg-surface/60 rounded border border-border-subtle backdrop-blur-sm"
          aria-label="Position watcher latency under 50 milliseconds"
        >
          <Activity size={12} className="text-emerald-400" aria-hidden="true" />
          <span>Watcher: &lt;50ms</span>
        </div>
      </div>

      {/* Emergency Kill-Switch Button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenKillSwitch}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 text-rose-400 border border-rose-500/30 hover:bg-rose-600/30 hover:text-rose-300 hover:shadow-[0_0_24px_-4px_rgba(225,29,72,0.45)] font-mono text-xs font-bold transition-all shadow-[0_0_12px_-4px_rgba(225,29,72,0.2)] active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B101D]"
          title="Emergency Position Square-Off & Autonomous System Shutdown"
          aria-label="Open emergency kill switch dialog"
        >
          <AlertOctagon size={14} aria-hidden="true" />
          KILL SWITCH
        </button>
      </div>
    </header>
  );
};