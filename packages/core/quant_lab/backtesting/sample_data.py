"""
Generate sample CSV data for backtesting validation.

Creates realistic-looking price data for AAPL, MSFT, TSLA
covering ~6 months of trading days for testing.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path

# Default output: repo_root/data
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_DIR = _REPO_ROOT / "data"

# Set random seed for reproducibility
np.random.seed(42)

def generate_price_data(ticker, start_price, days=120, trend=0.001, volatility=0.02):
    """Generate synthetic OHLCV data with trend and noise."""
    dates = []
    current_date = date(2024, 1, 2)
    while len(dates) < days:
        if current_date.weekday() < 5:
            dates.append(current_date)
        current_date += timedelta(days=1)

    prices = [start_price]
    for i in range(1, days):
        daily_return = trend + volatility * np.random.randn()
        new_price = prices[-1] * (1 + daily_return)
        prices.append(max(new_price, 1.0))

    data = []
    for i, (d, close) in enumerate(zip(dates, prices)):
        open_price = close * (1 + np.random.uniform(-0.005, 0.005))
        high = close * (1 + abs(np.random.uniform(0, 0.015)))
        low = close * (1 - abs(np.random.uniform(0, 0.015)))
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        base_volume = 50000000
        volume = int(base_volume * (1 + np.random.uniform(-0.3, 0.5)))
        data.append({
            "date": d,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
        })
    return pd.DataFrame(data)


def write_sample_data(data_dir: Path | str | None = None) -> Path:
    """Write sample CSVs to data_dir (default: repo data/)."""
    out = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
    out.mkdir(parents=True, exist_ok=True)

    generate_price_data("AAPL", 150.0, trend=0.0015, volatility=0.018).to_csv(out / "AAPL.csv", index=False)
    generate_price_data("MSFT", 350.0, trend=0.0012, volatility=0.015).to_csv(out / "MSFT.csv", index=False)
    generate_price_data("TSLA", 200.0, trend=0.002, volatility=0.035).to_csv(out / "TSLA.csv", index=False)

    fundamentals = pd.DataFrame([
        {"ticker": "AAPL", "market_cap": 2800000000000, "pe_ratio": 28.5, "revenue": 394000000000,
         "net_income": 99800000000, "total_assets": 352000000000, "total_liabilities": 290000000000,
         "free_cash_flow": 99000000000, "roe": 0.28, "roic": 0.35, "debt_to_equity": 0.85,
         "current_ratio": 1.1, "revenue_growth": 0.11, "earnings_growth": 0.13},
        {"ticker": "MSFT", "market_cap": 2900000000000, "pe_ratio": 32.0, "revenue": 211000000000,
         "net_income": 72000000000, "total_assets": 411000000000, "total_liabilities": 198000000000,
         "free_cash_flow": 65000000000, "roe": 0.34, "roic": 0.28, "debt_to_equity": 0.45,
         "current_ratio": 1.8, "revenue_growth": 0.12, "earnings_growth": 0.15},
        {"ticker": "TSLA", "market_cap": 700000000000, "pe_ratio": 65.0, "revenue": 96000000000,
         "net_income": 12000000000, "total_assets": 106000000000, "total_liabilities": 43000000000,
         "free_cash_flow": 8000000000, "roe": 0.19, "roic": 0.15, "debt_to_equity": 0.15,
         "current_ratio": 1.5, "revenue_growth": 0.51, "earnings_growth": 0.42},
    ])
    fundamentals.to_csv(out / "fundamentals.csv", index=False)
    return out


if __name__ == "__main__":
    dest = write_sample_data()
    print(f"Sample data written to {dest}")
