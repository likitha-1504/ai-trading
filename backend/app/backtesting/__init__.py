"""Event-driven backtesting, paper trading, and performance analytics package."""

from app.backtesting.journal import TradeJournal
from app.backtesting.metrics import PerformanceCalculator
from app.backtesting.paper_loop import PaperTradingLoop
from app.backtesting.simulator import BacktestEngine, TimestampOrderError
from app.backtesting.slippage_analysis import SlippageSensitivityAnalyzer
from app.backtesting.walk_forward import WalkForwardAnalyzer

__all__ = [
    "BacktestEngine",
    "PaperTradingLoop",
    "PerformanceCalculator",
    "SlippageSensitivityAnalyzer",
    "TimestampOrderError",
    "TradeJournal",
    "WalkForwardAnalyzer",
]
