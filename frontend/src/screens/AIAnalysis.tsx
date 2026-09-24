import React from "react";
import { AIAnalysisRecord } from "../types";
import { FactBanner } from "../components/ui/FactBanner";

interface AIAnalysisProps {
  analysis: AIAnalysisRecord;
}

export const AIAnalysis: React.FC<AIAnalysisProps> = ({ analysis }) => {
  const { qwen3_thesis, deepseek_r1_critique, council_resolution } = analysis;

  return (
    <div className="space-y-4">
      {/* Disclaimer Top Banner */}
      <FactBanner
        type="FINAL_DETERMINISTIC_GATE"
        title={`AI Council Synthesis: ${analysis.symbol} (${analysis.candidate_id})`}
        subtitle="Dual-model qualitative stress test. Models provide probabilistic reasoning; the Deterministic Trade Gate holds exclusive execution and sizing authority."
      >
        <div className="flex flex-wrap items-center gap-3 mt-2 pt-2 border-t border-emerald-900/40 text-xs font-mono">
          <span className="text-slate-400">Final Gate Verdict:</span>
          <span
            className={`font-bold px-2 py-0.5 rounded ${
              council_resolution.final_verdict === "APPROVED"
                ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                : "bg-rose-950 text-rose-300 border border-rose-700"
            }`}
          >
            {council_resolution.final_verdict}
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Effective Confidence:</span>
          <span className="text-slate-200 font-bold">
            {(council_resolution.effective_confidence * 100).toFixed(0)}%
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Decision Authority:</span>
          <span className="text-emerald-400 font-semibold">ZERO LLM ORDER AUTHORITY</span>
        </div>
      </FactBanner>

      {/* Dual Column AI Council Debate View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Qwen3 Primary Analyst */}
        <FactBanner
          type="QWEN3_ANALYSIS"
          title={`Qwen3 Primary Analyst (${qwen3_thesis.model_name})`}
          subtitle={`Latency: ${qwen3_thesis.latency_ms}ms • Confidence: ${(qwen3_thesis.confidence_score * 100).toFixed(0)}%`}
        >
          <div className="space-y-3 mt-3 text-xs font-mono">
            {/* Thesis Summary */}
            <div className="p-2.5 rounded bg-[#0B0E14] border border-purple-900/40">
              <span className="text-[10px] text-purple-400 uppercase font-bold">Thesis Hypothesis</span>
              <p className="text-slate-200 mt-1 italic leading-relaxed">{qwen3_thesis.thesis_summary}</p>
            </div>

            {/* Catalyst */}
            {qwen3_thesis.catalyst_identified && (
              <div className="p-2.5 rounded bg-[#0B0E14] border border-purple-900/40">
                <span className="text-[10px] text-purple-400 uppercase font-bold">Identified Catalyst</span>
                <p className="text-slate-300 mt-1">{qwen3_thesis.catalyst_identified}</p>
              </div>
            )}

            {/* Bullish Evidence */}
            <div>
              <span className="text-[10px] text-emerald-400 uppercase font-bold">Bullish Evidence (Qwen3)</span>
              <ul className="mt-1 space-y-1 list-disc list-inside text-slate-300">
                {qwen3_thesis.bullish_evidence.map((ev, i) => (
                  <li key={i}>{ev}</li>
                ))}
              </ul>
            </div>

            {/* Invalidation Conditions */}
            <div>
              <span className="text-[10px] text-rose-400 uppercase font-bold">Invalidation Triggers</span>
              <ul className="mt-1 space-y-1 list-disc list-inside text-rose-300/90">
                {qwen3_thesis.invalidation_conditions.map((inv, i) => (
                  <li key={i}>{inv}</li>
                ))}
              </ul>
            </div>
          </div>
        </FactBanner>

        {/* Right Column: DeepSeek-R1 Adversarial Challenger */}
        <FactBanner
          type="DEEPSEEK_R1_CHALLENGE"
          title={`DeepSeek-R1 Challenger (${deepseek_r1_critique.model_name})`}
          subtitle={`Latency: ${deepseek_r1_critique.latency_ms}ms • Risk Severity: ${deepseek_r1_critique.risk_severity}`}
        >
          <div className="space-y-3 mt-3 text-xs font-mono">
            {/* Critique Summary */}
            <div className="p-2.5 rounded bg-[#0B0E14] border border-indigo-900/40">
              <span className="text-[10px] text-indigo-400 uppercase font-bold">Adversarial Counter-Thesis</span>
              <p className="text-slate-200 mt-1 italic leading-relaxed">{deepseek_r1_critique.critique_summary}</p>
            </div>

            {/* Recommendation & Confidence Multiplier */}
            <div className="flex items-center justify-between p-2.5 rounded bg-[#0B0E14] border border-indigo-900/40">
              <div>
                <span className="text-[10px] text-indigo-400 uppercase font-bold">Challenger Stance</span>
                <p className="text-slate-200 font-bold mt-0.5">{deepseek_r1_critique.recommendation}</p>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-indigo-400 uppercase font-bold">Confidence Multiplier</span>
                <p className="text-slate-200 font-bold mt-0.5">{deepseek_r1_critique.adjusted_confidence_multiplier}x</p>
              </div>
            </div>

            {/* Blind Spots Identified */}
            <div>
              <span className="text-[10px] text-amber-400 uppercase font-bold">Blind Spots & Traps</span>
              <ul className="mt-1 space-y-1 list-disc list-inside text-amber-200/90">
                {deepseek_r1_critique.blind_spots_identified.map((bs, i) => (
                  <li key={i}>{bs}</li>
                ))}
              </ul>
            </div>

            {/* Downside Scenarios */}
            <div>
              <span className="text-[10px] text-rose-400 uppercase font-bold">Downside Failure Scenarios</span>
              <ul className="mt-1 space-y-1 list-disc list-inside text-rose-300/90">
                {deepseek_r1_critique.downside_scenarios.map((ds, i) => (
                  <li key={i}>{ds}</li>
                ))}
              </ul>
            </div>
          </div>
        </FactBanner>
      </div>

      {/* Synthesis Reasoning Summary */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2">
        <h4 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
          Council Arbitration & Synthesis Rationale
        </h4>
        <p className="text-xs font-mono text-slate-300 leading-relaxed bg-[#0B0E14] p-3 rounded border border-[#222938]">
          {council_resolution.reasoning}
        </p>
      </div>
    </div>
  );
};
