import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  isFact?: boolean;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  trend,
  trendValue,
  isFact = false,
  className = "",
}) => {
  const getTrendColor = (): string => {
    if (trend === "up") return "text-emerald-400";
    if (trend === "down") return "text-rose-400";
    return "text-slate-400";
  };

  return (
    <div
      className={`p-3.5 rounded-lg bg-[#151A23] border ${
        isFact ? "border-sky-800/40" : "border-[#222938]"
      } hover:border-slate-600 transition-colors ${className}`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        {isFact && (
          <span className="text-[9px] px-1.5 py-0.2 rounded bg-sky-950/80 text-sky-400 border border-sky-800/70 font-mono">
            FACT
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold font-mono text-slate-100 tracking-tight tabular-nums">
          {value}
        </span>
        {trendValue && (
          <span className={`text-xs font-mono font-medium ${getTrendColor()}`}>
            {trend === "up" ? "▲" : trend === "down" ? "▼" : "•"} {trendValue}
          </span>
        )}
      </div>

      {subtext && <p className="text-[11px] text-slate-500 font-mono mt-1">{subtext}</p>}
    </div>
  );
};
