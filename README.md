# Quant Factory

**Algorithmic trading backtesting platform** by [SomeRandmGuyy](https://github.com/SomeRandmGuyy).

Repository: **[https://github.com/SomeRandmGuyy/quant-factory](https://github.com/SomeRandmGuyy/quant-factory.git)**

Open-source lab for backtesting trading strategies with real-time visualization. Built as a monorepo (Python core + FastAPI + React). Equity-focused today; designed to extend toward crypto and broader trading.

> Looking for a deep file-by-file map of the codebase? See **[GROK.md](./GROK.md)**.

## Features

- **3 Strategies**: Value Moat (Buffett-inspired), Trend Following, Multi-Factor
- **Event-Driven Backtesting**: Point-in-time data access helps prevent look-ahead bias
- **Real-Time Streaming**: Server-Sent Events (SSE) for backtest progress
- **Modern Stack**: FastAPI + React + PostgreSQL/SQLite
- **Type-Safe**: Python type hints + TypeScript
- **Performance Metrics**: Sharpe, Sortino, Max Drawdown, Win Rate

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **OR:** Python 3.11+, Node.js 20+, PostgreSQL (optional)

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/SomeRandmGuyy/quant-factory.git
cd quant-factory

docker-compose up

# Web UI:  http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Core library
cd packages/core
pip install -e .

# 2. API package + deps
cd ../api
pip install -e .
# or: pip install fastapi uvicorn sqlalchemy pydantic-settings

# 3. Web UI
cd ../web
npm install

# 4. API server (Terminal 1)
cd packages/api
export PYTHONPATH=../core:.
python -m quant_lab_api.main
# → http://localhost:8000

# 5. Web server (Terminal 2)
cd packages/web
npm run dev
# → http://localhost:3000
```

> **Note:** Python import packages are still named `quant_lab` / `quant_lab_api` (legacy module paths). The product and repository are **Quant Factory**.

## Architecture

```
quant-factory/
├── packages/
│   ├── core/           # Python library (portfolio, strategies, backtesting)
│   ├── api/            # FastAPI service (REST + SSE streaming)
│   └── web/            # React UI (Vite + Tailwind + Recharts)
├── data/               # Local data cache (gitignored; provide CSVs for runs)
├── docker-compose.yml  # Full-stack orchestration
├── GROK.md             # Detailed project map for humans & agents
└── README.md
```

### Technology Stack

**Backend**

- FastAPI — async API
- SQLAlchemy — ORM (PostgreSQL / SQLite)
- Pandas / NumPy — quantitative analysis
- Pydantic — validation

**Frontend**

- React 18 + TypeScript
- Recharts — charts
- Tailwind CSS
- Vite

## Usage

### Running a Backtest

1. Open the Web UI: http://localhost:3000
2. Select a strategy: Value Moat, Trend Following, or Multi-Factor
3. Configure parameters:
   - Tickers: `AAPL,MSFT,TSLA` (comma-separated)
   - Date range: e.g. 2024-01-01 → 2024-06-30
   - Initial capital: `$100,000`
4. Click **Run Backtest**
5. Review the equity curve and performance metrics

### API Endpoints

```bash
# List strategies
curl http://localhost:8000/api/strategies

# Run backtest (SSE stream)
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "value_moat",
    "tickers": ["AAPL", "MSFT"],
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "initial_capital": 100000
  }'

# Health check
curl http://localhost:8000/health
```

## Trading Strategies

### 1. Value Moat Strategy

**Philosophy:** Buffett-inspired quality at reasonable prices

**Criteria:**

- ROE > 15%
- Revenue growth > 10%
- P/E reasonable (not overvalued)

**Use case:** Longer-horizon quality equities

### 2. Trend Following Strategy

**Philosophy:** Momentum-based systematic trading

**Criteria:**

- Moving average crossovers (20 / 50 / 200)
- Price momentum
- Volume confirmation

**Use case:** Capturing sustained trends (also a good fit for crypto price series)

### 3. Multi-Factor Strategy

**Philosophy:** Hybrid factor approach

**Criteria:**

- Value + quality + momentum scores
- Configurable weights and entry/exit thresholds

**Use case:** Balanced multi-signal exposure

## Performance Metrics

- **Total Return** — gain/loss over the backtest period
- **Sharpe Ratio** — risk-adjusted return
- **Sortino Ratio** — downside risk-adjusted return
- **Max Drawdown** — largest peak-to-trough decline
- **Win Rate** — share of profitable trades (approx.)

## Configuration

### Environment Variables

Copy `.env.example` to `.env` in the project root:

```env
# Application
APP_NAME=Quant Factory API
APP_VERSION=0.1.0
DEBUG=true

# Database (SQLite for local dev)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./quant_lab.db

# Or PostgreSQL
# DATABASE_TYPE=postgresql
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_USER=quantlab
# POSTGRES_PASSWORD=quantlab
# POSTGRES_DB=quantlab

# API
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Web
VITE_API_URL=http://localhost:8000
```

### Database Options

**SQLite (default):** no setup required.

**PostgreSQL:** used automatically via `docker-compose` (service `postgres`).

## Development

### Project Structure

```
packages/core/          # Core library (import: quant_lab)
├── quant_lab/
│   ├── data/          # Data providers (CSV, Yahoo)
│   ├── portfolio/     # Portfolio management
│   ├── strategies/    # Trading strategies
│   ├── backtesting/   # Backtesting engine
│   └── models/        # Domain models
└── tests/

packages/api/           # FastAPI service (import: quant_lab_api)
├── quant_lab_api/
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   ├── repositories/  # Data access
│   └── database/      # ORM models
└── tests/

packages/web/           # React frontend
├── src/
│   ├── components/    # UI components
│   └── api/           # API client + types
└── ...
```

### Running Tests

```bash
cd packages/core && pytest
cd packages/api && pytest
cd packages/web && npm test
```

> Test suites are configured but may still be incomplete in v0.1.0.

### Code Quality

```bash
black packages/core packages/api
mypy packages/core packages/api
cd packages/web && npm run lint
```

## Extending the Platform

### Adding a New Strategy

1. Create a strategy under `packages/core/quant_lab/strategies/`:

```python
from quant_lab.strategies.protocols import Strategy

class MyStrategy:
    name = "My Strategy"
    description = "My custom trading strategy"

    def generate_signals(self, market_data, portfolio, current_date):
        signals = []
        # Your logic here
        return signals
```

2. Register it in `packages/api/quant_lab_api/services/backtest_service.py`:

```python
AVAILABLE_STRATEGIES = {
    "my_strategy": MyStrategy,
    # ... existing strategies
}
```

### Adding Data Providers

Implement the `DataProvider` protocol in `packages/core/quant_lab/data/protocols.py` (CSV and Yahoo Finance are already available). For crypto, add an exchange/klines provider and wire it in `BacktestService`.

See **[GROK.md](./GROK.md)** for a crypto / multi-asset extension roadmap.

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Port conflicts | Change ports in `docker-compose.yml` or Vite/API config |
| Database connection | Check Postgres is up and credentials match `.env` |
| CORS errors | Add your frontend origin to `CORS_ORIGINS` |
| SSE buffering | Test with `curl` first; some proxies buffer event streams |
| Missing market data | API expects CSVs under the configured data dir (Docker: `/app/data`) |

## Contributing

1. Fork [SomeRandmGuyy/quant-factory](https://github.com/SomeRandmGuyy/quant-factory)
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -am 'Add feature'`
4. Push: `git push origin feature/my-feature`
5. Open a pull request

## License

MIT License © 2025 [SomeRandmGuyy](https://github.com/SomeRandmGuyy) — see [LICENSE](./LICENSE).

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Recharts](https://recharts.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pandas](https://pandas.pydata.org/)

---

| | |
|--|--|
| **Project** | Quant Factory |
| **Owner** | [SomeRandmGuyy](https://github.com/SomeRandmGuyy) |
| **Repository** | [github.com/SomeRandmGuyy/quant-factory](https://github.com/SomeRandmGuyy/quant-factory.git) |
| **Version** | 0.1.0 |
| **License** | MIT |
