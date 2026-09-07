"""Migration 005: yield_frac on stock — restaurant costing unlock.

Hand math (2026-09-06): pork 1 kg @ €6, yield 0.80 (trim + cook loss) ->
usable 800 g -> cost €6 / (1000 x 0.80) = €0.0075/g. A 150 g portion costs
€1.125 (was €0.90 ignoring trim). Batch-linked: the same pork in a ragu
batch costs through too. Ripple inherits yield with zero extra code.
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


class TestPricing:
    def test_yield_divides_purchase(self):
        line = {"name": "Pork shoulder", "amount_ml": 150, "unit": "g",
                "bottle_price_eur": 6.0, "bottle_volume_ml": 1000.0,
                "dimension": "weight", "yield_frac": 0.8}
        assert pricing.line_cost(line) == pytest.approx(150 * 6 / 800, abs=1e-9)

    def test_default_yield_is_byte_identical(self):
        plain = {"name": "Pork", "amount_ml": 150, "unit": "g",
                 "bottle_price_eur": 6.0, "bottle_volume_ml": 1000.0,
                 "dimension": "weight"}
        explicit = dict(plain, yield_frac=1.0)
        assert pricing.line_cost(plain) == pricing.line_cost(explicit)

    def test_volume_yield_also_honoured(self):
        # 500 ml juice concentrate reduces to 400 ml usable
        line = {"name": "Juice", "amount_ml": 50, "unit": "ml",
                "bottle_price_eur": 2.0, "bottle_volume_ml": 500.0,
                "dimension": "volume", "yield_frac": 0.8}
        assert pricing.line_cost(line) == pytest.approx(50 * 2 / 400, abs=1e-9)


class TestYieldApi:
    def _pork(self, yield_frac=0.8):
        return db.create_stock_item({"name": "Pork shoulder", "dimension": "weight",
                                     "bottle_volume_ml": 1000,
                                     "bottle_price_eur": 6.0,
                                     "yield_frac": yield_frac})

    def test_stock_item_carries_yield(self):
        item = self._pork()
        assert item["yield_frac"] == pytest.approx(0.8)

    def test_spec_cost_honours_yield(self):
        self._pork()
        spec = client.post("/api/specs", json={"name": "Pork plate"}).json()
        r = client.post(f"/api/specs/{spec['id']}/lines",
                        json={"name": "Pork shoulder", "amount_ml": 150, "unit": "g"})
        assert r.status_code == 200, r.text
        d = client.get(f"/api/specs/{spec['id']}").json()
        assert d["summary"]["cost_eur"] == pytest.approx(150 * 6 / 800, abs=1e-3)
        assert d["lines"][0]["row_cost_eur"] == pytest.approx(1.125, abs=1e-3)

    def test_batch_cost_honours_yield(self):
        self._pork()
        client.post("/api/batches", json={"name": "Ragu", "batch_size_ml": 1000}).json()
        r = client.post("/api/batches/1/lines",
                        json={"name": "Pork shoulder", "amount_ml": 500, "unit": "g"})
        assert r.status_code == 200, r.text
        b = client.get("/api/batches/1").json()
        # 500 g of meat that only yields 80% of its bought weight
        assert b["cost_eur"] == pytest.approx(500 * 6 / 800, abs=1e-3)

    def test_yield_invalid_values_422(self):
        for bad in (0, 1.5, -0.2):
            r = client.post("/api/stock", json={"name": f"Bad {bad}", "dimension": "weight",
                                                "bottle_volume_ml": 1000,
                                                "bottle_price_eur": 5.0,
                                                "yield_frac": bad})
            assert r.status_code == 422, f"yield {bad} should 422"

    def test_ripple_math_includes_yield(self):
        item = self._pork()
        spec = client.post("/api/specs", json={"name": "Pork plate"}).json()
        client.post(f"/api/specs/{spec['id']}/lines",
                    json={"name": "Pork shoulder", "amount_ml": 150, "unit": "g"})
        r = client.put(f"/api/stock/{item['id']}", json={
            "name": "Pork shoulder", "dimension": "weight", "bottle_volume_ml": 1000,
            "bottle_price_eur": 7.2, "yield_frac": 0.8})
        assert r.status_code == 200
        imp = [i for i in r.json()["impact"] if i["name"] == "Pork plate"]
        assert len(imp) == 1
        # 150 x 7.2 / 800 = 1.35 ; old 150 x 6 / 800 = 1.125
        assert imp[0]["cost_old"] == pytest.approx(1.125, abs=1e-3)
        assert imp[0]["cost_new"] == pytest.approx(1.35, abs=1e-3)

    def test_edit_without_yield_keeps_it(self):
        item = self._pork()
        # exclude_unset PUT: price-only edit must not reset yield to 1.0
        r = client.put(f"/api/stock/{item['id']}", json={
            "name": "Pork shoulder", "dimension": "weight", "bottle_volume_ml": 1000,
            "bottle_price_eur": 6.5})
        assert r.status_code == 200
        items = client.get("/api/stock").json()
        pork = [s for s in items if s["name"] == "Pork shoulder"][0]
        assert pork["yield_frac"] == pytest.approx(0.8)
