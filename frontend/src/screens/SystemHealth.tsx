import React from "react";
import { SystemHealthData } from "../types";
import { FactBanner } from "../components/ui/FactBanner";
import { MetricCard } from "../components/ui/MetricCard";
import { Cpu, Database, Activity } from "lucide-react";

interface SystemHealthProps {
  health: SystemHealthData;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ health }) => {
  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Subsystem Diagnostics & Latency Heartbeats"
        subtitle="Independent verification of SQLite Write-Ahead Logging, local Ollama inference server, and Position Watcher sub-50ms execution loops."
      />

      {/* Primary Subsystem Status Badges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Database Status"
          value={health.database}
          subtext="PRAGMA journal_mode = WAL"
          trend="up"
          trendValue="WAL Mode"
          isFact
        />
        <MetricCard
          label="Position Watcher"
          value={health.latencies.position_watcher_ms + " ms"}
          subtext="Sub-50ms hard stop loop"
          trend="up"
          trendValue="Nominal"
          isFact
        />
        <MetricCard
          label="AI Inference Server"
          value={health.ollama.status}
          subtext={`${health.ollama.loaded_models.length} Models Loaded`}
          trend="up"
          trendValue="Standby"
          isFact
        />
        <MetricCard
          label="Execution Engine"
          value={health.execution_engine}
          subtext="Paper Broker Sim Active"
          trend="up"
          trendValue="Ready"
          isFact
        />
      </div>

      {/* Latency Pipeline Bar Chart Breakdown */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-emerald-400" />
            <h4 className="font-bold text-slate-100 uppercase tracking-wider">
              Pipeline Latency Budget Breakdown (Target &lt; 50ms)
            </h4>
          </div>
          <span className="text-emerald-400 font-bold">Total Deterministic: ~13.3ms</span>
        </div>

        <div className="space-y-3">
          {/* Normalizer */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Market Data Normalizer:</span>
              <span className="font-bold">{health.latencies.normalizer_ms} ms</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-sky-500 rounded-full"
                style={{ width: `${(health.latencies.normalizer_ms / 10) * 100}%` }}
              />
            </div>
          </div>

          {/* Feature Engine */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Feature Engine (EMA/VWAP/ATR/RVOL):</span>
              <span className="font-bold">{health.latencies.feature_engine_ms} ms</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-sky-500 rounded-full"
                style={{ width: `${(health.latencies.feature_engine_ms / 10) * 100}%` }}
              />
            </div>
          </div>

          {/* Deterministic Trade Gate */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Deterministic Trade Gate (7-step validation):</span>
              <span className="font-bold">{health.latencies.trade_gate_ms} ms</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{ width: `${(health.latencies.trade_gate_ms / 10) * 100}%` }}
              />
            </div>
          </div>

          {/* Position Watcher Tick Sweep */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Position Watcher Tick Sweep (Autonomous Loop):</span>
              <span className="font-bold text-emerald-400">
                {health.latencies.position_watcher_ms} ms
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-400 rounded-full"
                style={{ width: `${(health.latencies.position_watcher_ms / 5) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Local Infrastructure: SQLite & Ollama Specs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        {/* SQLite */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2">
          <div className="flex items-center gap-2 pb-2 border-b border-[#222938]">
            <Database size={16} className="text-sky-400" />
            <h4 className="font-bold text-slate-100 uppercase tracking-wider">
              SQLite WAL Persistence
            </h4>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">Journal Mode:</span>
            <span className="font-bold text-emerald-400">{health.sqlite.journal_mode}</span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">WAL File Size:</span>
            <span className="font-bold text-slate-200">{health.sqlite.wal_size_kb} KB</span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">Connection Pool:</span>
            <span className="font-bold text-slate-200">{health.sqlite.connection_pool}</span>
          </div>
        </div>

        {/* Ollama */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-2">
          <div className="flex items-center gap-2 pb-2 border-b border-[#222938]">
            <Cpu size={16} className="text-purple-400" />
            <h4 className="font-bold text-slate-100 uppercase tracking-wider">
              Local Ollama Inference Engine
            </h4>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">Server Status:</span>
            <span className="font-bold text-emerald-400">{health.ollama.status}</span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">VRAM Allocation:</span>
            <span className="font-bold text-slate-200">{health.ollama.vram_used_mb} MB</span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span className="text-slate-400">Active Models:</span>
            <span className="font-bold text-purple-300">
              {health.ollama.loaded_models.join(", ")}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
