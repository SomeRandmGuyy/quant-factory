"""Position sizing helpers and pluggable sizers."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Protocol

import numpy as np
import pandas as pd


def size_by_percent(
    portfolio_value: Decimal | float | int,
    price: Decimal | float | int,
    pct: Decimal | float = Decimal("0.20"),
    quantize: Decimal = Decimal("0.00000001"),
) -> Decimal:
    """Size a position as a fraction of portfolio equity."""
    equity = Decimal(str(portfolio_value))
    px = Decimal(str(price))
    fraction = Decimal(str(pct))

    if equity <= 0:
        raise ValueError("portfolio_value must be positive")
    if px <= 0:
        raise ValueError("price must be positive")
    if fraction <= 0:
        return Decimal("0")

    notional = equity * fraction
    qty = (notional / px).quantize(quantize, rounding=ROUND_DOWN)
    return qty if qty > 0 else Decimal("0")


def realized_vol_from_prices(
    prices: pd.DataFrame,
    window: int = 20,
    bars_per_year: int = 252,
) -> float | None:
    """Annualized realized vol from close column."""
    if prices is None or len(prices) < 3:
        return None
    closes = prices["close"].astype(float).values
    if len(closes) < 3:
        return None
    rets = np.diff(closes) / closes[:-1]
    if len(rets) == 0:
        return None
    # use last `window` returns if available
    rets = rets[-window:] if len(rets) >= window else rets
    if len(rets) < 2:
        return None
    vol = float(np.std(rets, ddof=1)) * float(np.sqrt(bars_per_year))
    return vol if vol > 0 else None


class PositionSizer(Protocol):
    def size(
        self,
        *,
        equity: Decimal,
        price: Decimal,
        realized_vol: float | None = None,
        n_targets: int = 1,
        **kwargs,
    ) -> Decimal: ...


class PercentEquitySizer:
    def __init__(self, pct: float = 0.20):
        self.pct = pct

    def size(
        self,
        *,
        equity: Decimal,
        price: Decimal,
        realized_vol: float | None = None,
        n_targets: int = 1,
        **kwargs,
    ) -> Decimal:
        return size_by_percent(equity, price, self.pct)


class VolatilityTargetSizer:
    def __init__(
        self,
        target_annual_vol: float = 0.10,
        bars_per_year: int = 252,
        max_pct: float = 0.25,
    ):
        self.target_annual_vol = target_annual_vol
        self.bars_per_year = bars_per_year
        self.max_pct = max_pct

    def size(
        self,
        *,
        equity: Decimal,
        price: Decimal,
        realized_vol: float | None = None,
        n_targets: int = 1,
        **kwargs,
    ) -> Decimal:
        if realized_vol is None or realized_vol <= 0:
            return size_by_percent(equity, price, self.max_pct)
        # dollar risk budget = equity * target_vol
        # position notional = budget / realized_vol
        scale = self.target_annual_vol / realized_vol
        pct = min(self.max_pct, scale)
        return size_by_percent(equity, price, pct)


class EqualWeightSizer:
    def __init__(self, max_names: int = 5, max_pct: float = 0.5):
        self.max_names = max_names
        self.max_pct = max_pct

    def size(
        self,
        *,
        equity: Decimal,
        price: Decimal,
        realized_vol: float | None = None,
        n_targets: int = 1,
        **kwargs,
    ) -> Decimal:
        n = max(int(n_targets), 1)
        n = min(n, self.max_names)
        pct = min(self.max_pct, 1.0 / n)
        return size_by_percent(equity, price, pct)


def make_sizer(
    name: str = "percent",
    *,
    max_position_pct: float = 0.20,
    target_vol: float = 0.10,
    max_names: int = 5,
) -> PositionSizer:
    key = (name or "percent").lower()
    if key == "vol_target":
        return VolatilityTargetSizer(target_annual_vol=target_vol, max_pct=max_position_pct)
    if key == "equal_weight":
        return EqualWeightSizer(max_names=max_names, max_pct=max_position_pct)
    return PercentEquitySizer(pct=max_position_pct)


def resolve_size(
    sizer: PositionSizer | None,
    equity: Decimal,
    price: Decimal,
    *,
    max_position_pct: float = 0.20,
    realized_vol: float | None = None,
    n_targets: int = 1,
) -> Decimal:
    s = sizer or PercentEquitySizer(max_position_pct)
    return s.size(
        equity=equity,
        price=price,
        realized_vol=realized_vol,
        n_targets=n_targets,
    )
