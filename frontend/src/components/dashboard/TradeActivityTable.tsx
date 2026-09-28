import React, { useState } from "react";
import { ArrowUpRight, Eye } from "lucide-react";
import { PositionItem, OrderItem, CandidateItem, ScreenId } from "../../types";

type TabId = "ai" | "positions" | "orders" | "watchlist";

interface TradeActivityTableProps {
  positions: PositionItem[];
  orders: OrderItem[];
  candidates: CandidateItem[];
  onNavigate: (screen: ScreenId) => void;
}

const TABS: { id: TabId; label: string }[] = [
  { id: "ai", label: "AI TRADE ACTIVITY" },
  { id: "positions", label: "OPEN POSITIONS" },
  { id: "orders", label: "PENDING ORDERS" },
  { id: "watchlist", label: "WATCHLIST" },
];

const SIDE_PILL: Record<string, string> = {
  BUY: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  SELL: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  WATCH: "bg-slate-500/15 text-slate-300 border-slate-500/40",
};

const STATUS_BADGE: Record<string, string> = {
  FILLED: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40",
  FILLED_PARTIAL: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
  WATCHING: "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40",
  WATCHLIST: "bg-slate-500/15 text-slate-300 border border-slate-500/40",
};

const reasonFor = (c: CandidateItem): string => {
  const base = c.strategy_type === "MOMENTUM_CONTINUATION"
    ? "Momentum continuation confirmed above VWAP with expanding relative volume."
    : "Early-move detection flagged a pre-breakout volume signature.";
  return `${base} Rank ${c.rank_score.toFixed(1)} · Expected net edge ${c.expected_net_edge.toFixed(2)}% after Indian friction.`;
};

export const TradeActivityTable: React.FC<TradeActivityTableProps> = ({
  positions,
  orders,
  candidates,
  onNavigate,
}) => {
  const [tab, setTab] = useState<TabId>("ai");

  const openOrders = orders.filter(
    (o) => o.status !== "FILLED" && o.status !== "CANCELLED" && o.status !== "REJECTED",
  );

  return (
    <section className="glass-panel rounded-xl" aria-label="AI trade activity">
      <div className="flex flex-wrap items-center gap-1 border-b border-sky-500/12 px-3 py-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            aria-pressed={tab === t.id}
            className={`rounded px-2.5 py-1.5 text-[10px] font-semibold tracking-[0.12em] transition-colors ${
              tab === t.id
                ? "bg-sky-500/20 text-sky-100 shadow-glow-blue"
                : "text-slate-500 hover:bg-sky-500/8 hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => onNavigate(tab === "ai" ? "candidates" : "orders")}
          className="flex items-center gap-1 text-[10px] text-sky-400 transition-colors hover:text-sky-200"
        >
          View All <ArrowUpRight size={11} aria-hidden="true" />
        </button>
      </div>

      <div className="max-h-[290px] overflow-y-auto">
        {tab === "ai" &&
          (candidates.length === 0 ? (
            <EmptyRow label="No AI-reviewed candidates in the current session." />
          ) : (
            <table className="w-full text-left text-[11px]">
              <thead className="sticky top-0 bg-[#0B1124]/95 backdrop-blur">
                <tr className="text-slate-500">
                  <Th>Symbol</Th>
                  <Th>Action</Th>
                  <Th>AI Reasoning</Th>
                  <Th align="right">Target</Th>
                  <Th align="right">P&amp;L</Th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => {
                  const edge = c.expected_net_edge;
                  const isWatch = c.status === "DETECTED" || c.status === "IN_AI_REVIEW";
                  return (
                    <tr
                      key={c.candidate_id}
                      className="border-t border-sky-500/8 transition-colors hover:bg-sky-500/5"
                    >
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => onNavigate("chart")}
                          className="font-mono font-semibold text-slate-100 hover:text-neon-cyan"
                        >
                          {c.symbol}
                        </button>
                        <p className="font-mono text-[9px] text-slate-600">
                          Rank {c.rank_score.toFixed(1)}
                        </p>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-block rounded-full border px-2 py-0.5 text-[9px] font-bold tracking-wider ${
                            isWatch ? SIDE_PILL.WATCH : SIDE_PILL.BUY
                          }`}
                        >
                          {isWatch ? "WATCH" : "BUY"}
                        </span>
                      </td>
                      <td className="max-w-[260px] px-3 py-2 text-slate-400">
                        <span className="line-clamp-2">{reasonFor(c)}</span>
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                        {c.take_profit_price.toFixed(2)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-mono font-semibold tabular-nums ${
                          edge >= 0 ? "text-emerald-300" : "text-rose-300"
                        }`}
                      >
                        {edge >= 0 ? "+" : ""}
                        {edge.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ))}

        {tab === "positions" &&
          (positions.length === 0 ? (
            <EmptyRow label="No open positions. Position Watcher is idling." />
          ) : (
            <table className="w-full text-left text-[11px]">
              <thead className="sticky top-0 bg-[#0B1124]/95 backdrop-blur">
                <tr className="text-slate-500">
                  <Th>Symbol</Th>
                  <Th>Side</Th>
                  <Th>Status</Th>
                  <Th align="right">Entry</Th>
                  <Th align="right">LTP</Th>
                  <Th align="right">P&amp;L</Th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr
                    key={p.position_id}
                    className="border-t border-sky-500/8 transition-colors hover:bg-sky-500/5"
                  >
                    <td className="px-3 py-2 font-mono font-semibold text-slate-100">
                      {p.symbol}
                      <span className="ml-1.5 text-[9px] text-slate-600">x{p.quantity}</span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full border px-2 py-0.5 text-[9px] font-bold tracking-wider ${
                          p.side === "BUY" ? SIDE_PILL.BUY : SIDE_PILL.SELL
                        }`}
                      >
                        {p.side}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-[9px] font-semibold ${
                          p.watcher_status === "TRIGGERED"
                            ? STATUS_BADGE.WATCHING
                            : STATUS_BADGE.FILLED
                        }`}
                      >
                        {p.watcher_status === "TRIGGERED" ? "WATCHING" : "FILLED"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                      {p.entry_price.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                      {p.current_price.toFixed(2)}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono font-semibold tabular-nums ${
                        p.unrealized_pnl >= 0 ? "text-emerald-300" : "text-rose-300"
                      }`}
                    >
                      {p.unrealized_pnl >= 0 ? "+" : ""}
                      {p.unrealized_pnl.toFixed(2)} ({p.unrealized_pnl_pct.toFixed(2)}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

        {tab === "orders" &&
          (openOrders.length === 0 ? (
            <EmptyRow label="No pending orders in the execution queue." />
          ) : (
            <table className="w-full text-left text-[11px]">
              <thead className="sticky top-0 bg-[#0B1124]/95 backdrop-blur">
                <tr className="text-slate-500">
                  <Th>Symbol</Th>
                  <Th>Side</Th>
                  <Th>Type</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">Price</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {openOrders.map((o) => (
                  <tr
                    key={o.client_order_id}
                    className="border-t border-sky-500/8 transition-colors hover:bg-sky-500/5"
                  >
                    <td className="px-3 py-2 font-mono font-semibold text-slate-100">
                      {o.symbol}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full border px-2 py-0.5 text-[9px] font-bold tracking-wider ${
                          o.side === "BUY" ? SIDE_PILL.BUY : SIDE_PILL.SELL
                        }`}
                      >
                        {o.side}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-slate-400">{o.order_type}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                      {o.quantity}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                      {o.price !== undefined ? o.price.toFixed(2) : "MKT"}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-block rounded bg-amber-500/15 px-2 py-0.5 text-[9px] font-semibold text-amber-300">
                        {o.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

        {tab === "watchlist" &&
          (candidates.length === 0 ? (
            <EmptyRow label="Watchlist is empty." />
          ) : (
            <table className="w-full text-left text-[11px]">
              <thead className="sticky top-0 bg-[#0B1124]/95 backdrop-blur">
                <tr className="text-slate-500">
                  <Th>Symbol</Th>
                  <Th>State</Th>
                  <Th>Strategy</Th>
                  <Th align="right">Trigger</Th>
                  <Th align="right">Hard Stop</Th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr
                    key={c.candidate_id}
                    className="border-t border-sky-500/8 transition-colors hover:bg-sky-500/5"
                  >
                    <td className="px-3 py-2 font-mono font-semibold text-slate-100">
                      {c.symbol}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1 rounded bg-slate-500/15 px-2 py-0.5 text-[9px] font-semibold text-slate-300">
                        <Eye size={9} aria-hidden="true" /> WATCHING
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-slate-400">
                      {c.strategy_type === "MOMENTUM_CONTINUATION" ? "MOMENTUM" : "EARLY-MOVE"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-300">
                      {c.trigger_price.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-rose-300/90">
                      {c.hard_stop_price.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
      </div>
    </section>
  );
};

const Th: React.FC<{ children: React.ReactNode; align?: "right" }> = ({
  children,
  align = "left",
}) => (
  <th
    className={`px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.14em] ${
      align === "right" ? "text-right" : "text-left"
    }`}
  >
    {children}
  </th>
);

const EmptyRow: React.FC<{ label: string }> = ({ label }) => (
  <p className="px-4 py-8 text-center font-mono text-[11px] text-slate-600">{label}</p>
);

export default TradeActivityTable;
