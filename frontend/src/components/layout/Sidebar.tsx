import React from "react";
import {
  LayoutDashboard,
  Radio,
  BrainCircuit,
  Radar,
  Wallet,
  ClipboardList,
  SlidersHorizontal,
  LineChart,
  ShieldCheck,
  Newspaper,
  Settings as SettingsIcon,
  Sparkles,
  CandlestickChart,
  FlaskConical,
  HeartPulse,
  LucideIcon,
} from "lucide-react";
import { ScreenId } from "../../types";

interface SidebarProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
}

interface NavItem {
  id: ScreenId;
  label: string;
  icon: LucideIcon;
}

const PRIMARY_NAV: NavItem[] = [
  { id: "command", label: "Dashboard", icon: LayoutDashboard },
  { id: "positions", label: "Live Trading", icon: Radio },
  { id: "ai", label: "AI Decisions", icon: BrainCircuit },
  { id: "scanner", label: "Market Scanner", icon: Radar },
  { id: "performance", label: "Portfolio", icon: Wallet },
  { id: "orders", label: "Orders", icon: ClipboardList },
  { id: "strategies", label: "Strategies", icon: SlidersHorizontal },
  { id: "journal", label: "Performance", icon: LineChart },
  { id: "risk", label: "Risk Control", icon: ShieldCheck },
  { id: "logs", label: "News & Events", icon: Newspaper },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];

/** Remaining cockpit stations stay one click away below the main rail. */
const SECONDARY_NAV: NavItem[] = [
  { id: "candidates", label: "Candidate Feed", icon: Sparkles },
  { id: "chart", label: "Full Chart", icon: CandlestickChart },
  { id: "backtesting", label: "Backtesting", icon: FlaskConical },
  { id: "health", label: "System Health", icon: HeartPulse },
];

/** Orbital ring / planetary logo mark. */
const OrbitMark: React.FC = () => (
  <svg
    width="36"
    height="36"
    viewBox="0 0 48 48"
    fill="none"
    aria-hidden="true"
    className="shrink-0"
  >
    <defs>
      <radialGradient id="orbitCore" cx="35%" cy="30%">
        <stop offset="0%" stopColor="#E0FBFF" />
        <stop offset="55%" stopColor="#00F0FF" />
        <stop offset="100%" stopColor="#6366F1" />
      </radialGradient>
      <linearGradient id="orbitRing" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.95" />
        <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.85" />
      </linearGradient>
    </defs>
    <circle
      cx="24"
      cy="24"
      r="9"
      fill="url(#orbitCore)"
      style={{ filter: "drop-shadow(0 0 8px rgba(0,240,255,0.75))" }}
    />
    <ellipse
      cx="24"
      cy="24"
      rx="20"
      ry="8"
      stroke="url(#orbitRing)"
      strokeWidth="1.6"
      fill="none"
      className="origin-center animate-orbit-slow"
    />
    <ellipse
      cx="24"
      cy="24"
      rx="15"
      ry="15"
      stroke="rgba(56,189,248,0.45)"
      strokeWidth="1"
      fill="none"
      className="origin-center animate-orbit-rev"
      strokeDasharray="4 6"
    />
    <circle cx="44" cy="24" r="1.8" fill="#00E676" />
  </svg>
);

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onSelectScreen,
}) => {
  const renderItem = (item: NavItem, compact = false) => {
    const Icon = item.icon;
    const isActive = currentScreen === item.id;
    return (
      <button
        key={item.id}
        type="button"
        onClick={() => onSelectScreen(item.id)}
        aria-current={isActive ? "page" : undefined}
        className={[
          "group relative flex w-full items-center gap-2.5 rounded-lg transition-all duration-200",
          compact
            ? "px-2.5 py-1.5 text-[11px]"
            : "px-3 py-2 text-[13px]",
          isActive
            ? "bg-gradient-to-r from-sky-500/35 via-sky-500/12 to-transparent font-semibold text-white shadow-glow-blue"
            : "text-slate-400 hover:bg-sky-500/8 hover:text-sky-200",
        ].join(" ")}
      >
        {isActive && (
          <span
            aria-hidden="true"
            className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r bg-neon-cyan shadow-glow-cyan"
          />
        )}
        <Icon
          size={compact ? 13 : 16}
          className={isActive ? "text-neon-cyan" : "text-slate-500 group-hover:text-sky-300"}
          aria-hidden="true"
        />
        <span className="truncate tracking-wide">{item.label}</span>
      </button>
    );
  };

  return (
    <aside
      className="flex h-screen w-[248px] shrink-0 flex-col border-r border-sky-500/15 bg-[#070C1A]/85 backdrop-blur-xl"
      role="navigation"
      aria-label="Cockpit navigation"
    >
      {/* Brand header */}
      <div className="flex items-center gap-2.5 border-b border-sky-500/15 px-4 py-4">
        <OrbitMark />
        <div className="min-w-0">
          <p className="font-display text-[13px] font-bold tracking-[0.13em] text-slate-100">
            AI AGENT TRADING
          </p>
          <p className="mt-0.5 text-[9px] font-medium tracking-[0.18em] text-neon-cyan/80">
            TRADE SMARTER. LIVE FREER.
          </p>
        </div>
      </div>

      {/* Primary cockpit stations */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-3 no-scrollbar">
        <div className="space-y-0.5">{PRIMARY_NAV.map((item) => renderItem(item))}</div>

        <div className="my-3 h-px bg-gradient-to-r from-transparent via-sky-500/25 to-transparent" />

        <p className="px-2.5 pb-1.5 text-[9px] font-semibold tracking-[0.22em] text-slate-600">
          MORE STATIONS
        </p>
        <div className="space-y-0.5">
          {SECONDARY_NAV.map((item) => renderItem(item, true))}
        </div>
      </nav>

      {/* Footer quote */}
      <div className="border-t border-sky-500/15 px-4 py-3.5">
        <p className="font-display text-[10px] font-semibold tracking-[0.2em] text-slate-300 neon-text-cyan">
          DISCIPLINE COMPOUNDS
        </p>
        <p className="font-display text-[10px] font-semibold tracking-[0.2em] text-neon-cyan">
          FREEDOM.
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
