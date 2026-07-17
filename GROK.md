# GROK.md — Quant Factory Project Map

> **For humans and AI agents.** This is the authoritative walkthrough of the repository: what it is, how it is structured, what every file does, and how to extend it toward crypto and broader trading.
>
> **Repository:** https://github.com/SomeRandmGuyy/quant-factory.git  
> **Product name:** Quant Factory  
> **Version:** 0.1.0  
> **License:** MIT (Copyright 2025 SomeRandmGuyy)

---

## 1. What this project is

**Quant Factory** is a monorepo for **algorithmic trading strategy backtesting** with:

- A **Python core library** (portfolio, strategies, event-driven backtest engine, data providers)
- A **FastAPI** service (REST + Server-Sent Events progress streaming, optional DB persistence)
- A **React + Vite** web UI (configure backtests, view equity curve and metrics)
- **Docker Compose** for Postgres + API + web

It is **simulation / research oriented**, not a live broker or exchange connector. No real orders are sent.

### Current asset focus

Built for **equities** (daily OHLCV, equity-style fundamentals like ROE/P/E, Yahoo Finance via `yfinance`). Architecture is provider/strategy-pluggable, so **crypto and multi-asset trading** are natural next steps (see [§6](#6-extending-toward-crypto--broader-trading)).

### Internal package names (legacy)

Public branding is **Quant Factory**. Python import packages remain:

| Import path | Role |
|-------------|------|
| `quant_lab` | Core domain library (`packages/core`) |
| `quant_lab_api` | FastAPI app (`packages/api`) |

Renaming those would touch every import; leave them unless doing a deliberate migration.

---

## 2. High-level architecture

```
quant-factory/
├── packages/
│   ├── core/     # quant_lab — pure domain + backtest engine
│   ├── api/      # quant_lab_api — HTTP/SSE + SQLAlchemy
│   └── web/      # React UI
├── docker-compose.yml
├── pyproject.toml          # Poetry monorepo meta
├── package.json            # npm workspaces → packages/web
├── .env.example
├── README.md
├── GROK.md                 # this file
├── LICENSE
└── quant-lab/              # NESTED DUPLICATE of monorepo — do not treat as source of truth
```

### Runtime data flow

```
┌─────────────┐  POST /api/backtest/run   ┌──────────────────┐
│  Web (3000) │ ───────────────────────► │  API (8000)      │
│  React/Vite │  ◄── SSE progress/results │  BacktestService │
└─────────────┘                           └────────┬─────────┘
                                                   │
                          CSVDataProvider          │  strategy registry
                          (Yahoo exists unused)    ▼
                          ┌──────────────────────────────────┐
                          │  quant_lab core                  │
                          │  MarketData → Strategy signals   │
                          │  → Trade → Portfolio (immutable) │
                          │  → BacktestEngine day loop       │
                          │  → PerformanceMetrics / Results  │
                          └───────────────┬──────────────────┘
                                          │ persist optional
                                          ▼
                                   SQLite or PostgreSQL
                                   (BacktestRun rows)
```

### Domain concepts (core)

| Concept | Module | Meaning |
|---------|--------|---------|
| **OHLCV** | `models/market_data.py` | One bar: open/high/low/close/volume (+ optional adjusted_close) |
| **Fundamentals** | same | Equity metrics (P/E, ROE, growth, etc.) |
| **MarketData** | same | Tickers + price DataFrame + fundamentals; `as_of(date)` for point-in-time |
| **Signal** | `models/signal.py` | Strategy output: buy/sell/hold/short/cover + qty + confidence |
| **Trade** | `portfolio/trade.py` | Executed order with fees/slippage; built via `TradeBuilder` |
| **Position** | `portfolio/position.py` | Long/short holding, avg cost, unrealized PnL |
| **Portfolio** | `portfolio/portfolio.py` | Immutable cash + positions; `apply_trade` returns new state |
| **Strategy** | `strategies/protocols.py` | Protocol: `generate_signals(market_data, portfolio, current_date)` |
| **BacktestEngine** | `backtesting/engine.py` | Day loop: update prices → signals → execute → snapshot |
| **PerformanceMetrics** | `backtesting/metrics.py` | Sharpe, Sortino, max DD, Calmar, win rate, etc. |
| **BacktestResults** | `backtesting/results.py` | Aggregates metrics, equity curve, trade history |

### Design principles already in the code

1. **Point-in-time data** — engine uses `market_data.as_of(current_date)` to reduce look-ahead bias.
2. **Immutable portfolio** — trades return new `Portfolio` instances.
3. **Decimal money/prices** — precision for cash and fills.
4. **Pluggable data** — `DataProvider` protocol (CSV, Yahoo implemented).
5. **Pluggable strategies** — protocol + registry in API service.

---

## 3. How to run

### Docker (recommended)

```bash
git clone https://github.com/SomeRandmGuyy/quant-factory.git
cd quant-factory
docker-compose up
```

| Service | URL / port |
|---------|------------|
| Web UI | http://localhost:3000 |
| API + OpenAPI | http://localhost:8000/docs |
| Postgres | localhost:5432 (`quantlab` / `quantlab` / db `quantlab`) |

**Note:** API expects CSV data under `/app/data` inside the container. The repo gitignores `data/*`. You must mount or copy price CSVs (and optional `fundamentals.csv`) or generate them (see `sample_data.py`). Without data, backtests fail at load.

### Local development

```bash
# Core
cd packages/core && pip install -e .

# API deps + package
cd ../api && pip install -e .

# Web
cd ../web && npm install

# Terminal 1 — API
export PYTHONPATH=../core:.
# optional: export CSV paths if not using Docker defaults
python -m quant_lab_api.main   # :8000

# Terminal 2 — Web
npm run dev                   # :3000, proxies /api → :8000
```

Env template: copy `.env.example` → `.env`.

---

## 4. File-by-file reference

Paths are relative to the **repo root**. Prefer these over the nested `quant-lab/` copy.

---

### 4.1 Root files

#### `README.md`
User-facing product documentation: features, Docker/local setup, architecture sketch, strategy descriptions, API curl examples, env config, how to add strategies/providers, troubleshooting. Branded **Quant Factory**; clone URL points at SomeRandmGuyy/quant-factory.

#### `GROK.md`
This file — agent/human project map, file inventory, crypto extension notes, known gaps.

#### `LICENSE`
MIT License, Copyright (c) 2025 SomeRandmGuyy.

#### `.env.example`
Template for application settings:

- `APP_NAME`, `APP_VERSION`, `DEBUG`
- `DATABASE_TYPE` / `DATABASE_URL` (SQLite default) or Postgres vars
- `CORS_ORIGINS`, `API_PREFIX`
- `VITE_API_URL`
- Placeholders for future data provider API keys (Alpha Vantage, Polygon, etc.)

Copy to `.env` (gitignored). Note: API `Settings` currently reads a subset of these (see `config.py`); not every key is wired yet.

#### `.gitignore`
Ignores Python/Node build artifacts, venvs, `.env`, IDE dirs, coverage, and **`data/*`** (with optional `data/README.md` keep). SQLite DBs ignored. Comments advise not ignoring lockfiles.

#### `pyproject.toml` (root)
Poetry monorepo metadata:

- Package name: `quant-factory`
- Path deps: `quant-lab-core` → `packages/core`, `quant-lab-api` → `packages/api`
- Dev tools: pytest, mypy, black, ruff
- Tool configs: black line length 100, mypy strict-ish, pytest `testpaths` pointing at `packages/core/tests` and `packages/api/tests` (**those test dirs do not exist yet**)

#### `package.json` (root)
npm monorepo:

- Name: `quant-factory`
- Workspace: `packages/web` only
- Scripts: `web:dev`, `web:build`, `web:preview`, `web:lint`, etc.
- Repository URL: `https://github.com/SomeRandmGuyy/quant-factory.git`
- Author: SomeRandmGuyy

#### `docker-compose.yml`
Three services:

| Service | Image / build | Role |
|---------|---------------|------|
| `postgres` | `postgres:16-alpine` | DB volume `postgres_data`, healthcheck |
| `api` | build `packages/api/Dockerfile` | uvicorn `quant_lab_api.main:app` :8000 |
| `web` | build `packages/web/Dockerfile` | Vite dev server :3000 |

Network: `quant-factory-network`. Containers named `quant-factory-*`.

---

### 4.2 `packages/core/` — domain library (`quant_lab`)

#### `packages/core/pyproject.toml`
Poetry project `quant-lab-core`. Deps: pandas, numpy, pydantic, yfinance, python-dateutil. Dev: pytest, mypy, stubs. Package include: `quant_lab`.

#### `packages/core/setup.py`
setuptools fallback for `pip install -e .` without Poetry (same deps list).

#### `packages/core/README.md`
Placeholder (empty / minimal). Prefer root README + this GROK.md.

#### `packages/core/quant_lab/README.md`
Same — essentially empty placeholder.

---

#### Models — `packages/core/quant_lab/models/`

##### `__init__.py`
Re-exports `Signal`, `SignalAction`, `MarketData`.

##### `market_data.py`
- **`OHLCV`**: single-day bar; Decimal prices; frozen Pydantic model.
- **`Fundamentals`**: equity fundamental snapshot (market cap, P/E, revenue, ROE, ROIC, leverage, growth). Ticker uppercased. **Equity-centric** — crypto will need a different or optional model.
- **`MarketData`**: holds `tickers`, date range, `prices` DataFrame (`ticker, date, open, high, low, close, volume`), `fundamentals` dict. Methods:
  - `get_prices(ticker)`
  - `get_fundamentals(ticker)`
  - **`as_of(as_of_date)`** — filters prices to `date <= as_of_date` (point-in-time for backtests)

##### `signal.py`
- **`SignalAction`**: `buy`, `sell`, `hold`, `short`, `cover`
- **`Signal`**: ticker, action, quantity (Decimal), confidence [0,1], reasoning, metadata. `is_actionable()` ignores HOLD and zero qty. Frozen.

---

#### Data — `packages/core/quant_lab/data/`

##### `__init__.py`
Exports protocol, errors, `CSVDataProvider`, `YahooFinanceProvider`.

##### `protocols.py`
- **`DataProvider` Protocol** (runtime checkable):
  - `async fetch_prices(tickers, start, end) -> DataFrame`
  - `async fetch_fundamentals(tickers) -> dict[str, Fundamentals]`
  - `async validate_tickers(tickers) -> list[str]`
- Errors: `DataProviderError`, `DataNotFoundError`, `DataProviderConnectionError`, `DataProviderRateLimitError`

**Extension point for crypto:** implement this protocol (e.g. Binance/CCXT provider).

##### `csv_provider.py`
Loads `{TICKER}.csv` from a directory (columns: date, open, high, low, close, volume). Optional fundamentals CSV. Converts prices to Decimal. Used by **API BacktestService** as the live path.

##### `yahoo_provider.py`
Fetches history + limited fundamentals via **yfinance**. Good for equities; yfinance also exposes some crypto pairs (e.g. `BTC-USD`) but is not exchange-grade. **Not wired into the API service today** — only available in core.

---

#### Portfolio — `packages/core/quant_lab/portfolio/`

##### `__init__.py`
Exports `Portfolio`, `Position`, `Trade`, `TradeAction`.

##### `position.py`
- **`PositionSide`**: long / short
- **`Position`**: quantity, avg_price, current_price; cost basis, market value, unrealized PnL (side-aware); `add_shares` / `remove_shares` with realized PnL. Frozen. Ticker max length 10 (may be tight for some crypto symbols).

##### `trade.py`
- **`TradeAction`**: buy / sell / short / cover
- **`Trade`**: qty, price, fees, slippage, timestamp, metadata; `total_cost`, `effective_price()`, open/close helpers
- **`TradeBuilder`**: fluent builder with `with_commission_bps`, `with_slippage_bps`, metadata

##### `portfolio.py`
Immutable portfolio state machine:

- Create with `Portfolio.create(initial_capital)`
- Properties: total_value, unrealized/total PnL, return_pct, long/short/net/gross exposure
- `update_prices(dict)` → new portfolio
- `apply_trade(trade)` → buy/sell/short/cover handlers with cash/position checks
- `can_execute_trade(trade)` → (bool, reason) without mutating

**Crypto note:** sizing elsewhere uses `int(target_value / price)` (whole units). Fractional crypto will need quantity type/policy changes in strategies + engine.

---

#### Strategies — `packages/core/quant_lab/strategies/`

##### `__init__.py`
Exports protocol, configs, and three strategy classes.

##### `protocols.py`
- **`Strategy` Protocol**: `name`, `description`, `generate_signals(market_data, portfolio, current_date) -> list[Signal]`
- **`StrategyConfig`**: max_position_size (default 20%), min_confidence, commission_bps, slippage_bps

##### `value_moat.py`
Buffett-inspired **quality + valuation** strategy:

- Config: min ROE, min revenue growth, max P/E, quality/valuation weights
- Scores quality (ROE, growth, net margin) and valuation (PEG-like)
- BUY if combined score ≥ 0.6 and flat; SELL if score &lt; 0.4 and held

**Depends on equity fundamentals.** Poor fit for pure crypto without redesigned factors.

##### `trend_following.py`
Momentum / MA strategy:

- 20/50/200 SMAs, golden/death cross, volume surge, momentum %, stop loss −10%
- Needs enough history (`long_window` bars) — works on any liquid OHLCV series (stocks or crypto)

##### `multi_factor.py`
Composite **value (35%) + momentum (35%) + quality (30%)**:

- Entry/exit thresholds configurable
- Value/quality need fundamentals; momentum is pure price — partial crypto reuse possible with weight retuning

---

#### Backtesting — `packages/core/quant_lab/backtesting/`

##### `__init__.py`
Exports `BacktestEngine`, `BacktestConfig`, `PerformanceMetrics`, `BacktestResults`.

##### `engine.py`
Event-driven simulator:

- **`BacktestConfig`**: initial_capital, commission_bps, slippage_bps, rebalance_frequency (days)
- **`BacktestEngine.run()`** (async):
  1. Collect sorted trading days from all tickers
  2. Each day: `as_of` data → update mark prices → on rebalance days generate signals → convert to trades with fees → apply if executable → append daily snapshot
  3. Return `BacktestResults`

Assumes **daily bars** and a shared calendar of observed dates (union of ticker dates). Crypto 24/7 bars still work if dates are present; annualization uses 252 in metrics (see below).

##### `metrics.py`
**`PerformanceMetrics`** from daily portfolio values:

- total_return, annualized_return (CAGR), volatility, Sharpe, Sortino, max_drawdown, Calmar
- Trade-level: win_rate, profit_factor, avg_win_loss_ratio
- `trading_days_per_year = 252` (equity convention)
- Default risk-free rate 2%

##### `results.py`
**`BacktestResults`**: wraps snapshots, trades, final portfolio; lazy `metrics`; equity_curve / trade_history DataFrames; `summary()` ASCII report; `to_dict()`.

**Caveat:** `_calculate_trades_pnl` approximates per-trade PnL by splitting total realized PnL across closing trades (not true per-trade accounting).

##### `sample_data.py`
Script-style generator for synthetic AAPL/MSFT/TSLA OHLCV + fundamentals CSV.

**Issue:** hardcodes output paths under `/home/claude/quant-lab/data/`. Needs path fix for real use (e.g. repo `./data`).

---

### 4.3 `packages/api/` — FastAPI service (`quant_lab_api`)

#### `packages/api/pyproject.toml`
Poetry `quant-lab-api`: path dep on core; fastapi, uvicorn, sqlalchemy, alembic, psycopg2, pydantic-settings, aiofiles.

#### `packages/api/setup.py`
setuptools install_requires mirror for editable install.

#### `packages/api/Dockerfile`
Python 3.11 slim: copies core + api, `pip install -e` both, creates `/app/data`, runs uvicorn. Healthcheck hits `/health`.

#### `packages/api/quant_lab_api/__init__.py`
Package version `0.1.0`.

#### `config.py`
**`Settings`** (pydantic-settings, reads `.env`):

- `APP_NAME` default **"Quant Factory API"**
- `database_url` default SQLite `./quant_lab.db`
- `cors_origins` comma-separated → `CORS_ORIGINS` list property
- `csv_data_dir` default `/app/data`
- `fundamentals_file` default `/app/data/fundamentals.csv`
- Helpers: `is_sqlite`, `is_postgresql`

#### `main.py`
FastAPI app:

- Lifespan calls `init_db()`
- CORS middleware
- Routers: backtest, strategies
- `GET /` metadata, `GET /health`
- `__main__` runs uvicorn :8000

#### Database — `database/`

##### `__init__.py`
Exports `Base`, `get_db`, `init_db`.

##### `base.py`
Creates SQLAlchemy engine:

- SQLite: `StaticPool`, `check_same_thread=False`
- Postgres: pool_pre_ping, pool_size 5

`SessionLocal`, `get_db()` FastAPI dependency, `init_db()` → `create_all`.

##### `models.py`
**`BacktestRun`** table `backtest_runs`:

- Metadata: strategy_name, created_at, dates, duration, capital, tickers JSON, config JSON
- Results: final_value, returns, risk metrics columns, num_trades, win_rate, profit_factor
- Blobs: metrics / equity_curve / trade_history JSON
- status: completed | failed | running; error_message

#### Repositories — `repositories/`

##### `__init__.py` / `backtest_repository.py`
**`BacktestRepository`**: create, get_by_id, get_all (filter by strategy, pagination), delete, update_status. Maps metrics dict into denormalized columns on create.

#### Services — `services/`

##### `__init__.py` / `backtest_service.py`
**`BacktestService`**:

- Instantiates **CSVDataProvider only** (Yahoo unused here)
- **`AVAILABLE_STRATEGIES`** registry:
  - `value_moat` → ValueMoatStrategy
  - `trend_following` → TrendFollowingStrategy
  - `multi_factor` → MultiFactorStrategy
- `run_backtest(...)`: load data → MarketData → engine → format results dict; optional async progress_callback stages (`loading_data`, `initializing`, `running`, `computing_metrics`, `complete`)
- `get_available_strategies()`: id/name/description list for UI

**Extension:** register new strategies here; swap/add data providers here.

#### Routes — `routes/`

##### `__init__.py`
Exports backtest + strategies modules.

##### `strategies.py`
`GET /api/strategies` → list of `{id, name, description}`.

##### `backtest.py`
- **`POST /api/backtest/run`**: SSE stream. Body **`BacktestRequest`** uses field **`strategy_name`** (not `strategy_id`). Runs service in task, queues progress, persists via repository on success, yields `data: {...}` JSON lines; errors as `event: error`.
- **`GET /api/backtest/{id}`**: full stored result
- **`GET /api/backtest`**: paginated list (summary schema)
- **`DELETE /api/backtest/{id}`**

**Contract mismatch with frontend:** see [§7](#7-known-gaps--honest-maturity).

---

### 4.4 `packages/web/` — React UI

#### Tooling / config

| File | Role |
|------|------|
| `package.json` | Name `quant-factory-web`; React 18, Recharts, Vite 5, Tailwind, TS, ESLint scripts |
| `vite.config.ts` | Port 3000; **proxy `/api` → `http://localhost:8000`** |
| `tsconfig.json` / `tsconfig.node.json` | Strict TS, bundler resolution, React JSX |
| `tailwind.config.js` | Content globs for `index.html` + `src/**` |
| `postcss.config.js` | tailwind + autoprefixer |
| `index.html` | SPA shell; title **Quant Factory - Backtesting Platform** |
| `Dockerfile` | Node 20 Alpine, npm install, `npm run dev -- --host 0.0.0.0` |

#### `src/main.tsx`
React 18 root render of `<App />` with StrictMode; imports global CSS.

#### `src/index.css`
Tailwind directives + base body font stack.

#### `src/App.tsx`
Main layout:

- Header **Quant Factory**
- Progress bar while running
- Error banner
- Grid: `BacktestForm` | `EquityCurve` + `MetricsCard`
- Footer version string
- Calls `runBacktest` and interprets SSE events (progress with date/portfolio_value, complete results, error)

#### `src/api/client.ts`
- `fetchStrategies()` → `GET /api/strategies`
- `runBacktest(request, onEvent)` → `POST /api/backtest/run`, reads stream, parses SSE `event:` + `data:` pairs

Uses `API_BASE_URL = '/api'` (works with Vite proxy).

#### `src/api/index.ts`
**Despite the name, this file holds TypeScript interfaces**, not re-exports:

- `Strategy`, `BacktestRequest` (**`strategy_id`** field), `BacktestResults`, `ProgressEvent`, `BacktestEvent`

**Problem:** `client.ts` and components import from `../types`, but **`src/types/` does not exist**. Types live here instead — TypeScript build will fail until fixed (move to `src/types/index.ts` or fix imports).

#### `src/components/BacktestForm.tsx`
Form: strategy select (loaded from API), tickers CSV string, date range, initial capital. Submits `BacktestRequest` with **`strategy_id`**.

#### `src/components/EquityCurve.tsx`
Recharts line chart of portfolio value over time; running spinner; start/current/change summary.

#### `src/components/MetricsCard.tsx`
Grid of total return, final value, Sharpe, Sortino, max DD, win rate, trades, strategy; “key insights” heuristics.

---

### 4.5 Nested `quant-lab/` directory

```
quant-lab/
  ├── packages/   # near-duplicate of root packages/
  ├── README.md, docker-compose.yml, package.json, pyproject.toml, LICENSE, .env.example
```

This is a **full nested copy** of the monorepo (historical packaging accident or accidental submodule dump). **Source of truth is the root `packages/` tree.** Do not edit both. Candidates for cleanup: delete `quant-lab/` or replace with a git submodule pointer if ever needed.

---

## 5. Strategies summary (behavior)

| ID | Class | Inputs | Entry idea | Exit idea |
|----|-------|--------|------------|-----------|
| `value_moat` | ValueMoatStrategy | Fundamentals + price | High quality + fair value score | Score collapse |
| `trend_following` | TrendFollowingStrategy | OHLCV only | Golden cross + trend + volume | Death cross / stop |
| `multi_factor` | MultiFactorStrategy | Fundamentals + price | Combined factor ≥ threshold | Combined factor low |

All size new longs as ~`max_position_size * portfolio.total_value / price` (integer shares).

---

## 6. Extending toward crypto & broader trading

Planned direction: **more trading**, including **crypto**, without necessarily becoming a full exchange bot on day one. Recommended approach: keep core pure (backtest), add asset-class-aware data and sizing, then optional live adapters later.

### 6.1 What already helps

- `DataProvider` protocol — new `CryptoExchangeProvider` / CCXT / Binance historical klines
- `Strategy` protocol — trend/momentum strategies transfer; multi-factor can reweight to momentum-only
- Fee/slippage bps on `BacktestConfig` / `TradeBuilder` — map to maker/taker later
- Long/short plumbing already in portfolio (funding not modeled)

### 6.2 Gaps to close for crypto

| Area | Today | Needed |
|------|-------|--------|
| Symbols | Equity tickers, length ≤ 10 | Pairs (`BTC/USDT`), venues, bases; relax validators |
| Session | Daily equity-like dates | 24/7 bars; optional hour/minute timeframes |
| Annualization | 252 trading days | 365 (or bar-count aware) for crypto metrics |
| Fundamentals | Equity Fundamentals model | Optional: funding rate, OI, on-chain; or price-only strategies |
| Quantity | Integer shares | Fractional `Decimal` quantities |
| Data path | CSV + unused Yahoo | Exchange REST/WS historical loaders; cache under `data/` |
| Value Moat | Equity ROE/P/E | Disable for crypto or invent token quality factors |
| Live trading | None | Separate package: exchange auth, order state machine; **do not mix into pure backtest engine** |

### 6.3 Suggested incremental roadmap

1. **Fix UI ↔ API contracts** (strategy field names, SSE schema, types path) so equity path is solid.
2. **Fractional quantity + symbol validation** in models/portfolio/strategies.
3. **Crypto data provider** implementing `DataProvider` (klines → OHLCV DataFrame); fundamentals can return `{}`.
4. **Metrics calendar** configurable (`bars_per_year`).
5. **Strategy pack**: keep Trend Following; add crypto-friendly momentum/mean-reversion; gate Value Moat behind asset class.
6. **API**: provider choice in `BacktestRequest` (`csv` | `yahoo` | `crypto`).
7. **UI**: asset class toggle, pair picker, fee presets (spot vs perpetual).
8. **Later:** paper/live execution adapters outside `quant_lab` core.

### 6.4 Where to touch code for a crypto provider

1. `packages/core/quant_lab/data/my_crypto_provider.py` — implement protocol  
2. Export from `data/__init__.py`  
3. `BacktestService.__init__` / `run_backtest` — select provider by request  
4. Optionally relax `Signal.ticker` / `Position.ticker` max_length  
5. Change strategy size calc from `int(...)` to Decimal floor with min notional  

---

## 7. Known gaps & honest maturity

README historically overstated “Production Ready.” Treat **0.1.0 as a scaffold with solid domain design** and incomplete integration polish:

| Issue | Detail |
|-------|--------|
| Missing `src/types` | Frontend imports `../types` but types live in `src/api/index.ts` |
| strategy_id vs strategy_name | Web sends `strategy_id`; API expects `strategy_name` |
| SSE schema drift | API emits stage progress (`loading_data`, …) as plain `data:`; client expects `event: progress` with per-day `date` / `portfolio_value` for live chart |
| No automated tests | pytest paths configured; `packages/*/tests` absent |
| Empty package READMEs | core/api package READMEs not filled |
| Yahoo unused by API | Only CSV in `BacktestService` |
| Sample data paths | Hardcoded `/home/claude/quant-lab/data/` |
| Nested `quant-lab/` | Duplicate tree confuses tooling and agents |
| Trade PnL metrics | Approximated, not true trade-by-trade PnL |
| data/ gitignored | Fresh clone has no price files for CSV provider |
| Alembic listed | Dependency present; migrations not set up (uses `create_all`) |

---

## 8. API quick reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/api/strategies` | List strategies |
| POST | `/api/backtest/run` | Run backtest (SSE) |
| GET | `/api/backtest` | List past runs |
| GET | `/api/backtest/{id}` | Get run |
| DELETE | `/api/backtest/{id}` | Delete run |

Example body (API contract):

```json
{
  "strategy_name": "trend_following",
  "tickers": ["AAPL", "MSFT"],
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "initial_capital": 100000,
  "commission_bps": 5,
  "slippage_bps": 2,
  "rebalance_frequency": 5
}
```

---

## 9. Conventions for contributors & agents

1. **Edit root `packages/`**, not nested `quant-lab/`.
2. Keep **core free of FastAPI/React** — domain logic in `quant_lab` only.
3. New strategies: implement protocol → export → register in `AVAILABLE_STRATEGIES`.
4. New data sources: implement `DataProvider` → wire in service.
5. Prefer **Decimal** for money; avoid float cash math in portfolio paths.
6. Preserve **point-in-time** access in strategies (only use data ≤ `current_date`).
7. Branding: product name **Quant Factory**; repo **SomeRandmGuyy/quant-factory**; Python packages may still say `quant_lab*`.
8. Do not add live trading secrets or exchange keys into core; keep in env / separate package.

---

## 10. Quick mental model

```
Strategy (pure function of MarketData + Portfolio + date)
    → Signals
        → Trades (+ fees)
            → Portfolio transitions
                → Daily equity snapshots
                    → Metrics + API/DB + UI charts
```

Everything else (Docker, React, SQLAlchemy) is delivery and storage around that loop.

---

*Last updated for Quant Factory branding and full tree review. When adding crypto or multi-asset support, update §6 and the file map for any new modules.*
