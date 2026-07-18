"""Portfolio risk limits and order gate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction


@dataclass
class RiskLimits:
    max_position_pct: float = 0.25
    max_gross_leverage: float = 2.0
    max_drawdown_halt: float = 0.30
    allow_reduce_when_halted: bool = True


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str = ""


class RiskGate:
    """Enforces position size, leverage, and drawdown halt policies."""

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self.peak_equity: Decimal | None = None

    def update_equity_peak(self, equity: Decimal) -> None:
        eq = Decimal(str(equity))
        if self.peak_equity is None or eq > self.peak_equity:
            self.peak_equity = eq

    def current_drawdown(self, equity: Decimal) -> float:
        eq = Decimal(str(equity))
        if not self.peak_equity or self.peak_equity <= 0:
            return 0.0
        dd = float((eq - self.peak_equity) / self.peak_equity)
        return min(0.0, dd)

    def is_halted(self, equity: Decimal) -> bool:
        dd = abs(self.current_drawdown(equity))
        return dd >= self.limits.max_drawdown_halt

    def _is_reducing(self, trade: Trade) -> bool:
        return trade.action in (TradeAction.SELL, TradeAction.COVER, "sell", "cover")

    def check_portfolio_state(self, portfolio: Portfolio) -> GateDecision:
        equity = portfolio.total_value
        if self.is_halted(equity):
            return GateDecision(
                False,
                f"drawdown_halt: dd={abs(self.current_drawdown(equity)):.2%} "
                f">= {self.limits.max_drawdown_halt:.2%}",
            )
        return GateDecision(True)

    def check_order(
        self,
        portfolio: Portfolio,
        trade: Trade,
        equity: Decimal | None = None,
    ) -> GateDecision:
        eq = Decimal(str(equity if equity is not None else portfolio.total_value))
        if eq <= 0:
            return GateDecision(False, "non_positive_equity")

        reducing = self._is_reducing(trade)
        if self.is_halted(eq):
            if reducing and self.limits.allow_reduce_when_halted:
                return GateDecision(True)
            return GateDecision(False, "drawdown_halt_blocks_new_risk")

        notional = Decimal(str(trade.quantity)) * Decimal(str(trade.price))
        # projected single-name weight after trade (approx using trade notional)
        ticker = trade.ticker.upper()
        existing = portfolio.get_position(ticker)
        existing_val = Decimal("0")
        if existing:
            existing_val = existing.market_value

        if trade.action in (TradeAction.BUY, TradeAction.SHORT, "buy", "short"):
            projected = existing_val + notional
        else:
            projected = max(Decimal("0"), existing_val - notional)

        weight = float(projected / eq) if eq else 0.0
        if weight > self.limits.max_position_pct + 1e-9 and not reducing:
            return GateDecision(
                False,
                f"max_position: weight={weight:.2%} > {self.limits.max_position_pct:.2%}",
            )

        # gross leverage after trade (approx)
        long_exp = portfolio.long_exposure
        short_exp = portfolio.short_exposure
        if trade.action in (TradeAction.BUY, "buy"):
            long_exp = long_exp + notional
        elif trade.action in (TradeAction.SHORT, "short"):
            short_exp = short_exp + notional
        elif trade.action in (TradeAction.SELL, "sell"):
            long_exp = max(Decimal("0"), long_exp - notional)
        elif trade.action in (TradeAction.COVER, "cover"):
            short_exp = max(Decimal("0"), short_exp - notional)

        gross = float((long_exp + short_exp) / eq) if eq else 0.0
        if gross > self.limits.max_gross_leverage + 1e-9 and not reducing:
            return GateDecision(
                False,
                f"max_gross_leverage: {gross:.2f} > {self.limits.max_gross_leverage:.2f}",
            )

        return GateDecision(True)
