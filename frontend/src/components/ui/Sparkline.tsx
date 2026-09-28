import React from "react";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  /** Soft fill beneath the line. */
  fill?: boolean;
  strokeWidth?: number;
  className?: string;
}

const buildPath = (
  values: number[],
  width: number,
  height: number,
  padding: number,
): { line: string; area: string } => {
  if (values.length === 0) {
    return { line: "", area: "" };
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const innerW = width - padding * 2;
  const innerH = height - padding * 2;
  const stepX = values.length > 1 ? innerW / (values.length - 1) : 0;

  const points = values.map((v, i) => {
    const x = padding + i * stepX;
    const y = padding + innerH - ((v - min) / span) * innerH;
    return { x, y };
  });

  // Catmull-Rom style smoothing via cubic midpoints
  let line = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  for (let i = 1; i < points.length; i += 1) {
    const prev = points[i - 1];
    const curr = points[i];
    const cx = (prev.x + curr.x) / 2;
    line += ` C ${cx.toFixed(2)} ${prev.y.toFixed(2)}, ${cx.toFixed(2)} ${curr.y.toFixed(
      2,
    )}, ${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`;
  }

  const area = `${line} L ${points[points.length - 1].x.toFixed(2)} ${height} L ${points[0].x.toFixed(
    2,
  )} ${height} Z`;

  return { line, area };
};

/**
 * Compact SVG polyline sparkline used across KPI cards and portfolio widgets.
 */
export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 40,
  color = "#10B981",
  fill = true,
  strokeWidth = 2,
  className = "",
}) => {
  const gradientId = `spark-${color.replace(/[^a-z0-9]/gi, "")}-${width}x${height}`;
  const { line, area } = buildPath(data, width, height, strokeWidth + 1);
  const isUp = data.length > 1 ? data[data.length - 1] >= data[0] : true;
  const effectiveColor = isUp ? color : "#F43F5E";

  if (!line) {
    return <div style={{ width, height }} className={className} />;
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={effectiveColor} stopOpacity={0.35} />
          <stop offset="100%" stopColor={effectiveColor} stopOpacity={0} />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gradientId})`} />}
      <path
        d={line}
        fill="none"
        stroke={effectiveColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: `drop-shadow(0 0 4px ${effectiveColor}66)` }}
      />
    </svg>
  );
};

interface BarSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

/**
 * Vertical bar sparkline (used for P&L style metrics).
 */
export const BarSparkline: React.FC<BarSparklineProps> = ({
  data,
  width = 120,
  height = 40,
  color = "#10B981",
  className = "",
}) => {
  if (data.length === 0) {
    return <div style={{ width, height }} className={className} />;
  }

  const max = Math.max(...data.map((v) => Math.abs(v))) || 1;
  const gap = 2;
  const barW = Math.max(1.5, (width - gap * (data.length - 1)) / data.length);
  const usableH = height - 6;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden="true"
    >
      {data.map((v, i) => {
        const h = Math.max(2, (Math.abs(v) / max) * usableH);
        return (
          <rect
            key={i}
            x={i * (barW + gap)}
            y={height - h}
            width={barW}
            height={h}
            rx={Math.min(1.5, barW / 2)}
            fill={v >= 0 ? color : "#F43F5E"}
            opacity={0.55 + 0.45 * (i / Math.max(1, data.length - 1))}
          />
        );
      })}
    </svg>
  );
};

export default Sparkline;
