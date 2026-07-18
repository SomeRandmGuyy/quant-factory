"""Benchmark equity curves and excess return helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

import pandas as pd


def excess_return(strategy_values: list[float], benchmark_values: list[float]) -> float:
    """Total return of strategy minus total return of benchmark."""
    if len(strategy_values) < 2 or len(benchmark_values) < 2:
        return 0.0
    if strategy_values[0] == 0 or benchmark_values[0] == 0:
        return 0.0
    s = strategy_values[-1] / strategy_values[0] - 1.0
    b = benchmark_values[-1] / benchmark_values[0] - 1.0
    return s - b


def total_return(values: list[float]) -> float:
    if len(values) < 2 or values[0] == 0:
        return 0.0
    return values[-1] / values[0] - 1.0


def buy_and_hold_equity(
    prices: pd.DataFrame,
    initial_capital: float,
) -> list[dict]:
    """
    Build a buy-and-hold equity curve from OHLCV rows for a single ticker.

    Expects columns: date, close (sorted ascending).
    """
    if prices is None or prices.empty:
        return []

    df = prices.sort_values("date").copy()
    first_close = float(df.iloc[0]["close"])
    if first_close <= 0:
        return []

    shares = initial_capital / first_close
    curve: list[dict] = []
    for _, row in df.iterrows():
        d = row["date"]
        if hasattr(d, "isoformat"):
            d_out = d
        else:
            d_out = d
        value = shares * float(row["close"])
        curve.append({"date": d_out, "total_value": value})
    return curve


def align_equity_on_dates(
    strategy_snaps: list[dict],
    benchmark_snaps: list[dict],
) -> tuple[list[float], list[float], list]:
    """Inner-join strategy and benchmark snapshots by date."""
    s_map = {}
    for s in strategy_snaps:
        d = s["date"]
        key = d.isoformat() if hasattr(d, "isoformat") else str(d)
        s_map[key] = float(s["total_value"])

    b_map = {}
    for b in benchmark_snaps:
        d = b["date"]
        key = d.isoformat() if hasattr(d, "isoformat") else str(d)
        b_map[key] = float(b["total_value"])

    keys = sorted(set(s_map) & set(b_map))
    return (
        [s_map[k] for k in keys],
        [b_map[k] for k in keys],
        keys,
    )
