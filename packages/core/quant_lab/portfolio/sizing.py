"""Position sizing helpers (fractional quantities supported)."""

from decimal import Decimal, ROUND_DOWN


def size_by_percent(
    portfolio_value: Decimal | float | int,
    price: Decimal | float | int,
    pct: Decimal | float = Decimal("0.20"),
    quantize: Decimal = Decimal("0.00000001"),
) -> Decimal:
    """
    Size a position as a fraction of portfolio equity.

    Returns a non-negative Decimal quantity (fractional OK).
    Rounds down to ``quantize`` precision to avoid overspending.
    """
    equity = Decimal(str(portfolio_value))
    px = Decimal(str(price))
    fraction = Decimal(str(pct))

    if equity <= 0:
        raise ValueError("portfolio_value must be positive")
    if px <= 0:
        raise ValueError("price must be positive")
    if fraction <= 0:
        return Decimal("0")

    notional = equity * fraction
    qty = (notional / px).quantize(quantize, rounding=ROUND_DOWN)
    return qty if qty > 0 else Decimal("0")
