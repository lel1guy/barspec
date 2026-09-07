"""Migration 006: categories — menu sections + spec-list filtering.

Free-form category on specs (bar decides the taxonomy). Partial PUTs must
never wipe it (exclude_unset) — a menu price edit carries no category.
Duplicate keeps category AND (latent-004 fix) batch-pour lines.
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


class TestCategoryApi:
    def test_create_and_list_category(self):
        client.post("/api/specs", json={"name": "Sbagliato", "category": "Spritz"})
        specs = client.get("/api/specs").json()
        sb = [s for s in specs if s["name"] == "Sbagliato"][0]
        assert sb["category"] == "Spritz"
        assert sb["name"] == "Sbagliato"  # seed still there

    def test_menu_carries_category(self):
        client.post("/api/specs", json={"name": "Sbagliato", "category": "Spritz"})
        menu = client.get("/api/menu").json()
        sb = [m for m in menu if m["name"] == "Sbagliato"][0]
        assert sb["category"] == "Spritz"

    def test_seed_specs_uncategorised(self):
        specs = client.get("/api/specs").json()
        assert all(s["category"] is None for s in specs)

    def test_partial_put_preserves_category(self):
        client.post("/api/specs", json={"name": "Sbagliato", "category": "Spritz"})
        sid = [s for s in client.get("/api/specs").json()
               if s["name"] == "Sbagliato"][0]["id"]
        # menu-style price-only edit (subset payload)
        r = client.put(f"/api/specs/{sid}", json={"name": "Sbagliato",
                                                  "price_eur": 8.0, "target_gp": 70})
        assert r.status_code == 200
        s = client.get(f"/api/specs/{sid}").json()
        assert s["category"] == "Spritz"     # not wiped
        assert s["price_eur"] == 8.0

    def test_update_category_and_clear(self):
        client.post("/api/specs", json={"name": "Sbagliato", "category": "Spritz"})
        sid = [s for s in client.get("/api/specs").json()
               if s["name"] == "Sbagliato"][0]["id"]
        client.put(f"/api/specs/{sid}", json={"name": "Sbagliato",
                                              "category": "Aperitivos"})
        assert client.get(f"/api/specs/{sid}").json()["category"] == "Aperitivos"
        client.put(f"/api/specs/{sid}", json={"name": "Sbagliato", "category": None})
        assert client.get(f"/api/specs/{sid}").json()["category"] is None

    def test_duplicate_keeps_category_and_batch_lines(self):
        # latent-004 regression: a spec pouring a house syrup must duplicate
        db.create_stock_item({"name": "Sugar", "dimension": "weight",
                              "bottle_volume_ml": 1000, "bottle_price_eur": 1.5})
        client.post("/api/batches", json={"name": "Simple Syrup 1:1",
                                          "batch_size_ml": 1000}).json()
        client.post("/api/batches/1/lines",
                    json={"name": "Sugar", "amount_ml": 500, "unit": "g"})
        client.post("/api/batches/1/lines",
                    json={"name": "Water", "amount_ml": 500, "unit": "ml",
                          "cost_eur": 0})
        spec = client.post("/api/specs", json={"name": "Syrup Soda",
                                               "category": "Soft drinks"}).json()
        client.post(f"/api/specs/{spec['id']}/lines",
                    json={"batch_id": 1, "amount_ml": 40, "unit": "ml"})
        r = client.post(f"/api/specs/{spec['id']}/duplicate")
        assert r.status_code == 200
        dup = r.json()
        assert dup["name"] == "Syrup Soda (copy)"
        assert dup["category"] == "Soft drinks"
        assert len(dup["lines"]) == 1
        line = dup["lines"][0]
        assert line["kind"] == "batch" and line["batch_id"] == 1
        assert line["row_cost_eur"] == pytest.approx(0.03, abs=1e-3)
        assert dup["summary"]["cost_eur"] == pytest.approx(0.03, abs=1e-3)
