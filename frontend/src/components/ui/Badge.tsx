import React from "react";
import { BadgeState } from "../../types";

interface BadgeProps {
  state: BadgeState | string;
  className?: string;
  children?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ state, className = "", children }) => {
  const normalized = state.toUpperCase() as BadgeState;

  const getStyle = (): string => {
    switch (normalized) {
      case "BUY":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-600/40";
      case "SELL":
        return "bg-rose-500/15 text-rose-400 border-rose-600/40";
      case "HOLD":
        return "bg-slate-500/15 text-slate-400 border-slate-600/40";
      case "WATCH":
        return "bg-cyan-500/15 text-cyan-400 border-cyan-600/40";
      case "RISK":
        return "bg-amber-500/15 text-amber-400 border-amber-600/40 animate-pulse";
      case "ERROR":
        return "bg-red-500/25 text-red-300 border-red-600/50";
      case "CONNECTED":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "DISCONNECTED":
        return "bg-rose-500/20 text-rose-400 border-rose-500/30";
      case "AI THINKING":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse";
      case "AI UNAVAILABLE":
        return "bg-slate-500/20 text-slate-400 border-slate-600/30";
      case "PENDING":
        return "bg-yellow-500/15 text-yellow-400 border-yellow-600/40";
      case "PARTIAL FILL":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "FILLED":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/50";
      case "CANCELLED":
        return "bg-slate-500/20 text-slate-400 border-slate-600/40";
      case "REJECTED":
        return "bg-rose-500/20 text-rose-400 border-rose-600/50";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${getStyle()} ${className}`}
    >
      {children || state}
    </span>
  );
};
