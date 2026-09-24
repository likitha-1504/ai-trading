import React from "react";
import { CapitalState } from "../types";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";
import { ShieldAlert } from "lucide-react";

interface RiskCapitalProps {
  capital: CapitalState;
}

export const RiskCapital: React.FC<RiskCapitalProps> = ({ capital }) => {
  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Deterministic Risk Governance & Capital Protection Engine"
        subtitle="Enforces capital ceilings, max daily drawdown circuit breaker (3.0%), minimum liquidity (70/100), and max relative spread (15 bps) without LLM intervention."
      />

      {/* Capital Allocation & Autonomous Limits Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Starting Capital Cap */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2 font-mono text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Micro-Capital Cap:</span>
            <span className="text-slate-100 font-bold">₹100.00 base</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-sky-500 rounded-full"
              style={{ width: `${(capital.deployed_capital / capital.starting_capital) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-500">
            <span>Deployed: ₹{capital.deployed_capital.toFixed(2)}</span>
            <span>Available: ₹{capital.available_capital.toFixed(2)}</span>
          </div>
        </div>

        {/* Autonomous Threshold Meter */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2 font-mono text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Autonomous Gate Limit:</span>
            <span className="text-emerald-400 font-bold">≤ ₹300.00</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-emerald-500 w-1/3 rounded-full" />
          </div>
          <p className="text-[11px] text-slate-500">
            Trades &gt; ₹300 require explicit manual confirmation.
          </p>
        </div>

        {/* Daily Drawdown Circuit Breaker Gauge */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-amber-900/30 space-y-2 font-mono text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Daily Drawdown Circuit Breaker:</span>
            <span className="text-amber-400 font-bold">
              {capital.daily_drawdown_pct.toFixed(2)}% / {capital.max_drawdown_limit_pct.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full"
              style={{
                width: `${Math.min(
                  (capital.daily_drawdown_pct / capital.max_drawdown_limit_pct) * 100,
                  100
                )}%`,
              }}
            />
          </div>
          <p className="text-[11px] text-slate-500">
            Reaching 3.0% automatically halts trading for the remainder of the session.
          </p>
        </div>
      </div>

      {/* Risk Limits Configuration Summary */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3 font-mono text-xs">
        <h4 className="font-bold text-slate-200 uppercase tracking-wider">
          Enforced Mathematical Risk Limits (System Invariants)
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <span className="text-[10px] text-slate-500 uppercase">Max Open Positions</span>
            <p className="text-sm font-bold text-slate-100 mt-0.5">1 Position</p>
            <span className="text-[10px] text-slate-500">Single active slot</span>
          </div>
          <div className="p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <span className="text-[10px] text-slate-500 uppercase">Max Position Size</span>
            <p className="text-sm font-bold text-slate-100 mt-0.5">₹300.00</p>
            <span className="text-[10px] text-slate-500">Strict capital cap</span>
          </div>
          <div className="p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <span className="text-[10px] text-slate-500 uppercase">Max Spread Hurdle</span>
            <p className="text-sm font-bold text-slate-100 mt-0.5">15 bps</p>
            <span className="text-[10px] text-slate-500">Reject wide spreads</span>
          </div>
          <div className="p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <span className="text-[10px] text-slate-500 uppercase">Min Net Edge Hurdle</span>
            <p className="text-sm font-bold text-emerald-400 mt-0.5">0.35%</p>
            <span className="text-[10px] text-slate-500">Clears Indian friction</span>
          </div>
        </div>
      </div>

      {/* Real-Time Risk Events Log */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} className="text-amber-400" />
            <h4 className="font-bold text-slate-200 uppercase tracking-wider">
              Recent Risk Events & Circuit Breaker Telemetry
            </h4>
          </div>
          <Badge state="CONNECTED">CIRCUIT WATCHER ACTIVE</Badge>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-300">Daily Drawdown Status: Nominal (0.00%)</span>
            </div>
            <span className="text-slate-500 text-[11px]">Last evaluated: 10:15:30 IST</span>
          </div>
          <div className="flex items-center justify-between p-2.5 rounded bg-[#0B0E14] border border-[#222938]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-300">Intraday Square-off Cutoff: 15:15 IST (Auto-exit configured)</span>
            </div>
            <span className="text-slate-500 text-[11px]">Hard boundary</span>
          </div>
        </div>
      </div>
    </div>
  );
};
