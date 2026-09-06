"""Migration 004: syrups/batches — pure math, end-to-end API, the two-level
ripple, expiry, guards.

Hand-computed references (2026-09-06):
  Simple syrup 1000 ml:  500 g sugar (kg stock €1.50/1000 g) -> 0.75
                         + 500 ml water free-text €0          -> 0.00
                         total 0.75, per_ml 0.00075
  Spec uses 40 ml syrup  -> 40 x 0.75 / 1000 = 0.03
  Campari tea 500 ml:    Campari 200 ml @ €19/700 = 5.428571
                         + sugar 100 g = 0.15
                         + water 200 ml €0
                         total 5.578571 per 500 ml
  Spec uses 30 ml batch  -> 30 x 5.578571 / 500 = 0.334714
  Campari 19 -> 25:      batch total -> 200x25/700 + 0.15 = 7.292857
                         spec cost -> 30 x 7.292857 / 500 = 0.437571
"""
import pytest
from fastapi.testclient import TestClient

import db
import main
import pricing

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


# ---------- pure pricing ----------

class TestBatchPricing:
    def test_batch_cost_stock_vs_free(self):
        lines = [
            {"stock_item_id": 1, "name": "Sugar", "amount_ml": 500, "unit": "g",
             "bottle_price_eur": 1.5, "bottle_volume_ml": 1000.0,
             "dimension": "weight", "cost_eur": None},
            {"stock_item_id": None, "name": "Water", "amount_ml": 500,
             "unit": "ml", "cost_eur": 0.0},
        ]
        assert pricing.batch_cost(lines) == pytest.approx(0.75, abs=1e-9)

    def test_batch_cost_per_ml_and_serve(self):
        total = 0.75
        assert pricing.batch_cost_per_ml(total, 1000) == pytest.approx(0.00075)
        assert pricing.serve_batch_cost(40, "ml", total, 1000) == pytest.approx(0.03)
        # 4 cl of the same batch is the same 40 ml
        assert pricing.serve_batch_cost(4, "cl", total, 1000) == pytest.approx(0.03)

    def test_line_cost_batch_branch(self):
        line = {"serve_batch": True, "batch_id": 9, "amount_ml": 40, "unit": "ml",
                "batch_cost_total": 0.75, "batch_size_ml": 1000}
        assert pricing.line_cost(line) == pytest.approx(0.03)
        # a batch INGREDIENT row keeps its parent batch_id but no serve marker
        ing = {"batch_id": 9, "stock_item_id": 16, "amount_ml": 500, "unit": "g",
               "bottle_price_eur": 1.5, "bottle_volume_ml": 1000.0,
               "dimension": "weight"}
        assert pricing.line_cost(ing) == pytest.approx(0.75)


# ---------- end-to-end API ----------

class TestBatchApi:
    def _syrup(self):
        db.create_stock_item({"name": "Sugar", "dimension": "weight",
                              "bottle_volume_ml": 1000, "bottle_price_eur": 1.5})
        b = client.post("/api/batches", json={
            "name": "Simple Syrup 1:1", "method": "stir, no heat",
            "batch_size_ml": 1000, "shelf_life_days": 30}).json()
        bid = b["id"]
        client.post(f"/api/batches/{bid}/lines",
                    json={"name": "Sugar", "amount_ml": 500, "unit": "g"})
        client.post(f"/api/batches/{bid}/lines",
                    json={"name": "Water", "amount_ml": 500, "unit": "ml",
                          "cost_eur": 0})
        return client.get(f"/api/batches/{bid}").json()

    def test_batch_cost_derived_end_to_end(self):
        b = self._syrup()
        assert b["cost_eur"] == pytest.approx(0.75, abs=1e-3)
        assert b["cost_per_ml"] == pytest.approx(0.00075, abs=1e-6)
        assert b["line_count"] == 2
        # stock-linked sugar line derives; water line is free-text costed
        bl = [l for l in b["lines"] if l["name"] == "Sugar"][0]
        assert bl["stock_item_id"] is not None and bl["cost_eur"] is None
        w = [l for l in b["lines"] if l["name"] == "Water"][0]
        assert w["stock_item_id"] is None and w["cost_eur"] == 0.0

    def test_spec_uses_batch(self):
        self._syrup()
        spec = client.post("/api/specs", json={"name": "Syrup Soda"}).json()
        r = client.post(f"/api/specs/{spec['id']}/lines",
                        json={"batch_id": 1, "amount_ml": 40, "unit": "ml"})
        assert r.status_code == 200, r.text
        d = r.json()
        line = d["lines"][0]
        assert line["kind"] == "batch" and line["batch_id"] == 1
        assert line["row_cost_eur"] == pytest.approx(0.03, abs=1e-3)
        assert d["summary"]["cost_eur"] == pytest.approx(0.03, abs=1e-3)
        # syrup is liquid: it counts toward drink volume, carries no abv
        assert d["summary"]["total_ml"] == pytest.approx(40.0)
        assert d["summary"]["abv"] == 0.0

    def test_free_text_without_cost_rejected(self):
        client.post("/api/batches", json={"name": "Mystery", "batch_size_ml": 100}).json()
        r = client.post("/api/batches/1/lines",
                        json={"name": "Unicorn dust", "amount_ml": 10, "unit": "g"})
        assert r.status_code == 400
        r2 = client.post("/api/batches/1/lines",
                         json={"name": "Water", "amount_ml": 10, "unit": "ml",
                               "cost_eur": 0})
        assert r2.status_code == 200

    def test_batch_line_unit_must_match_stock_dimension(self):
        db.create_stock_item({"name": "Sugar", "dimension": "weight",
                              "bottle_volume_ml": 1000, "bottle_price_eur": 1.5})
        client.post("/api/batches", json={"name": "Bad", "batch_size_ml": 100}).json()
        r = client.post("/api/batches/1/lines",
                        json={"name": "Sugar", "amount_ml": 500, "unit": "ml"})
        assert r.status_code == 400

    def test_spec_batch_line_volume_units_only(self):
        self._syrup()
        spec = client.post("/api/specs", json={"name": "Grams of syrup?"}).json()
        r = client.post(f"/api/specs/{spec['id']}/lines",
                        json={"batch_id": 1, "amount_ml": 9, "unit": "g"})
        assert r.status_code == 400

    def test_delete_guards(self):
        b = self._syrup()
        spec = client.post("/api/specs", json={"name": "Uses syrup"}).json()
        client.post(f"/api/specs/{spec['id']}/lines",
                    json={"batch_id": b["id"], "amount_ml": 40, "unit": "ml"})
        # batch in use by a spec -> cannot delete
        assert client.delete(f"/api/batches/{b['id']}").status_code == 400
        # stock item used by a batch (but no spec) -> cannot delete stock
        sugar = [s for s in client.get("/api/stock").json() if s["name"] == "Sugar"][0]
        spec2 = client.post("/api/specs", json={"name": "Plain"}).json()
        client.delete(f"/api/specs/{spec2['id']}")
        # move syrup usage out first: delete the spec line, then batch, then sugar
        spec3 = client.post("/api/specs", json={"name": "Tmp"}).json()
        client.delete(f"/api/specs/{spec3['id']}")
        d = client.get(f"/api/specs/{spec['id']}").json()
        client.delete(f"/api/lines/{d['lines'][0]['id']}")
        assert client.delete(f"/api/batches/{b['id']}").status_code == 200
        assert client.delete(f"/api/stock/{sugar['id']}").status_code == 200


class TestTwoLevelRipple:
    def _campari_tea_chain(self):
        # spec -> batch -> Campari bottle (sugar first: the batch line links it)
        sugar = db.create_stock_item({"name": "Sugar", "dimension": "weight",
                                      "bottle_volume_ml": 1000,
                                      "bottle_price_eur": 1.5})
        b = client.post("/api/batches", json={
            "name": "Campari Tea", "batch_size_ml": 500}).json()
        bid = b["id"]
        for line in [
            {"name": "Campari", "amount_ml": 200, "unit": "ml"},
            {"name": "Sugar", "amount_ml": 100, "unit": "g"},
            {"name": "Water", "amount_ml": 200, "unit": "ml", "cost_eur": 0},
        ]:
            r = client.post(f"/api/batches/{bid}/lines", json=line)
            assert r.status_code == 200, r.text
        spec = client.post("/api/specs", json={"name": "Bitter Fizz"}).json()
        r = client.post(f"/api/specs/{spec['id']}/lines",
                        json={"batch_id": bid, "amount_ml": 30, "unit": "ml"})
        assert r.status_code == 200
        # sanity: batch cost must include the real sugar link now
        b2 = client.get(f"/api/batches/{bid}").json()
        assert b2["cost_eur"] == pytest.approx(200 * 19 / 700 + 0.15, abs=1e-3)
        return bid, spec["id"]

    def test_ripple_walks_stock_to_batch_to_spec(self):
        bid, sid = self._campari_tea_chain()
        campari = [s for s in client.get("/api/stock").json()
                   if s["name"] == "Campari"][0]
        r = client.put(f"/api/stock/{campari['id']}", json={
            "name": "Campari", "abv": 25, "bottle_price_eur": 25.0,
            "bottle_volume_ml": 700})
        assert r.status_code == 200, r.text
        impact = r.json()["impact"]
        assert any(i["spec_id"] == sid for i in impact), impact
        row = [i for i in impact if i["spec_id"] == sid][0]
        assert row["name"] == "Bitter Fizz"
        assert row["cost_old"] == pytest.approx(0.335, abs=1e-3)
        assert row["cost_new"] == pytest.approx(0.438, abs=1e-3)
        # and the batch itself reflects the new price immediately
        b2 = client.get(f"/api/batches/{bid}").json()
        assert b2["cost_eur"] == pytest.approx(200 * 25 / 700 + 0.15, abs=1e-3)
        # the spec read fresh also shows the new cost (no stale through layer)
        d = client.get(f"/api/specs/{sid}").json()
        assert d["summary"]["cost_eur"] == pytest.approx(0.438, abs=1e-3)


class TestExpiry:
    def test_days_left(self):
        b = client.post("/api/batches", json={
            "name": "Fresh Batch", "batch_size_ml": 500,
            "shelf_life_days": 14}).json()
        assert b["days_left"] == 14

    def test_expired_red(self):
        b = client.post("/api/batches", json={
            "name": "Old Batch", "batch_size_ml": 500,
            "made_date": "2026-07-01", "shelf_life_days": 30}).json()
        assert b["days_left"] < 0

    def test_no_shelf_life_keeps_forever(self):
        b = client.post("/api/batches", json={
            "name": "Forever Batch", "batch_size_ml": 500}).json()
        assert b["days_left"] is None
