"""Portfolio buy/sell invariants."""
from decimal import Decimal

from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction


def test_buy_reduces_cash_and_opens_long():
    p = Portfolio.create(100_000)
    trade = Trade(
        ticker="AAPL",
        action=TradeAction.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        fees=Decimal("1"),
        slippage=Decimal("0"),
    )
    p2 = p.apply_trade(trade)
    assert p2.cash == Decimal("100000") - Decimal("1001")
    pos = p2.get_position("AAPL")
    assert pos is not None
    assert pos.quantity == Decimal("10")


def test_cannot_buy_with_insufficient_cash():
    p = Portfolio.create(100)
    trade = Trade(
        ticker="AAPL",
        action=TradeAction.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
    )
    try:
        p.apply_trade(trade)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "cash" in str(e).lower() or "Insufficient" in str(e)


def test_sell_realizes_pnl():
    p = Portfolio.create(10_000)
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.BUY, quantity=Decimal("10"), price=Decimal("100"))
    )
    p = p.update_prices({"X": Decimal("110")})
    p = p.apply_trade(
        Trade(ticker="X", action=TradeAction.SELL, quantity=Decimal("10"), price=Decimal("110"))
    )
    assert p.get_position("X") is None
    assert p.realized_pnl == Decimal("100")
