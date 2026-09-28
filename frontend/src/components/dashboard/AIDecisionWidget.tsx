import React from "react";
import { Rocket, ShieldAlert } from "lucide-react";
import { AIAnalysisRecord, CandidateItem, PositionItem } from "../../types";

interface AIDecisionWidgetProps {
  analysis: AIAnalysisRecord;
  candidate?: CandidateItem;
  position?: PositionItem;
  onNavigateToOrders?: () => void;
}

interface ParamRow {
  label: string;
  value: string;
  tone?: "default" | "bullish" | "bearish";
}

/**
 * Execution parameters derived from deterministic engine facts.
 * The "Execute Trade" action is an explicit operator hand-off to the Orders
 * station — it never places an order by itself.
 */
export const AIDecisionWidget: React.FC<AIDecisionWidgetProps> = ({
  analysis,
  candidate,
  position,
  onNavigateToOrders,
}) => {
  const verdict = analysis.council_resolution?.final_verdict ?? "VETOED";
  const isBuy = verdict === "APPROVED" || verdict === "DOWNSIZED";

  const entry = candidate?.trigger_price ?? position?.entry_price ?? 0;
  const stop = candidate?.hard_stop_price ?? position?.hard_stop_price ?? entry * 0.985;
  const target1 = candidate?.take_profit_price ?? entry * 1.012;
  const target2 = target1 * 1.012;
  const notional = entry > 0 ? Math.max(1, Math.round(300 / entry)) : 0;

  const reason =
    analysis.council_resolution?.reasoning ||
    analysis.qwen3_thesis?.thesis_summary ||
    "Awaiting deterministic trade gate verdict.";

  const rows: ParamRow[] = [
    { label: "Entry Zone", value: entry > 0 ? `₹${entry.toFixed(2)}` : "—", tone: "default" },
    { label: "Target 1", value: `₹${target1.toFixed(2)}`, tone: "bullish" },
    { label: "Target 2", value: `₹${target2.toFixed(2)}`, tone: "bullish" },
    { label: "Stop Loss", value: `₹${stop.toFixed(2)}`, tone: "bearish" },
    { label: "Position Size", value: `${notional} qty`, tone: "default" },
    { label: "Strategy", value: candidate?.strategy_type === "EARLY_MOVE_DETECTION" ? "EARLY-MOVE" : "MOMENTUM", tone: "default" },
  ];

  return (
    <section className="glass-panel rounded-xl p-4" aria-label="AI trade decision">
      <div className="flex items-center gap-2">
        <span
          className={`flex h-full items-center rounded-lg px-3 py-2 font-display text-xl font-extrabold tracking-[0.16em] ${
            isBuy
              ? "bg-emerald-500/18 text-emerald-300 shadow-glow-emerald"
              : "bg-rose-500/18 text-rose-300 shadow-glow-crimson"
          }`}
        >
          {isBuy ? "BUY" : "SELL"}
        </span>
        <div className="min-w-0">
          <p className="font-mono text-sm font-bold text-slate-100">
            {analysis.symbol}
          </p>
          <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-slate-500">
            {verdict} · GATE{" "}
            {analysis.council_resolution?.deterministic_gate_passed ? "PASSED" : "BLOCKED"}
          </p>
        </div>
      </div>

      <dl className="mt-3 space-y-1.5">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex items-center justify-between rounded-md border border-sky-500/10 bg-white/[0.02] px-2.5 py-1.5"
          >
            <dt className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
              {r.label}
            </dt>
            <dd
              className={`font-mono text-[11px] font-semibold tabular-nums ${
                r.tone === "bullish"
                  ? "text-emerald-300"
                  : r.tone === "bearish"
                    ? "text-rose-300"
                    : "text-slate-200"
              }`}
            >
              {r.value}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-3 rounded-md border border-sky-500/12 bg-sky-500/5 p-2.5">
        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-sky-400">
          Reason
        </p>
        <p className="mt-1 line-clamp-4 text-[10px] leading-relaxed text-slate-400">{reason}</p>
      </div>

      <button
        type="button"
        onClick={onNavigateToOrders}
        disabled={!isBuy}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 via-sky-500 to-violet-500 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-space-void shadow-glow-blue transition-all hover:shadow-glow-cyan active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Rocket size={14} aria-hidden="true" />
        Execute Trade
      </button>

      <p className="mt-2 flex items-start gap-1.5 text-[9px] leading-relaxed text-slate-600">
        <ShieldAlert size={11} className="mt-px shrink-0" aria-hidden="true" />
        Deterministic Trade Gate owns execution authority. This action routes to the Orders
        station for operator confirmation.
      </p>
    </section>
  );
};

export default AIDecisionWidget;
