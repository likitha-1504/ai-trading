import React from "react";

export type BannerType = "SYSTEM_FACT" | "QWEN3_ANALYSIS" | "DEEPSEEK_R1_CHALLENGE" | "FINAL_DETERMINISTIC_GATE";

interface FactBannerProps {
  type: BannerType;
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;
  className?: string;
}

export const FactBanner: React.FC<FactBannerProps> = ({
  type,
  title,
  subtitle,
  children,
  className = "",
}) => {
  switch (type) {
    case "SYSTEM_FACT":
      return (
        <div
          className={`p-3.5 rounded-lg bg-[#151A23] border border-[#0369A1]/60 shadow-[0_0_15px_rgba(2,132,199,0.05)] ${className}`}
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-sky-950/80 text-sky-400 border border-sky-700/80 text-[10px] font-mono font-bold tracking-wider">
                [SYSTEM FACT]
              </span>
              {title && <span className="text-xs font-semibold text-slate-100">{title}</span>}
            </div>
            <span className="text-[10px] text-sky-500/80 font-mono">Verified Deterministic Truth</span>
          </div>
          {subtitle && <p className="text-xs text-slate-300 font-mono mb-2">{subtitle}</p>}
          {children}
        </div>
      );

    case "QWEN3_ANALYSIS":
      return (
        <div
          className={`p-3.5 rounded-lg bg-[#151A23] border-1.5 border-dashed border-[#6D28D9]/70 bg-gradient-to-b from-purple-950/10 to-transparent ${className}`}
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-600/60 text-[10px] font-mono font-bold tracking-wider">
                [QWEN3 ANALYSIS]
              </span>
              {title && <span className="text-xs font-semibold text-purple-200">{title}</span>}
            </div>
            <span className="text-[10px] text-purple-400/80 font-mono italic">Probabilistic LLM</span>
          </div>
          {subtitle && <p className="text-xs text-slate-300 font-sans italic mb-2">{subtitle}</p>}
          {children}
          <div className="mt-2.5 pt-2 border-t border-purple-900/40 flex items-center justify-between">
            <span className="text-[10px] text-purple-400/70 italic">
              ⚠️ Probabilistic LLM speculation. Never guarantees market trajectory.
            </span>
          </div>
        </div>
      );

    case "DEEPSEEK_R1_CHALLENGE":
      return (
        <div
          className={`p-3.5 rounded-lg bg-[#151A23] border-1.5 border-dashed border-indigo-500/60 bg-gradient-to-b from-indigo-950/15 to-transparent ${className}`}
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-600/60 text-[10px] font-mono font-bold tracking-wider">
                [DEEPSEEK-R1 CHALLENGE]
              </span>
              {title && <span className="text-xs font-semibold text-indigo-200">{title}</span>}
            </div>
            <span className="text-[10px] text-indigo-400/80 font-mono italic">Adversarial Stress Test</span>
          </div>
          {subtitle && <p className="text-xs text-slate-300 font-sans italic mb-2">{subtitle}</p>}
          {children}
          <div className="mt-2.5 pt-2 border-t border-indigo-900/40 flex items-center justify-between">
            <span className="text-[10px] text-indigo-400/70 italic">
              🛡️ Adversarial critique searching for structural flaws and downside traps.
            </span>
          </div>
        </div>
      );

    case "FINAL_DETERMINISTIC_GATE":
      return (
        <div
          className={`p-3.5 rounded-lg bg-[#151A23] border-2 border-emerald-600/70 shadow-[0_0_20px_rgba(16,185,129,0.06)] ${className}`}
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/80 text-[10px] font-mono font-bold tracking-wider">
                [FINAL DETERMINISTIC GATE]
              </span>
              {title && <span className="text-xs font-semibold text-emerald-200">{title}</span>}
            </div>
            <span className="text-[10px] text-emerald-400 font-mono font-semibold">Zero LLM Order Authority</span>
          </div>
          {subtitle && <p className="text-xs text-slate-200 font-mono mb-2">{subtitle}</p>}
          {children}
        </div>
      );
  }
};
