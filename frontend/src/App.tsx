import React from "react";

export function App() {
  return (
    <div className="min-h-screen bg-[#0B0E14] text-[#F1F5F9] p-6">
      <header className="flex items-center justify-between border-b border-[#222938] pb-4 mb-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight">AI Micro-Trading Terminal</h1>
          <p className="text-xs text-slate-400">Deterministic Safety Core • Dual-LLM Council</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs px-2.5 py-1 rounded bg-sky-950/60 text-sky-400 border border-sky-800/80 font-mono">
            [SYSTEM FACT] Capital: ₹100.00
          </span>
          <span className="text-xs px-2.5 py-1 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/80 font-mono">
            Paper Mode Active
          </span>
        </div>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <section className="p-4 rounded-lg bg-[#151A23] border border-[#222938]">
          <h2 className="text-sm font-semibold text-slate-200 mb-2">Command Center</h2>
          <p className="text-xs text-slate-400">Phase 00 Control Plane Initialized.</p>
        </section>

        <section className="p-4 rounded-lg bg-[#151A23] border border-[#222938]">
          <h2 className="text-sm font-semibold text-slate-200 mb-2">Position Monitor</h2>
          <p className="text-xs text-slate-400">Zero active positions. Position Watcher idling.</p>
        </section>

        <section className="p-4 rounded-lg bg-[#151A23] border border-purple-900/40 border-dashed">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-purple-300">AI Reasoning Council</h2>
            <span className="text-[10px] text-purple-400 bg-purple-950/80 px-2 py-0.5 rounded">
              Qualitative Layer
            </span>
          </div>
          <p className="text-xs text-slate-400 italic">
            Qwen3 Analyst & DeepSeek-R1 Challenger standby.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
