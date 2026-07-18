import pytest
from decimal import Decimal
from datetime import date
import pandas as pd

from quant_lab.models.market_data import MarketData
from quant_lab.models.signal import Signal, SignalAction
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.backtesting.engine import BacktestEngine, BacktestConfig
from quant_lab.backtesting.results import BacktestResults
from quant_lab.portfolio.trade import Trade, TradeAction


class BuyThenSellStrategy:
    name = "BuyThenSell"
    description = "test"
    def __init__(self):
        self.calls = 0

    def generate_signals(self, market_data, portfolio, current_date):
        self.calls += 1
        ticker = market_data.tickers[0]
        prices = market_data.get_prices(ticker)
        prices = prices[prices["date"] <= current_date]
        if prices.empty:
            return []
        px = prices.iloc[-1]["close"]
        if portfolio.get_position(ticker) is None and self.calls == 1:
            return [Signal(ticker=ticker, action=SignalAction.BUY, quantity=Decimal("10"), confidence=1.0)]
        if portfolio.get_position(ticker) is not None and self.calls >= 3:
            pos = portfolio.get_position(ticker)
            return [Signal(ticker=ticker, action=SignalAction.SELL, quantity=pos.quantity, confidence=1.0)]
        return []


@pytest.mark.asyncio
async def test_executed_closing_trade_has_realized_pnl_metadata():
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
    rows = []
    closes = [100, 100, 110, 110]
    for d, c in zip(dates, closes):
        rows.append({
            "ticker": "X", "date": d, "open": Decimal(str(c)), "high": Decimal(str(c)),
            "low": Decimal(str(c)), "close": Decimal(str(c)), "volume": 1_000_000,
        })
    md = MarketData(
        tickers=["X"], start_date=dates[0], end_date=dates[-1],
        prices=pd.DataFrame(rows), fundamentals={},
    )
    engine = BacktestEngine(BuyThenSellStrategy(), md, BacktestConfig(initial_capital=100_000, rebalance_frequency=1, commission_bps=0, slippage_bps=0, impact_bps=0))
    results = await engine.run()
    closing = [t for t in results.executed_trades if t.is_closing]
    assert closing, results.executed_trades
    assert "realized_pnl" in closing[0].metadata
    assert closing[0].metadata["realized_pnl"] == pytest.approx(100.0)


def test_results_win_rate_uses_per_trade_pnl():
    trades = [
        Trade(ticker="A", action=TradeAction.SELL, quantity=1, price=10, metadata={"realized_pnl": 10}),
        Trade(ticker="B", action=TradeAction.SELL, quantity=1, price=10, metadata={"realized_pnl": 5}),
        Trade(ticker="C", action=TradeAction.SELL, quantity=1, price=10, metadata={"realized_pnl": -3}),
    ]
    snaps = [{"date": date(2024, 1, 2), "total_value": 100.0, "cash": 100, "positions_value": 0, "num_positions": 0, "realized_pnl": 0, "unrealized_pnl": 0},
             {"date": date(2024, 1, 3), "total_value": 112.0, "cash": 112, "positions_value": 0, "num_positions": 0, "realized_pnl": 12, "unrealized_pnl": 0}]
    p = Portfolio.create(100)
    res = BacktestResults("t", date(2024,1,2), date(2024,1,3), 100, 112, snaps, trades, p)
    assert res.metrics["win_rate"] == pytest.approx(2 / 3)
