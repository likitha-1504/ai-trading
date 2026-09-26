"""Phase 30 Advanced Market Intelligence Package.

Exports:
- Trend and Regime Detection
- Volatility Regime and Squeeze Analysis
- Sector Context and Mansfield Relative Strength
- Cross-Sectional Market Breadth
- Unified Point-in-Time Advanced Market Intelligence Engine
- Regime-Conditioned Backtesting Evaluator
"""

from app.market_intelligence.backtest_evaluator import (
    RegimeBacktestEvaluator,
    SimulatedTrade,
)
from app.market_intelligence.intelligence_engine import (
    AdvancedMarketIntelligenceEngine,
)
from app.market_intelligence.market_breadth import BreadthAnalyzer
from app.market_intelligence.models import (
    AdvancedMarketIntelligenceSnapshot,
    BreadthRegime,
    MarketBreadthSummary,
    MarketIntelligenceAction,
    RegimeBacktestMetric,
    RegimeBacktestSummary,
    RegimeClassification,
    SectorContextSummary,
    SectorPerformance,
    TrendRegime,
    VolatilityClassification,
    VolatilityState,
)
from app.market_intelligence.regime_detector import RegimeDetector
from app.market_intelligence.sector_context import NSE_SECTOR_MAP, SectorAnalyzer
from app.market_intelligence.volatility_regime import VolatilityAnalyzer

__all__ = [
    "NSE_SECTOR_MAP",
    "AdvancedMarketIntelligenceEngine",
    "AdvancedMarketIntelligenceSnapshot",
    "BreadthAnalyzer",
    "BreadthRegime",
    "MarketBreadthSummary",
    "MarketIntelligenceAction",
    "RegimeBacktestEvaluator",
    "RegimeBacktestMetric",
    "RegimeBacktestSummary",
    "RegimeClassification",
    "RegimeDetector",
    "SectorAnalyzer",
    "SectorContextSummary",
    "SectorPerformance",
    "SimulatedTrade",
    "TrendRegime",
    "VolatilityAnalyzer",
    "VolatilityClassification",
    "VolatilityState",
]
