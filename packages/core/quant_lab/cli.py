"""Command-line interface for Quant Factory core backtests."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from quant_lab.data.csv_provider import CSVDataProvider
from quant_lab.data.yahoo_provider import YahooFinanceProvider
from quant_lab.models.market_data import MarketData
from quant_lab.backtesting import BacktestEngine, BacktestConfig, WalkForwardRunner
from quant_lab.backtesting.benchmark import (
    buy_and_hold_equity,
    align_equity_on_dates,
    excess_return,
    total_return,
)
from quant_lab.strategies import (
    ValueMoatStrategy,
    TrendFollowingStrategy,
    MultiFactorStrategy,
)

STRATEGIES = {
    "value_moat": ValueMoatStrategy,
    "trend_following": TrendFollowingStrategy,
    "multi_factor": MultiFactorStrategy,
}


def _provider(name: str, data_dir: str | None, fundamentals: str | None):
    if name == "yahoo":
        return YahooFinanceProvider()
    if not data_dir:
        raise SystemExit("--data-dir required for csv provider")
    fund = fundamentals or str(Path(data_dir) / "fundamentals.csv")
    return CSVDataProvider(data_dir, fund)


async def _load_market(provider, tickers, start, end) -> MarketData:
    prices = await provider.fetch_prices(tickers, start, end)
    funds = await provider.fetch_fundamentals(tickers)
    return MarketData(
        tickers=tickers,
        start_date=start,
        end_date=end,
        prices=prices,
        fundamentals=funds,
    )


async def cmd_backtest(args: argparse.Namespace) -> int:
    provider = _provider(args.provider, args.data_dir, args.fundamentals)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    strategy_cls = STRATEGIES.get(args.strategy)
    if not strategy_cls:
        raise SystemExit(f"Unknown strategy: {args.strategy}")

    load_tickers = list(tickers)
    if args.benchmark:
        load_tickers.append(args.benchmark.upper())

    market = await _load_market(provider, load_tickers, start, end)
    # strategy only on requested tickers
    strat_market = MarketData(
        tickers=tickers,
        start_date=start,
        end_date=end,
        prices=market.prices[market.prices["ticker"].isin(tickers)].copy(),
        fundamentals={k: v for k, v in market.fundamentals.items() if k in tickers},
    )

    config = BacktestConfig(
        initial_capital=args.capital,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        impact_bps=args.impact_bps,
        rebalance_frequency=args.rebalance,
    )
    engine = BacktestEngine(strategy_cls(), strat_market, config)
    results = await engine.run()
    out = {
        "strategy_name": results.strategy_name,
        "metrics": results.metrics,
        "num_trades": results.num_trades,
        "final_value": results.final_value,
    }

    if args.benchmark:
        bdf = market.get_prices(args.benchmark.upper())
        bdf = bdf[(bdf["date"] >= start) & (bdf["date"] <= end)]
        bench = buy_and_hold_equity(bdf, args.capital)
        s_vals, b_vals, _ = align_equity_on_dates(results.daily_snapshots, bench)
        out["metrics"] = dict(out["metrics"])
        out["metrics"]["benchmark_ticker"] = args.benchmark.upper()
        out["metrics"]["benchmark_return"] = total_return(b_vals)
        out["metrics"]["excess_return"] = excess_return(s_vals, b_vals)

    text = json.dumps(out, indent=2, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text)
        print(f"Wrote {args.json_out}")
    else:
        print(text)
    return 0


async def cmd_walk_forward(args: argparse.Namespace) -> int:
    provider = _provider(args.provider, args.data_dir, args.fundamentals)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    strategy_cls = STRATEGIES.get(args.strategy)
    if not strategy_cls:
        raise SystemExit(f"Unknown strategy: {args.strategy}")

    market = await _load_market(provider, tickers, start, end)
    config = BacktestConfig(
        initial_capital=args.capital,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        impact_bps=args.impact_bps,
        rebalance_frequency=args.rebalance,
    )
    runner = WalkForwardRunner(strategy_cls(), market, config)
    report = await runner.run(
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        mode=args.mode,
    )
    text = json.dumps(report, indent=2, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text)
        print(f"Wrote {args.json_out}")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quant_lab", description="Quant Factory CLI")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--strategy", required=True, choices=list(STRATEGIES))
        sp.add_argument("--tickers", required=True, help="Comma-separated tickers")
        sp.add_argument("--start", required=True, help="YYYY-MM-DD")
        sp.add_argument("--end", required=True, help="YYYY-MM-DD")
        sp.add_argument("--provider", default="csv", choices=["csv", "yahoo"])
        sp.add_argument("--data-dir", default=None)
        sp.add_argument("--fundamentals", default=None)
        sp.add_argument("--capital", type=float, default=100_000)
        sp.add_argument("--commission-bps", type=float, default=5.0)
        sp.add_argument("--slippage-bps", type=float, default=2.0)
        sp.add_argument("--impact-bps", type=float, default=0.0)
        sp.add_argument("--rebalance", type=int, default=5)
        sp.add_argument("--json-out", default=None)

    bt = sub.add_parser("backtest", help="Run a single backtest")
    add_common(bt)
    bt.add_argument("--benchmark", default=None)
    bt.set_defaults(func=lambda a: asyncio.run(cmd_backtest(a)))

    wf = sub.add_parser("walk-forward", help="Run walk-forward OOS evaluation")
    add_common(wf)
    wf.add_argument("--train-days", type=int, default=60)
    wf.add_argument("--test-days", type=int, default=20)
    wf.add_argument("--step-days", type=int, default=20)
    wf.add_argument("--mode", default="rolling", choices=["rolling", "expanding"])
    wf.set_defaults(func=lambda a: asyncio.run(cmd_walk_forward(a)))

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
