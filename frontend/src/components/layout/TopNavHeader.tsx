import React from "react";
import {
  Search,
  Bell,
  Settings as SettingsIcon,
  Moon,
  Sun,
  ChevronDown,
  AlertOctagon,
  ShieldCheck,
} from "lucide-react";
import { ScreenId } from "../../types";

interface TopNavHeaderProps {
  onOpenKillSwitch: () => void;
  isHalted: boolean;
  /** Execution mode reported by the live system health feed. */
  mode: "PAPER" | "LIVE";
  isDark: boolean;
  onToggleTheme: () => void;
  onNavigate: (screen: ScreenId) => void;
}

const SEARCH_HINT = "Search symbol (e.g. RELIANCE, INFY, BTC...)";

export const TopNavHeader: React.FC<TopNavHeaderProps> = ({
  onOpenKillSwitch,
  isHalted,
  mode,
  isDark,
  onToggleTheme,
  onNavigate,
}) => {
  const [query, setQuery] = React.useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const sym = query.trim().toUpperCase();
    if (!sym) return;
    onNavigate("chart");
  };

  return (
    <header
      className="sticky top-0 z-40 border-b border-sky-500/15 bg-[#070C1A]/80 backdrop-blur-xl"
      role="banner"
      aria-label="Cockpit top navigation"
    >
      <div className="flex h-14 items-center gap-3 px-4">
        {/* Symbol search */}
        <form onSubmit={handleSubmit} className="relative w-full max-w-[380px]">
          <Search
            size={15}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={SEARCH_HINT}
            aria-label="Search symbol"
            className="w-full rounded-full border border-sky-500/20 bg-white/[0.03] py-2 pl-9 pr-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-neon-cyan/60 focus:outline-none focus:shadow-glow-cyan"
          />
        </form>

        {/* Live agent status */}
        <div
          className="hidden items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/8 px-3 py-1.5 md:flex"
          aria-label="AI agents online"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 animate-pulse-ring" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          <span className="text-[11px] font-medium tracking-wide text-emerald-300">
            AI Agents Online
          </span>
        </div>

        {isHalted && (
          <span
            role="status"
            aria-live="polite"
            className="flex items-center gap-1.5 rounded-full border border-rose-500/50 bg-rose-500/15 px-3 py-1.5 text-[11px] font-bold tracking-wide text-rose-300"
          >
            <AlertOctagon size={13} aria-hidden="true" />
            SYSTEM HALTED
          </span>
        )}

        <div className="flex-1" />

        {/* Mode indicator — mirrors the Deterministic Trade Gate's real mode.
            The dashboard never grants itself execution authority. */}
        <div
          className="relative hidden items-center gap-2 rounded-full border border-sky-500/20 bg-white/[0.03] py-1.5 pl-3 pr-8 sm:flex"
          title="Execution mode reported by the live system health feed"
        >
          <span className="text-[11px] text-slate-400">Live Trading:</span>
          <span className="flex items-center gap-1 text-[11px] font-semibold text-sky-200">
            <ShieldCheck size={12} className="text-emerald-400" aria-hidden="true" />
            {mode === "PAPER" ? "Paper" : "Live"}
          </span>
          <ChevronDown
            size={13}
            aria-hidden="true"
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500"
          />
        </div>

        {/* Action icons */}
        <button
          type="button"
          onClick={() => onNavigate("logs")}
          className="relative rounded-lg border border-sky-500/15 bg-white/[0.03] p-2 text-slate-400 transition-colors hover:border-sky-500/40 hover:text-sky-200"
          title="Notifications & Event Stream"
          aria-label="Notifications"
        >
          <Bell size={15} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-neon-cyan shadow-glow-cyan" />
        </button>

        <button
          type="button"
          onClick={onToggleTheme}
          className="rounded-lg border border-sky-500/15 bg-white/[0.03] p-2 text-slate-400 transition-colors hover:border-sky-500/40 hover:text-sky-200"
          title={isDark ? "Switch to deep-space light mode" : "Switch to deep-space dark mode"}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <button
          type="button"
          onClick={() => onNavigate("settings")}
          className="rounded-lg border border-sky-500/15 bg-white/[0.03] p-2 text-slate-400 transition-colors hover:border-sky-500/40 hover:text-sky-200"
          title="Settings"
          aria-label="Settings"
        >
          <SettingsIcon size={15} />
        </button>

        <div
          className="flex h-8 w-8 items-center justify-center rounded-full border border-neon-cyan/40 bg-gradient-to-br from-sky-500/30 to-violet-500/30 font-display text-[11px] font-bold text-cyan-100"
          title="Operator: SV"
          aria-label="Operator profile SV"
        >
          SV
        </div>

        {/* Emergency kill switch — safety invariant, never removed */}
        <button
          type="button"
          onClick={onOpenKillSwitch}
          className="flex items-center gap-1.5 rounded-lg border border-rose-500/60 bg-rose-600/25 px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-wider text-rose-200 shadow-glow-crimson transition-all hover:bg-rose-600/45 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 active:scale-95"
          title="Emergency Position Square-Off & Autonomous System Shutdown"
          aria-label="Open emergency kill switch dialog"
        >
          <AlertOctagon size={14} aria-hidden="true" />
          Kill Switch
        </button>
      </div>

      {/* Mission quote strip */}
      <div className="flex items-center justify-between gap-4 border-t border-sky-500/10 px-4 py-1">
        <p className="truncate text-[9px] font-semibold tracking-[0.28em] text-slate-500">
          SAME MARKETS. A BRIGHTER YOU.
        </p>
        <p className="truncate font-display text-[9px] font-semibold tracking-[0.28em] text-neon-cyan/70">
          &lsquo;ANALYZE. ADAPT. EXECUTE. EVOLVE.&rsquo;
        </p>
      </div>
    </header>
  );
};

export default TopNavHeader;
