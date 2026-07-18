"""Backtesting engine and performance metrics."""

from quant_lab.backtesting.engine import BacktestEngine, BacktestConfig
from quant_lab.backtesting.metrics import (
    PerformanceMetrics,
    excess_return,
    historical_var,
    historical_cvar,
    underwater_series,
)
from quant_lab.backtesting.results import BacktestResults
from quant_lab.backtesting.costs import SimpleCostModel, CostResult
from quant_lab.backtesting.walk_forward import WalkForwardRunner, WalkForwardSplit, generate_splits
from quant_lab.backtesting.benchmark import (
    buy_and_hold_equity,
    align_equity_on_dates,
    total_return,
)

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "PerformanceMetrics",
    "BacktestResults",
    "SimpleCostModel",
    "CostResult",
    "WalkForwardRunner",
    "WalkForwardSplit",
    "generate_splits",
    "buy_and_hold_equity",
    "align_equity_on_dates",
    "excess_return",
    "total_return",
    "historical_var",
    "historical_cvar",
    "underwater_series",
]
