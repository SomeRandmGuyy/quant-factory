import pytest
from datetime import date
from decimal import Decimal
import pandas as pd

from quant_lab.models.market_data import MarketData
from quant_lab.models.signal import Signal, SignalAction
from quant_lab.backtesting.engine import BacktestEngine, BacktestConfig
from quant_lab.risk.limits import RiskLimits


class OversizeBuyStrategy:
    name = "Oversize"
    description = "test"
    def generate_signals(self, market_data, portfolio, current_date):
        t = market_data.tickers[0]
        if portfolio.get_position(t):
            return []
        # try to buy 50% of equity at price 100 -> 500 shares on 100k = 50%
        return [Signal(ticker=t, action=SignalAction.BUY, quantity=Decimal("500"), confidence=1.0)]


@pytest.mark.asyncio
async def test_engine_rejects_oversize_when_gate_enabled():
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
    rows = []
    for d in dates:
        rows.append({
            "ticker": "X", "date": d,
            "open": Decimal("100"), "high": Decimal("100"), "low": Decimal("100"),
            "close": Decimal("100"), "volume": 1_000_000,
        })
    md = MarketData(tickers=["X"], start_date=dates[0], end_date=dates[-1], prices=pd.DataFrame(rows), fundamentals={})
    cfg = BacktestConfig(
        initial_capital=100_000,
        rebalance_frequency=1,
        commission_bps=0,
        enable_risk_gate=True,
        risk_limits=RiskLimits(max_position_pct=0.10, max_gross_leverage=5.0, max_drawdown_halt=0.9),
    )
    engine = BacktestEngine(OversizeBuyStrategy(), md, cfg)
    results = await engine.run()
    assert results.portfolio.get_position("X") is None
    assert len(engine.rejected_trades) >= 1
