"""S2: audit trail — the receipts book for money-touching edits."""
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _gin():
    return [s for s in client.get("/api/stock").json()
            if s["name"] == "London dry gin"][0]


def _audit():
    return client.get("/api/audit").json()


def test_price_edit_logged_old_to_new():
    g = _gin()
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "bottle_price_eur": 20.0})
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "bottle_price_eur": 24.5})
    rows = _audit()
    assert rows[0]["action"] == "price"
    assert rows[0]["target"] == "London dry gin"
    assert rows[0]["detail"] == "€20.00 -> €24.50"


def test_noop_edit_not_logged():
    g = _gin()
    client.put(f"/api/stock/{g['id']}",
               json={"name": g["name"], "bottle_price_eur": g["bottle_price_eur"]})
    assert _audit() == []


def test_spec_price_change_logged():
    neg = [s for s in client.get("/api/specs").json() if s["name"] == "Negroni"][0]
    client.put(f"/api/specs/{neg['id']}",
               json={"name": "Negroni", "price_eur": 9.5})
    rows = _audit()
    assert rows[0]["action"] == "spec_price"
    assert rows[0]["target"] == "Negroni"
    assert "-> €9.50" in rows[0]["detail"]


def test_deletes_logged():
    g = _gin()
    r = client.delete(f"/api/stock/{g['id']}")
    assert r.status_code == 409  # in use — nothing logged
    assert _audit() == []
    client.post("/api/stock", json={"name": "Orphan", "dimension": "volume",
                                    "bottle_volume_ml": 700, "bottle_price_eur": 3.0})
    orphan = [s for s in client.get("/api/stock").json() if s["name"] == "Orphan"][0]
    client.delete(f"/api/stock/{orphan['id']}")
    assert _audit()[0]["target"] == "Orphan"


def test_trail_is_append_only_newest_first():
    g = _gin()
    client.put(f"/api/stock/{g['id']}", json={"name": g["name"], "bottle_price_eur": 20})
    client.put(f"/api/stock/{g['id']}", json={"name": g["name"], "bottle_price_eur": 21})
    client.put(f"/api/stock/{g['id']}", json={"name": g["name"], "bottle_price_eur": 22})
    rows = _audit()
    assert [r["detail"] for r in rows[:2]] == ["€21.00 -> €22.00", "€20.00 -> €21.00"]
