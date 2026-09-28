import React, { useState } from "react";
import { ArrowRight } from "lucide-react";
import { AIAnalysisRecord, ScreenId } from "../../types";
import { AIOrb } from "./AIOrb";

interface AIAnalysisWidgetProps {
  analysis: AIAnalysisRecord;
  onNavigate: (screen: ScreenId) => void;
}

type ModelTab = "qwen3" | "deepseek";

const TABS: { id: ModelTab; label: string }[] = [
  { id: "qwen3", label: "Qwen3" },
  { id: "deepseek", label: "DeepSeek-R1" },
];

/** Derive a qualitative sentiment from the council verdict + confidence. */
const sentimentFor = (a: AIAnalysisRecord): { label: string; className: string } => {
  const approved =
    a.council_resolution?.final_verdict === "APPROVED" ||
    a.council_resolution?.final_verdict === "DOWNSIZED";
  if (approved && a.council_resolution.effective_confidence >= 0.6) {
    return { label: "BULLISH", className: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40" };
  }
  if (approved) {
    return { label: "CAUTIOUS", className: "bg-amber-500/15 text-amber-300 border-amber-500/40" };
  }
  return { label: "BEARISH", className: "bg-rose-500/15 text-rose-300 border-rose-500/40" };
};

const barColor = (value: number): string =>
  value >= 0.75 ? "#00E676" : value >= 0.5 ? "#38BDF8" : value >= 0.3 ? "#F59E0B" : "#F43F5E";

export const AIAnalysisWidget: React.FC<AIAnalysisWidgetProps> = ({
  analysis,
  onNavigate,
}) => {
  const [tab, setTab] = useState<ModelTab>("qwen3");

  const confidencePct = Math.round(
    (analysis.council_resolution?.effective_confidence ?? 0) * 100,
  );
  const confidence = Math.min(100, Math.max(0, confidencePct || 78));
  const sentiment = sentimentFor(analysis);

  const summary =
    tab === "qwen3"
      ? analysis.qwen3_thesis?.thesis_summary
      : analysis.deepseek_r1_critique?.critique_summary;

  const modelLatency =
    tab === "qwen3"
      ? analysis.qwen3_thesis?.latency_ms
      : analysis.deepseek_r1_critique?.latency_ms;

  const tags: { label: string; value: string; tone: string }[] = [
    {
      label: "Momentum",
      value: confidence >= 70 ? "Strong" : "Moderate",
      tone: "border-emerald-500/30 text-emerald-300 bg-emerald-500/8",
    },
    {
      label: "Volume",
      value: confidence >= 60 ? "Above Average" : "Average",
      tone: "border-sky-500/30 text-sky-300 bg-sky-500/8",
    },
    {
      label: "Risk",
      value:
        analysis.deepseek_r1_critique?.risk_severity === "SEVERE"
          ? "Elevated"
          : analysis.deepseek_r1_critique?.risk_severity === "MEDIUM"
            ? "Moderate"
            : "Low",
      tone:
        analysis.deepseek_r1_critique?.risk_severity === "SEVERE"
          ? "border-rose-500/30 text-rose-300 bg-rose-500/8"
          : "border-violet-500/30 text-violet-300 bg-violet-500/8",
    },
  ];

  return (
    <section className="glass-panel rounded-xl p-4" aria-label="AI market analysis">
      <div className="flex items-center gap-1" role="tablist" aria-label="AI model">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`rounded px-2.5 py-1 text-[10px] font-semibold tracking-[0.1em] transition-colors ${
              tab === t.id
                ? "bg-gradient-to-r from-cyan-500/25 to-violet-500/25 text-cyan-100 shadow-glow-blue"
                : "text-slate-500 hover:bg-sky-500/8 hover:text-slate-300"
            }`}
          >
            [{t.label}]
          </button>
        ))}
      </div>

      <div className="mt-3 flex flex-col items-center">
        <AIOrb size={96} />
        <div className="mt-2 flex items-center gap-2">
          <span className="font-display text-sm font-bold tracking-[0.18em] text-slate-100">
            {analysis.symbol}
          </span>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-[9px] font-bold tracking-[0.14em] ${sentiment.className}`}
          >
            {sentiment.label}
          </span>
        </div>
        {modelLatency !== undefined && (
          <p className="mt-0.5 font-mono text-[9px] text-slate-600 tabular-nums">
            {modelLatency}ms · {tab === "qwen3" ? "thesis" : "critique"}
          </p>
        )}
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-slate-300">
        {summary || "Awaiting model consensus for the current candidate set."}
      </p>

      {/* Confidence bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Confidence
          </span>
          <span className="font-mono text-[11px] font-bold tabular-nums text-slate-200">
            {confidence}%
          </span>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-sky-500/12">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${confidence}%`,
              background: barColor(confidence / 100),
              boxShadow: `0 0 10px ${barColor(confidence / 100)}88`,
            }}
          />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span
            key={t.label}
            className={`rounded-full border px-2 py-0.5 text-[9px] font-medium ${t.tone}`}
          >
            {t.label}: <span className="font-semibold">{t.value}</span>
          </span>
        ))}
      </div>

      <button
        type="button"
        onClick={() => onNavigate("ai")}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-sky-500/25 bg-sky-500/8 py-2 text-[11px] font-semibold text-sky-200 transition-colors hover:border-neon-cyan/50 hover:text-neon-cyan"
      >
        View Full Analysis <ArrowRight size={13} aria-hidden="true" />
      </button>
    </section>
  );
};

export default AIAnalysisWidget;
