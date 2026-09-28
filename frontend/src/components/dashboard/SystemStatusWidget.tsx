import React from "react";
import { Activity, ArrowUpRight } from "lucide-react";
import { SystemHealthData, ScreenId } from "../../types";

interface SystemStatusWidgetProps {
  health: SystemHealthData;
  onNavigate: (screen: ScreenId) => void;
}

interface PingRow {
  label: string;
  value: string;
  ok: boolean;
}

const ms = (v: number | undefined): string =>
  `${typeof v === "number" && isFinite(v) ? v : 0}ms`;

export const SystemStatusWidget: React.FC<SystemStatusWidgetProps> = ({
  health,
  onNavigate,
}) => {
  const allOk = health?.status === "HEALTHY";
  const mode = health?.mode === "LIVE" ? "LIVE" : "PAPER";

  const rows: PingRow[] = [
    { label: "Market Data", value: ms(health?.latencies?.normalizer_ms), ok: true },
    { label: "Broker (Paper)", value: ms(health?.latencies?.trade_gate_ms), ok: true },
    {
      label: "AI Models",
      value:
        health?.ollama?.loaded_models?.length && health.ollama.loaded_models.length > 0
          ? health.ollama.loaded_models.join(" & ")
          : "Qwen3 & DeepSeek-R1",
      ok: (health?.ollama?.status ?? "").toUpperCase() !== "OFFLINE",
    },
    { label: "Strategy Engine", value: ms(health?.latencies?.feature_engine_ms), ok: true },
    { label: "Risk Manager", value: ms(health?.latencies?.position_watcher_ms), ok: true },
  ];

  return (
    <section className="glass-panel rounded-xl p-4" aria-label="System status">
      <div className="flex items-center justify-between">
        <h3 className="cockpit-label">System Status</h3>
        <span
          className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-semibold ${
            allOk
              ? "border-emerald-500/35 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/35 bg-amber-500/10 text-amber-300"
          }`}
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 animate-pulse-ring" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
          </span>
          {allOk ? "All Systems Operational" : "Degraded — Review Required"}
        </span>
      </div>

      <ul className="mt-2.5 space-y-1">
        {rows.map((r) => (
          <li
            key={r.label}
            className="flex items-center justify-between rounded-md border border-sky-500/10 bg-white/[0.02] px-2.5 py-1.5"
          >
            <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <Activity
                size={11}
                className={r.ok ? "text-emerald-400" : "text-rose-400"}
                aria-hidden="true"
              />
              {r.label}
            </span>
            <span
              className={`font-mono text-[10px] font-semibold tabular-nums ${
                r.ok ? "text-slate-200" : "text-rose-300"
              }`}
            >
              {r.value}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-2.5 flex items-center justify-between border-t border-sky-500/12 pt-2 font-mono text-[9px] text-slate-600">
        <span>MODE: {mode}</span>
        <span>SQLite {health?.sqlite?.journal_mode ?? "WAL"}</span>
        <button
          type="button"
          onClick={() => onNavigate("health")}
          className="flex items-center gap-0.5 text-sky-400 transition-colors hover:text-sky-200"
        >
          Health <ArrowUpRight size={10} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
};

export default SystemStatusWidget;
