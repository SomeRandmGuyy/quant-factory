from decimal import Decimal
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction
from quant_lab.risk.limits import RiskLimits, RiskGate


def test_blocks_order_over_max_position_pct():
    p = Portfolio.create(100_000)
    gate = RiskGate(RiskLimits(max_position_pct=0.2, max_gross_leverage=5.0))
    gate.update_equity_peak(p.total_value)
    trade = Trade(ticker="AAPL", action=TradeAction.BUY, quantity=Decimal("300"), price=Decimal("100"))
    # 300*100=30k = 30% > 20%
    d = gate.check_order(p, trade)
    assert d.allowed is False
    assert "max_position" in d.reason


def test_drawdown_halt_blocks_new_buys():
    p = Portfolio.create(100_000)
    gate = RiskGate(RiskLimits(max_drawdown_halt=0.10, max_position_pct=1.0, max_gross_leverage=10))
    gate.update_equity_peak(Decimal("100000"))
    # simulate equity drop
    # force peak high and current low by updating peak then checking with lower equity
    gate.peak_equity = Decimal("100000")
    trade = Trade(ticker="AAPL", action=TradeAction.BUY, quantity=Decimal("1"), price=Decimal("100"))
    # pass equity=80000 -> 20% DD
    d = gate.check_order(p, trade, equity=Decimal("80000"))
    assert d.allowed is False
    assert "drawdown" in d.reason


def test_drawdown_halt_allows_sells():
    p = Portfolio.create(100_000)
    # open a position first
    p = p.apply_trade(Trade(ticker="AAPL", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")))
    gate = RiskGate(RiskLimits(max_drawdown_halt=0.10, max_position_pct=1.0, max_gross_leverage=10))
    gate.peak_equity = Decimal("100000")
    sell = Trade(ticker="AAPL", action=TradeAction.SELL, quantity=Decimal("10"), price=Decimal("90"))
    d = gate.check_order(p, sell, equity=Decimal("80000"))
    assert d.allowed is True
