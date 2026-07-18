from decimal import Decimal
from quant_lab.backtesting.costs import SimpleCostModel


def test_commission_scales_with_notional():
    m = SimpleCostModel(commission_bps=10, impact_bps_per_participation=0)
    c1 = m.estimate(100_000)
    c2 = m.estimate(200_000)
    assert c2.commission == c1.commission * 2


def test_impact_zero_when_adv_missing():
    m = SimpleCostModel(commission_bps=5, impact_bps_per_participation=10)
    c = m.estimate(100_000, adv_notional=None)
    assert c.impact == 0


def test_impact_increases_with_participation():
    m = SimpleCostModel(commission_bps=0, impact_bps_per_participation=10)
    low = m.estimate(10_000, adv_notional=1_000_000)
    high = m.estimate(100_000, adv_notional=1_000_000)
    assert high.impact > low.impact
