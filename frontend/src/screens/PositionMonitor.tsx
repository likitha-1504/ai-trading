import React, { useState } from "react";
import { PositionItem } from "../types";
import { Badge } from "../components/ui/Badge";
import { FactBanner } from "../components/ui/FactBanner";
import { Eye } from "lucide-react";

interface PositionMonitorProps {
  positions: PositionItem[];
  onManualClose: (positionId: string) => Promise<void>;
}

export const PositionMonitor: React.FC<PositionMonitorProps> = ({
  positions,
  onManualClose,
}) => {
  const [closingId, setClosingId] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const handleCloseClick = async (posId: string) => {
    if (confirmingId !== posId) {
      setConfirmingId(posId);
      return;
    }
    setClosingId(posId);
    try {
      await onManualClose(posId);
    } finally {
      setClosingId(null);
      setConfirmingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Independent Position Watcher (Zero LLM Dependency)"
        subtitle="Active positions are continuously surveyed at the tick level (<50ms). Sub-tick hard stops, trailing stops, stale data exits, and 15:15 IST auto-square-off are executed deterministically without LLM delay."
      />

      {/* Positions Table */}
      <div className="rounded-lg bg-[#151A23] border border-[#222938] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0B0E14] text-slate-400 border-b border-[#222938] uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-4 font-semibold">Position ID</th>
                <th className="py-2.5 px-4 font-semibold">Symbol</th>
                <th className="py-2.5 px-4 font-semibold">Side</th>
                <th className="py-2.5 px-4 font-semibold">Qty</th>
                <th className="py-2.5 px-4 font-semibold">Entry Price</th>
                <th className="py-2.5 px-4 font-semibold">Current Price</th>
                <th className="py-2.5 px-4 font-semibold">Hard Stop</th>
                <th className="py-2.5 px-4 font-semibold">Unrealized P&L</th>
                <th className="py-2.5 px-4 font-semibold">Watcher State</th>
                <th className="py-2.5 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222938]">
              {positions.length > 0 ? (
                positions.map((pos) => {
                  const isConfirming = confirmingId === pos.position_id;
                  const isClosing = closingId === pos.position_id;

                  return (
                    <tr key={pos.position_id} className="hover:bg-[#1C2331]/60 transition-colors">
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {pos.position_id}
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-100 flex items-center gap-2">
                        {pos.symbol}
                      </td>
                      <td className="py-3 px-4">
                        <Badge state={pos.side}>{pos.side}</Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-200 tabular-nums">{pos.quantity}</td>
                      <td className="py-3 px-4 text-slate-300 tabular-nums">₹{pos.entry_price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-slate-100 font-bold tabular-nums">
                        ₹{pos.current_price.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-rose-400 tabular-nums font-semibold">
                        ₹{pos.hard_stop_price.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 tabular-nums">
                        <span
                          className={`font-bold ${
                            pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {pos.unrealized_pnl >= 0 ? "+" : ""}₹{pos.unrealized_pnl.toFixed(2)} (
                          {pos.unrealized_pnl_pct >= 0 ? "+" : ""}
                          {pos.unrealized_pnl_pct.toFixed(2)}%)
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px]">
                          <Eye size={13} />
                          SUB-50MS ACTIVE
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleCloseClick(pos.position_id)}
                          disabled={isClosing}
                          className={`px-3 py-1 rounded text-xs font-mono font-bold transition-all ${
                            isConfirming
                              ? "bg-rose-600 text-white animate-pulse"
                              : "bg-[#0B0E14] text-rose-400 border border-rose-900/50 hover:bg-rose-950"
                          }`}
                        >
                          {isClosing
                            ? "SQUARING..."
                            : isConfirming
                            ? "CLICK TO CONFIRM"
                            : "SQUARE OFF"}
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500 font-mono text-xs">
                    Zero open positions. Position Watcher idling in heartbeat loop.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
