import pytest
from quant_lab.backtesting import WalkForwardRunner, BacktestConfig
from quant_lab.strategies.multi_factor import MultiFactorStrategy


@pytest.mark.asyncio
async def test_runner_returns_folds_and_aggregate(sample_market_data):
    runner = WalkForwardRunner(
        MultiFactorStrategy(),
        sample_market_data,
        BacktestConfig(initial_capital=100_000, rebalance_frequency=5),
    )
    report = await runner.run(train_days=10, test_days=5, step_days=5, mode="rolling")
    assert "folds" in report
    assert report["aggregate"]["n_folds"] >= 1
    assert "oos_total_return_mean" in report["aggregate"]
