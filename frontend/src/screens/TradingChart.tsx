import React, { useState } from "react";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";


interface TradingChartProps {
  selectedSymbol: string;
}

export const TradingChart: React.FC<TradingChartProps> = ({
  selectedSymbol = "INFY",
}) => {
  const [timeframe, setTimeframe] = useState<string>("1m");
  const [showVWAP, setShowVWAP] = useState<boolean>(true);
  const [showVolume, setShowVolume] = useState<boolean>(true);

  // Realistic mock candle data for interactive SVG chart
  const candles = [
    { time: "09:15", open: 1860, high: 1868, low: 1858, close: 1865, vol: 42000, vwap: 1863 },
    { time: "09:20", open: 1865, high: 1872, low: 1862, close: 1870, vol: 58000, vwap: 1866 },
    { time: "09:25", open: 1870, high: 1876, low: 1868, close: 1874, vol: 64000, vwap: 1869 },
    { time: "09:30", open: 1874, high: 1885, low: 1872, close: 1882, vol: 92000, vwap: 1873 },
    { time: "09:35", open: 1882, high: 1888, low: 1879, close: 1885, vol: 78000, vwap: 1877 },
    { time: "09:40", open: 1885, high: 1892, low: 1883, close: 1890, vol: 85000, vwap: 1881 },
    { time: "09:45", open: 1890, high: 1898, low: 1888, close: 1894, vol: 112000, vwap: 1886 },
    { time: "09:50", open: 1894, high: 1896, low: 1891, close: 1894.2, vol: 67000, vwap: 1888 },
  ];

  const minPrice = 1855;
  const maxPrice = 1920;
  const priceRange = maxPrice - minPrice;

  // Key execution levels for INFY
  const entryPrice = 1890.0;
  const hardStopPrice = 1878.0;
  const trailingStopPrice = 1886.0;
  const takeProfitPrice = 1914.0;
  const currentPrice = 1894.2;

  const getY = (price: number): number => {
    return 260 - ((price - minPrice) / priceRange) * 230;
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title={`Live Technical Chart: ${selectedSymbol}`}
        subtitle="1-minute OHLCV aggregation with deterministic VWAP and Watcher price triggers."
      />

      {/* Chart Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-[#151A23] border border-[#222938]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold font-mono text-slate-100">{selectedSymbol}</span>
            <Badge state="BUY">NSE: EQ</Badge>
            <span className="text-xs font-mono text-slate-400">₹{currentPrice.toFixed(2)}</span>
          </div>

          <div className="flex items-center gap-1 border-l border-[#222938] pl-3">
            {["1m", "5m", "15m"].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                  timeframe === tf
                    ? "bg-[#1C2331] text-sky-400 font-bold border border-sky-800"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={showVWAP}
              onChange={(e) => setShowVWAP(e.target.checked)}
              className="rounded border-[#222938] bg-[#0B0E14] text-sky-600 focus:ring-0"
            />
            <span className="text-amber-400">●</span> VWAP Overlay
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={showVolume}
              onChange={(e) => setShowVolume(e.target.checked)}
              className="rounded border-[#222938] bg-[#0B0E14] text-sky-600 focus:ring-0"
            />
            <span className="text-slate-400">■</span> Volume Sub-Pane
          </label>
        </div>
      </div>

      {/* SVG Canvas Candlestick Chart */}
      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] relative overflow-hidden">
        {/* Execution Levels Legend */}
        <div className="flex flex-wrap items-center gap-4 mb-3 pb-2 border-b border-[#222938] text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-cyan-400" />
            <span className="text-slate-300">Entry: ₹{entryPrice.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-rose-500 border-dashed" />
            <span className="text-rose-400">Hard Stop: ₹{hardStopPrice.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-amber-400" />
            <span className="text-amber-300">Trailing Stop: ₹{trailingStopPrice.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-emerald-400" />
            <span className="text-emerald-300">Take Profit: ₹{takeProfitPrice.toFixed(2)}</span>
          </div>
        </div>

        {/* Interactive SVG Chart */}
        <div className="w-full h-[320px] relative">
          <svg className="w-full h-full" viewBox="0 0 800 300" preserveAspectRatio="none">
            {/* Background grid lines */}
            {[1860, 1880, 1900, 1920].map((p) => {
              const y = getY(p);
              return (
                <g key={p}>
                  <line x1="0" y1={y} x2="750" y2={y} stroke="#222938" strokeDasharray="3 3" />
                  <text x="755" y={y + 3} fill="#64748B" fontSize="9" fontFamily="monospace">
                    ₹{p}
                  </text>
                </g>
              );
            })}

            {/* Price Marker Lines */}
            {/* Take Profit Target (Green Solid) */}
            <line
              x1="0"
              y1={getY(takeProfitPrice)}
              x2="750"
              y2={getY(takeProfitPrice)}
              stroke="#10B981"
              strokeWidth="1.5"
            />
            {/* Current Price Line (White) */}
            <line
              x1="0"
              y1={getY(currentPrice)}
              x2="750"
              y2={getY(currentPrice)}
              stroke="#F1F5F9"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
            {/* Trailing Stop Level (Amber Dotted) */}
            <line
              x1="0"
              y1={getY(trailingStopPrice)}
              x2="750"
              y2={getY(trailingStopPrice)}
              stroke="#F59E0B"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            {/* Entry Price (Cyan Solid) */}
            <line
              x1="0"
              y1={getY(entryPrice)}
              x2="750"
              y2={getY(entryPrice)}
              stroke="#06B6D4"
              strokeWidth="1.5"
            />
            {/* Hard Stop Loss (Red Dashed) */}
            <line
              x1="0"
              y1={getY(hardStopPrice)}
              x2="750"
              y2={getY(hardStopPrice)}
              stroke="#EF4444"
              strokeWidth="1.5"
              strokeDasharray="5 3"
            />

            {/* Candlesticks & Volume */}
            {candles.map((c, i) => {
              const x = 50 + i * 90;
              const isBullish = c.close >= c.open;
              const candleColor = isBullish ? "#10B981" : "#EF4444";
              const openY = getY(c.open);
              const closeY = getY(c.close);
              const highY = getY(c.high);
              const lowY = getY(c.low);
              const topY = Math.min(openY, closeY);
              const height = Math.max(Math.abs(closeY - openY), 2);

              return (
                <g key={c.time}>
                  {/* High-Low Wick */}
                  <line x1={x} y1={highY} x2={x} y2={lowY} stroke={candleColor} strokeWidth="1.5" />
                  {/* Candle Body */}
                  <rect
                    x={x - 14}
                    y={topY}
                    width={28}
                    height={height}
                    fill={candleColor}
                    rx="1"
                  />

                  {/* Volume Sub-Bar at bottom */}
                  {showVolume && (
                    <rect
                      x={x - 10}
                      y={290 - (c.vol / 120000) * 45}
                      width={20}
                      height={(c.vol / 120000) * 45}
                      fill={candleColor}
                      opacity="0.3"
                    />
                  )}

                  {/* Time label */}
                  <text x={x - 12} y="298" fill="#64748B" fontSize="9" fontFamily="monospace">
                    {c.time}
                  </text>
                </g>
              );
            })}

            {/* VWAP Polyline */}
            {showVWAP && (
              <polyline
                fill="none"
                stroke="#F59E0B"
                strokeWidth="1.5"
                points={candles.map((c, i) => `${50 + i * 90},${getY(c.vwap)}`).join(" ")}
              />
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};
