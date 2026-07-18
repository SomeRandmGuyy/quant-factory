from datetime import date
from decimal import Decimal
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction
from quant_lab.risk.stops import StopConfig, StopManager


def test_stop_loss_long():
    p = Portfolio.create(100_000)
    p = p.apply_trade(Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")))
    p = p.update_prices({"X": Decimal("89")})
    sm = StopManager(StopConfig(stop_loss_pct=0.10))
    sm.on_fill(
        Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")),
        date(2024, 1, 2),
    )
    sigs = sm.evaluate(p, {"X": Decimal("89")}, date(2024, 1, 10))
    assert len(sigs) == 1
    action = sigs[0].action.value if hasattr(sigs[0].action, "value") else sigs[0].action
    assert action == "sell"


def test_take_profit_long():
    p = Portfolio.create(100_000)
    p = p.apply_trade(Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")))
    p = p.update_prices({"X": Decimal("112")})
    sm = StopManager(StopConfig(take_profit_pct=0.10))
    sm.on_fill(
        Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")),
        date(2024, 1, 2),
    )
    sigs = sm.evaluate(p, {"X": Decimal("112")}, date(2024, 1, 10))
    assert len(sigs) == 1


def test_time_stop():
    p = Portfolio.create(100_000)
    p = p.apply_trade(Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")))
    p = p.update_prices({"X": Decimal("100")})
    sm = StopManager(StopConfig(time_stop_days=5))
    sm.on_fill(
        Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100")),
        date(2024, 1, 2),
    )
    sigs = sm.evaluate(p, {"X": Decimal("100")}, date(2024, 1, 10))
    assert len(sigs) == 1
