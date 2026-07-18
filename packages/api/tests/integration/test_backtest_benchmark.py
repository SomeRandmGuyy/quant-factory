import json


def test_backtest_with_benchmark_spy(client):
    payload = {
        "strategy_name": "multi_factor",
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-02",
        "end_date": "2024-02-29",
        "initial_capital": 100000,
        "provider": "csv",
        "benchmark_ticker": "SPY",
        "save_experiment": False,
    }
    with client.stream("POST", "/api/backtest/run", json=payload) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "Internal error" not in body
    found = False
    for line in body.splitlines():
        if line.startswith("data: ") and "excess_return" in line:
            data = json.loads(line[len("data: "):])
            if data.get("stage") == "complete":
                metrics = data["results"]["metrics"]
                assert "excess_return" in metrics
                assert "benchmark_return" in metrics
                found = True
    assert found, body[-800:]
