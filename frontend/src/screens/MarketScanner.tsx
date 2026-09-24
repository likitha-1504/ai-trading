import React, { useState } from "react";
import { MarketScannerItem } from "../types";
import { Badge } from "../components/ui/Badge";
import { FactBanner } from "../components/ui/FactBanner";
import { Radar, Filter, BarChart3, ArrowUpDown } from "lucide-react";

interface MarketScannerProps {
  scannerData: MarketScannerItem[];
  onSelectSymbol: (symbol: string) => void;
}

export const MarketScanner: React.FC<MarketScannerProps> = ({
  scannerData,
  onSelectSymbol,
}) => {
  const [universe, setUniverse] = useState<string>("NIFTY_50");
  const [filterActiveOnly, setFilterActiveOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<keyof MarketScannerItem>("rvol_10");
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const filtered = scannerData
    .filter((item) => (filterActiveOnly ? item.status === "ACTIVE" : true))
    .sort((a, b) => {
      const valA = a[sortBy];
      const valB = b[sortBy];
      if (typeof valA === "number" && typeof valB === "number") {
        return sortAsc ? valA - valB : valB - valA;
      }
      return 0;
    });

  const handleSort = (field: keyof MarketScannerItem) => {
    if (sortBy === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortBy(field);
      setSortAsc(false);
    }
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Real-Time Normalized Market Scanner Feed"
        subtitle="Calculated strictly from 1-second ticks and 1-minute aggregated bars. Free of lookahead bias."
      />

      {/* Filter and Universe Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-[#151A23] border border-[#222938]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-300">
            <Radar size={16} className="text-sky-400" />
            <span className="font-bold">UNIVERSE:</span>
          </div>

          <div className="flex items-center gap-1">
            {["NIFTY_50", "LIQUID_MICRO_CAPS", "CUSTOM_WATCHLIST"].map((u) => (
              <button
                key={u}
                onClick={() => setUniverse(u)}
                className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                  universe === u
                    ? "bg-[#1C2331] text-sky-400 font-bold border border-sky-800/80"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {u.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <label className="flex items-center gap-2 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={filterActiveOnly}
              onChange={(e) => setFilterActiveOnly(e.target.checked)}
              className="rounded border-[#222938] bg-[#0B0E14] text-sky-600 focus:ring-0"
            />
            <Filter size={12} className="text-slate-400" />
            Active Momentum Only
          </label>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">Total Scanned: {scannerData.length}</span>
        </div>
      </div>

      {/* Market Scanner Grid Table */}
      <div className="rounded-lg bg-[#151A23] border border-[#222938] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0B0E14] text-slate-400 border-b border-[#222938] uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-4 font-semibold">Symbol</th>
                <th
                  className="py-2.5 px-4 font-semibold cursor-pointer hover:text-slate-200"
                  onClick={() => handleSort("last_price")}
                >
                  <div className="flex items-center gap-1">
                    Last Price <ArrowUpDown size={10} />
                  </div>
                </th>
                <th
                  className="py-2.5 px-4 font-semibold cursor-pointer hover:text-slate-200"
                  onClick={() => handleSort("change_pct")}
                >
                  <div className="flex items-center gap-1">
                    Change % <ArrowUpDown size={10} />
                  </div>
                </th>
                <th
                  className="py-2.5 px-4 font-semibold cursor-pointer hover:text-slate-200"
                  onClick={() => handleSort("rvol_10")}
                >
                  <div className="flex items-center gap-1">
                    RVOL 10 <ArrowUpDown size={10} />
                  </div>
                </th>
                <th className="py-2.5 px-4 font-semibold">VWAP Distance</th>
                <th className="py-2.5 px-4 font-semibold">Spread (bps)</th>
                <th className="py-2.5 px-4 font-semibold">Sector</th>
                <th className="py-2.5 px-4 font-semibold">Status</th>
                <th className="py-2.5 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222938]">
              {filtered.map((item) => (
                <tr key={item.symbol} className="hover:bg-[#1C2331]/60 transition-colors">
                  <td className="py-2.5 px-4 font-bold text-slate-100 flex items-center gap-2">
                    {item.symbol}
                  </td>
                  <td className="py-2.5 px-4 text-slate-200 tabular-nums">
                    ₹{item.last_price.toFixed(2)}
                  </td>
                  <td
                    className={`py-2.5 px-4 font-semibold tabular-nums ${
                      item.change_pct >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {item.change_pct >= 0 ? "+" : ""}
                    {item.change_pct.toFixed(2)}%
                  </td>
                  <td className="py-2.5 px-4 text-slate-200 tabular-nums font-bold">
                    <span
                      className={
                        item.rvol_10 >= 2.0
                          ? "text-emerald-400 font-bold"
                          : item.rvol_10 >= 1.2
                          ? "text-sky-300"
                          : "text-slate-400"
                      }
                    >
                      {item.rvol_10.toFixed(2)}x
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-300 tabular-nums">
                    <span className={item.vwap_distance_pct >= 0 ? "text-emerald-400" : "text-rose-400"}>
                      {item.vwap_distance_pct >= 0 ? "+" : ""}
                      {item.vwap_distance_pct.toFixed(2)}%
                    </span>{" "}
                    <span className="text-[10px] text-slate-500">(₹{item.vwap.toFixed(1)})</span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-300 tabular-nums">
                    <span className={item.spread_bps <= 5.0 ? "text-emerald-400" : "text-amber-400"}>
                      {item.spread_bps.toFixed(1)} bps
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 text-[11px]">{item.sector}</td>
                  <td className="py-2.5 px-4">
                    <Badge
                      state={
                        item.status === "ACTIVE"
                          ? "BUY"
                          : item.status === "WATCHING"
                          ? "WATCH"
                          : "HOLD"
                      }
                    >
                      {item.status}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <button
                      onClick={() => onSelectSymbol(item.symbol)}
                      className="px-2.5 py-1 rounded bg-[#0B0E14] hover:bg-sky-950/80 text-sky-400 border border-[#222938] hover:border-sky-800 text-[11px] font-mono flex items-center gap-1 ml-auto"
                    >
                      <BarChart3 size={12} />
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
