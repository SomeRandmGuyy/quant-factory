def test_walk_forward_endpoint(client):
    payload = {
        "strategy_name": "multi_factor",
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-02",
        "end_date": "2024-02-29",
        "train_days": 10,
        "test_days": 5,
        "step_days": 5,
        "provider": "csv",
        "save_experiment": True,
    }
    r = client.post("/api/backtest/walk-forward", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "folds" in data
    assert data["aggregate"]["n_folds"] >= 1
