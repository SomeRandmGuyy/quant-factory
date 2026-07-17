"""Yahoo provider network test (skipped offline)."""
from datetime import date

import pytest

from quant_lab.data.yahoo_provider import YahooFinanceProvider


@pytest.mark.network
@pytest.mark.asyncio
async def test_yahoo_fetch_prices_columns():
    p = YahooFinanceProvider()
    df = await p.fetch_prices(["AAPL"], date(2024, 1, 2), date(2024, 1, 31))
    assert set(df.columns) >= {"ticker", "date", "open", "high", "low", "close", "volume"}
    assert len(df) > 0
