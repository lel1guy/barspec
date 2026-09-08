"""A.7: daily sales -> actual GP + shrinkage."""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _spec(name):
    return [s for s in client.get("/api/specs").json() if s["name"] == name][0]


def _gin():
    return [s for s in client.get("/api/stock").json()
            if s["name"] == "London dry gin"][0]


def _day():
    return "2026-09-05"


def test_post_summary_and_snapshot_freezing():
    neg = _spec("Negroni")
    client.put(f"/api/specs/{neg['id']}", json={"name": "Negroni", "price_eur": 9.5})
    r = client.post("/api/sales", json={"day": _day(),
                                        "lines": [{"spec_id": neg["id"], "qty": 10}]})
    assert r.status_code == 200 and r.json()["created"] == 1
    # re-post replaces (idempotent), never duplicates
    r2 = client.post("/api/sales", json={"day": _day(),
                                         "lines": [{"spec_id": neg["id"], "qty": 15}]})
    assert r2.json() == {"created": 0, "updated": 1, "skipped": []}
    s = client.get(f"/api/sales/summary?from_day={_day()}&to_day={_day()}").json()
    assert s["totals"]["qty"] == 15
    # snapshot freeze: change the price AFTER posting, GP stays on the old price
    cost_before = s["rows"][0]["cost"] / s["rows"][0]["qty"]
    client.put(f"/api/specs/{neg['id']}", json={"name": "Negroni", "price_eur": 12.0})
    s2 = client.get(f"/api/sales/summary?from_day={_day()}&to_day={_day()}").json()
    assert s2["totals"]["revenue"] == pytest.approx(15 * 9.5, abs=0.01)
    assert s2["rows"][0]["cost"] == pytest.approx(cost_before * 15, abs=0.05)
    gp = s2["totals"]
    assert gp["gp_pct"] == pytest.approx(100 * (gp["gp_eur"] / gp["revenue"]), abs=0.1)


def test_unpriced_spec_skipped_and_delete():
    # a spec with NO price can't be posted (no revenue basis)
    r = client.post("/api/specs", json={"name": "Ghost spec", "glass": "Rocks"})
    ghost_id = r.json()["id"]
    res = client.post("/api/sales", json={"day": _day(),
                                          "lines": [{"spec_id": ghost_id, "qty": 1}]})
    assert res.json()["skipped"] == ["Ghost spec"]
    neg = _spec("Negroni")
    client.put(f"/api/specs/{neg['id']}", json={"name": "Negroni", "price_eur": 8.0})
    client.post("/api/sales", json={"day": _day(),
                                    "lines": [{"spec_id": neg["id"], "qty": 2}]})
    line = client.get(f"/api/sales?from_day={_day()}&to_day={_day()}").json()[0]
    assert client.delete(f"/api/sales/{line['id']}").status_code == 200
    assert client.get("/api/sales").json() == []


def test_bad_day_and_bad_qty_rejected():
    neg = _spec("Negroni")
    client.put(f"/api/specs/{neg['id']}", json={"name": "Negroni", "price_eur": 8.0})
    assert client.post("/api/sales", json={"day": "05/09/2026",
                                           "lines": [{"spec_id": neg["id"], "qty": 1}]}).status_code == 422
    assert client.post("/api/sales", json={"day": _day(),
                                           "lines": [{"spec_id": neg["id"], "qty": 0}]}).status_code == 422
    assert client.post("/api/sales", json={"day": _day(), "lines": []}).status_code == 422


def test_shrinkage_clean_when_sales_match_usage():
    import db as dbm
    # server stamps takes/sales with date('now') (UTC) — use the SAME clock
    # so a local/UTC date boundary (midnight) can never desync the window
    day = dbm._conn().execute("SELECT date('now')").fetchone()[0]
    neg = _spec("Negroni")
    client.put(f"/api/specs/{neg['id']}", json={"name": "Negroni", "price_eur": 9.0})
    gin = _gin()
    client.patch(f"/api/stock/{gin['id']}/par", json={"par_level": 5})
    # older count: 3 full gins ; newest: 1 full -> used 2 bottles = 1400 ml
    client.post("/api/stock-takes", json={"lines": [
        {"stock_item_id": gin["id"], "full_bottles": 3, "open_fraction": 0.0}]})
    # same-day re-post REPLACES by design — post once with the full qty
    client.post("/api/sales", json={"day": day,
                                    "lines": [{"spec_id": neg["id"], "qty": 40}]})
    client.post("/api/stock-takes", json={"lines": [
        {"stock_item_id": gin["id"], "full_bottles": 1, "open_fraction": 0.0}]})
    s = client.get("/api/sales/shrinkage").json()
    assert s["window"] == [day, day]
    gin_row = next(r for r in s["rows"] if r["name"] == "London dry gin")
    # expected = sales x the spec's real gin pour (whatever the seed says)
    det = client.get(f"/api/specs/{neg['id']}").json()
    pour = next(l["amount_ml"] for l in det["lines"]
                if l.get("stock_item_id") == gin["id"])
    assert gin_row["expected_ml"] == pytest.approx(40 * pour, abs=0.1)
    assert gin_row["used_ml"] == pytest.approx(1400.0, abs=0.1)   # 2 bottles gone
    # 40 drinks can't account for 1400 ml when the pour is < 35 ml: a leak
    assert gin_row["diff_eur"] > 0
    assert s["leak_eur"] > 0


def test_shrinkage_needs_two_counts():
    assert client.get("/api/sales/shrinkage").json()["window"] is None
