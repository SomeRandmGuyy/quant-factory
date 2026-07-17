"""Position sizing helpers."""
from decimal import Decimal

from quant_lab.portfolio.sizing import size_by_percent


def test_size_by_percent_returns_decimal():
    q = size_by_percent(Decimal("100000"), Decimal("333.33"), Decimal("0.1"))
    assert isinstance(q, Decimal)
    assert q > 0


def test_size_by_percent_zero_on_non_positive_pct():
    assert size_by_percent(1000, 10, 0) == Decimal("0")


def test_size_by_percent_rejects_bad_price():
    try:
        size_by_percent(1000, 0, 0.1)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
