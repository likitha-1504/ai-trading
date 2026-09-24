import React from "react";
import { AlertOctagon, ShieldCheck, Activity } from "lucide-react";
import { CapitalState } from "../../types";

interface TopBarProps {
  capital: CapitalState;
  onOpenKillSwitch: () => void;
  isHalted: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  capital,
  onOpenKillSwitch,
  isHalted,
}) => {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-4 py-2.5 bg-[#0B0E14] border-b border-[#222938]">
      {/* Brand & Mode Identification */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <h1 className="text-sm font-bold tracking-tight text-slate-100 uppercase">
            AI Micro-Trader
          </h1>
        </div>

        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/80 font-mono font-medium flex items-center gap-1">
          <ShieldCheck size={12} />
          PAPER: ACTIVE
        </span>

        {isHalted && (
          <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-600 font-mono font-bold animate-pulse flex items-center gap-1">
            <AlertOctagon size={12} />
            SYSTEM HALTED
          </span>
        )}
      </div>

      {/* Global Real-Time Capital Facts */}
      <div className="hidden lg:flex items-center gap-3">
        {/* Sky-blue border strictly identifying deterministic fact */}
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-[#151A23] border border-[#0369A1]/60 font-mono text-xs">
          <span className="text-[10px] text-sky-400 font-bold bg-sky-950/90 px-1 rounded border border-sky-800/70">
            SYSTEM FACT
          </span>
          <span className="text-slate-400">Equity:</span>
          <span className="text-slate-100 font-bold tabular-nums">
            ₹{capital.total_equity.toFixed(2)}
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">Avail:</span>
          <span className="text-slate-200 tabular-nums">
            ₹{capital.available_capital.toFixed(2)}
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">Deployed:</span>
          <span className="text-slate-200 tabular-nums">
            ₹{capital.deployed_capital.toFixed(2)}
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">P&L:</span>
          <span
            className={`font-bold tabular-nums ${
              capital.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            {capital.realized_pnl >= 0 ? "+" : ""}₹{capital.realized_pnl.toFixed(2)}
          </span>
        </div>

        <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 px-2 py-1 bg-[#151A23] rounded border border-[#222938]">
          <Activity size={12} className="text-emerald-400" />
          <span>Watcher: &lt;50ms</span>
        </div>
      </div>

      {/* Emergency Kill-Switch Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenKillSwitch}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 text-rose-400 border border-rose-500/50 hover:bg-rose-600 hover:text-white font-mono text-xs font-bold transition-all shadow-[0_0_15px_rgba(225,29,72,0.15)] active:scale-95"
          title="Emergency Position Square-Off & Autonomous System Shutdown"
        >
          <AlertOctagon size={14} />
          KILL SWITCH
        </button>
      </div>
    </header>
  );
};
