import React from "react";

interface AIOrbProps {
  size?: number;
  /** Orb accent colours. */
  colorA?: string;
  colorB?: string;
  className?: string;
}

/**
 * Glowing circular AI orb: layered radial gradient core, orbit rings and
 * pulsing halo. Purely decorative, referenced with aria-hidden.
 */
export const AIOrb: React.FC<AIOrbProps> = ({
  size = 88,
  colorA = "#00F0FF",
  colorB = "#8B5CF6",
  className = "",
}) => {
  const uid = `${colorA.replace(/[^a-z0-9]/gi, "")}-${colorB.replace(/[^a-z0-9]/gi, "")}`;

  return (
    <span
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {/* Pulsing halo */}
      <span
        className="absolute inset-0 rounded-full animate-pulse-glow"
        style={{ boxShadow: `0 0 28px 4px ${colorA}55` }}
      />
      <svg width={size} height={size} viewBox="0 0 100 100" className="absolute inset-0">
        <defs>
          <radialGradient id={`orb-core-${uid}`} cx="36%" cy="32%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="34%" stopColor={colorA} />
            <stop offset="72%" stopColor={colorB} />
            <stop offset="100%" stopColor="#0B132B" />
          </radialGradient>
          <linearGradient id={`orb-ring-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={colorA} stopOpacity="0.95" />
            <stop offset="100%" stopColor={colorB} stopOpacity="0.9" />
          </linearGradient>
        </defs>

        <circle cx="50" cy="50" r="26" fill={`url(#orb-core-${uid})`} />
        <circle
          cx="50"
          cy="50"
          r="34"
          fill="none"
          stroke={`url(#orb-ring-${uid})`}
          strokeWidth="1.4"
          className="origin-center animate-orbit-slow"
        />
        <ellipse
          cx="50"
          cy="50"
          rx="45"
          ry="16"
          fill="none"
          stroke={colorA}
          strokeOpacity="0.45"
          strokeWidth="1.2"
          className="origin-center animate-orbit-rev"
        />
        <ellipse
          cx="50"
          cy="50"
          rx="16"
          ry="45"
          fill="none"
          stroke={colorB}
          strokeOpacity="0.35"
          strokeWidth="1"
          className="origin-center animate-orbit-slow"
        />
        <circle cx="50" cy="16" r="2" fill={colorA} />
        <circle cx="95" cy="50" r="1.6" fill={colorB} />
      </svg>
    </span>
  );
};

export default AIOrb;
