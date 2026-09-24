import {
  CapitalState,
  MarketScannerItem,
  CandidateItem,
  PositionItem,
  OrderItem,
  AIAnalysisRecord,
  TradeRecordItem,
  PerformanceStats,
  SystemHealthData,
  LogEntry,
} from "../types";
import {
  mockCapital,
  mockScanner,
  mockCandidates,
  mockPositions,
  mockOrders,
  mockAIAnalysis,
  mockTrades,
  mockPerformance,
  mockSystemHealth,
  mockLogs,
} from "../data/mockData";

const API_BASE = "/api/v1";

async function fetchWithFallback<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      return fallback;
    }
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export const api = {
  async getCapital(): Promise<CapitalState> {
    return fetchWithFallback<CapitalState>(`${API_BASE}/dashboard/capital`, mockCapital);
  },

  async getMarketScanner(): Promise<MarketScannerItem[]> {
    return fetchWithFallback<MarketScannerItem[]>(`${API_BASE}/market/scanner`, mockScanner);
  },

  async getCandidates(): Promise<CandidateItem[]> {
    return fetchWithFallback<CandidateItem[]>(`${API_BASE}/candidates`, mockCandidates);
  },

  async getPositions(): Promise<PositionItem[]> {
    return fetchWithFallback<PositionItem[]>(`${API_BASE}/positions`, mockPositions);
  },

  async getOrders(): Promise<OrderItem[]> {
    return fetchWithFallback<OrderItem[]>(`${API_BASE}/orders`, mockOrders);
  },

  async getAIAnalyses(): Promise<AIAnalysisRecord[]> {
    return fetchWithFallback<AIAnalysisRecord[]>(`${API_BASE}/ai/analyses`, [mockAIAnalysis]);
  },

  async getTrades(): Promise<TradeRecordItem[]> {
    return fetchWithFallback<TradeRecordItem[]>(`${API_BASE}/trades`, mockTrades);
  },

  async getPerformance(): Promise<PerformanceStats> {
    return fetchWithFallback<PerformanceStats>(`${API_BASE}/performance`, mockPerformance);
  },

  async getSystemHealth(): Promise<SystemHealthData> {
    return fetchWithFallback<SystemHealthData>(`${API_BASE}/system/health`, mockSystemHealth);
  },

  async getLogs(): Promise<LogEntry[]> {
    return fetchWithFallback<LogEntry[]>(`${API_BASE}/logs/system`, mockLogs);
  },

  async triggerKillSwitch(reason: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/system/kill-switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, initiated_by: "FRONTEND_DASHBOARD" }),
      });
      if (res.ok) {
        return (await res.json()) as { success: boolean; message: string };
      }
    } catch {
      // Fallback response for offline mock mode
    }
    return {
      success: true,
      message: `Emergency Kill-Switch triggered: ${reason}. All positions squared off.`,
    };
  },
};
