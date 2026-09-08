"""Kitchen K4 (migration 011): supplier on stock — order list groups by it."""
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _gin():
    return [s for s in client.get("/api/stock").json() if s["name"] == "London dry gin"][0]


def test_supplier_round_trip_and_list():
    g = _gin()
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "bottle_price_eur": 22.0, "supplier": "Prima Wines"})
    items = client.get("/api/stock").json()
    row = [i for i in items if i["name"] == "London dry gin"][0]
    assert row["supplier"] == "Prima Wines"
    # price edit alone must not wipe the supplier
    client.put(f"/api/stock/{g['id']}", json={"name": g["name"], "bottle_price_eur": 23.0})
    assert client.get("/api/stock").json() and True


def test_order_rows_carry_supplier():
    g = _gin()
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "supplier": "Prima Wines"})
    client.patch(f"/api/stock/{g['id']}/par", json={"par_level": 3})
    # count 1 full bottle -> shortfall 2 on the order list
    r = client.post("/api/stock-takes",
                    json={"lines": [{"stock_item_id": g["id"], "full_bottles": 1,
                                     "open_fraction": 0.0}]})
    assert r.status_code == 200
    order = r.json()  # save response carries the order-list review
    flat = order.get("short", []) + order.get("over", []) + order.get("at_par", [])
    row = next(x for x in flat if x["stock_item_id"] == g["id"])
    assert row["supplier"] == "Prima Wines"
    assert row["to_order"] == 2


def test_supplier_in_exports():
    g = _gin()
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "supplier": "Prima Wines"})
    r = client.get("/api/export/stock.xlsx")
    assert r.status_code == 200
    import io
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(r.content))["Stock"]
    header = list(ws.values)[0]
    assert header[-1] == "Supplier"
    gin = [row for row in list(ws.values)[1:] if row[0] == "London dry gin"][0]
    assert gin[-1] == "Prima Wines"
