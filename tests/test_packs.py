"""014: purchase packs — case/keg math, straight-serve costing."""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _add(name, **kw):
    r = client.post("/api/stock", json={"name": name, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_case_of_cans_derives_unit_price():
    can = _add("Beer can X", dimension="count", bottle_volume_ml=1,
               pack_size=24, pack_price_eur=18.0, pack_name="case")
    assert can["bottle_price_eur"] == pytest.approx(0.75)
    assert can["pack_price_eur"] == 18.0 and can["pack_size"] == 24
    assert can["pack_name"] == "case"


def test_single_bottle_without_pack_keeps_price():
    b = _add("Wine Y", dimension="volume", bottle_volume_ml=750, bottle_price_eur=9.0)
    assert b["bottle_price_eur"] == 9.0
    assert b["pack_price_eur"] is None


def test_keg_poured_by_the_glass_costs_right():
    keg = _add("Lager Keg 30L", dimension="volume", bottle_volume_ml=30000,
               bottle_price_eur=90.0, abv=5.0)
    s = client.post("/api/specs", json={"name": "Fino", "category": "Cerveja",
                                        "price_eur": 1.8, "target_gp": 70}).json()
    r = client.post(f"/api/specs/{s['id']}/lines",
                    json={"name": "Lager Keg 30L", "amount_ml": 200, "unit": "ml"})
    assert r.status_code == 200, r.text
    d = client.get(f"/api/specs/{s['id']}").json()
    assert d["summary"]["cost_eur"] == pytest.approx(0.6, abs=1e-3)   # 90/30000*200
    assert d["summary"]["abv"] == pytest.approx(5.0)


def test_pack_price_edit_ripples_unit_and_cost():
    can = _add("Soda can Z", dimension="count", bottle_volume_ml=1,
               pack_size=24, pack_price_eur=7.2, pack_name="case")
    assert can["bottle_price_eur"] == pytest.approx(0.3)
    s = client.post("/api/specs", json={"name": "Soda Z", "category": "Bebidas",
                                        "price_eur": 1.5}).json()
    client.post(f"/api/specs/{s['id']}/lines",
                json={"name": "Soda can Z", "amount_ml": 1, "unit": "piece"})
    r = client.put(f"/api/stock/{can['id']}",
                   json={"name": "Soda can Z", "dimension": "count",
                         "bottle_volume_ml": 1, "bottle_price_eur": 0.3,
                         "pack_price_eur": 9.6, "pack_size": 24, "pack_name": "case"})
    assert r.status_code == 200, r.text
    body = r.json()
    it = next(x for x in client.get("/api/stock").json() if x["id"] == can["id"])
    assert it["bottle_price_eur"] == pytest.approx(0.4)
    assert it["pack_price_eur"] == 9.6
    assert body["impact"] and body["impact"][0]["cost_old"] == pytest.approx(0.3)
