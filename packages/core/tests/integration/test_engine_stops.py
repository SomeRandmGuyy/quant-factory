import pytest
from datetime import date
from decimal import Decimal
import pandas as pd

from quant_lab.models.market_data import MarketData
from quant_lab.models.signal import Signal, SignalAction
from quant_lab.backtesting.engine import BacktestEngine, BacktestConfig
from quant_lab.risk.stops import StopConfig


class BuyOnceStrategy:
    name = "BuyOnce"
    description = "test"
    def __init__(self):
        self.done = False

    def generate_signals(self, market_data, portfolio, current_date):
        if self.done or portfolio.get_position(market_data.tickers[0]):
            return []
        self.done = True
        return [Signal(ticker=market_data.tickers[0], action=SignalAction.BUY, quantity=Decimal("10"), confidence=1.0)]


@pytest.mark.asyncio
async def test_engine_stop_loss_flattens_position():
    dates = [date(2024, 1, 2 + i) for i in range(6)]
    # skip weekends roughly - use sequential weekdays
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5), date(2024, 1, 8), date(2024, 1, 9)]
    closes = [100, 100, 95, 90, 88, 88]
    rows = []
    for d, c in zip(dates, closes):
        rows.append({
            "ticker": "X", "date": d,
            "open": Decimal(str(c)), "high": Decimal(str(c)), "low": Decimal(str(c)),
            "close": Decimal(str(c)), "volume": 1_000_000,
        })
    md = MarketData(tickers=["X"], start_date=dates[0], end_date=dates[-1], prices=pd.DataFrame(rows), fundamentals={})
    cfg = BacktestConfig(
        initial_capital=100_000,
        rebalance_frequency=1,
        commission_bps=0,
        slippage_bps=0,
        enable_risk_gate=False,
        stop_config=StopConfig(stop_loss_pct=0.10),
    )
    engine = BacktestEngine(BuyOnceStrategy(), md, cfg)
    results = await engine.run()
    # should have closed via stop
    assert results.portfolio.get_position("X") is None
    assert any(t.is_closing for t in results.executed_trades)
