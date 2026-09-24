import React, { useState } from "react";
import { TradeRecordItem } from "../types";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";


interface TradeJournalProps {
  trades: TradeRecordItem[];
}

export const TradeJournal: React.FC<TradeJournalProps> = ({ trades }) => {
  const [selectedTrade, setSelectedTrade] = useState<TradeRecordItem | null>(trades[0] || null);

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Immutable Trade Journal & Statutory Cost Breakdown"
        subtitle="Every executed trade lifecycle is permanently logged with Indian statutory friction: STT, Exchange Turnover, SEBI Charges, Stamp Duty, and GST."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Trades List */}
        <div className="lg:col-span-1 rounded-lg bg-[#151A23] border border-[#222938] p-3 space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-[#222938] text-xs font-mono text-slate-300 font-bold">
            <span>EXECUTED TRADES ({trades.length})</span>
            <span>SORT: LATEST</span>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {trades.map((t) => {
              const isSelected = selectedTrade?.trade_id === t.trade_id;
              const isProfit = t.net_pnl >= 0;

              return (
                <div
                  key={t.trade_id}
                  onClick={() => setSelectedTrade(t)}
                  className={`p-3 rounded-lg cursor-pointer transition-all border font-mono text-xs ${
                    isSelected
                      ? "bg-[#1C2331] border-sky-600 shadow-sm"
                      : "bg-[#0B0E14] border-[#222938] hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-100">{t.symbol}</span>
                    <span
                      className={`font-bold tabular-nums ${
                        isProfit ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {isProfit ? "+" : ""}₹{t.net_pnl.toFixed(2)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                    <span>{t.strategy}</span>
                    <Badge state={t.exit_trigger}>{t.exit_trigger}</Badge>
                  </div>

                  <div className="text-[10px] text-slate-500 mt-1">
                    {new Date(t.entry_timestamp).toLocaleDateString()} • {new Date(t.entry_timestamp).toLocaleTimeString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Detailed Retrospective View */}
        <div className="lg:col-span-2 rounded-lg bg-[#151A23] border border-[#222938] p-4 space-y-4">
          {selectedTrade ? (
            <div className="space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between pb-3 border-b border-[#222938]">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-100">{selectedTrade.symbol}</h3>
                    <Badge state={selectedTrade.side}>{selectedTrade.side}</Badge>
                    <span className="text-slate-400">Trade ID: {selectedTrade.trade_id}</span>
                  </div>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Plan ID: {selectedTrade.plan_id} • Strategy: {selectedTrade.strategy}
                  </p>
                </div>

                <div className="text-right">
                  <span
                    className={`text-lg font-bold tabular-nums ${
                      selectedTrade.net_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {selectedTrade.net_pnl >= 0 ? "+" : ""}₹{selectedTrade.net_pnl.toFixed(2)}
                  </span>
                  <p className="text-[10px] text-slate-500">Net Realized P&L</p>
                </div>
              </div>

              {/* Execution Details Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 p-3 rounded bg-[#0B0E14] border border-[#222938]">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Entry Price</span>
                  <p className="font-bold text-slate-100 tabular-nums">₹{selectedTrade.entry_price.toFixed(2)}</p>
                  <span className="text-[10px] text-slate-500">
                    {new Date(selectedTrade.entry_timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Exit Price</span>
                  <p className="font-bold text-slate-100 tabular-nums">₹{selectedTrade.exit_price.toFixed(2)}</p>
                  <span className="text-[10px] text-slate-500">
                    {new Date(selectedTrade.exit_timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Duration</span>
                  <p className="font-bold text-slate-200">
                    {Math.round(selectedTrade.holding_duration_seconds / 60)} mins
                  </p>
                  <span className="text-[10px] text-slate-500">
                    ({selectedTrade.holding_duration_seconds}s)
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Exit Reason</span>
                  <p className="font-bold text-amber-300">{selectedTrade.exit_trigger}</p>
                  <span className="text-[10px] text-slate-500">Deterministic</span>
                </div>
              </div>

              {/* Indian Statutory Cost Breakdown Table */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                  Indian Statutory Friction Breakdown (P&L Drag)
                </span>
                <div className="grid grid-cols-3 md:grid-cols-6 gap-2 p-2.5 rounded bg-[#0B0E14] border border-[#222938] text-[11px]">
                  <div>
                    <span className="text-slate-500">Brokerage</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.brokerage.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">STT</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.stt.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">Exch Charges</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.exchange_charges.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">SEBI Charges</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.sebi_charges.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">Stamp Duty</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.stamp_duty.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">GST (18%)</span>
                    <p className="text-slate-200 font-bold">₹{selectedTrade.gst.toFixed(2)}</p>
                  </div>
                </div>

                <div className="flex justify-between p-2 rounded bg-sky-950/30 border border-sky-800/40 text-xs">
                  <span className="text-slate-300">
                    Gross P&L: <span className="font-bold">₹{selectedTrade.gross_pnl.toFixed(2)}</span>
                  </span>
                  <span className="text-rose-300">
                    Total Statutory Friction: <span className="font-bold">-₹{selectedTrade.total_friction.toFixed(2)}</span>
                  </span>
                  <span className="text-emerald-300 font-bold">
                    Net P&L: ₹{selectedTrade.net_pnl.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 font-mono text-xs">
              Select a trade from the journal list to view retrospective audit details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
