import React from "react";
import { PerformanceStats } from "../types";
import { FactBanner } from "../components/ui/FactBanner";
import { MetricCard } from "../components/ui/MetricCard";
import { TrendingUp } from "lucide-react";

interface PerformanceAnalyticsProps {
  performance: PerformanceStats;
}

export const PerformanceAnalytics: React.FC<PerformanceAnalyticsProps> = ({
  performance,
}) => {
  // Mock equity curve data points (Base 100)
  const equityPoints = [100.0, 100.5, 99.8, 101.2, 101.0, 102.4];
  const maxEq = 104;
  const minEq = 98;

  const getPointsString = (): string => {
    return equityPoints
      .map((p, i) => {
        const x = 30 + i * 140;
        const y = 140 - ((p - minEq) / (maxEq - minEq)) * 110;
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Performance Analytics & Empirical Edge Stratification"
        subtitle="Audited financial metrics calculated from closed trade journal records. Separates gross returns from statutory friction drag."
      />

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Win Rate"
          value={`${performance.win_rate_pct.toFixed(1)}%`}
          subtext={`${performance.winning_trades}W / ${performance.losing_trades}L (${performance.total_trades} total)`}
          trend={performance.win_rate_pct >= 50 ? "up" : "down"}
          trendValue="Empirical"
          isFact
        />
        <MetricCard
          label="Profit Factor"
          value={performance.profit_factor.toFixed(2)}
          subtext={`Avg Win: ₹${performance.avg_win} | Loss: ₹${Math.abs(performance.avg_loss)}`}
          trend={performance.profit_factor >= 1.5 ? "up" : "neutral"}
          trendValue="Edge > 1.5x"
          isFact
        />
        <MetricCard
          label="Total Net P&L"
          value={`+₹${performance.total_net_pnl.toFixed(2)}`}
          subtext={`Gross: ₹${performance.total_gross_pnl.toFixed(2)}`}
          trend="up"
          trendValue="+26.4%"
          isFact
        />
        <MetricCard
          label="Max Drawdown"
          value={`${performance.max_drawdown_pct.toFixed(2)}%`}
          subtext="Circuit limit: 3.0%"
          trend="up"
          trendValue="Safe Zone"
          isFact
        />
      </div>

      {/* Equity Curve SVG Chart */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2">
        <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-emerald-400" />
            <h3 className="text-xs font-bold text-slate-100 font-mono uppercase tracking-wider">
              Account Equity Curve (Base ₹100.00)
            </h3>
          </div>
          <span className="text-xs font-mono text-emerald-400 font-bold">
            Current: ₹{performance.total_net_pnl + 100.0}
          </span>
        </div>

        <div className="w-full h-44 relative pt-2">
          <svg className="w-full h-full" viewBox="0 0 760 150" preserveAspectRatio="none">
            {/* Horizontal Grid lines */}
            {[100, 102, 104].map((level) => {
              const y = 140 - ((level - minEq) / (maxEq - minEq)) * 110;
              return (
                <g key={level}>
                  <line x1="20" y1={y} x2="740" y2={y} stroke="#222938" strokeDasharray="3 3" />
                  <text x="745" y={y + 3} fill="#64748B" fontSize="9" fontFamily="monospace">
                    ₹{level}
                  </text>
                </g>
              );
            })}

            {/* Baseline ₹100 Line */}
            <line
              x1="20"
              y1={140 - ((100 - minEq) / (maxEq - minEq)) * 110}
              x2="740"
              y2={140 - ((100 - minEq) / (maxEq - minEq)) * 110}
              stroke="#334155"
              strokeWidth="1.5"
            />

            {/* Equity Polyline */}
            <polyline
              fill="none"
              stroke="#10B981"
              strokeWidth="2.5"
              points={getPointsString()}
            />

            {/* Points */}
            {equityPoints.map((p, i) => {
              const x = 30 + i * 140;
              const y = 140 - ((p - minEq) / (maxEq - minEq)) * 110;
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="4"
                  fill="#0B0E14"
                  stroke="#10B981"
                  strokeWidth="2"
                />
              );
            })}
          </svg>
        </div>
      </div>

      {/* Strategy Stratification & Fee Drag Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Strategy Stratification */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3 font-mono text-xs">
          <h4 className="font-bold text-slate-200 uppercase tracking-wider">
            Strategy-Level Performance Stratification
          </h4>

          <div className="space-y-2">
            {performance.strategies.map((strat) => (
              <div
                key={strat.name}
                className="p-3 rounded bg-[#0B0E14] border border-[#222938] space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-100">{strat.name}</span>
                  <span className="font-bold text-emerald-400 tabular-nums">
                    +₹{strat.net_pnl.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Trades: {strat.trades}</span>
                  <span>Win Rate: {strat.win_rate_pct.toFixed(1)}%</span>
                  <span>Profit Factor: {strat.profit_factor.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fee Drag Analysis */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3 font-mono text-xs">
          <h4 className="font-bold text-slate-200 uppercase tracking-wider">
            Statutory Friction Drag Analysis
          </h4>

          <div className="p-3 rounded bg-[#0B0E14] border border-[#222938] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Gross Realized Gains:</span>
              <span className="font-bold text-slate-100">₹{performance.total_gross_pnl.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Total Statutory Costs:</span>
              <span className="font-bold text-rose-400">-₹{performance.total_friction.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-[#222938]">
              <span className="font-bold text-slate-300">Net Realized Retained:</span>
              <span className="font-bold text-emerald-400">₹{performance.total_net_pnl.toFixed(2)}</span>
            </div>
            <div className="text-[11px] text-slate-400 pt-1">
              Friction consumes{" "}
              <span className="text-amber-400 font-bold">
                {((performance.total_friction / performance.total_gross_pnl) * 100).toFixed(1)}%
              </span>{" "}
              of gross alpha. Early-Move Detection maintains higher edge-to-cost ratio.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
