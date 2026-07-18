def test_list_experiments_after_walk_forward(client):
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
    listed = client.get("/api/experiments?kind=walk_forward")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) >= 1
    assert all(row["kind"] == "walk_forward" for row in rows)
