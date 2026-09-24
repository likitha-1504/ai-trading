import React from "react";
import { CandidateItem } from "../types";
import { Badge } from "../components/ui/Badge";
import { FactBanner } from "../components/ui/FactBanner";
import { ArrowRight, Cpu } from "lucide-react";

interface CandidateFeedProps {
  candidates: CandidateItem[];
  onInspectAI: (candidateId: string) => void;
}

export const CandidateFeed: React.FC<CandidateFeedProps> = ({
  candidates,
  onInspectAI,
}) => {
  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Deterministic Strategy Candidate Pipeline"
        subtitle="Candidates are strictly emitted by algorithmic rules (Momentum Continuation & Early-Move Detection). AI models cannot autonomously create candidates."
      />

      {/* Pipeline Status Stages Bar */}
      <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono">
        <div className="p-2 rounded bg-[#151A23] border border-[#222938]">
          <span className="text-[10px] text-slate-500 uppercase">Stage 1</span>
          <p className="font-bold text-slate-200">1. Algorithmic Detect</p>
        </div>
        <div className="p-2 rounded bg-[#151A23] border border-purple-900/40">
          <span className="text-[10px] text-purple-400 uppercase">Stage 2</span>
          <p className="font-bold text-purple-300">2. AI Council Review</p>
        </div>
        <div className="p-2 rounded bg-[#151A23] border border-sky-900/40">
          <span className="text-[10px] text-sky-400 uppercase">Stage 3</span>
          <p className="font-bold text-sky-300">3. Risk & Cost Gate</p>
        </div>
        <div className="p-2 rounded bg-[#151A23] border border-emerald-900/40">
          <span className="text-[10px] text-emerald-400 uppercase">Stage 4</span>
          <p className="font-bold text-emerald-300">4. Watcher Handoff</p>
        </div>
      </div>

      {/* Candidates List Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {candidates.map((c) => (
          <div
            key={c.candidate_id}
            className={`p-4 rounded-lg bg-[#151A23] border ${
              c.status === "PROMOTED"
                ? "border-emerald-600/60 shadow-[0_0_15px_rgba(16,185,129,0.06)]"
                : c.status === "IN_AI_REVIEW"
                ? "border-purple-600/50"
                : c.status === "REJECTED"
                ? "border-rose-900/40 opacity-70"
                : "border-[#222938]"
            } space-y-3`}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold font-mono text-slate-100">{c.symbol}</span>
                <Badge
                  state={
                    c.strategy_type === "MOMENTUM_CONTINUATION" ? "BUY" : "WATCH"
                  }
                >
                  {c.strategy_type === "MOMENTUM_CONTINUATION" ? "MOMENTUM" : "EARLY-MOVE"}
                </Badge>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-slate-400">
                  Rank: <span className="font-bold text-slate-200">{c.rank_score.toFixed(1)}</span>
                </span>
                <Badge
                  state={
                    c.status === "PROMOTED"
                      ? "FILLED"
                      : c.status === "IN_AI_REVIEW"
                      ? "AI THINKING"
                      : c.status === "REJECTED"
                      ? "REJECTED"
                      : "PENDING"
                  }
                >
                  {c.status}
                </Badge>
              </div>
            </div>

            {/* Price Targets and Edges */}
            <div className="grid grid-cols-3 gap-2 p-2 rounded bg-[#0B0E14] border border-[#222938] text-xs font-mono">
              <div>
                <span className="text-[10px] text-slate-500 uppercase">Trigger</span>
                <p className="font-bold text-slate-100 tabular-nums">₹{c.trigger_price.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-[10px] text-rose-400 uppercase">Hard Stop</span>
                <p className="font-bold text-rose-400 tabular-nums">₹{c.hard_stop_price.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-[10px] text-emerald-400 uppercase">Target</span>
                <p className="font-bold text-emerald-400 tabular-nums">₹{c.take_profit_price.toFixed(2)}</p>
              </div>
            </div>

            {/* Friction & Net Edge Calculation */}
            <div className="flex items-center justify-between text-xs font-mono pt-1 text-slate-400">
              <span>
                Friction: <span className="text-slate-300">~{c.friction_estimate.toFixed(2)}%</span>
              </span>
              <span>
                Gross Edge: <span className="text-slate-200">{c.expected_gross_edge.toFixed(2)}%</span>
              </span>
              <span className="font-bold text-emerald-400">
                Net Edge: +{c.expected_net_edge.toFixed(2)}%
              </span>
            </div>

            {/* Footer with AI Inspection Button */}
            <div className="flex items-center justify-between pt-2 border-t border-[#222938] text-[11px] font-mono">
              <span className="text-slate-500">
                Detected: {new Date(c.detected_at).toLocaleTimeString()}
              </span>

              <button
                onClick={() => onInspectAI(c.candidate_id)}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-[#1C2331] hover:bg-purple-950/80 text-purple-300 border border-purple-800/60 hover:border-purple-600 text-xs font-mono font-medium transition-colors"
              >
                <Cpu size={13} className="text-purple-400" />
                Inspect AI Council <ArrowRight size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
