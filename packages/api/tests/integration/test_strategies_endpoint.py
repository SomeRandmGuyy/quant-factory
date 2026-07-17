def test_list_strategies_shape(client):
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
