# Local development (this server)

## Quick start

```bash
cd /root/.grok/worktrees/repos-quant-factory/quant-factory
source .venv/bin/activate

# API (port 8001 — 8000 is already used on this host)
export PYTHONPATH="$PWD/packages/core:$PWD/packages/api"
uvicorn quant_lab_api.main:app --host 0.0.0.0 --port 8001 --app-dir packages/api

# Web (separate terminal)
cd packages/web
npm run dev -- --host 0.0.0.0 --port 3000
```

- **Web UI:** http://localhost:3000 (or `http://<server-ip>:3000`)
- **API:** http://localhost:8001
- **API docs:** http://localhost:8001/docs

## Configuration

- `.env` at repo root (gitignored) sets SQLite DB, CORS, and `CSV_DATA_DIR` → `./data`
- Sample tickers: `AAPL`, `MSFT`, `TSLA` under `data/*.csv` plus `data/fundamentals.csv`

## Smoke tests

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/api/strategies
```

## Process management

```bash
kill $(cat /tmp/quant-factory-api.pid) 2>/dev/null
kill $(cat /tmp/quant-factory-web.pid) 2>/dev/null
tail -f /tmp/quant-factory-api.log /tmp/quant-factory-web.log
```

## Notes

- Port **8000** is occupied on this host; use **8001**.
- Trend Following may produce **zero trades** on short synthetic data (needs golden cross). Try **Value Moat** or **Multi-Factor** for activity.
- Do not commit `.env` or API keys.


## Data providers

Backtest body field `provider`:

- `csv` (default) — reads `CSV_DATA_DIR`
- `yahoo` — live Yahoo Finance (network)

```bash
curl -N -X POST http://127.0.0.1:8001/api/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"strategy_name":"value_moat","tickers":["AAPL","MSFT"],"start_date":"2024-01-02","end_date":"2024-06-28","initial_capital":100000,"provider":"csv"}'
```

## Tests

```bash
source .venv/bin/activate
export PYTHONPATH=packages/core:packages/api
pytest packages/core/tests packages/api/tests -q -m "not network"
cd packages/web && npm test
```


## Phase 1 APIs

```bash
# Walk-forward
curl -X POST http://127.0.0.1:8001/api/backtest/walk-forward \
  -H 'Content-Type: application/json' \
  -d '{"strategy_name":"multi_factor","tickers":["AAPL","MSFT"],"start_date":"2024-01-02","end_date":"2024-02-29","train_days":10,"test_days":5,"step_days":5,"provider":"csv"}'

# Experiments
curl http://127.0.0.1:8001/api/experiments

# CLI
export PYTHONPATH=packages/core
python -m quant_lab.cli backtest --strategy multi_factor --tickers AAPL,MSFT \
  --start 2024-01-02 --end 2024-02-29 --provider csv \
  --data-dir packages/core/tests/fixtures/sample_prices
```


## Phase 2 risk controls

Backtest body may include:

- `sizer`: `percent` | `vol_target` | `equal_weight`
- `max_position_pct`, `max_gross_leverage`, `max_drawdown_halt`, `enable_risk_gate`
- `stop_loss_pct`, `take_profit_pct`, `time_stop_days`
- Results metrics: `var_95`, `cvar_95`, plus `underwater_curve`
