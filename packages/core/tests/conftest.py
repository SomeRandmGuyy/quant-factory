"""Core test fixtures."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from quant_lab.models.market_data import MarketData, Fundamentals

FIXTURES = Path(__file__).parent / "fixtures" / "sample_prices"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def sample_prices_df(fixtures_dir: Path) -> pd.DataFrame:
    frames = []
    for ticker in ("AAPL", "MSFT"):
        df = pd.read_csv(fixtures_dir / f"{ticker}.csv")
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ticker"] = ticker
        for col in ("open", "high", "low", "close"):
            df[col] = df[col].apply(lambda x: Decimal(str(x)))
        frames.append(df[["ticker", "date", "open", "high", "low", "close", "volume"]])
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def sample_market_data(sample_prices_df: pd.DataFrame, fixtures_dir: Path) -> MarketData:
    fund_df = pd.read_csv(fixtures_dir / "fundamentals.csv")
    fundamentals = {}
    for _, row in fund_df.iterrows():
        t = str(row["ticker"]).upper()
        fundamentals[t] = Fundamentals(
            ticker=t,
            market_cap=Decimal(str(row["market_cap"])),
            pe_ratio=float(row["pe_ratio"]),
            revenue=Decimal(str(row["revenue"])),
            net_income=Decimal(str(row["net_income"])),
            total_assets=Decimal(str(row["total_assets"])),
            total_liabilities=Decimal(str(row["total_liabilities"])),
            free_cash_flow=Decimal(str(row["free_cash_flow"])),
            roe=float(row["roe"]),
            roic=float(row["roic"]),
            debt_to_equity=float(row["debt_to_equity"]),
            current_ratio=float(row["current_ratio"]),
            revenue_growth=float(row["revenue_growth"]),
            earnings_growth=float(row["earnings_growth"]),
        )
    dates = sorted(sample_prices_df["date"].unique())
    return MarketData(
        tickers=["AAPL", "MSFT"],
        start_date=dates[0],
        end_date=dates[-1],
        prices=sample_prices_df,
        fundamentals=fundamentals,
    )
