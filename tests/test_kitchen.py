"""Kitchen K1 (migration 009): batch portions + the stock loss log."""
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


class TestBatchServings:
    def _mayo(self):
        db.create_stock_item({"name": "Eggs", "dimension": "count",
                              "bottle_volume_ml": 12, "bottle_price_eur": 3.0})
        db.create_stock_item({"name": "Oil", "dimension": "volume",
                              "bottle_volume_ml": 1000, "bottle_price_eur": 2.5})
        client.post("/api/batches", json={"name": "Mayo 500", "batch_size_ml": 500,
                                          "servings": 20}).json()
        # 4 eggs @ 3/12 = 1.00 ; 200 ml oil @ 2.5/1000 = 0.50 -> 1.50 total
        client.post("/api/batches/1/lines", json={"name": "Eggs", "amount_ml": 4,
                                                  "unit": "piece"})
        client.post("/api/batches/1/lines", json={"name": "Oil", "amount_ml": 200,
                                                  "unit": "ml"})

    def test_cost_per_serve(self):
        self._mayo()
        b = client.get("/api/batches/1").json()
        assert b["servings"] == 20
        assert b["cost_eur"] == pytest.approx(1.5, abs=1e-3)
        assert b["cost_per_serve"] == pytest.approx(0.075, abs=1e-3)  # 1.50/20

    def test_servings_optional(self):
        client.post("/api/batches", json={"name": "Syrup", "batch_size_ml": 1000}).json()
        b = client.get("/api/batches/1").json()
        assert b["servings"] is None and b["cost_per_serve"] is None

    def test_serving_edit_keeps_size(self):
        self._mayo()
        r = client.put("/api/batches/1", json={"name": "Mayo 500", "servings": 40})
        assert r.status_code == 200
        b = client.get("/api/batches/1").json()
        assert b["batch_size_ml"] == 500      # not wiped by partial edit
        assert b["cost_per_serve"] == pytest.approx(round(1.5 / 40, 3), abs=1e-9)

    def test_servings_validation(self):
        r = client.post("/api/batches", json={"name": "Bad", "batch_size_ml": 500,
                                              "servings": 0})
        assert r.status_code == 422
        r = client.post("/api/batches", json={"name": "Bad", "batch_size_ml": 500,
                                              "servings": -3})
        assert r.status_code == 422


class TestAdjustments:
    def _gin(self):
        return [s for s in client.get("/api/stock").json()
                if s["name"] == "London dry gin"][0]

    def test_log_and_list(self):
        g = self._gin()
        r = client.post(f"/api/stock/{g['id']}/adjust",
                        json={"delta": -50, "reason": "Spillage", "note": "sink"})
        assert r.status_code == 200
        body = r.json()
        assert body["delta"] == -50 and body["item_name"] == "London dry gin"
        rows = client.get("/api/stock-adjustments").json()
        assert len(rows) == 1 and rows[0]["reason"] == "Spillage"

    def test_positive_correction_allowed(self):
        g = self._gin()
        client.post(f"/api/stock/{g['id']}/adjust",
                    json={"delta": 25, "reason": "Correction"})
        assert client.get("/api/stock-adjustments").json()[0]["delta"] == 25

    def test_guards(self):
        g = self._gin()
        assert client.post(f"/api/stock/{g['id']}/adjust",
                           json={"delta": 0, "reason": "Waste"}).status_code == 400
        assert client.post(f"/api/stock/{g['id']}/adjust",
                           json={"delta": -10, "reason": "  "}).status_code == 400
        assert client.post("/api/stock/99999/adjust",
                           json={"delta": -10, "reason": "Waste"}).status_code == 400

    def test_snapshots_untouched(self):
        # adjustments must not affect count snapshots / par math
        g = self._gin()
        client.post(f"/api/stock/{g['id']}/adjust",
                    json={"delta": -100, "reason": "Spillage"})
        assert client.get("/api/stock-takes/sheet").status_code == 200
        assert client.get("/api/stock-takes/trends").status_code == 200
