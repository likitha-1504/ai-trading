import { useState, useEffect, useCallback } from "react";
import {
  ScreenId,
  CapitalState,
  PositionItem,
  CandidateItem,
  MarketScannerItem,
  OrderItem,
  AIAnalysisRecord,
  TradeRecordItem,
  PerformanceStats,
  SystemHealthData,
  LogEntry,
} from "./types";
import { api } from "./services/api";
import { Sidebar } from "./components/layout/Sidebar";
import { TopNavHeader } from "./components/layout/TopNavHeader";
import { KillSwitchModal } from "./components/layout/KillSwitchModal";
import { AIAssistantBar } from "./components/dashboard/AIAssistantBar";

// 15 Screens
import { CommandCenter } from "./screens/CommandCenter";
import { MarketScanner } from "./screens/MarketScanner";
import { CandidateFeed } from "./screens/CandidateFeed";
import { TradingChart } from "./screens/TradingChart";
import { PositionMonitor } from "./screens/PositionMonitor";
import { OrdersExecution } from "./screens/OrdersExecution";
import { AIAnalysis } from "./screens/AIAnalysis";
import { TradeJournal } from "./screens/TradeJournal";
import { PerformanceAnalytics } from "./screens/PerformanceAnalytics";
import { Backtesting } from "./screens/Backtesting";
import { RiskCapital } from "./screens/RiskCapital";
import { SystemHealth } from "./screens/SystemHealth";
import { LogsEvents } from "./screens/LogsEvents";
import { StrategyManagement } from "./screens/StrategyManagement";
import { Settings } from "./screens/Settings";

// Initial mock data as fast defaults
import {
  mockCapital,
  mockPositions,
  mockCandidates,
  mockScanner,
  mockOrders,
  mockAIAnalysis,
  mockTrades,
  mockPerformance,
  mockSystemHealth,
  mockLogs,
} from "./data/mockData";

export function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>("command");
  const [capital, setCapital] = useState<CapitalState>(mockCapital);
  const [positions, setPositions] = useState<PositionItem[]>(mockPositions);
  const [candidates, setCandidates] = useState<CandidateItem[]>(mockCandidates);
  const [scannerData, setScannerData] = useState<MarketScannerItem[]>(mockScanner);
  const [orders, setOrders] = useState<OrderItem[]>(mockOrders);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisRecord>(mockAIAnalysis);
  const [trades, setTrades] = useState<TradeRecordItem[]>(mockTrades);
  const [performance, setPerformance] = useState<PerformanceStats>(mockPerformance);
  const [health, setHealth] = useState<SystemHealthData>(mockSystemHealth);
  const [logs, setLogs] = useState<LogEntry[]>(mockLogs);

  const [selectedSymbol, setSelectedSymbol] = useState<string>("INFY");
  const [isKillSwitchOpen, setIsKillSwitchOpen] = useState<boolean>(false);
  const [isHalted, setIsHalted] = useState<boolean>(false);
  const [isDark, setIsDark] = useState<boolean>(true);
  const [assistantNote, setAssistantNote] = useState<string | null>(null);

  // Poll backend/service with fallback
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const [
          capData,
          posData,
          candData,
          scanData,
          ordData,
          aiData,
          trdData,
          perfData,
          hltData,
          logData,
        ] = await Promise.all([
          api.getCapital(),
          api.getPositions(),
          api.getCandidates(),
          api.getMarketScanner(),
          api.getOrders(),
          api.getAIAnalyses(),
          api.getTrades(),
          api.getPerformance(),
          api.getSystemHealth(),
          api.getLogs(),
        ]);

        if (isMounted) {
          setCapital(capData);
          setPositions(posData);
          setCandidates(candData);
          setScannerData(scanData);
          setOrders(ordData);
          if (aiData.length > 0) setAiAnalysis(aiData[0]);
          setTrades(trdData);
          setPerformance(perfData);
          setHealth(hltData);
          setLogs(logData);
        }
      } catch (err) {
        console.error("Telemetry fetch error (using fallback):", err);
      }
    };

    loadData();
    const interval = setInterval(loadData, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Keep the OS/browser chrome in sync with the cockpit theme toggle.
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  useEffect(() => {
    if (!assistantNote) return;
    const timer = window.setTimeout(() => setAssistantNote(null), 6000);
    return () => window.clearTimeout(timer);
  }, [assistantNote]);

  const handleTriggerKillSwitch = async (reason: string) => {
    await api.triggerKillSwitch(reason);
    setIsHalted(true);
    setPositions([]);
  };

  const handleManualSquareOff = async (positionId: string) => {
    setPositions((prev) => prev.filter((p) => p.position_id !== positionId));
  };

  const handleInspectSymbol = (sym: string) => {
    setSelectedSymbol(sym);
    setCurrentScreen("chart");
  };

  const handleInspectCandidateAI = (_candidateId: string) => {
    setCurrentScreen("ai");
  };

  const handleNavigate = useCallback((screen: ScreenId) => {
    setCurrentScreen(screen);
  }, []);

  const handleAssistantSubmit = (prompt: string) => {
    setAssistantNote(prompt);
  };

  return (
    <div className="relative flex min-h-screen text-slate-100">
      {/* Decorative deep-space backdrop */}
      <div className="cosmic-backdrop" aria-hidden="true" />

      <Sidebar currentScreen={currentScreen} onSelectScreen={setCurrentScreen} />

      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <TopNavHeader
          onOpenKillSwitch={() => setIsKillSwitchOpen(true)}
          isHalted={isHalted}
          mode={health?.mode === "LIVE" ? "LIVE" : "PAPER"}
          isDark={isDark}
          onToggleTheme={() => setIsDark((d) => !d)}
          onNavigate={handleNavigate}
        />

        <main className="flex-1 px-5 pb-32 pt-4">
          {currentScreen === "command" && (
            <CommandCenter
              capital={capital}
              positions={positions}
              candidates={candidates}
              orders={orders}
              performance={performance}
              analysis={aiAnalysis}
              health={health}
              onNavigate={handleNavigate}
            />
          )}

          {currentScreen === "scanner" && (
            <MarketScanner scannerData={scannerData} onSelectSymbol={handleInspectSymbol} />
          )}

          {currentScreen === "candidates" && (
            <CandidateFeed candidates={candidates} onInspectAI={handleInspectCandidateAI} />
          )}

          {currentScreen === "chart" && <TradingChart selectedSymbol={selectedSymbol} />}

          {currentScreen === "positions" && (
            <PositionMonitor positions={positions} onManualClose={handleManualSquareOff} />
          )}

          {currentScreen === "orders" && <OrdersExecution orders={orders} />}

          {currentScreen === "ai" && <AIAnalysis analysis={aiAnalysis} />}

          {currentScreen === "journal" && <TradeJournal trades={trades} />}

          {currentScreen === "performance" && (
            <PerformanceAnalytics performance={performance} />
          )}

          {currentScreen === "backtesting" && <Backtesting />}

          {currentScreen === "risk" && <RiskCapital capital={capital} />}

          {currentScreen === "health" && <SystemHealth health={health} />}

          {currentScreen === "logs" && <LogsEvents logs={logs} />}

          {currentScreen === "strategies" && <StrategyManagement />}

          {currentScreen === "settings" && <Settings />}
        </main>

        {/* Floating AI assistant dock */}
        <AIAssistantBar onSubmit={handleAssistantSubmit} />
        <div aria-live="polite" className="sr-only">
          {assistantNote ? `AI assistant request: ${assistantNote}` : ""}
        </div>
      </div>

      {/* Astronaut cockpit silhouette + mission quote */}
      <div className="cockpit-plate" aria-hidden="true">
        <svg
          className="cockpit-plate__silhouette"
          viewBox="0 0 132 92"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="plate-fade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#0B132B" stopOpacity="0.1" />
            </linearGradient>
          </defs>
          {/* Helmet */}
          <circle cx="66" cy="30" r="17" stroke="url(#plate-fade)" strokeWidth="2" fill="#0B132B" fillOpacity="0.55" />
          <path d="M54 26a12 12 0 0 1 24 0" stroke="#00F0FF" strokeOpacity="0.6" strokeWidth="1.4" fill="none" />
          {/* Shoulders / torso */}
          <path
            d="M30 92c2-20 16-30 36-30s34 10 36 30"
            stroke="url(#plate-fade)"
            strokeWidth="2"
            fill="#0B132B"
            fillOpacity="0.5"
          />
          {/* Arm reaching to console */}
          <path d="M100 92c1-12-4-20-12-25" stroke="#38BDF8" strokeOpacity="0.45" strokeWidth="1.6" fill="none" />
          {/* Console edge */}
          <path d="M104 92h28" stroke="#00F0FF" strokeOpacity="0.5" strokeWidth="1.6" />
          <circle cx="118" cy="84" r="2" fill="#00E676" />
          <circle cx="126" cy="88" r="1.4" fill="#38BDF8" />
        </svg>
        <p className="cockpit-plate__quote">
          16:24:38
          <br />
          TRADES A BRIGHTER TOMORROW.
        </p>
      </div>

      {/* Kill-Switch Double Confirmation Modal */}
      <KillSwitchModal
        isOpen={isKillSwitchOpen}
        onClose={() => setIsKillSwitchOpen(false)}
        onConfirm={handleTriggerKillSwitch}
      />
    </div>
  );
}

export default App;
