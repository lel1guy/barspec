"""015: purchase orders — frozen prices, partial receive, drift, history."""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _setup():
    client.post("/api/auth/setup", json={"pin": "4321"})


def _add(name="Beer X", price=18.0, size=24, dim="count"):
    r = client.post("/api/stock", json={"name": name, "dimension": dim,
                                        "bottle_volume_ml": 1 if dim == "count" else 750,
                                        "bottle_price_eur": price if not size else 0,
                                        "pack_size": size, "pack_price_eur": price if size else None,
                                        "pack_name": "case"})
    assert r.status_code == 200, r.text
    return r.json()


def test_po_opens_with_frozen_prices():
    _setup()
    can = _add("Beer X", price=14.4, size=24)
    r = client.post("/api/pos", json={"supplier": "Makro Cash and Carry",
                                      "lines": [{"stock_item_id": can["id"], "qty": 2}]})
    assert r.status_code == 200, r.text
    po = r.json()
    assert po["status"] == "open" and po["line_count"] == 1
    assert po["lines"][0]["unit_price_eur"] == pytest.approx(0.6)   # 14.4/24 frozen


def test_price_rise_before_receive_detects_drift():
    _setup()
    can = _add("Beer Y", price=14.4, size=24)
    po = client.post("/api/pos", json={"supplier": "CCEP",
                                       "lines": [{"stock_item_id": can["id"], "qty": 5}]}).json()
    # supplier raises the price after the order; stored cost unchanged
    client.put(f"/api/stock/{can['id']}",
               json={"name": "Beer Y", "dimension": "count", "bottle_volume_ml": 1,
                     "bottle_price_eur": 0.6, "pack_size": 24,
                     "pack_price_eur": 16.8, "pack_name": "case"})
    r = client.post(f"/api/pos/{po['id']}/receive", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["po"]["status"] == "received"
    assert body["received_eur"] == pytest.approx(3.0)               # old frozen 0.6 × 5
    assert len(body["drift"]) == 1
    assert body["drift"][0]["invoice_unit"] == pytest.approx(0.6)
    assert body["drift"][0]["stored_unit"] == pytest.approx(0.7)


def test_partial_receive_keeps_po_open():
    _setup()
    can = _add("Beer Z", price=14.4, size=24)
    po = client.post("/api/pos", json={"supplier": "Super Bock Group",
                                       "lines": [{"stock_item_id": can["id"], "qty": 4}]}).json()
    r = client.post(f"/api/pos/{po['id']}/receive",
                    json={"lines": [{"stock_item_id": can["id"], "qty": 1}]})
    assert r.status_code == 200
    body = r.json()
    assert body["po"]["status"] == "open"
    assert body["po"]["lines"][0]["qty_received"] == 1
    # receive the rest -> closes
    r2 = client.post(f"/api/pos/{po['id']}/receive", json={})
    assert r2.json()["po"]["status"] == "received"


def test_price_history_records_paid_units():
    _setup()
    can = _add("Beer H", price=14.4, size=24)
    po = client.post("/api/pos", json={"supplier": "CCEP",
                                       "lines": [{"stock_item_id": can["id"], "qty": 2}]}).json()
    client.post(f"/api/pos/{po['id']}/receive", json={})
    h = client.get(f"/api/stock/{can['id']}/price-history").json()
    assert len(h) == 1 and h[0]["unit_price_eur"] == pytest.approx(0.6)
    assert h[0]["qty_received"] == 2


def test_pos_owner_gated():
    client.post("/api/auth/setup", json={"pin": "4321"})
    anon = TestClient(main.app)
    assert anon.get("/api/pos").status_code == 401
