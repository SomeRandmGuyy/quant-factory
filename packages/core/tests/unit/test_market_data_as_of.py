"""Point-in-time MarketData filtering."""
from datetime import date


def test_as_of_excludes_future_bars(sample_market_data):
    mid = sorted(sample_market_data.prices["date"].unique())[10]
    pit = sample_market_data.as_of(mid)
    assert pit.prices["date"].max() <= mid
    assert len(pit.prices) < len(sample_market_data.prices)
