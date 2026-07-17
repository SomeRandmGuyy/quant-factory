"""CSV provider offline load."""
import pytest
from datetime import date

from quant_lab.data.csv_provider import CSVDataProvider


@pytest.mark.asyncio
async def test_csv_provider_fetch_prices(fixtures_dir):
    p = CSVDataProvider(fixtures_dir, fixtures_dir / "fundamentals.csv")
    df = await p.fetch_prices(["AAPL", "MSFT"], date(2024, 1, 2), date(2024, 2, 29))
    assert set(df.columns) >= {"ticker", "date", "open", "high", "low", "close", "volume"}
    assert set(df["ticker"].unique()) == {"AAPL", "MSFT"}
    assert len(df) > 0


@pytest.mark.asyncio
async def test_csv_provider_fundamentals(fixtures_dir):
    p = CSVDataProvider(fixtures_dir, fixtures_dir / "fundamentals.csv")
    funds = await p.fetch_fundamentals(["AAPL"])
    assert "AAPL" in funds
    assert funds["AAPL"].roe is not None
