from decimal import Decimal
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction


def test_long_round_trip_realized_pnl():
    p = Portfolio.create(10_000)
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100"))
    )
    p = p.update_prices({"X": Decimal("110")})
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.SELL, quantity=Decimal("10"), price=Decimal("110"))
    )
    assert p.realized_pnl == Decimal("100")


def test_short_round_trip_realized_pnl():
    p = Portfolio.create(10_000)
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.SHORT, quantity=Decimal("5"), price=Decimal("100"))
    )
    p = p.update_prices({"X": Decimal("90")})
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.COVER, quantity=Decimal("5"), price=Decimal("90"))
    )
    assert p.realized_pnl == Decimal("50")
