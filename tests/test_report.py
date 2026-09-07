"""K2 report: section P&L + dead stock."""
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _seed_two_sections():
    # Classic: Negroni 90 ml @ ~2.197 priced at 9.50; Espresso Martini priced 11
    for s in client.get("/api/specs").json():
        if s["name"] in ("Negroni", "Espresso Martini"):
            client.put(f"/api/specs/{s['id']}",
                       json={"name": s["name"], "category": "Classics",
                             "price_eur": 9.5 if s["name"] == "Negroni" else 11.0})
    # Unpriced, uncategorised spec for the '—' bucket
    client.post("/api/specs", json={"name": "Staff Drink", "price_eur": None})
    return client.get("/api/specs").json()


def test_pnl_sections_and_margins():
    _seed_two_sections()
    r = client.get("/api/report/pnl")
    assert r.status_code == 200
    report = r.json()
    cats = {s["category"]: s for s in report["sections"]}
    classics = cats["Classics"]
    assert classics["spec_count"] == 2
    # avg cost ~ (2.197 + espresso martini cost) / 2 — check cost sanity range
    assert 1.5 < classics["avg_cost"] < 3.0
    assert classics["avg_price"] == pytest.approx(10.25, abs=0.01)  # (9.5+11)/2
    # margin = (10.25 - avg_cost)/10.25
    expect = round((10.25 - classics["avg_cost"]) / 10.25 * 100, 1)
    assert classics["margin_pct"] == pytest.approx(expect, abs=0.1)
    assert "—" in cats  # the staff drink bucket exists


def test_dead_stock_counts_only_unused():
    _seed_two_sections()
    # an item nobody uses: shelf value asleep
    db.create_stock_item({"name": "Verjus bottle", "dimension": "volume",
                          "bottle_volume_ml": 750, "bottle_price_eur": 12.0})
    report = client.get("/api/report/pnl").json()
    names = {d["name"] for d in report["dead_items"]}
    assert "Verjus bottle" in names
    assert "London dry gin" not in names   # used by specs
    total = round(sum(d["value_eur"] for d in report["dead_items"]), 2)
    assert report["dead_stock_eur"] == total
    assert total >= 12.0
