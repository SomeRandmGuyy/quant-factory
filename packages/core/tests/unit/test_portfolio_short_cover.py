"""Short / cover portfolio paths."""
from decimal import Decimal

from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction
from quant_lab.portfolio.position import PositionSide


def test_short_opens_short_position():
    p = Portfolio.create(10_000)
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.SHORT, quantity=Decimal("5"), price=Decimal("100"))
    )
    pos = p.get_position("X")
    assert pos is not None
    assert pos.side == PositionSide.SHORT
    assert pos.quantity == Decimal("5")
    assert p.cash > Decimal("10000")


def test_cover_closes_short():
    p = Portfolio.create(10_000)
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.SHORT, quantity=Decimal("5"), price=Decimal("100"))
    )
    p = p.update_prices({"X": Decimal("90")})
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.COVER, quantity=Decimal("5"), price=Decimal("90"))
    )
    assert p.get_position("X") is None
    assert p.realized_pnl == Decimal("50")
