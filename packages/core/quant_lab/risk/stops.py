"""Engine-level stop-loss, take-profit, and time stops."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from quant_lab.models.signal import Signal, SignalAction
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.position import PositionSide
from quant_lab.portfolio.trade import Trade, TradeAction


@dataclass
class StopConfig:
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    time_stop_days: int | None = None

    @property
    def enabled(self) -> bool:
        return any(
            x is not None
            for x in (self.stop_loss_pct, self.take_profit_pct, self.time_stop_days)
        )


@dataclass
class PositionEntry:
    ticker: str
    side: str
    entry_price: Decimal
    entry_date: date
    quantity: Decimal


class StopManager:
    def __init__(self, config: StopConfig | None = None):
        self.config = config or StopConfig()
        self.entries: dict[str, PositionEntry] = {}

    def on_fill(self, trade: Trade, fill_date: date) -> None:
        ticker = trade.ticker.upper()
        action = trade.action.value if hasattr(trade.action, "value") else str(trade.action)
        if action in ("buy", "short"):
            side = "long" if action == "buy" else "short"
            existing = self.entries.get(ticker)
            if existing and existing.side == side:
                # average entry
                new_qty = existing.quantity + trade.quantity
                avg = (
                    existing.entry_price * existing.quantity + trade.price * trade.quantity
                ) / new_qty
                self.entries[ticker] = PositionEntry(
                    ticker=ticker,
                    side=side,
                    entry_price=avg,
                    entry_date=existing.entry_date,
                    quantity=new_qty,
                )
            else:
                self.entries[ticker] = PositionEntry(
                    ticker=ticker,
                    side=side,
                    entry_price=trade.price,
                    entry_date=fill_date,
                    quantity=trade.quantity,
                )
        elif action in ("sell", "cover"):
            if ticker in self.entries:
                ent = self.entries[ticker]
                remaining = ent.quantity - trade.quantity
                if remaining <= 0:
                    del self.entries[ticker]
                else:
                    self.entries[ticker] = PositionEntry(
                        ticker=ent.ticker,
                        side=ent.side,
                        entry_price=ent.entry_price,
                        entry_date=ent.entry_date,
                        quantity=remaining,
                    )

    def evaluate(
        self,
        portfolio: Portfolio,
        prices: dict[str, Decimal],
        current_date: date,
    ) -> list[Signal]:
        if not self.config.enabled:
            return []

        signals: list[Signal] = []
        for ticker, entry in list(self.entries.items()):
            pos = portfolio.get_position(ticker)
            if not pos or ticker not in prices:
                continue
            price = prices[ticker]
            entry_px = entry.entry_price
            if entry_px <= 0:
                continue

            if entry.side == "long":
                ret = float((price - entry_px) / entry_px)
                action = SignalAction.SELL
            else:
                ret = float((entry_px - price) / entry_px)  # profit if price down
                action = SignalAction.COVER

            hit = False
            reason = ""
            if self.config.stop_loss_pct is not None and ret <= -abs(self.config.stop_loss_pct):
                hit = True
                reason = f"stop_loss ({ret:.2%})"
            if self.config.take_profit_pct is not None and ret >= abs(self.config.take_profit_pct):
                hit = True
                reason = f"take_profit ({ret:.2%})"
            if self.config.time_stop_days is not None:
                held = (current_date - entry.entry_date).days
                if held >= self.config.time_stop_days:
                    hit = True
                    reason = f"time_stop ({held}d)"

            if hit:
                signals.append(
                    Signal(
                        ticker=ticker,
                        action=action,
                        quantity=pos.quantity,
                        confidence=1.0,
                        reasoning=reason,
                        metadata={"engine_stop": 1},
                    )
                )
        return signals
