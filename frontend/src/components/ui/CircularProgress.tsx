import React from "react";

interface CircularProgressProps {
  /** Current value in the same unit as `max`. */
  value: number;
  /** Upper bound used to derive the sweep angle. Defaults to 100. */
  max?: number;
  /** Diameter of the gauge in pixels. */
  size?: number;
  /** Ring thickness in pixels. */
  strokeWidth?: number;
  /** Track colour (CSS colour string). */
  trackColor?: string;
  /** Active arc colour (CSS colour string). */
  color?: string;
  /** Optional glow colour applied to the arc filter. */
  glowColor?: string;
  label?: string;
  valueText?: string;
  className?: string;
}

const clamp01 = (n: number): number => (n < 0 ? 0 : n > 1 ? 1 : n);

/**
 * Radial SVG donut gauge with a smoothly animated stroke sweep.
 */
export const CircularProgress: React.FC<CircularProgressProps> = ({
  value,
  max = 100,
  size = 72,
  strokeWidth = 7,
  trackColor = "rgba(56, 189, 248, 0.15)",
  color = "#00F0FF",
  glowColor,
  label,
  valueText,
  className = "",
}) => {
  const safeMax = max > 0 ? max : 1;
  const ratio = clamp01(value / safeMax);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - ratio);
  const center = size / 2;
  const filterId = `cp-glow-${size}-${color.replace(/[^a-z0-9]/gi, "")}`;

  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={label ? `${label}: ${valueText ?? value}` : undefined}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {glowColor && (
          <defs>
            <filter id={filterId} x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="2.4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        )}

        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />

        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${center} ${center})`}
          filter={glowColor ? `url(#${filterId})` : undefined}
          style={{
            transition: "stroke-dashoffset 900ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-semibold leading-none text-slate-100 tabular-nums"
          style={{ fontSize: Math.max(10, size * 0.26) }}
        >
          {valueText ?? value}
        </span>
        {label && (
          <span
            className="mt-0.5 uppercase tracking-widest text-slate-400"
            style={{ fontSize: Math.max(7, size * 0.13) }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
};

export default CircularProgress;
