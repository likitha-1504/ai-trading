import { useState, useEffect } from "react";
import { ScreenId, CapitalState, PositionItem, CandidateItem, MarketScannerItem, OrderItem, AIAnalysisRecord, TradeRecordItem, PerformanceStats, SystemHealthData, LogEntry } from "./types";
import { api } from "./services/api";
import { TopBar } from "./components/layout/TopBar";
import { NavBar } from "./components/layout/NavBar";
import { StatusBar } from "./components/layout/StatusBar";
import { KillSwitchModal } from "./components/layout/KillSwitchModal";

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

  return (
    <div className="min-h-screen bg-[#0B0E14] text-[#F1F5F9] flex flex-col font-sans selection:bg-purple-900/40 selection:text-purple-200">
      {/* Top Header */}
      <TopBar
        capital={capital}
        onOpenKillSwitch={() => setIsKillSwitchOpen(true)}
        isHalted={isHalted}
      />

      {/* Global Tab Navigation (All 15 Screens) */}
      <NavBar
        currentScreen={currentScreen}
        onSelectScreen={(screen) => setCurrentScreen(screen)}
      />

      {/* Active Screen View */}
      <main className="flex-1 p-4 pb-14 max-w-[1600px] w-full mx-auto">
        {currentScreen === "command" && (
          <CommandCenter
            capital={capital}
            positions={positions}
            candidates={candidates}
            logs={logs}
            onNavigate={(screen) => setCurrentScreen(screen)}
          />
        )}

        {currentScreen === "scanner" && (
          <MarketScanner
            scannerData={scannerData}
            onSelectSymbol={handleInspectSymbol}
          />
        )}

        {currentScreen === "candidates" && (
          <CandidateFeed
            candidates={candidates}
            onInspectAI={handleInspectCandidateAI}
          />
        )}

        {currentScreen === "chart" && (
          <TradingChart selectedSymbol={selectedSymbol} />
        )}

        {currentScreen === "positions" && (
          <PositionMonitor
            positions={positions}
            onManualClose={handleManualSquareOff}
          />
        )}

        {currentScreen === "orders" && (
          <OrdersExecution orders={orders} />
        )}

        {currentScreen === "ai" && (
          <AIAnalysis analysis={aiAnalysis} />
        )}

        {currentScreen === "journal" && (
          <TradeJournal trades={trades} />
        )}

        {currentScreen === "performance" && (
          <PerformanceAnalytics performance={performance} />
        )}

        {currentScreen === "backtesting" && (
          <Backtesting />
        )}

        {currentScreen === "risk" && (
          <RiskCapital capital={capital} />
        )}

        {currentScreen === "health" && (
          <SystemHealth health={health} />
        )}

        {currentScreen === "logs" && (
          <LogsEvents logs={logs} />
        )}

        {currentScreen === "strategies" && (
          <StrategyManagement />
        )}

        {currentScreen === "settings" && (
          <Settings />
        )}
      </main>

      {/* Persistent Bottom Status Bar */}
      <StatusBar health={health} />

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
