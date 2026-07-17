# PHASES.md — Quant Factory Upgrade Roadmap (Agent Guide)

> **Audience:** Grok / human contributors implementing upgrades later.  
> **Method:** **Test-Driven Development (TDD)** — write failing tests first, implement until green, refactor.  
> **Product:** Quant Factory — algorithmic trading backtesting monorepo  
> **Repo:** https://github.com/SomeRandmGuyy/quant-factory  
> **Related:** [GROK.md](./GROK.md) (file map), [docs/LOCAL_DEV.md](./docs/LOCAL_DEV.md) (run locally)

---

## How to use this document

1. Pick the **lowest unfinished phase** (do not skip Phase 0/1 for live trading).
2. For each **step**, follow the **TDD loop** below.
3. Keep **`packages/core/quant_lab` pure** (no FastAPI, no exchange API keys).
4. Put HTTP in `packages/api`, UI in `packages/web`, future execution in a new package (e.g. `packages/execution`).
5. After each step: `pytest` green + manual smoke if it touches API/UI.

### Global TDD loop

```text
RED   → write a failing test that defines correct behavior
GREEN → write the minimum production code to pass
REFACTOR → clean up without changing behavior; re-run tests
COMMIT → small, focused commit message
```

### Where tests live (create if missing)

```text
packages/core/tests/
  unit/
  integration/
packages/api/tests/
  unit/
  integration/
packages/web/src/  (optional Vitest later)
```

### How to run tests

```bash
cd /path/to/quant-factory
source .venv/bin/activate   # if using local venv
export PYTHONPATH=packages/core:packages/api
pytest packages/core/tests packages/api/tests -q
```

### Conventions for agents

| Rule | Detail |
|------|--------|
| Decimal money | Cash, prices, quantities use `Decimal` in portfolio paths |
| Point-in-time | Strategies must only use data `date <= current_date` |
| No look-ahead | Never join future fundamentals onto past bars without a PIT calendar |
| JSON-safe API | Dates → ISO strings; no `inf`/`nan` in responses |
| Strategy registry | New strategies: implement protocol + register in `AVAILABLE_STRATEGIES` |
| Data providers | Implement `DataProvider` protocol; wire in `BacktestService` |

---

## Baseline (today)

| Area | Current state |
|------|----------------|
| Core | Portfolio (long/short), 3 strategies, daily `BacktestEngine`, metrics |
| Data | `CSVDataProvider`, `YahooFinanceProvider` (API uses CSV only) |
| API | FastAPI + SSE backtest, SQLite/Postgres `BacktestRun` |
| Web | React form + equity curve + metrics |
| Gaps | Weak tests, UI/API contracts partially fixed, no walk-forward, no live trading |

---

# Phase 0 — Make current app runnable & trustworthy

**Goal:** Reliable local runs, correct contracts, smoke coverage.  
**Exit criteria:** CI can run pytest; UI can complete a backtest; Yahoo optional; no known serialization bugs.

---

### Step 0.1 — Test layout & smoke tests for domain math

**Why:** Without tests, every later phase will regress silently.

#### TDD — RED

Create `packages/core/tests/unit/test_portfolio_buy_sell.py`:

```python
"""Portfolio buy/sell invariants (TDD seed)."""
from decimal import Decimal
from quant_lab.portfolio.portfolio import Portfolio
from quant_lab.portfolio.trade import Trade, TradeAction


def test_buy_reduces_cash_and_opens_long():
    p = Portfolio.create(100_000)
    trade = Trade(
        ticker="AAPL",
        action=TradeAction.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        fees=Decimal("1"),
        slippage=Decimal("0"),
    )
    p2 = p.apply_trade(trade)
    assert p2.cash == Decimal("100000") - Decimal("1001")
    pos = p2.get_position("AAPL")
    assert pos is not None
    assert pos.quantity == Decimal("10")


def test_cannot_buy_with_insufficient_cash():
    p = Portfolio.create(100)
    trade = Trade(
        ticker="AAPL",
        action=TradeAction.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
    )
    try:
        p.apply_trade(trade)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "cash" in str(e).lower() or "Insufficient" in str(e)
```

```bash
pytest packages/core/tests/unit/test_portfolio_buy_sell.py -q
# Expect FAIL until portfolio package is importable in path; then GREEN if already correct
```

#### GREEN / REFACTOR

- Ensure `PYTHONPATH` / editable install includes `quant_lab`.
- Fix any broken portfolio edge cases the tests reveal.
- Do **not** change public behavior without updating tests.

#### Done when

- [ ] `pytest packages/core/tests/unit/test_portfolio_buy_sell.py` passes
- [ ] CI or local script documents the command

---

### Step 0.2 — API health & strategies contract tests

**Why:** Frontend depends on stable JSON shapes.

#### TDD — RED

`packages/api/tests/integration/test_strategies_endpoint.py`:

```python
from fastapi.testclient import TestClient
from quant_lab_api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_list_strategies_shape():
    r = client.get("/api/strategies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for s in data:
        assert set(s.keys()) >= {"id", "name", "description"}
    ids = {s["id"] for s in data}
    assert "trend_following" in ids
    assert "value_moat" in ids
    assert "multi_factor" in ids
```

#### GREEN

- Install `httpx` for TestClient if needed.
- Fix route prefix or CORS only if tests fail for real contract reasons.

---

### Step 0.3 — Backtest SSE + JSON serializable results

**Why:** Equity curve used `date` objects → `Object of type date is not JSON serializable`.

#### TDD — RED

`packages/api/tests/integration/test_backtest_run_sse.py`:

```python
import json
from fastapi.testclient import TestClient
from quant_lab_api.main import app

client = TestClient(app)


def test_backtest_sse_completes_with_json_safe_payload(tmp_path, monkeypatch):
    # Prefer fixtures: point CSV_DATA_DIR at packages with sample data
    # or monkeypatch BacktestService to use known MarketData
    payload = {
        "strategy_name": "value_moat",
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-02",
        "end_date": "2024-06-28",
        "initial_capital": 100000,
    }
    with client.stream("POST", "/api/backtest/run", json=payload) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "Internal error" not in body
    assert "complete" in body
    # last data line should parse as JSON with equity_curve dates as strings
    for line in body.splitlines():
        if line.startswith("data: ") and "equity_curve" in line:
            data = json.loads(line[len("data: "):])
            if data.get("stage") == "complete":
                curve = data["results"]["equity_curve"]
                assert isinstance(curve[0]["date"], str)
```

#### Implementation sketch (GREEN)

```python
# packages/api/quant_lab_api/services/backtest_service.py
def _json_safe(obj):
    ...  # date/datetime -> isoformat; Decimal -> float; filter inf/nan

results_dict = _json_safe({...})
```

In routes, prefer `json.dumps(data, default=str)` as belt-and-suspenders.

#### Done when

- [ ] SSE stream ends with `stage: complete` without error events
- [ ] Equity curve dates are ISO strings

---

### Step 0.4 — Frontend / API field contract

**Why:** Form used `strategy_id`; API expects `strategy_name`. Types lived in wrong path.

#### TDD (frontend, optional Vitest)

```typescript
// packages/web/src/types/index.ts — source of truth
export interface BacktestRequest {
  strategy_name: string;
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
}
```

Manual acceptance:

1. Open UI → select strategy → Run  
2. Network tab shows body with `strategy_name`  
3. Equity curve renders after complete event  

#### Files to keep aligned

| File | Responsibility |
|------|----------------|
| `packages/web/src/types/index.ts` | Types |
| `packages/web/src/api/client.ts` | Fetch + SSE parse |
| `packages/web/src/components/BacktestForm.tsx` | Form fields |
| `packages/api/.../routes/backtest.py` | `BacktestRequest.strategy_name` |

---

### Step 0.5 — Optional Yahoo provider in API

**Why:** Demo without shipping CSVs; equities + some crypto pairs via yfinance.

#### TDD — RED

`packages/core/tests/integration/test_yahoo_provider_shape.py` (mark network tests):

```python
import pytest
from datetime import date
from quant_lab.data.yahoo_provider import YahooFinanceProvider

@pytest.mark.network
@pytest.mark.asyncio
async def test_yahoo_fetch_prices_columns():
    p = YahooFinanceProvider()
    df = await p.fetch_prices(["AAPL"], date(2024, 1, 2), date(2024, 1, 31))
    assert set(df.columns) >= {"ticker", "date", "open", "high", "low", "close", "volume"}
    assert len(df) > 0
```

#### GREEN sketch

```python
# BacktestRequest
provider: Literal["csv", "yahoo"] = "csv"

# BacktestService.run_backtest
if provider == "yahoo":
    self.data_provider = YahooFinanceProvider()
else:
    self.data_provider = CSVDataProvider(...)
```

```bash
pytest -m "not network"   # default CI
pytest -m network         # optional
```

---

### Step 0.6 — Fractional quantity foundation

**Why:** Crypto and modern brokers use fractional units; `int(target / price)` truncates.

#### TDD — RED

```python
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
```

Then strategy sizing tests:

```python
def test_size_position_returns_decimal_not_int():
    from quant_lab.portfolio.sizing import size_by_percent  # new module
    q = size_by_percent(
        portfolio_value=Decimal("100000"),
        price=Decimal("333.33"),
        pct=Decimal("0.1"),
    )
    assert isinstance(q, Decimal)
    assert q > 0
```

#### GREEN sketch

```python
# packages/core/quant_lab/portfolio/sizing.py
from decimal import Decimal, ROUND_DOWN

def size_by_percent(portfolio_value: Decimal, price: Decimal, pct: Decimal) -> Decimal:
    if price <= 0:
        raise ValueError("price must be positive")
    notional = portfolio_value * pct
    # keep more precision for crypto; round to 8 dp as default
    return (notional / price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
```

Update strategies to call `size_by_percent` instead of `int(...)`.

Relax ticker `max_length=10` if needed for longer symbols.

---

# Phase 1 — Research-grade backtesting

**Goal:** Hard to fool yourself; comparable experiments.  
**Exit criteria:** Walk-forward API or CLI; real per-trade PnL; benchmark excess return; costs model tested.

---

### Step 1.1 — True trade-level PnL

**Why:** `BacktestResults._calculate_trades_pnl` currently approximates by splitting total realized PnL.

#### TDD — RED

```python
def test_round_trip_pnl_on_long():
    """Buy 10 @ 100, sell 10 @ 110 → realized +100 (ignoring fees)."""
    p = Portfolio.create(10_000)
    p = p.apply_trade(Trade(ticker="X", action=TradeAction.BUY,
                            quantity=Decimal("10"), price=Decimal("100")))
    p = p.update_prices({"X": Decimal("110")})
    p = p.apply_trade(Trade(ticker="X", action=TradeAction.SELL,
                            quantity=Decimal("10"), price=Decimal("110")))
    assert p.realized_pnl == Decimal("100")
```

Extend engine/results to attach **per-fill realized PnL** on closing trades:

```python
# Desired result shape
{"ticker": "X", "action": "sell", "realized_pnl": 100.0, ...}
```

```python
def test_results_win_rate_uses_per_trade_pnl():
    # fixture: 2 wins, 1 loss → win_rate == 2/3
    ...
```

#### GREEN

- Track FIFO lots **or** use `remove_shares` realized PnL already returned and store it on `Trade.metadata["realized_pnl"]`.
- Metrics `win_rate` uses list of closing-trade PnLs only.

---

### Step 1.2 — Transaction cost model (beyond flat bps)

**Why:** Flat bps understates costs for large orders / illiquid names.

#### TDD — RED

```python
from quant_lab.backtesting.costs import SimpleCostModel, CostResult

def test_cost_model_linear_impact():
    model = SimpleCostModel(commission_bps=5, impact_bps_per_adv=10)
    cost = model.estimate(
        notional=Decimal("100000"),
        adv_notional=Decimal("1000000"),  # 10% ADV
        side="buy",
    )
    assert cost.commission > 0
    assert cost.impact > 0
    assert cost.total == cost.commission + cost.impact
```

#### GREEN sketch

```python
# packages/core/quant_lab/backtesting/costs.py
@dataclass
class SimpleCostModel:
    commission_bps: float = 5.0
    impact_bps_per_adv: float = 10.0  # extra bps * (notional/ADV)

    def estimate(self, notional: Decimal, adv_notional: Decimal, side: str) -> CostResult:
        ...
```

Wire into `BacktestEngine._signal_to_trade` via `TradeBuilder`.

---

### Step 1.3 — Benchmark & excess return

**Why:** Absolute return without SPY/BTC context is misleading.

#### TDD — RED

```python
from quant_lab.backtesting.metrics import PerformanceMetrics, excess_return

def test_excess_return():
    strategy = [100, 110]  # +10%
    bench = [100, 105]     # +5%
    # define clear API: either total excess or series
    assert abs(excess_return(strategy, bench) - 0.05) < 1e-9
```

#### GREEN sketch

```python
def excess_return(strategy_values: list[float], benchmark_values: list[float]) -> float:
    s = (strategy_values[-1] / strategy_values[0]) - 1
    b = (benchmark_values[-1] / benchmark_values[0]) - 1
    return s - b
```

Load benchmark series via same `DataProvider` (`SPY` or `BTC-USD`).

Expose in API metrics: `benchmark_ticker`, `benchmark_return`, `excess_return`.

---

### Step 1.4 — Walk-forward / out-of-sample splits

**Why:** Core anti-overfitting tool for beginners and pros.

#### TDD — RED

```python
from datetime import date
from quant_lab.backtesting.walk_forward import WalkForwardSplit, generate_splits

def test_generate_expanding_splits():
    splits = generate_splits(
        start=date(2020, 1, 1),
        end=date(2022, 12, 31),
        train_days=180,
        test_days=60,
        step_days=60,
        mode="expanding",
    )
    assert len(splits) >= 1
    for s in splits:
        assert s.train_end <= s.test_start
        assert s.test_start < s.test_end
```

```python
@pytest.mark.asyncio
async def test_walk_forward_runner_aggregates_oos_metrics(sample_market_data, strategy):
    from quant_lab.backtesting.walk_forward import WalkForwardRunner
    runner = WalkForwardRunner(strategy=strategy, market_data=sample_market_data)
    report = await runner.run(train_days=60, test_days=20, step_days=20)
    assert "folds" in report
    assert "oos_total_return" in report["aggregate"]
```

#### GREEN sketch

```python
# packages/core/quant_lab/backtesting/walk_forward.py
@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: date
    train_end: date
    test_start: date
    test_end: date

def generate_splits(...) -> list[WalkForwardSplit]:
    ...

class WalkForwardRunner:
    async def run(self, ...) -> dict:
        # for each split:
        #   optionally fit params on train (later)
        #   backtest on test window only with BacktestEngine
        # aggregate OOS equity / metrics
        ...
```

#### API sketch

```python
class WalkForwardRequest(BaseModel):
    strategy_name: str
    tickers: list[str]
    start_date: str
    end_date: str
    train_days: int = 180
    test_days: int = 60
    step_days: int = 60
```

`POST /api/backtest/walk-forward` → JSON report (SSE optional later).

#### Done when

- [ ] Unit tests for split generation  
- [ ] Integration test with synthetic prices  
- [ ] Document how to interpret OOS vs IS metrics in UI or README  

---

### Step 1.5 — Experiment store (params → metrics)

**Why:** Reproducible research log.

#### TDD — RED

```python
def test_create_experiment_record(db_session):
    repo = ExperimentRepository(db_session)
    exp = repo.create(
        name="wf-trend-v1",
        strategy_name="trend_following",
        params={"short_window": 20},
        metrics={"oos_sharpe": 0.5},
    )
    assert exp.id is not None
    assert repo.get_by_id(exp.id).params["short_window"] == 20
```

#### GREEN

- New SQLAlchemy model `Experiment` or extend `BacktestRun` with `params` + `tags`.
- `GET /api/experiments` list.

---

### Step 1.6 — CLI research entrypoint

**Why:** Faster iteration than UI for agents and power users.

#### TDD — RED

```python
def test_cli_backtest_exits_zero(tmp_path):
    # invoke: python -m quant_lab.cli backtest --strategy trend_following ...
    ...
```

#### GREEN sketch

```python
# packages/core/quant_lab/cli.py
# argparse or typer:
#   backtest | walk-forward | fetch-data
```

```bash
python -m quant_lab.cli backtest \
  --strategy multi_factor \
  --tickers AAPL,MSFT \
  --start 2024-01-01 --end 2024-06-30 \
  --provider csv --data-dir ./data
```

---

# Phase 2 — Portfolio construction & risk

**Goal:** Signals become a controlled portfolio process.  
**Exit criteria:** Pluggable sizers; hard risk limits; richer risk metrics in API/UI.

---

### Step 2.1 — Position sizing strategies

#### TDD — RED

```python
from quant_lab.portfolio.sizing import VolatilityTargetSizer

def test_vol_target_scales_down_for_high_vol():
    sizer = VolatilityTargetSizer(target_annual_vol=0.10, bars_per_year=252)
    q_low = sizer.size(equity=Decimal("100000"), price=Decimal("100"), realized_vol=0.10)
    q_high = sizer.size(equity=Decimal("100000"), price=Decimal("100"), realized_vol=0.40)
    assert q_high < q_low
```

#### GREEN sketch

```python
class PositionSizer(Protocol):
    def size(self, *, equity: Decimal, price: Decimal, **kwargs) -> Decimal: ...

class PercentEquitySizer: ...
class VolatilityTargetSizer: ...
class EqualWeightSizer: ...
```

Engine/strategies call sizer instead of hard-coded 20%.

---

### Step 2.2 — Portfolio constraints / risk limits

#### TDD — RED

```python
from quant_lab.risk.limits import RiskLimits, RiskGate

def test_blocks_order_over_max_position_pct():
    gate = RiskGate(RiskLimits(max_position_pct=0.2, max_gross_leverage=1.0))
    decision = gate.check_order(
        portfolio=...,  # fixture ~ fully invested
        proposed_notional=Decimal("50000"),
        equity=Decimal("100000"),
    )
    assert decision.allowed is False
    assert "max_position" in decision.reason
```

#### GREEN sketch

```python
# packages/core/quant_lab/risk/limits.py
@dataclass
class RiskLimits:
    max_position_pct: float = 0.25
    max_gross_leverage: float = 1.0
    max_drawdown_halt: float = 0.20  # halt new risk if DD worse

class RiskGate:
    def check_order(...) -> GateDecision: ...
    def check_portfolio_state(...) -> GateDecision: ...
```

Integrate **before** `portfolio.apply_trade` in `BacktestEngine`.

---

### Step 2.3 — Stops as engine features

**Why:** Stops currently only partially exist inside Trend Following.

#### TDD — RED

```python
def test_stop_loss_emits_sell_when_price_breaches():
    # open long entry 100, stop 10% → price 89 → force sell
    ...
```

#### GREEN

```python
@dataclass
class StopConfig:
    stop_loss_pct: float | None = 0.10
    take_profit_pct: float | None = None
    time_stop_days: int | None = None
```

Engine maintains entry metadata per position; evaluates stops daily **before** strategy signals (or after—document order).

---

### Step 2.4 — Risk metrics pack

#### TDD — RED

```python
def test_cvar_not_worse_than_var():
    returns = np.array([-0.05, -0.02, 0.01, 0.02, -0.08, 0.0])
    from quant_lab.backtesting.metrics import historical_var, historical_cvar
    var = historical_var(returns, alpha=0.95)
    cvar = historical_cvar(returns, alpha=0.95)
    assert cvar <= var  # more extreme average loss
```

Add: rolling Sharpe series, underwater equity curve helper for UI.

Expose via `metrics` dict and MetricsCard.

---

# Phase 3 — Multi-asset & crypto

**Goal:** Same engine works for crypto/spot (then perps later).  
**Exit criteria:** Crypto provider + fractional size + at least one crypto-native strategy demo.

---

### Step 3.1 — Symbol & asset class model

#### TDD — RED

```python
from quant_lab.models.instrument import Instrument, AssetClass

def test_parse_crypto_pair():
    inst = Instrument.parse("BTC/USDT")
    assert inst.asset_class == AssetClass.CRYPTO
    assert inst.base == "BTC"
    assert inst.quote == "USDT"
```

#### GREEN sketch

```python
class AssetClass(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    ETF = "etf"
    FX = "fx"

@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: AssetClass
    base: str | None = None
    quote: str | None = None
```

MarketData may carry `instruments: dict[str, Instrument]`.

---

### Step 3.2 — Crypto data provider (CCXT or REST)

#### TDD — RED

```python
@pytest.mark.network
@pytest.mark.asyncio
async def test_crypto_provider_ohlcv_shape():
    from quant_lab.data.ccxt_provider import CcxtDataProvider
    p = CcxtDataProvider(exchange_id="binance")
    df = await p.fetch_prices(["BTC/USDT"], date(2024, 1, 1), date(2024, 1, 10))
    assert not df.empty
    assert (df["close"] > 0).all()
```

Offline unit test with mocked HTTP/ccxt responses (preferred in CI):

```python
@pytest.mark.asyncio
async def test_crypto_provider_maps_ccxt_candles(monkeypatch):
    # monkeypatch exchange.fetch_ohlcv to return fixed candles
    ...
```

#### GREEN

```python
class CcxtDataProvider:
    async def fetch_prices(...): ...
    async def fetch_fundamentals(...):  # return {} for spot crypto
        return {}
```

Register `provider="ccxt"` in API.

**Dependencies:** `ccxt` in core optional extra: `pip install quant-lab-core[crypto]`.

---

### Step 3.3 — Calendar & annualization

#### TDD — RED

```python
def test_crypto_annualization_uses_365():
    m = PerformanceMetrics(daily_values=[100, 101], initial_capital=100, bars_per_year=365)
    # volatility scaling uses sqrt(365) not sqrt(252)
    assert m.trading_days_per_year == 365
```

#### GREEN

```python
class PerformanceMetrics:
    def __init__(..., bars_per_year: int = 252):
        self.trading_days_per_year = bars_per_year
```

Pass `bars_per_year=365` for crypto daily bars; for hourly, use `24*365`.

---

### Step 3.4 — Crypto-friendly strategy pack

#### TDD — RED

```python
def test_momentum_strategy_no_fundamentals_required(sample_crypto_market_data):
    from quant_lab.strategies.crypto_momentum import CryptoMomentumStrategy
    s = CryptoMomentumStrategy()
    signals = s.generate_signals(sample_crypto_market_data, Portfolio.create(10_000), sample_crypto_market_data.end_date)
    assert isinstance(signals, list)
```

Gate `ValueMoatStrategy` behind equity asset class (skip tickers without fundamentals rather than crash).

---

### Step 3.5 — UI asset mode (later in phase)

- Toggle: Equities | Crypto  
- Default tickers: `AAPL,MSFT` vs `BTC/USDT,ETH/USDT`  
- Provider select: csv | yahoo | ccxt  

Frontend tests optional; manual QA checklist in PR.

---

# Phase 4 — Factors, ML, research intelligence

**Prerequisite:** Phase 1 walk-forward exists. **Do not** train ML on full sample without OOS.

---

### Step 4.1 — Factor library

#### TDD — RED

```python
import pandas as pd
from quant_lab.factors.momentum import momentum_12_1

def test_momentum_factor_shape():
    prices = pd.Series([100, 101, 102, 110, 108], index=pd.date_range("2024-01-01", periods=5, freq="D"))
    # with short window for unit test
    f = momentum_12_1(prices, lookback=3, skip=1)
    assert len(f) == len(prices)
```

#### GREEN sketch

```text
packages/core/quant_lab/factors/
  momentum.py
  value.py
  quality.py
  low_vol.py
  combine.py   # z-score, winsorize, weighted sum
```

---

### Step 4.2 — Simple ML model with walk-forward

#### TDD — RED

```python
def test_ridge_signal_model_fit_predict_shapes():
    from quant_lab.models.ml.ridge_signal import RidgeSignalModel
    import numpy as np
    X = np.random.randn(100, 3)
    y = np.random.randn(100)
    m = RidgeSignalModel()
    m.fit(X[:80], y[:80])
    pred = m.predict(X[80:])
    assert pred.shape == (20,)
```

Integration: walk-forward only trains on train folds (Phase 1.4).

**Rule for agents:** Any ML PR without walk-forward tests is incomplete.

---

### Step 4.3 — Feature store (Parquet)

#### TDD — RED

```python
def test_feature_store_roundtrip(tmp_path):
    from quant_lab.data.feature_store import FeatureStore
    store = FeatureStore(tmp_path)
    df = pd.DataFrame({"date": ["2024-01-01"], "ticker": ["AAPL"], "mom": [0.1]})
    store.write("momentum_v1", df)
    out = store.read("momentum_v1")
    assert out.iloc[0]["mom"] == 0.1
```

---

### Step 4.4 — LLM research copilot (optional)

**Scope:** Explain backtest JSON, suggest hypotheses, **never** auto-place live orders.

#### TDD — RED

```python
def test_explain_metrics_prompt_contains_sharpe():
    from quant_lab_api.services.research_copilot import build_explain_prompt
    prompt = build_explain_prompt({"sharpe_ratio": 1.2, "max_drawdown": -0.1})
    assert "sharpe" in prompt.lower()
```

Mock the LLM HTTP client in tests; no network in CI.

---

# Phase 5 — Paper → live execution

**Goal:** Same signals → orders with auditability.  
**Exit criteria:** Paper adapter parity tests; testnet connector; kill switch.

---

### Step 5.1 — Order domain model

#### TDD — RED

```python
from quant_lab.execution.orders import Order, OrderSide, OrderType, OrderStatus

def test_order_defaults_to_new():
    o = Order(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"), order_type=OrderType.MARKET)
    assert o.status == OrderStatus.NEW
```

Keep in core **or** new `packages/execution` depending on coupling; prefer new package if broker SDKs are heavy.

---

### Step 5.2 — Paper broker adapter

#### TDD — RED

```python
@pytest.mark.asyncio
async def test_paper_broker_fill_at_given_price():
    from quant_lab.execution.paper import PaperBroker
    broker = PaperBroker(cash=Decimal("10000"))
    fill = await broker.submit(Order(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"), ...), market_price=Decimal("100"))
    assert fill.status == OrderStatus.FILLED
    assert broker.cash < Decimal("10000")
```

#### Parity test (critical)

```python
@pytest.mark.asyncio
async def test_paper_path_matches_backtest_cash_path_on_same_prints():
    """Same price series + signals → same final equity within fee tolerance."""
    ...
```

---

### Step 5.3 — Exchange / broker connectors

#### TDD — RED

- Mock REST responses for place/cancel/status.
- Never hit real production APIs in CI.

```python
@pytest.mark.asyncio
async def test_binance_testnet_client_signs_request(monkeypatch):
    ...
```

#### GREEN

```text
packages/execution/
  brokers/
    paper.py
    alpaca.py
    binance_testnet.py
  oms.py
```

Secrets only via env:

```env
BINANCE_API_KEY=
BINANCE_API_SECRET=
ALPACA_KEY_ID=
ALPACA_SECRET_KEY=
EXECUTION_MODE=paper   # paper | testnet | live
```

**Live mode requires explicit `EXECUTION_MODE=live` + `I_UNDERSTAND_LIVE_RISK=true`.**

---

### Step 5.4 — OMS + kill switch

#### TDD — RED

```python
def test_kill_switch_rejects_new_orders():
    oms = OrderManagementSystem(...)
    oms.activate_kill_switch("max drawdown")
    with pytest.raises(KillSwitchActive):
        oms.submit(...)
```

#### GREEN

- Persist orders/fills to DB.
- Endpoint `POST /api/execution/kill` for emergency halt.
- Alerting hook (log + optional webhook).

---

### Step 5.5 — Reconciliation

#### TDD — RED

```python
def test_reconcile_detects_position_mismatch():
    report = reconcile(local_positions={...}, broker_positions={...})
    assert report.has_breaks is True
```

Run on a schedule (cron / background task), not only on demand.

---

# Cross-cutting work (any phase)

### C1 — CI pipeline

```yaml
# .github/workflows/test.yml (sketch)
# - python 3.11/3.12
# - pip install -e packages/core -e packages/api
# - pytest -m "not network"
# - (optional) npm ci && npm run build in packages/web
```

### C2 — Deterministic fixtures

```python
# packages/core/tests/conftest.py
@pytest.fixture
def sample_ohlcv_df():
    # fixed seed synthetic bars for AAPL/MSFT
    ...
```

### C3 — Property-based tests (optional advanced)

```python
from hypothesis import given, strategies as st

@given(st.decimals(min_value="1", max_value="1000", places=2))
def test_buy_never_makes_cash_negative_if_rejected(price):
    ...
```

### C4 — Documentation updates per phase

When completing a phase step, update:

1. This file’s **Done when** checkboxes (or a `PHASES_STATUS.md` tracker)  
2. `GROK.md` file map if new modules appear  
3. `README.md` user-facing features if user-visible  

---

# Suggested implementation order (checklist for agents)

```text
[ ] 0.1 Portfolio unit tests
[ ] 0.2 API health/strategies tests
[ ] 0.3 SSE JSON-safe backtest test
[ ] 0.4 Frontend contract alignment (manual + types)
[ ] 0.5 Yahoo provider flag + network-marked tests
[ ] 0.6 Fractional sizing module + strategy migration
[ ] 1.1 Per-trade PnL
[ ] 1.2 Cost model
[ ] 1.3 Benchmark excess return
[ ] 1.4 Walk-forward splits + runner
[ ] 1.5 Experiment store
[ ] 1.6 CLI
[ ] 2.1 Sizers
[ ] 2.2 RiskGate
[ ] 2.3 Engine stops
[ ] 2.4 CVaR / underwater metrics
[ ] 3.1 Instrument model
[ ] 3.2 Ccxt provider (mocked tests)
[ ] 3.3 bars_per_year
[ ] 3.4 Crypto momentum strategy
[ ] 3.5 UI asset mode
[ ] 4.x Factors / ML / feature store (only with walk-forward)
[ ] 5.x Paper → testnet → live with kill switch
```

---

# Anti-patterns (do not do)

| Anti-pattern | Do instead |
|--------------|------------|
| Train ML on full period then “test” on same period | Walk-forward / purged CV |
| Add live trading before paper parity tests | Step 5.2 parity test |
| Put Binance secrets in git | `.env` only |
| Rewrite engine in new language mid-phase | Finish correctness in Python first |
| Skip tests “because demo” | At least unit tests for money math |
| 10 strategies before 1 validated OOS | One strategy + walk-forward |

---

# Definition of “state-of-the-art” for this project

Not flashy charts alone. For Quant Factory it means:

1. **Correct money math** (tested)  
2. **Honest validation** (walk-forward, costs, benchmarks)  
3. **Risk controls** (limits, stops, kill switch)  
4. **Multi-asset data** (equities + crypto)  
5. **Reproducible experiments**  
6. **Safe path to execution** (paper → testnet → tiny live)  

Agents implementing upgrades should optimize for those six properties.

---

*End of PHASES.md — expand individual steps into PRs; keep each PR one step when possible.*
