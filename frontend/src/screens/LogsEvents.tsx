import React, { useState } from "react";
import { LogEntry } from "../types";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";
import { Download, Search } from "lucide-react";

interface LogsEventsProps {
  logs: LogEntry[];
}

export const LogsEvents: React.FC<LogsEventsProps> = ({ logs }) => {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedLevel, setSelectedLevel] = useState<string>("ALL");

  const filtered = logs.filter((log) => {
    const matchesSearch =
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.source.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLevel = selectedLevel === "ALL" || log.level === selectedLevel;
    return matchesSearch && matchesLevel;
  });

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(logs, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `trading_system_logs_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Structured Telemetry & System Event Stream"
        subtitle="Chronological audit records emitted by system components. Stored synchronously into SQLite with WAL durability."
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-[#151A23] border border-[#222938] font-mono text-xs">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search logs or source..."
              className="pl-8 pr-3 py-1.5 rounded bg-[#0B0E14] border border-[#222938] text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 text-xs w-64"
            />
          </div>

          <div className="flex items-center gap-1 border-l border-[#222938] pl-3">
            {["ALL", "INFO", "WARN", "ERROR", "CRITICAL"].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setSelectedLevel(lvl)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  selectedLevel === lvl
                    ? "bg-[#1C2331] text-sky-400 font-bold border border-sky-800"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleExportJSON}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1C2331] hover:bg-[#252f42] text-slate-200 border border-[#222938] font-bold transition-colors"
        >
          <Download size={13} />
          Export JSON
        </button>
      </div>

      {/* Logs Stream Table */}
      <div className="rounded-lg bg-[#151A23] border border-[#222938] overflow-hidden font-mono text-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#0B0E14] text-slate-400 border-b border-[#222938] uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                <th className="py-2.5 px-4 font-semibold">Level</th>
                <th className="py-2.5 px-4 font-semibold">Source</th>
                <th className="py-2.5 px-4 font-semibold">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222938] text-[11px]">
              {filtered.map((log) => (
                <tr key={log.id} className="hover:bg-[#1C2331]/60">
                  <td className="py-2.5 px-4 text-slate-400 tabular-nums">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="py-2.5 px-4">
                    <Badge
                      state={
                        log.level === "INFO"
                          ? "HOLD"
                          : log.level === "WARN"
                          ? "RISK"
                          : log.level === "ERROR"
                          ? "ERROR"
                          : "REJECTED"
                      }
                    >
                      {log.level}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-4 text-sky-400 font-semibold">{log.source}</td>
                  <td className="py-2.5 px-4 text-slate-200">{log.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
