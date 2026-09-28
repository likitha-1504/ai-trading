import React, { useMemo } from "react";
import {
  CapitalState,
  PositionItem,
  CandidateItem,
  OrderItem,
  AIAnalysisRecord,
  PerformanceStats,
  SystemHealthData,
  ScreenId,
} from "../types";
import { CircularProgress } from "../components/ui/CircularProgress";
import { Sparkline, BarSparkline } from "../components/ui/Sparkline";
import { TradingChartWidget } from "../components/dashboard/TradingChartWidget";
import { TradeActivityTable } from "../components/dashboard/TradeActivityTable";
import { AIAnalysisWidget } from "../components/dashboard/AIAnalysisWidget";
import { AIDecisionWidget } from "../components/dashboard/AIDecisionWidget";
import { PortfolioWidget } from "../components/dashboard/PortfolioWidget";
import { SystemStatusWidget } from "../components/dashboard/SystemStatusWidget";

interface CommandCenterProps {
  capital: CapitalState;
  positions: PositionItem[];
  candidates: CandidateItem[];
  orders: OrderItem[];
  performance: PerformanceStats;
  analysis: AIAnalysisRecord;
  health: SystemHealthData;
  onNavigate: (screen: ScreenId) => void;
}

const COMPANY_NAMES: Record<string, string> = {
  RELIANCE: "Reliance Industries Ltd.",
  HDFCBANK: "HDFC Bank Ltd.",
  SBIN: "State Bank of India",
  INFY: "Infosys Ltd.",
  TCS: "Tata Consultancy Services",
  ICICIBANK: "ICICI Bank Ltd.",
};

const inr = (v: number, digits = 2): string =>
  new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(isFinite(v) ? v : 0);

/** Deterministic smooth wave series for the risk-adjusted return gauge. */
const waveSeries = (seedValue: number, count = 24): number[] =>
  Array.from({ length: count }, (_, i) => {
    const t = i / (count - 1);
    return (
      seedValue +
      Math.sin(t * Math.PI * 4) * 0.18 +
      Math.sin(t * Math.PI * 9 + 1.2) * 0.07 +
      t * 0.12
    );
  });

interface KpiShellProps {
  label: string;
  children: React.ReactNode;
  footer?: string;
}

const KpiShell: React.FC<KpiShellProps> = ({ label, children, footer }) => (
  <div className="glass-panel flex items-center justify-between gap-3 rounded-xl p-3.5">
    <div className="min-w-0 flex-1">
      <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
        {label}
      </p>
      {children}
      {footer && (
        <p className="mt-0.5 font-mono text-[9px] text-slate-600 tabular-nums">{footer}</p>
      )}
    </div>
  </div>
);

export const CommandCenter: React.FC<CommandCenterProps> = ({
  capital,
  positions,
  candidates,
  orders,
  performance,
  analysis,
  health,
  onNavigate,
}) => {
  const equity = capital?.total_equity ?? 0;
  const starting = capital?.starting_capital ?? 0;
  const realized = capital?.realized_pnl ?? 0;
  const openCount = positions?.length ?? 0;
  const winRate = performance?.win_rate_pct ?? 0;

  const capitalChangePct = starting > 0 ? ((equity - starting) / starting) * 100 : 0;
  const pnlChangePct = starting > 0 ? (realized / starting) * 100 : 0;

  const avgLoss = Math.abs(performance?.avg_loss ?? 0);
  const sharpe = useMemo(() => {
    const ratio = avgLoss > 0 ? (performance?.expectancy ?? 0) / avgLoss : 0;
    const n = Math.sqrt(Math.max(1, performance?.total_trades ?? 1));
    const win = (winRate || 0) / 100;
    return Number((ratio * win * n).toFixed(2));
  }, [avgLoss, performance, winRate]);

  const equitySeries = useMemo(() => {
    const base = starting > 0 ? starting : equity || 1;
    const drift = (equity || base) - base;
    return Array.from({ length: 24 }, (_, i) => {
      const t = i / 23;
      return base + drift * t + Math.sin(t * Math.PI * 3.4) * Math.abs(drift || base * 0.004) * 0.3;
    });
  }, [equity, starting]);

  const pnlSeries = useMemo(() => {
    const amp = Math.abs(realized) || 1;
    return Array.from({ length: 18 }, (_, i) =>
      realized + Math.sin(i / 2.1) * amp * 0.6 - (i / 17) * amp * 0.8,
    );
  }, [realized]);

  const focusCandidate = useMemo(() => {
    const live = candidates.find((c) => c.status === "PROMOTED") ?? candidates[0];
    return live;
  }, [candidates]);

  const focusPosition = positions?.[0];

  const focusSymbol = focusCandidate?.symbol ?? focusPosition?.symbol ?? "RELIANCE";
  const focusPrice =
    focusPosition?.current_price ?? focusCandidate?.take_profit_price ?? 0;
  const focusChange = focusPosition
    ? (focusPosition.unrealized_pnl_pct ?? 0)
    : focusCandidate?.expected_net_edge ?? 0.82;

  return (
    <div className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiShell
          label="Total Capital"
          footer={`Base ₹${inr(starting)} · Deployed ₹${inr(capital?.deployed_capital ?? 0)}`}
        >
          <div className="mt-1 flex items-end justify-between gap-2">
            <div>
              <p className="font-mono text-xl font-bold leading-none text-slate-50 tabular-nums">
                ₹{inr(equity)}
              </p>
              <p
                className={`mt-1 font-mono text-[11px] font-semibold tabular-nums ${
                  capitalChangePct >= 0 ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                {capitalChangePct >= 0 ? "+" : ""}
                {capitalChangePct.toFixed(2)}%
              </p>
            </div>
            <Sparkline data={equitySeries} width={92} height={38} color="#00E676" />
          </div>
        </KpiShell>

        <KpiShell label="Today's P&L" footer="Net of Indian friction">
          <div className="mt-1 flex items-end justify-between gap-2">
            <div>
              <p
                className={`font-mono text-xl font-bold leading-none tabular-nums ${
                  realized >= 0 ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                {realized >= 0 ? "+" : ""}₹{inr(Math.abs(realized))}
              </p>
              <p
                className={`mt-1 font-mono text-[11px] font-semibold tabular-nums ${
                  pnlChangePct >= 0 ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                {pnlChangePct >= 0 ? "+" : ""}
                {pnlChangePct.toFixed(2)}%
              </p>
            </div>
            <BarSparkline data={pnlSeries} width={92} height={38} color="#00E676" />
          </div>
        </KpiShell>

        <KpiShell
          label="Open Positions"
          footer={`Watcher ${health?.latencies?.position_watcher_ms ?? 0}ms`}
        >
          <div className="mt-1 flex items-center gap-3">
            <p className="font-mono text-xl font-bold leading-none text-slate-50 tabular-nums">
              {openCount}
            </p>
            <CircularProgress
              value={openCount}
              max={Math.max(5, openCount)}
              size={44}
              strokeWidth={5}
              color="#00F0FF"
              glowColor="#00F0FF"
              className="ml-auto"
            />
          </div>
        </KpiShell>

        <KpiShell
          label="Win Rate"
          footer={`${performance?.winning_trades ?? 0}W / ${performance?.losing_trades ?? 0}L of ${performance?.total_trades ?? 0}`}
        >
          <div className="mt-1 flex items-center gap-3">
            <p className="font-mono text-xl font-bold leading-none text-slate-50 tabular-nums">
              {winRate.toFixed(0)}%
            </p>
            <CircularProgress
              value={winRate}
              max={100}
              size={44}
              strokeWidth={5}
              color="#00E676"
              glowColor="#00E676"
              className="ml-auto"
            />
          </div>
        </KpiShell>

        <KpiShell
          label="Sharpe Ratio"
          footer="Expectancy ÷ avg loss, √n scaled"
        >
          <div className="mt-1 flex items-end justify-between gap-2">
            <p className="font-mono text-xl font-bold leading-none text-slate-50 tabular-nums">
              {sharpe.toFixed(2)}
            </p>
            <Sparkline
              data={waveSeries(sharpe, 24)}
              width={92}
              height={38}
              color="#8B5CF6"
            />
          </div>
        </KpiShell>
      </div>

      {/* Three-column command grid */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        {/* Column 1 — chart + activity table */}
        <div className="space-y-4 xl:col-span-6 2xl:col-span-6">
          <TradingChartWidget
            symbol={focusSymbol}
            companyName={COMPANY_NAMES[focusSymbol] ?? `${focusSymbol} Limited`}
            exchange="NSE"
            capClass="LARGE CAP"
            lastPrice={focusPrice}
            changePct={focusChange}
            onOpenFullChart={() => onNavigate("chart")}
          />

          <TradeActivityTable
            positions={positions}
            orders={orders}
            candidates={candidates}
            onNavigate={onNavigate}
          />
        </div>

        {/* Column 2 — AI analysis + AI decision */}
        <div className="space-y-4 xl:col-span-3 2xl:col-span-3">
          <AIAnalysisWidget analysis={analysis} onNavigate={onNavigate} />
          <AIDecisionWidget
            analysis={analysis}
            candidate={focusCandidate}
            position={focusPosition}
            onNavigateToOrders={() => onNavigate("orders")}
          />
        </div>

        {/* Column 3 — portfolio + system status */}
        <div className="space-y-4 xl:col-span-3 2xl:col-span-3">
          <PortfolioWidget
            capital={capital}
            positions={positions}
            onNavigate={onNavigate}
          />
          <SystemStatusWidget health={health} onNavigate={onNavigate} />
        </div>
      </div>
    </div>
  );
};

export default CommandCenter;
