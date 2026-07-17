import json


def test_backtest_sse_completes_with_json_safe_payload(client):
    payload = {
        "strategy_name": "value_moat",
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-02",
        "end_date": "2024-02-29",
        "initial_capital": 100000,
        "provider": "csv",
    }
    with client.stream("POST", "/api/backtest/run", json=payload) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "Internal error" not in body
    assert "complete" in body
    found = False
    for line in body.splitlines():
        if line.startswith("data: ") and "equity_curve" in line:
            data = json.loads(line[len("data: "):])
            if data.get("stage") == "complete":
                curve = data["results"]["equity_curve"]
                assert isinstance(curve[0]["date"], str)
                found = True
    assert found, body[-500:]
