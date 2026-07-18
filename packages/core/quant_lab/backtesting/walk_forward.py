"""Walk-forward / out-of-sample split generation and runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Literal, Optional

from quant_lab.backtesting.engine import BacktestConfig, BacktestEngine
from quant_lab.models.market_data import MarketData
from quant_lab.strategies.protocols import Strategy


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: date
    train_end: date
    test_start: date
    test_end: date


def generate_splits(
    start: date,
    end: date,
    *,
    train_days: int,
    test_days: int,
    step_days: int,
    mode: Literal["rolling", "expanding"] = "rolling",
) -> list[WalkForwardSplit]:
    """
    Generate walk-forward folds using calendar days.

    Rolling: train window fixed length sliding forward.
    Expanding: train_start fixed at ``start``, train_end grows.
    Test window is always immediately after train_end.
    """
    if train_days <= 0 or test_days <= 0 or step_days <= 0:
        raise ValueError("train_days, test_days, and step_days must be positive")
    if start >= end:
        raise ValueError("start must be before end")

    splits: list[WalkForwardSplit] = []

    if mode == "rolling":
        train_start = start
        while True:
            train_end = train_start + timedelta(days=train_days - 1)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_days - 1)
            if test_end > end:
                break
            splits.append(
                WalkForwardSplit(train_start, train_end, test_start, test_end)
            )
            train_start = train_start + timedelta(days=step_days)
    elif mode == "expanding":
        # first fold needs at least train_days of history
        train_end = start + timedelta(days=train_days - 1)
        while True:
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_days - 1)
            if test_end > end:
                break
            splits.append(
                WalkForwardSplit(start, train_end, test_start, test_end)
            )
            train_end = train_end + timedelta(days=step_days)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return splits


def _slice_market_data(market_data: MarketData, start: date, end: date) -> MarketData:
    prices = market_data.prices
    mask = (prices["date"] >= start) & (prices["date"] <= end)
    sliced = prices.loc[mask].copy()
    return MarketData(
        tickers=market_data.tickers,
        start_date=start,
        end_date=end,
        prices=sliced,
        fundamentals=market_data.fundamentals,
    )


class WalkForwardRunner:
    """Run backtests on each OOS test window (capital reset per fold)."""

    def __init__(
        self,
        strategy: Strategy,
        market_data: MarketData,
        config: Optional[BacktestConfig] = None,
        max_folds: int = 50,
    ):
        self.strategy = strategy
        self.market_data = market_data
        self.config = config or BacktestConfig()
        self.max_folds = max_folds

    async def run(
        self,
        train_days: int = 60,
        test_days: int = 20,
        step_days: int = 20,
        mode: Literal["rolling", "expanding"] = "rolling",
    ) -> dict:
        splits = generate_splits(
            self.market_data.start_date,
            self.market_data.end_date,
            train_days=train_days,
            test_days=test_days,
            step_days=step_days,
            mode=mode,
        )
        if not splits:
            raise ValueError(
                "No walk-forward folds fit the date range; "
                "reduce train/test days or expand the period"
            )
        splits = splits[: self.max_folds]

        folds: list[dict] = []
        oos_returns: list[float] = []
        oos_sharpes: list[float] = []

        for split in splits:
            test_data = _slice_market_data(
                self.market_data, split.test_start, split.test_end
            )
            if test_data.prices.empty:
                continue

            engine = BacktestEngine(
                strategy=self.strategy,
                market_data=test_data,
                config=self.config,
            )
            results = await engine.run()
            metrics = results.metrics
            folds.append(
                {
                    "train_start": split.train_start.isoformat(),
                    "train_end": split.train_end.isoformat(),
                    "test_start": split.test_start.isoformat(),
                    "test_end": split.test_end.isoformat(),
                    "metrics": {
                        "total_return": metrics.get("total_return"),
                        "sharpe_ratio": metrics.get("sharpe_ratio"),
                        "max_drawdown": metrics.get("max_drawdown"),
                        "final_value": metrics.get("final_value"),
                    },
                    "num_trades": results.num_trades,
                }
            )
            if metrics.get("total_return") is not None:
                oos_returns.append(float(metrics["total_return"]))
            sharpe = metrics.get("sharpe_ratio")
            if sharpe is not None:
                oos_sharpes.append(float(sharpe))

        aggregate = {
            "n_folds": len(folds),
            "oos_total_return_mean": mean(oos_returns) if oos_returns else 0.0,
            "oos_total_return_std": pstdev(oos_returns) if len(oos_returns) > 1 else 0.0,
            "oos_sharpe_mean": mean(oos_sharpes) if oos_sharpes else 0.0,
        }

        return {
            "strategy_name": getattr(self.strategy, "name", "unknown"),
            "tickers": list(self.market_data.tickers),
            "mode": mode,
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "folds": folds,
            "aggregate": aggregate,
        }
