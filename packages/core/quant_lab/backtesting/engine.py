"""
Backtesting engine with event-driven simulation.

Key principles:
- Point-in-time data (no look-ahead bias)
- Realistic trade execution (fees / optional impact model)
- Per-closing-trade realized PnL in trade metadata
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from quant_lab.models.market_data import MarketData
from quant_lab.models.signal import Signal
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction, TradeBuilder
from quant_lab.strategies.protocols import Strategy
from quant_lab.backtesting.costs import SimpleCostModel


class BacktestConfig:
    """Configuration for backtesting."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_bps: float = 5.0,
        slippage_bps: float = 2.0,
        rebalance_frequency: int = 1,
        impact_bps: float = 0.0,
        cost_model: Optional[SimpleCostModel] = None,
    ):
        self.initial_capital = initial_capital
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        self.rebalance_frequency = rebalance_frequency
        self.impact_bps = impact_bps
        if cost_model is not None:
            self.cost_model = cost_model
        else:
            self.cost_model = SimpleCostModel(
                commission_bps=commission_bps,
                impact_bps_per_participation=impact_bps,
                slippage_bps=slippage_bps,
            )


class BacktestEngine:
    """Event-driven backtesting engine."""

    def __init__(
        self,
        strategy: Strategy,
        market_data: MarketData,
        config: Optional[BacktestConfig] = None,
    ):
        self.strategy = strategy
        self.market_data = market_data
        self.config = config or BacktestConfig()
        self.portfolio = Portfolio.create(
            initial_capital=Decimal(str(self.config.initial_capital))
        )
        self.daily_snapshots: list[dict] = []
        self.executed_trades: list[Trade] = []

    async def run(self) -> "BacktestResults":
        from quant_lab.backtesting.results import BacktestResults

        trading_days = self._get_trading_days()
        if not trading_days:
            raise ValueError("No trading days available in market data")

        for i, current_date in enumerate(trading_days):
            point_in_time_data = self.market_data.as_of(current_date)
            current_prices = self._get_current_prices(point_in_time_data, current_date)
            self.portfolio = self.portfolio.update_prices(current_prices)

            if i % self.config.rebalance_frequency == 0:
                signals = self.strategy.generate_signals(
                    market_data=point_in_time_data,
                    portfolio=self.portfolio,
                    current_date=current_date,
                )
                for signal in signals:
                    if not signal.is_actionable():
                        continue
                    trade = self._signal_to_trade(
                        signal, current_prices, point_in_time_data, current_date
                    )
                    if not trade:
                        continue
                    can_execute, _reason = self.portfolio.can_execute_trade(trade)
                    if not can_execute:
                        continue

                    before_realized = self.portfolio.realized_pnl
                    self.portfolio = self.portfolio.apply_trade(trade)
                    delta = self.portfolio.realized_pnl - before_realized
                    meta = dict(trade.metadata or {})
                    meta["realized_pnl"] = float(delta)
                    trade = trade.model_copy(update={"metadata": meta})
                    self.executed_trades.append(trade)

            self.daily_snapshots.append(
                {
                    "date": current_date,
                    "total_value": float(self.portfolio.total_value),
                    "cash": float(self.portfolio.cash),
                    "positions_value": float(
                        self.portfolio.long_exposure + self.portfolio.short_exposure
                    ),
                    "num_positions": len(self.portfolio.positions),
                    "realized_pnl": float(self.portfolio.realized_pnl),
                    "unrealized_pnl": float(self.portfolio.unrealized_pnl),
                }
            )

        return BacktestResults(
            strategy_name=self.strategy.name,
            start_date=trading_days[0],
            end_date=trading_days[-1],
            initial_capital=self.config.initial_capital,
            final_value=float(self.portfolio.total_value),
            daily_snapshots=self.daily_snapshots,
            executed_trades=self.executed_trades,
            portfolio=self.portfolio,
        )

    def _get_trading_days(self) -> list[date]:
        all_dates = set()
        for ticker in self.market_data.tickers:
            ticker_prices = self.market_data.get_prices(ticker)
            all_dates.update(ticker_prices["date"].tolist())
        return sorted(list(all_dates))

    def _get_current_prices(
        self,
        market_data: MarketData,
        current_date: date,
    ) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        for ticker in market_data.tickers:
            ticker_prices = market_data.get_prices(ticker)
            ticker_prices = ticker_prices[ticker_prices["date"] == current_date]
            if not ticker_prices.empty:
                prices[ticker] = ticker_prices.iloc[0]["close"]
        return prices

    def _median_adv_notional(
        self,
        market_data: MarketData,
        ticker: str,
        current_date: date,
        window: int = 20,
    ) -> Optional[Decimal]:
        """Approximate ADV in currency units from recent volume * close."""
        df = market_data.get_prices(ticker)
        df = df[df["date"] <= current_date].tail(window)
        if df.empty:
            return None
        dollar_vol = []
        for _, row in df.iterrows():
            dollar_vol.append(float(row["close"]) * float(row["volume"]))
        if not dollar_vol:
            return None
        dollar_vol.sort()
        mid = dollar_vol[len(dollar_vol) // 2]
        return Decimal(str(mid)) if mid > 0 else None

    def _signal_to_trade(
        self,
        signal: Signal,
        current_prices: dict[str, Decimal],
        market_data: MarketData,
        current_date: date,
    ) -> Optional[Trade]:
        if signal.ticker not in current_prices:
            return None

        price = current_prices[signal.ticker]
        action_map = {
            "buy": TradeAction.BUY,
            "sell": TradeAction.SELL,
            "short": TradeAction.SHORT,
            "cover": TradeAction.COVER,
            TradeAction.BUY: TradeAction.BUY,
            TradeAction.SELL: TradeAction.SELL,
            TradeAction.SHORT: TradeAction.SHORT,
            TradeAction.COVER: TradeAction.COVER,
        }
        # signal.action may be enum or string depending on pydantic config
        raw_action = signal.action
        if hasattr(raw_action, "value"):
            key = raw_action.value
        else:
            key = raw_action
        trade_action = action_map.get(key) or action_map.get(str(key).lower())
        if not trade_action:
            return None

        notional = Decimal(str(signal.quantity)) * price
        adv = self._median_adv_notional(market_data, signal.ticker, current_date)
        costs = self.config.cost_model.estimate(
            notional=notional,
            adv_notional=adv,
            side=str(key),
        )

        trade = Trade(
            ticker=signal.ticker,
            action=trade_action,
            quantity=signal.quantity,
            price=price,
            fees=costs.commission + costs.impact,
            slippage=costs.slippage,
            metadata={
                "signal_confidence": float(signal.confidence),
                "signal_reasoning": signal.reasoning or "",
                "commission": float(costs.commission),
                "impact": float(costs.impact),
            },
        )
        return trade
