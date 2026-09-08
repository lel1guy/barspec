"""Dashboard/attention endpoint (progress-audit gap #1)."""
import datetime
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _stock_id(name):
    return next(i["id"] for i in client.get("/api/stock").json() if i["name"] == name)


def test_dashboard_shape_when_empty():
    d = client.get("/api/dashboard").json()
    assert d["last_count"] is None
    assert d["low"] == [] and d["expiring"] == []
    assert d["losses_month"] == 0.0 and d["loss_entries_month"] == 0


def test_low_stock_after_a_count_below_par():
    gin = _stock_id("London dry gin")
    client.patch(f"/api/stock/{gin}/par", json={"par_level": 3})   # par lives on its own endpoint
    client.post("/api/stock-takes", json={"lines": [
        {"stock_item_id": gin, "full_bottles": 1, "open_fraction": 0.0}]})
    d = client.get("/api/dashboard").json()
    assert d["last_count"] is not None
    assert any(r["name"] == "London dry gin" and r["need"] == 2 for r in d["low"])
    assert d["needs_count_days"] == 0


def test_losses_month_counted_in_euros():
    gin = _stock_id("London dry gin")   # seed price €22 / 700 ml
    client.post(f"/api/stock/{gin}/adjust", json={
        "delta": -140.0, "reason": "Spillage", "note": "drop"})
    d = client.get("/api/dashboard").json()
    assert d["loss_entries_month"] == 1
    assert d["losses_month"] == round(140 * (22.0 / 700.0), 2)
