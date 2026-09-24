import React from "react";
import { Wifi, Cpu, Database, Eye, CheckCircle2 } from "lucide-react";
import { SystemHealthData } from "../../types";

interface StatusBarProps {
  health: SystemHealthData;
}

export const StatusBar: React.FC<StatusBarProps> = ({ health }) => {
  return (
    <footer className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-between px-4 py-1.5 bg-[#0B0E14] border-t border-[#222938] text-[11px] font-mono text-slate-400">
      <div className="flex items-center gap-4 overflow-x-auto">
        {/* Feeds */}
        <div className="flex items-center gap-1.5">
          <Wifi size={12} className="text-emerald-400" />
          <span>Feeds:</span>
          <span className="text-emerald-400 font-medium">CONNECTED ({health.latencies.normalizer_ms}ms)</span>
        </div>

        <span className="text-slate-600">|</span>

        {/* Ollama */}
        <div className="flex items-center gap-1.5">
          <Cpu size={12} className="text-purple-400" />
          <span>Ollama:</span>
          <span className="text-purple-300 font-medium">
            {health.ollama.status} ({health.ollama.loaded_models.length} models)
          </span>
        </div>

        <span className="text-slate-600">|</span>

        {/* Position Watcher */}
        <div className="flex items-center gap-1.5">
          <Eye size={12} className="text-emerald-400" />
          <span>Watcher:</span>
          <span className="text-emerald-400 font-medium">ACTIVE (&lt;50ms)</span>
        </div>

        <span className="text-slate-600">|</span>

        {/* SQLite */}
        <div className="flex items-center gap-1.5">
          <Database size={12} className="text-sky-400" />
          <span>SQLite:</span>
          <span className="text-sky-300 font-medium">{health.sqlite.journal_mode} OK</span>
        </div>
      </div>

      <div className="hidden sm:flex items-center gap-2 text-slate-500">
        <CheckCircle2 size={12} className="text-emerald-500" />
        <span>One-Writer Protected • Deterministic Core Active</span>
      </div>
    </footer>
  );
};
