"""
Backtesting engine with event-driven simulation.

Order of operations each day:
1. Update mark prices
2. Update risk peak equity
3. Evaluate engine stops → execute reduce-only exits
4. Strategy signals on rebalance days
5. RiskGate filter → apply trades (with realized PnL metadata)
6. Daily snapshot
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Any

from quant_lab.models.market_data import MarketData
from quant_lab.models.signal import Signal, SignalAction
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction
from quant_lab.portfolio.sizing import (
    PositionSizer,
    make_sizer,
    realized_vol_from_prices,
)
from quant_lab.strategies.protocols import Strategy
from quant_lab.backtesting.costs import SimpleCostModel
from quant_lab.risk.limits import RiskLimits, RiskGate
from quant_lab.risk.stops import StopConfig, StopManager


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
        risk_limits: Optional[RiskLimits] = None,
        enable_risk_gate: bool = True,
        stop_config: Optional[StopConfig] = None,
        sizer: Optional[PositionSizer] = None,
        sizer_name: str = "percent",
        max_position_pct: float = 0.20,
        target_vol: float = 0.10,
        resize_signals: bool = False,
    ):
        self.initial_capital = initial_capital
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        self.rebalance_frequency = rebalance_frequency
        self.impact_bps = impact_bps
        self.enable_risk_gate = enable_risk_gate
        self.risk_limits = risk_limits if risk_limits is not None else RiskLimits()
        self.stop_config = stop_config or StopConfig()
        self.sizer = sizer or make_sizer(
            sizer_name, max_position_pct=max_position_pct, target_vol=target_vol
        )
        self.sizer_name = sizer_name
        self.max_position_pct = max_position_pct
        self.target_vol = target_vol
        self.resize_signals = resize_signals
        if cost_model is not None:
            self.cost_model = cost_model
        else:
            self.cost_model = SimpleCostModel(
                commission_bps=commission_bps,
                impact_bps_per_participation=impact_bps,
                slippage_bps=slippage_bps,
            )


class BacktestEngine:
    """Event-driven backtesting engine with risk controls."""

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
        self.rejected_trades: list[dict] = []
        self.risk_gate = (
            RiskGate(self.config.risk_limits) if self.config.enable_risk_gate else None
        )
        self.stop_manager = StopManager(self.config.stop_config)

    async def run(self) -> "BacktestResults":
        from quant_lab.backtesting.results import BacktestResults

        trading_days = self._get_trading_days()
        if not trading_days:
            raise ValueError("No trading days available in market data")

        for i, current_date in enumerate(trading_days):
            point_in_time_data = self.market_data.as_of(current_date)
            current_prices = self._get_current_prices(point_in_time_data, current_date)
            self.portfolio = self.portfolio.update_prices(current_prices)

            if self.risk_gate:
                self.risk_gate.update_equity_peak(self.portfolio.total_value)

            # 1) Engine stops first (reduce-only)
            stop_signals = self.stop_manager.evaluate(
                self.portfolio, current_prices, current_date
            )
            for signal in stop_signals:
                self._try_execute_signal(
                    signal, current_prices, point_in_time_data, current_date, force_reduce=True
                )

            # 2) Strategy on rebalance days
            if i % self.config.rebalance_frequency == 0:
                signals = self.strategy.generate_signals(
                    market_data=point_in_time_data,
                    portfolio=self.portfolio,
                    current_date=current_date,
                )
                for signal in signals:
                    if not signal.is_actionable():
                        continue
                    if self.config.resize_signals:
                        signal = self._maybe_resize(signal, point_in_time_data, current_date)
                        if not signal.is_actionable():
                            continue
                    self._try_execute_signal(
                        signal, current_prices, point_in_time_data, current_date, force_reduce=False
                    )

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
                    "drawdown": (
                        self.risk_gate.current_drawdown(self.portfolio.total_value)
                        if self.risk_gate
                        else 0.0
                    ),
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
            rejected_trades=self.rejected_trades,
        )

    def _maybe_resize(
        self, signal: Signal, market_data: MarketData, current_date: date
    ) -> Signal:
        action = signal.action.value if hasattr(signal.action, "value") else str(signal.action)
        if action not in ("buy", "short"):
            return signal
        prices = market_data.get_prices(signal.ticker)
        prices = prices[prices["date"] <= current_date]
        vol = realized_vol_from_prices(prices)
        px = prices.iloc[-1]["close"] if not prices.empty else None
        if px is None:
            return signal
        qty = self.config.sizer.size(
            equity=self.portfolio.total_value,
            price=Decimal(str(px)),
            realized_vol=vol,
            n_targets=max(len(market_data.tickers), 1),
        )
        return signal.model_copy(update={"quantity": qty})

    def _try_execute_signal(
        self,
        signal: Signal,
        current_prices: dict[str, Decimal],
        market_data: MarketData,
        current_date: date,
        force_reduce: bool,
    ) -> None:
        trade = self._signal_to_trade(signal, current_prices, market_data, current_date)
        if not trade:
            return

        if self.risk_gate and not force_reduce:
            state = self.risk_gate.check_portfolio_state(self.portfolio)
            if not state.allowed and trade.is_opening:
                self.rejected_trades.append(
                    {"date": current_date.isoformat(), "ticker": trade.ticker, "reason": state.reason}
                )
                return
            decision = self.risk_gate.check_order(self.portfolio, trade)
            if not decision.allowed:
                self.rejected_trades.append(
                    {
                        "date": current_date.isoformat(),
                        "ticker": trade.ticker,
                        "reason": decision.reason,
                    }
                )
                return

        can_execute, reason = self.portfolio.can_execute_trade(trade)
        if not can_execute:
            self.rejected_trades.append(
                {
                    "date": current_date.isoformat(),
                    "ticker": trade.ticker,
                    "reason": reason,
                }
            )
            return

        before_realized = self.portfolio.realized_pnl
        self.portfolio = self.portfolio.apply_trade(trade)
        delta = self.portfolio.realized_pnl - before_realized
        meta = dict(trade.metadata or {})
        meta["realized_pnl"] = float(delta)
        trade = trade.model_copy(update={"metadata": meta})
        self.executed_trades.append(trade)
        self.stop_manager.on_fill(trade, current_date)

    def _get_trading_days(self) -> list[date]:
        all_dates: set[date] = set()
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
        df = market_data.get_prices(ticker)
        df = df[df["date"] <= current_date].tail(window)
        if df.empty:
            return None
        dollar_vol = [float(row["close"]) * float(row["volume"]) for _, row in df.iterrows()]
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
        raw = signal.action
        key = raw.value if hasattr(raw, "value") else str(raw)
        key = str(key).lower()
        action_map = {
            "buy": TradeAction.BUY,
            "sell": TradeAction.SELL,
            "short": TradeAction.SHORT,
            "cover": TradeAction.COVER,
        }
        trade_action = action_map.get(key)
        if not trade_action:
            return None

        notional = Decimal(str(signal.quantity)) * price
        adv = self._median_adv_notional(market_data, signal.ticker, current_date)
        costs = self.config.cost_model.estimate(
            notional=notional, adv_notional=adv, side=key
        )
        return Trade(
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
