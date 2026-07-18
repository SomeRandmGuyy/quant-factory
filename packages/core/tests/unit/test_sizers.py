from decimal import Decimal
import pandas as pd
import numpy as np
from quant_lab.portfolio.sizing import (
    PercentEquitySizer,
    VolatilityTargetSizer,
    EqualWeightSizer,
    realized_vol_from_prices,
)


def test_percent_sizer_basic():
    s = PercentEquitySizer(0.1)
    q = s.size(equity=Decimal("100000"), price=Decimal("100"))
    assert q == Decimal("100")


def test_vol_target_scales_down_for_high_vol():
    s = VolatilityTargetSizer(target_annual_vol=0.10, max_pct=1.0)
    q_low = s.size(equity=Decimal("100000"), price=Decimal("100"), realized_vol=0.10)
    q_high = s.size(equity=Decimal("100000"), price=Decimal("100"), realized_vol=0.40)
    assert q_high < q_low


def test_vol_target_fallback_when_vol_missing():
    s = VolatilityTargetSizer(target_annual_vol=0.10, max_pct=0.2)
    q = s.size(equity=Decimal("100000"), price=Decimal("100"), realized_vol=None)
    assert q == Decimal("200")  # 20% of equity / 100


def test_equal_weight_splits_across_names():
    s = EqualWeightSizer(max_names=4, max_pct=1.0)
    q = s.size(equity=Decimal("100000"), price=Decimal("100"), n_targets=4)
    assert q == Decimal("250")  # 25%


def test_realized_vol_from_prices_positive():
    closes = 100 * np.cumprod(1 + np.random.default_rng(0).normal(0, 0.01, 30))
    df = pd.DataFrame({"close": closes})
    vol = realized_vol_from_prices(df, window=20)
    assert vol is not None and vol > 0
