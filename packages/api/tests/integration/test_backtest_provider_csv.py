import json


def test_unknown_provider_errors(client):
    payload = {
        "strategy_name": "value_moat",
        "tickers": ["AAPL"],
        "start_date": "2024-01-02",
        "end_date": "2024-01-31",
        "provider": "not_a_provider",
    }
    # pydantic rejects invalid literal with 422
    r = client.post("/api/backtest/run", json=payload)
    assert r.status_code == 422
