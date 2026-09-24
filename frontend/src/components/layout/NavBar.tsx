import React from "react";
import {
  LayoutDashboard,
  Radar,
  Sparkles,
  CandlestickChart,
  Layers,
  ClipboardList,
  Cpu,
  BookOpen,
  TrendingUp,
  History,
  ShieldAlert,
  HeartPulse,
  Terminal,
  Sliders,
  Settings as SettingsIcon,
  LucideIcon,
} from "lucide-react";
import { ScreenId } from "../../types";

interface NavBarProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
}

interface NavItem {
  id: ScreenId;
  label: string;
  icon: LucideIcon;
  num: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "command", label: "Command", icon: LayoutDashboard, num: "1" },
  { id: "scanner", label: "Scanner", icon: Radar, num: "2" },
  { id: "candidates", label: "Candidates", icon: Sparkles, num: "3" },
  { id: "chart", label: "Chart", icon: CandlestickChart, num: "4" },
  { id: "positions", label: "Positions", icon: Layers, num: "5" },
  { id: "orders", label: "Orders", icon: ClipboardList, num: "6" },
  { id: "ai", label: "AI Council", icon: Cpu, num: "7" },
  { id: "journal", label: "Journal", icon: BookOpen, num: "8" },
  { id: "performance", label: "Performance", icon: TrendingUp, num: "9" },
  { id: "backtesting", label: "Backtest", icon: History, num: "10" },
  { id: "risk", label: "Risk & Cap", icon: ShieldAlert, num: "11" },
  { id: "health", label: "Health", icon: HeartPulse, num: "12" },
  { id: "logs", label: "Logs", icon: Terminal, num: "13" },
  { id: "strategies", label: "Strategies", icon: Sliders, num: "14" },
  { id: "settings", label: "Settings", icon: SettingsIcon, num: "15" },
];

export const NavBar: React.FC<NavBarProps> = ({
  currentScreen,
  onSelectScreen,
}) => {
  return (
    <nav className="flex items-center gap-1 px-4 py-2 bg-[#0B0E14] border-b border-[#222938] overflow-x-auto no-scrollbar">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = currentScreen === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelectScreen(item.id)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
              isActive
                ? "bg-[#1C2331] text-sky-400 font-semibold border border-sky-800/60 shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#151A23] border border-transparent"
            }`}
          >
            <span className="text-[10px] text-slate-500 font-normal">{item.num}.</span>
            <Icon size={14} className={isActive ? "text-sky-400" : "text-slate-400"} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
