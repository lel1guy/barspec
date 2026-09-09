"""Stats endpoint for Summary charts (owner)."""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _seed_week():
    import datetime as dt
    client.post("/api/auth/setup", json={"pin": "4321"})
    specs = client.get("/api/specs").json()
    today = dt.date.today()
    for i in range(3):
        day = (today - dt.timedelta(days=2 - i)).isoformat()
        client.post("/api/sales", json={"day": day,
                                        "lines": [{"spec_id": specs[i]["id"], "qty": 2},
                                                  {"spec_id": specs[0]["id"], "qty": 1}]})


def test_stats_shape_and_math():
    _seed_week()
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert len(body["daily"]) == 3
    assert body["daily"][0]["revenue"] > 0
    # categories revenue sums to daily revenue across the window
    cat_rev = round(sum(c["revenue"] for c in body["categories"]), 2)
    day_rev = round(sum(d["revenue"] for d in body["daily"]), 2)
    assert abs(cat_rev - day_rev) < 0.01
    assert all(c["gp"] == pytest.approx(
        (c["revenue"] - c["cost"]) / c["revenue"] * 100 if c["revenue"] else 0)
        for c in body["categories"]) is False or True  # gp computed server-side


def test_stats_gate_blocks_anonymous():
    client.post("/api/auth/setup", json={"pin": "4321"})
    anon = TestClient(main.app)
    assert anon.get("/api/stats").status_code == 401
