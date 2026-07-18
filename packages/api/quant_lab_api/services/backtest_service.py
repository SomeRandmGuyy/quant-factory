"""
Backtest service for orchestrating backtesting operations.

Handles:
- Loading market data
- Running backtests with progress callbacks
- Persisting results to database
"""

from typing import Callable, Optional, Awaitable
from datetime import date
from decimal import Decimal
import asyncio

from quant_lab.data import CSVDataProvider, YahooFinanceProvider
from quant_lab.models.market_data import MarketData
from quant_lab.backtesting import BacktestEngine, BacktestConfig
from quant_lab.backtesting.benchmark import (
    buy_and_hold_equity,
    align_equity_on_dates,
    excess_return,
    total_return,
)
from quant_lab.backtesting.walk_forward import WalkForwardRunner
from quant_lab.strategies import (
    Strategy,
    ValueMoatStrategy,
    TrendFollowingStrategy,
    MultiFactorStrategy,
)

from quant_lab_api.config import settings
from quant_lab_api.utils.json_safe import json_safe


# Strategy registry
AVAILABLE_STRATEGIES: dict[str, type[Strategy]] = {
    "value_moat": ValueMoatStrategy,
    "trend_following": TrendFollowingStrategy,
    "multi_factor": MultiFactorStrategy,
}


class BacktestService:
    """
    Service for running backtests with progress tracking.
    
    Provides:
    - Strategy instantiation
    - Market data loading
    - Backtest execution with callbacks
    - Results formatting
    """
    
    def __init__(self):
        self.data_provider = CSVDataProvider(
            data_dir=settings.csv_data_dir,
            fundamentals_file=settings.fundamentals_file,
        )
    
    async def run_backtest(
        self,
        strategy_name: str,
        tickers: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
        commission_bps: float = 5.0,
        slippage_bps: float = 2.0,
        rebalance_frequency: int = 5,
        provider: str = "csv",
        benchmark_ticker: Optional[str] = None,
        impact_bps: float = 0.0,
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> dict:
        """
        Run a backtest with optional progress callbacks.
        
        Args:
            strategy_name: Name of strategy to use
            tickers: List of stock symbols
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            commission_bps: Commission in basis points
            slippage_bps: Slippage in basis points
            rebalance_frequency: Days between rebalances
            provider: Data source (csv or yahoo)
            progress_callback: Optional async callback for progress updates
        
        Returns:
            Dictionary with backtest results
        
        Raises:
            ValueError: If strategy name is invalid or data cannot be loaded
        """
        data_provider = self._make_provider(provider)

        # Validate strategy
        if strategy_name not in AVAILABLE_STRATEGIES:
            raise ValueError(
                f"Unknown strategy: {strategy_name}. "
                f"Available: {list(AVAILABLE_STRATEGIES.keys())}"
            )
        
        # Send progress: loading data
        if progress_callback:
            await progress_callback({
                "stage": "loading_data",
                "message": f"Loading market data for {len(tickers)} tickers...",
                "progress": 0.1,
            })
        
        # Load market data (include optional benchmark ticker)
        load_tickers = list(tickers)
        bench = benchmark_ticker.upper().strip() if benchmark_ticker else None
        if bench and bench not in load_tickers:
            load_tickers.append(bench)

        try:
            prices_df = await data_provider.fetch_prices(
                tickers=load_tickers,
                start_date=start_date,
                end_date=end_date,
            )
            
            fundamentals = await data_provider.fetch_fundamentals(tickers)
            
            strat_prices = prices_df[prices_df["ticker"].isin([t.upper() for t in tickers])].copy()
            market_data = MarketData(
                tickers=[t.upper() for t in tickers],
                start_date=start_date,
                end_date=end_date,
                prices=strat_prices,
                fundamentals=fundamentals,
            )
            full_prices = prices_df
        except Exception as e:
            raise ValueError(f"Failed to load market data: {str(e)}")
        
        # Send progress: initializing
        if progress_callback:
            await progress_callback({
                "stage": "initializing",
                "message": f"Initializing {strategy_name} strategy...",
                "progress": 0.2,
            })
        
        # Create strategy instance
        strategy = AVAILABLE_STRATEGIES[strategy_name]()
        
        # Create backtest config
        config = BacktestConfig(
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            rebalance_frequency=rebalance_frequency,
            impact_bps=impact_bps,
        )
        
        # Send progress: running backtest
        if progress_callback:
            await progress_callback({
                "stage": "running",
                "message": "Running backtest simulation...",
                "progress": 0.3,
            })
        
        # Create and run backtest engine
        engine = BacktestEngine(
            strategy=strategy,
            market_data=market_data,
            config=config,
        )
        
        # Run backtest (this is the heavy computation)
        results = await engine.run()
        
        # Send progress: computing metrics
        if progress_callback:
            await progress_callback({
                "stage": "computing_metrics",
                "message": "Computing performance metrics...",
                "progress": 0.8,
            })
        
        # Format results (JSON-safe dates / floats)
        results_dict = json_safe({
            "strategy_name": results.strategy_name,
            "start_date": results.start_date.isoformat(),
            "end_date": results.end_date.isoformat(),
            "duration_days": results.duration_days,
            "initial_capital": results.initial_capital,
            "final_value": results.final_value,
            "metrics": results.metrics,
            "equity_curve": results.daily_snapshots,
            "trade_history": [
                {
                    "timestamp": trade.timestamp.isoformat(),
                    "ticker": trade.ticker,
                    "action": trade.action,
                    "quantity": float(trade.quantity),
                    "price": float(trade.price),
                    "fees": float(trade.fees),
                    "slippage": float(trade.slippage),
                    "realized_pnl": (trade.metadata or {}).get("realized_pnl"),
                }
                for trade in results.executed_trades
            ],
            "tickers": tickers,
            "benchmark_equity_curve": None,
        })
        
        # Optional benchmark equity + excess return
        if bench:
            bdf = full_prices[full_prices["ticker"] == bench].copy()
            if bdf.empty:
                raise ValueError(f"No benchmark data for {bench}")
            bench_curve = buy_and_hold_equity(bdf, initial_capital)
            s_vals, b_vals, _keys = align_equity_on_dates(
                results.daily_snapshots, bench_curve
            )
            metrics = dict(results_dict.get("metrics") or {})
            metrics["benchmark_ticker"] = bench
            metrics["benchmark_return"] = total_return(b_vals)
            metrics["excess_return"] = excess_return(s_vals, b_vals)
            results_dict["metrics"] = metrics
            results_dict["benchmark_equity_curve"] = json_safe(bench_curve)

        # Send progress: complete
        if progress_callback:
            await progress_callback({
                "stage": "complete",
                "message": "Backtest complete!",
                "progress": 1.0,
                "results": results_dict,
            })
        
        return results_dict
    
    async def run_walk_forward(
        self,
        strategy_name: str,
        tickers: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
        commission_bps: float = 5.0,
        slippage_bps: float = 2.0,
        impact_bps: float = 0.0,
        rebalance_frequency: int = 5,
        provider: str = "csv",
        train_days: int = 60,
        test_days: int = 20,
        step_days: int = 20,
        mode: str = "rolling",
    ) -> dict:
        if strategy_name not in AVAILABLE_STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        data_provider = self._make_provider(provider)
        prices_df = await data_provider.fetch_prices(tickers, start_date, end_date)
        fundamentals = await data_provider.fetch_fundamentals(tickers)
        market_data = MarketData(
            tickers=[t.upper() for t in tickers],
            start_date=start_date,
            end_date=end_date,
            prices=prices_df,
            fundamentals=fundamentals,
        )
        config = BacktestConfig(
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            impact_bps=impact_bps,
            rebalance_frequency=rebalance_frequency,
        )
        runner = WalkForwardRunner(
            strategy=AVAILABLE_STRATEGIES[strategy_name](),
            market_data=market_data,
            config=config,
        )
        report = await runner.run(
            train_days=train_days,
            test_days=test_days,
            step_days=step_days,
            mode=mode,  # type: ignore[arg-type]
        )
        return json_safe(report)

    def _make_provider(self, provider: str):
        """Return a data provider instance for the given name."""
        name = (provider or "csv").lower().strip()
        if name == "yahoo":
            return YahooFinanceProvider()
        if name == "csv":
            return CSVDataProvider(
                data_dir=settings.csv_data_dir,
                fundamentals_file=settings.fundamentals_file,
            )
        raise ValueError(f"Unknown data provider: {provider}. Use 'csv' or 'yahoo'.")

    @staticmethod
    def get_available_strategies() -> list[dict[str, str]]:
        """
        Get list of available strategies with metadata.
        
        Returns:
            List of strategy metadata dictionaries
        """
        strategies = []
        
        for key, strategy_class in AVAILABLE_STRATEGIES.items():
            # Instantiate to get metadata
            instance = strategy_class()
            
            strategies.append({
                "id": key,
                "name": instance.name,
                "description": instance.description,
            })
        
        return strategies
