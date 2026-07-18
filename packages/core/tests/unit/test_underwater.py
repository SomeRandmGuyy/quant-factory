from quant_lab.backtesting.metrics import underwater_series


def test_underwater_zero_on_monotone_up():
    dd = underwater_series([100, 110, 120])
    assert all(abs(x) < 1e-12 for x in dd)


def test_underwater_negative_after_drop():
    dd = underwater_series([100, 120, 90])
    assert dd[-1] < 0
    assert abs(dd[-1] - (90 / 120 - 1)) < 1e-9
