from datetime import date
from decimal import Decimal
import pandas as pd
from quant_lab.backtesting.benchmark import buy_and_hold_equity, total_return


def test_buy_and_hold_flat_prices():
    df = pd.DataFrame({
        "date": [date(2024, 1, 2), date(2024, 1, 3)],
        "close": [Decimal("100"), Decimal("100")],
    })
    curve = buy_and_hold_equity(df, 10_000)
    vals = [c["total_value"] for c in curve]
    assert abs(total_return(vals) - 0.0) < 1e-9


def test_buy_and_hold_up_10pct():
    df = pd.DataFrame({
        "date": [date(2024, 1, 2), date(2024, 1, 3)],
        "close": [Decimal("100"), Decimal("110")],
    })
    curve = buy_and_hold_equity(df, 10_000)
    vals = [c["total_value"] for c in curve]
    assert abs(total_return(vals) - 0.1) < 1e-9
