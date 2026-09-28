import React, { useMemo } from "react";
import { ArrowRight, TrendingUp } from "lucide-react";
import { CapitalState, PositionItem, ScreenId } from "../../types";
import { Sparkline } from "../ui/Sparkline";

interface PortfolioWidgetProps {
  capital: CapitalState;
  positions: PositionItem[];
  onNavigate: (screen: ScreenId) => void;
}

const formatINR = (v: number): string =>
  new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(isFinite(v) ? v : 0);

export const PortfolioWidget: React.FC<PortfolioWidgetProps> = ({
  capital,
  positions,
  onNavigate,
}) => {
  const equity = capital.total_equity ?? 0;
  const starting = capital.starting_capital ?? 0;
  const realized = capital.realized_pnl ?? 0;
  const unrealized = capital.unrealized_pnl ?? 0;

  const dailyReturnPct = starting > 0 ? ((equity - starting) / starting) * 100 : 0;

  const spark = useMemo(() => {
    const base = starting > 0 ? starting : equity;
    const totalDrift = equity - base;
    return Array.from({ length: 20 }, (_, i) => {
      const t = i / 19;
      const wave = Math.sin(t * Math.PI * 3.1) * (Math.abs(totalDrift) * 0.35 + base * 0.002);
      return base + totalDrift * t + wave;
    });
  }, [equity, starting]);

  const holdings = positions.slice(0, 3);

  return (
    <section className="glass-panel rounded-xl p-4" aria-label="Portfolio summary">
      <div className="flex items-center justify-between">
        <h3 className="cockpit-label">Portfolio</h3>
        <TrendingUp size={14} className="text-sky-400" aria-hidden="true" />
      </div>

      <div className="mt-2 flex items-end justify-between gap-2">
        <div>
          <p className="font-mono text-xl font-bold text-slate-50 tabular-nums">
            ₹{formatINR(equity)}
          </p>
          <p
            className={`mt-0.5 font-mono text-[11px] font-semibold tabular-nums ${
              dailyReturnPct >= 0 ? "text-emerald-300" : "text-rose-300"
            }`}
          >
            {dailyReturnPct >= 0 ? "+" : ""}
            {dailyReturnPct.toFixed(2)}% today
          </p>
        </div>
        <Sparkline data={spark} width={96} height={38} color="#00E676" />
      </div>

      <div className="mt-2 flex items-center gap-3 font-mono text-[10px] tabular-nums">
        <span className="text-emerald-300">Realized +{formatINR(realized)}</span>
        <span className="text-slate-600">|</span>
        <span className="text-sky-300">Unrealized {formatINR(unrealized)}</span>
      </div>

      <div className="mt-3 border-t border-sky-500/12 pt-2">
        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Active Holdings
        </p>

        {holdings.length === 0 ? (
          <p className="py-4 text-center font-mono text-[10px] text-slate-600">
            No active holdings.
          </p>
        ) : (
          <ul className="mt-1.5 space-y-1.5">
            {holdings.map((p) => {
              const value = p.current_price * p.quantity;
              const retPct = (p.entry_price * p.quantity) > 0
                ? p.unrealized_pnl_pct
                : 0;
              return (
                <li
                  key={p.position_id}
                  className="flex items-center justify-between rounded-md border border-sky-500/10 bg-white/[0.02] px-2.5 py-1.5"
                >
                  <div className="min-w-0">
                    <p className="font-mono text-[11px] font-bold text-slate-100">
                      {p.symbol}
                    </p>
                    <p className="font-mono text-[9px] text-slate-500 tabular-nums">
                      {p.quantity} qty @ {p.current_price.toFixed(2)} · ₹{formatINR(value)}
                    </p>
                  </div>
                  <span
                    className={`font-mono text-[11px] font-semibold tabular-nums ${
                      retPct >= 0 ? "text-emerald-300" : "text-rose-300"
                    }`}
                  >
                    {retPct >= 0 ? "+" : ""}
                    {retPct.toFixed(2)}%
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <button
        type="button"
        onClick={() => onNavigate("performance")}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-sky-500/20 bg-sky-500/6 py-2 text-[11px] font-semibold text-sky-200 transition-colors hover:border-neon-cyan/45 hover:text-neon-cyan"
      >
        View All <ArrowRight size={12} aria-hidden="true" />
      </button>
    </section>
  );
};

export default PortfolioWidget;
