"""Fractional position quantities."""
from decimal import Decimal

from quant_lab.portfolio.position import Position, PositionSide


def test_fractional_position_quantity():
    pos = Position(
        ticker="BTC-USD",
        side=PositionSide.LONG,
        quantity=Decimal("0.001"),
        avg_price=Decimal("60000"),
        current_price=Decimal("61000"),
    )
    assert pos.quantity == Decimal("0.001")
    assert pos.market_value == Decimal("0.001") * Decimal("61000")
