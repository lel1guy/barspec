"""Migration 007: dilution % — ice melt during shake/stir.

Hand math (2026-09-07): Negroni recipe 90 ml @ 25.9% ABV. Hard-shaken specs
run ~25% melt, stirred ~10-15%. A shaken variant at 25%: served 112.5 ml,
served ABV 25.9 / 1.25 = 20.7%. Cost unchanged (water is free) — the recipe
volume is still the measured pour.
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
    def test_served_volume(self):
        assert pricing.served_volume(90, 25) == pytest.approx(112.5)
        assert pricing.served_volume(90, 0) == 90.0

    def test_served_abv(self):
        # 25.9% recipe, 25% dilution -> same alcohol in 1.25x liquid
        assert pricing.served_abv(25.9, 25) == pytest.approx(20.72, abs=0.01)
        assert pricing.served_abv(25.9, 0) == pytest.approx(25.9)

    def test_dilution_factor_clamped(self):
        assert pricing.dilution_factor(-10) == 1.0  # never shrinks
        assert pricing.dilution_factor(None) == 1.0


class TestDilutionApi:
    def test_summary_carries_served_values(self):
        spec = client.post("/api/specs", json={"name": "Shaken Negroni",
                                               "dilution_pct": 25}).json()
        # Negroni lines: gin 30ml 40 + campari 30ml 25 + vermouth 30ml 16
        for ln in [{"name": "London dry gin", "amount_ml": 30, "unit": "ml"},
                   {"name": "Campari", "amount_ml": 30, "unit": "ml"},
                   {"name": "Sweet vermouth", "amount_ml": 30, "unit": "ml"}]:
            client.post(f"/api/specs/{spec['id']}/lines", json=ln)
        d = client.get(f"/api/specs/{spec['id']}").json()
        s = d["summary"]
        recipe_abv = (30 * 0.40 + 30 * 0.25 + 30 * 0.16) / 90 * 100  # 27.0
        assert s["total_ml"] == pytest.approx(90.0)
        assert s["abv"] == pytest.approx(recipe_abv, abs=0.1)
        assert s["dilution_pct"] == 25.0
        assert s["served_ml"] == pytest.approx(112.5)
        assert s["served_abv"] == pytest.approx(recipe_abv / 1.25, abs=0.1)
        # cost is the recipe cost — dilution adds nothing (water is free)
        assert s["cost_eur"] == pytest.approx(2.197, abs=1e-3)

    def test_no_dilution_is_byte_identical(self):
        spec = client.get("/api/specs").json()
        neg = [x for x in spec if x["name"] == "Negroni"][0]
        det = client.get(f"/api/specs/{neg['id']}").json()
        s = det["summary"]
        assert s["dilution_pct"] == 0
        assert s["served_ml"] == s["total_ml"]
        assert s["served_abv"] == s["abv"]

    def test_partial_put_preserves_dilution(self):
        client.post("/api/specs", json={"name": "Sbagliato Shake",
                                        "dilution_pct": 20}).json()
        sid = [s for s in client.get("/api/specs").json()
               if s["name"] == "Sbagliato Shake"][0]["id"]
        client.put(f"/api/specs/{sid}", json={"name": "Sbagliato Shake",
                                              "price_eur": 9.0, "target_gp": 70})
        d = client.get(f"/api/specs/{sid}").json()
        assert d["dilution_pct"] == 20.0

    def test_duplicate_keeps_dilution(self):
        client.post("/api/specs", json={"name": "Dil", "dilution_pct": 18}).json()
        sid = [s for s in client.get("/api/specs").json() if s["name"] == "Dil"][0]["id"]
        dup = client.post(f"/api/specs/{sid}/duplicate").json()
        assert dup["dilution_pct"] == 18.0

    def test_edit_clear_dilution(self):
        client.post("/api/specs", json={"name": "Was Shaken", "dilution_pct": 22}).json()
        sid = [s for s in client.get("/api/specs").json()
               if s["name"] == "Was Shaken"][0]["id"]
        client.put(f"/api/specs/{sid}", json={"name": "Was Shaken", "dilution_pct": 0})
        d = client.get(f"/api/specs/{sid}").json()
        assert d["dilution_pct"] == 0
        assert d["summary"]["served_ml"] == d["summary"]["total_ml"]
