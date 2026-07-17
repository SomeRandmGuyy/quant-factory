"""Backtest engine smoke on fixture data."""
import pytest
from decimal import Decimal

from quant_lab.backtesting.engine import BacktestEngine, BacktestConfig
from quant_lab.strategies.multi_factor import MultiFactorStrategy


@pytest.mark.asyncio
async def test_engine_runs_and_returns_results(sample_market_data):
    engine = BacktestEngine(
        strategy=MultiFactorStrategy(),
        market_data=sample_market_data,
        config=BacktestConfig(initial_capital=100_000, rebalance_frequency=5),
    )
    results = await engine.run()
    assert results.final_value > 0
    assert len(results.daily_snapshots) > 0
    assert results.metrics["total_return"] is not None
