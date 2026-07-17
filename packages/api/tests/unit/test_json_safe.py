"""json_safe helper tests."""
from datetime import date
from decimal import Decimal
import math

from quant_lab_api.utils.json_safe import json_safe


def test_json_safe_date():
    assert json_safe(date(2024, 1, 2)) == "2024-01-02"


def test_json_safe_decimal():
    assert json_safe(Decimal("1.5")) == 1.5


def test_json_safe_inf_to_none():
    assert json_safe(math.inf) is None
    assert json_safe(-math.inf) is None
    assert json_safe(math.nan) is None


def test_json_safe_nested():
    out = json_safe({"d": date(2024, 6, 1), "xs": [Decimal("2")]})
    assert out == {"d": "2024-06-01", "xs": [2.0]}
