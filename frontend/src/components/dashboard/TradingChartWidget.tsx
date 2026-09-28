import React, { useMemo, useState } from "react";
import { Star, SlidersHorizontal, PenLine, Layers, Crosshair } from "lucide-react";

interface Candle {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  maFast: number;
  maSlow: number;
}

interface TradingChartWidgetProps {
  symbol: string;
  companyName: string;
  exchange: string;
  capClass: string;
  lastPrice: number;
  changePct: number;
  onOpenFullChart?: () => void;
}

const TIMEFRAMES = ["1m", "5m", "15m", "1H", "4H", "1D", "1W", "1M"];
const CANDLE_COUNT = 56;

/** Deterministic pseudo-random so the series is stable across re-renders. */
const seeded = (seed: number): (() => number) => {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
};

const hashSymbol = (symbol: string): number =>
  symbol.split("").reduce((acc, ch) => acc * 31 + ch.charCodeAt(0), 7);

const buildSeries = (symbol: string, basePrice: number, count: number): Candle[] => {
  const rand = seeded(hashSymbol(symbol) + count);
  const candles: Candle[] = [];
  let price = basePrice * 0.985;
  const closes: number[] = [];

  for (let i = 0; i < count; i += 1) {
    const drift = (rand() - 0.42) * basePrice * 0.006;
    const open = price;
    const close = Math.max(basePrice * 0.9, open + drift);
    const wick = (0.3 + rand() * 0.9) * basePrice * 0.0025;
    const high = Math.max(open, close) + wick;
    const low = Math.min(open, close) - wick * (0.6 + rand() * 0.8);
    const volume = Math.round((0.4 + rand() * 1.6) * 180000);
    candles.push({ open, high, low, close, volume, maFast: 0, maSlow: 0 });
    closes.push(close);
    price = close;
  }

  const ma = (period: number, i: number): number => {
    if (i < period - 1) return closes[i];
    let sum = 0;
    for (let k = i - period + 1; k <= i; k += 1) sum += closes[k];
    return sum / period;
  };

  return candles.map((c, i) => ({
    ...c,
    maFast: ma(7, i),
    maSlow: ma(21, i),
  }));
};

const W = 760;
const H = 250;
const PAD_TOP = 14;
const PAD_BOTTOM = 18;
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;
const VOL_H = 42;

export const TradingChartWidget: React.FC<TradingChartWidgetProps> = ({
  symbol,
  companyName,
  exchange,
  capClass,
  lastPrice,
  changePct,
  onOpenFullChart,
}) => {
  const [timeframe, setTimeframe] = useState("5m");
  const [isFavorite, setIsFavorite] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const candles = useMemo(
    () => buildSeries(symbol, lastPrice, CANDLE_COUNT),
    [symbol, lastPrice],
  );

  const { min, max } = useMemo(() => {
    const lows = candles.map((c) => c.low);
    const highs = candles.map((c) => c.high);
    return { min: Math.min(...lows), max: Math.max(...highs) };
  }, [candles]);

  const span = max - min || 1;
  const stepX = W / candles.length;
  const bodyW = Math.max(3, stepX * 0.56);

  const yOf = (price: number): number =>
    PAD_TOP + PLOT_H - ((price - min) / span) * PLOT_H;

  const linePath = (key: "maFast" | "maSlow"): string =>
    candles
      .map((c, i) => `${i === 0 ? "M" : "L"} ${(i * stepX + stepX / 2).toFixed(1)} ${yOf(c[key]).toFixed(1)}`)
      .join(" ");

  const maxVol = Math.max(...candles.map((c) => c.volume)) || 1;
  const isUp = changePct >= 0;
  const activeCandle = hoverIndex !== null ? candles[hoverIndex] : candles[candles.length - 1];

  const gridLines = [0, 0.25, 0.5, 0.75, 1];
  const priceTicks = gridLines
    .map((g) => max - g * span)
    .reverse()
    .map((p) => p.toFixed(2));

  return (
    <section className="glass-panel rounded-xl p-4" aria-label={`${symbol} price chart`}>
      {/* Symbol header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <button
            type="button"
            onClick={() => setIsFavorite((f) => !f)}
            className="mt-1 transition-transform hover:scale-110"
            aria-label={isFavorite ? `Remove ${symbol} from watchlist` : `Add ${symbol} to watchlist`}
            aria-pressed={isFavorite}
          >
            <Star
              size={16}
              className={isFavorite ? "fill-amber-400 text-amber-400" : "text-slate-600"}
            />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-lg font-bold tracking-wide text-slate-50">
                {symbol}
              </h2>
              <span className="rounded border border-sky-500/30 bg-sky-500/10 px-1.5 py-0.5 text-[9px] font-semibold tracking-widest text-sky-300">
                {exchange}
              </span>
              <span className="rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 text-[9px] font-semibold tracking-widest text-violet-300">
                {capClass}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">{companyName}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p
              className={`font-mono text-xl font-bold tabular-nums ${
                isUp ? "text-emerald-300" : "text-rose-300"
              }`}
            >
              {lastPrice.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
            <p
              className={`font-mono text-[11px] tabular-nums ${
                isUp ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {isUp ? "+" : ""}
              {changePct.toFixed(2)}%
            </p>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-y border-sky-500/10 py-2">
        <div className="flex items-center gap-0.5" role="group" aria-label="Timeframe">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              type="button"
              onClick={() => setTimeframe(tf)}
              aria-pressed={timeframe === tf}
              className={`rounded px-2 py-1 font-mono text-[11px] transition-colors ${
                timeframe === tf
                  ? "bg-sky-500/25 text-sky-200 shadow-glow-blue"
                  : "text-slate-500 hover:bg-sky-500/10 hover:text-slate-300"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          {[
            { icon: SlidersHorizontal, label: "Indicators" },
            { icon: PenLine, label: "Draw" },
            { icon: Layers, label: "Compare" },
          ].map(({ icon: Icon, label }) => (
            <button
              key={label}
              type="button"
              className="flex items-center gap-1 rounded border border-sky-500/15 bg-white/[0.02] px-2 py-1 text-[10px] text-slate-400 transition-colors hover:border-sky-500/40 hover:text-sky-200"
              aria-label={label}
            >
              <Icon size={12} aria-hidden="true" />
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={onOpenFullChart}
            className="flex items-center gap-1 rounded border border-sky-500/15 bg-white/[0.02] px-2 py-1 text-[10px] text-slate-400 transition-colors hover:border-sky-500/40 hover:text-sky-200"
            aria-label="Open full chart station"
          >
            <Crosshair size={12} aria-hidden="true" />
            Expand
          </button>
        </div>
      </div>

      {/* Candlestick canvas */}
      <div className="relative mt-3">
        <div
          className="flex"
          onMouseLeave={() => setHoverIndex(null)}
          role="presentation"
        >
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-[250px] w-full"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="maFastGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.9" />
              </linearGradient>
              <linearGradient id="maSlowGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#6366F1" stopOpacity="0.85" />
              </linearGradient>
            </defs>

            {/* Horizontal grid */}
            {gridLines.map((g) => (
              <line
                key={g}
                x1={0}
                x2={W}
                y1={PAD_TOP + PLOT_H * g}
                y2={PAD_TOP + PLOT_H * g}
                stroke="rgba(56,189,248,0.09)"
                strokeWidth={1}
              />
            ))}

            {/* Volume sub-bars */}
            {candles.map((c, i) => {
              const h = (c.volume / maxVol) * VOL_H;
              return (
                <rect
                  key={`v-${i}`}
                  x={i * stepX + stepX * 0.22}
                  y={H - h}
                  width={bodyW}
                  height={h}
                  fill={c.close >= c.open ? "#10B981" : "#F43F5E"}
                  opacity={0.22}
                />
              );
            })}

            {/* Candles */}
            {candles.map((c, i) => {
              const up = c.close >= c.open;
              const stroke = up ? "#10B981" : "#F43F5E";
              const fill = up ? "rgba(16,185,129,0.85)" : "rgba(244,63,94,0.85)";
              const yO = yOf(c.open);
              const yC = yOf(c.close);
              const top = Math.min(yO, yC);
              const bodyH = Math.max(1.5, Math.abs(yC - yO));
              return (
                <g key={i} opacity={hoverIndex === null || hoverIndex === i ? 1 : 0.55}>
                  <line
                    x1={i * stepX + stepX / 2}
                    x2={i * stepX + stepX / 2}
                    y1={yOf(c.high)}
                    y2={yOf(c.low)}
                    stroke={stroke}
                    strokeWidth={1}
                  />
                  <rect
                    x={i * stepX + stepX / 2 - bodyW / 2}
                    y={top}
                    width={bodyW}
                    height={bodyH}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={0.8}
                    rx={0.6}
                  />
                </g>
              );
            })}

            {/* Moving average curves */}
            <path
              d={linePath("maFast")}
              fill="none"
              stroke="url(#maFastGrad)"
              strokeWidth={1.8}
              strokeLinecap="round"
            />
            <path
              d={linePath("maSlow")}
              fill="none"
              stroke="url(#maSlowGrad)"
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeDasharray="5 3"
            />

            {/* Last price guide */}
            <line
              x1={0}
              x2={W}
              y1={yOf(activeCandle.close)}
              y2={yOf(activeCandle.close)}
              stroke="rgba(0,240,255,0.35)"
              strokeWidth={1}
              strokeDasharray="4 4"
            />
          </svg>
        </div>

        {/* Right-axis price labels with active pill */}
        <div
          className="pointer-events-none absolute right-0 top-0 flex h-[250px] flex-col justify-between py-[14px]"
          aria-hidden="true"
        >
          {priceTicks.map((t, i) => (
            <span
              key={t + i}
              className="-translate-y-1/2 rounded-l border border-sky-500/25 bg-[#0B1124]/90 px-1.5 py-0.5 font-mono text-[9px] tabular-nums text-slate-500"
            >
              {t}
            </span>
          ))}
        </div>

        {/* Current price pill pinned to last candle */}
        <div
          className="pointer-events-none absolute right-10 -translate-y-1/2"
          style={{ top: yOf(activeCandle.close) / H * 100 + "%" }}
          aria-hidden="true"
        >
          <span
            className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold tabular-nums ${
              isUp
                ? "bg-emerald-500/85 text-space-void"
                : "bg-rose-500/85 text-space-void"
            }`}
          >
            {activeCandle.close.toFixed(2)}
          </span>
        </div>

        {/* Hover capture layer */}
        <div
          className="absolute inset-0 flex"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            setHoverIndex(Math.min(CANDLE_COUNT - 1, Math.max(0, Math.floor(x / rect.width * CANDLE_COUNT))));
          }}
          role="presentation"
        >
          {candles.map((_, i) => (
            <div key={i} className="h-full flex-1" />
          ))}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] text-slate-500">
        <span className="text-sky-400">MA 7 · MA 21</span>
        <span className="tabular-nums">
          O {activeCandle.open.toFixed(2)} · H {activeCandle.high.toFixed(2)} · L{" "}
          {activeCandle.low.toFixed(2)} · C {activeCandle.close.toFixed(2)}
        </span>
        <span className="tabular-nums">Vol {activeCandle.volume.toLocaleString("en-IN")}</span>
      </div>
    </section>
  );
};

export default TradingChartWidget;
