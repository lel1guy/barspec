"""Units engine (S2): dimensions, canonical conversion, dimension-aware cost.

Pure math + API café proof. Locked defaults (2026-09-06): dash = 1 ml,
barspoon = 5 ml fixed volume sub-units; weight items excluded from the
stock-take count walk.

Hand-computed references:
  bitters  200 ml bottle @ €16      -> €0.08/ml  -> 2 dash = 2 ml = €0.16
  coffee   1 kg bag (1000 g) @ €18  -> €0.018/g  -> 9 g = €0.162
  limes    12-piece box @ €3.60     -> €0.30/pc  -> 1 pc = €0.30
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


# ---------- pure conversion math ----------

class TestUnitTables:
    def test_unit_dimensions(self):
        assert pricing.UNIT_DIMENSION["ml"] == "volume"
        assert pricing.UNIT_DIMENSION["cl"] == "volume"
        assert pricing.UNIT_DIMENSION["oz"] == "volume"
        assert pricing.UNIT_DIMENSION["dash"] == "volume"
        assert pricing.UNIT_DIMENSION["barspoon"] == "volume"
        assert pricing.UNIT_DIMENSION["g"] == "weight"
        assert pricing.UNIT_DIMENSION["kg"] == "weight"
        assert pricing.UNIT_DIMENSION["piece"] == "count"

    def test_canonical_factors(self):
        assert pricing.canonical_amount(3, "cl") == 30.0
        assert pricing.canonical_amount(1.5, "l") == 1500.0
        assert pricing.canonical_amount(1, "oz") == pytest.approx(29.5735)
        assert pricing.canonical_amount(2, "dash") == 2.0      # 1 dash = 1 ml
        assert pricing.canonical_amount(1, "barspoon") == 5.0
        assert pricing.canonical_amount(9, "g") == 9.0
        assert pricing.canonical_amount(1, "kg") == 1000.0
        assert pricing.canonical_amount(1, "piece") == 1.0

    def test_valid_unit(self):
        assert pricing.valid_unit("ml") and pricing.valid_unit("kg")
        assert not pricing.valid_unit("gallons") and not pricing.valid_unit("")


class TestLegacyIdentical:
    """The engine must not move a single cent of pre-engine cost."""

    def _vol_line(self, ml=30.0, price=22.0, vol=700.0, extra=None):
        line = {"name": "X", "amount_ml": ml, "abv": 40.0,
                "bottle_price_eur": price, "bottle_volume_ml": vol}
        if extra:
            line.update(extra)
        return line

    def test_no_unit_key_unchanged(self):
        assert pricing.line_cost(self._vol_line()) == pytest.approx(30 * 22 / 700)

    def test_explicit_ml_volume_identical(self):
        plain = pricing.line_cost(self._vol_line())
        explicit = pricing.line_cost(
            self._vol_line(extra={"unit": "ml", "dimension": "volume"}))
        assert plain == explicit

    def test_legacy_negroni_cost_identical(self):
        lines = [
            self._vol_line(30, 22.0, 700, {"name": "Gin", "unit": "ml", "dimension": "volume"}),
            self._vol_line(30, 19.0, 700, {"name": "Campari", "unit": "ml", "dimension": "volume"}),
            self._vol_line(30, 11.0, 750, {"name": "Vermouth", "unit": "ml", "dimension": "volume"}),
        ]
        assert pricing.drink_cost(lines) == pytest.approx(
            30 * 22 / 700 + 30 * 19 / 700 + 30 * 11 / 750)
        assert pricing.drink_volume(lines) == pytest.approx(90.0)

    def test_dash_priced_via_bottle(self):
        # 2 dash of 200 ml @ €16 bitters -> 2 ml x 16/200 = €0.16
        line = {"name": "Angostura bitters", "amount_ml": 2, "unit": "dash",
                "abv": 0, "bottle_price_eur": 16.0, "bottle_volume_ml": 200.0,
                "dimension": "volume"}
        assert pricing.line_cost(line) == pytest.approx(0.16, abs=1e-9)

    def test_barspoon_5ml(self):
        line = {"name": "Syrup", "amount_ml": 1, "unit": "barspoon", "abv": 0,
                "bottle_price_eur": 5.0, "bottle_volume_ml": 1000.0,
                "dimension": "volume"}
        assert pricing.line_cost(line) == pytest.approx(0.025)  # 5 ml of €5/1000ml


class TestCrossDimension:
    def test_weight_line_cost(self):
        # 9 g coffee from a 1000 g €18 bag
        line = {"name": "Espresso beans", "amount_ml": 9, "unit": "g", "abv": 0,
                "bottle_price_eur": 18.0, "bottle_volume_ml": 1000.0,
                "dimension": "weight"}
        assert pricing.line_cost(line) == pytest.approx(0.162, abs=1e-9)

    def test_count_line_cost(self):
        # 1 lime from a 12-piece €3.60 box
        line = {"name": "Lime", "amount_ml": 1, "unit": "piece", "abv": 0,
                "bottle_price_eur": 3.6, "bottle_volume_ml": 12.0,
                "dimension": "count"}
        assert pricing.line_cost(line) == pytest.approx(0.30, abs=1e-9)

    def test_weight_lines_carry_no_drink_volume(self):
        vol = {"name": "Milk", "amount_ml": 60, "unit": "ml", "abv": 0,
               "bottle_price_eur": 2.0, "bottle_volume_ml": 1000.0,
               "dimension": "volume"}
        g = {"name": "Beans", "amount_ml": 9, "unit": "g", "abv": 0,
             "bottle_price_eur": 18.0, "bottle_volume_ml": 1000.0,
             "dimension": "weight"}
        pc = {"name": "Cup", "amount_ml": 1, "unit": "piece", "abv": 0,
              "bottle_price_eur": 0.4, "bottle_volume_ml": 1.0,
              "dimension": "count"}
        # 9 g of beans is not 9 ml of drink; only the 60 ml milk counts
        assert pricing.drink_volume([vol, g, pc]) == pytest.approx(60.0)
        assert pricing.drink_abv([vol, g, pc]) == 0.0
        # cost still sums every dimension
        assert pricing.drink_cost([vol, g, pc]) == pytest.approx(
            60 * 2 / 1000 + 0.162 + 0.4, abs=1e-9)


# ---------- API café proof (end to end) ----------

class TestCafeProof:
    def test_espresso_cost_end_to_end(self):
        # coffee beans: weight dimension, 1000 g purchase, €18
        item = db.create_stock_item({"name": "Espresso beans", "abv": 0,
                                     "bottle_price_eur": 18.0,
                                     "bottle_volume_ml": 1000.0,
                                     "dimension": "weight"})
        assert item["dimension"] == "weight"
        spec = client.post("/api/specs", json={"name": "Espresso"}).json()
        # 9 g line
        resp = client.post(f"/api/specs/{spec['id']}/lines",
                           json={"name": "Espresso beans", "amount_ml": 9,
                                 "unit": "g"})
        assert resp.status_code == 200, resp.text
        detail = client.get(f"/api/specs/{spec['id']}").json()
        assert detail["summary"]["cost_eur"] == pytest.approx(0.162, abs=1e-3)
        line = detail["lines"][0]
        assert line["unit"] == "g" and line["dimension"] == "weight"
        # 9 g is not drink volume
        assert detail["summary"]["total_ml"] == 0.0

    def test_mixed_cafe_spec(self):
        # espresso with milk: 9 g beans + 60 ml milk + 1 piece cup
        db.create_stock_item({"name": "Espresso beans", "abv": 0,
                              "bottle_price_eur": 18.0,
                              "bottle_volume_ml": 1000.0, "dimension": "weight"})
        db.create_stock_item({"name": "Milk", "abv": 0,
                              "bottle_price_eur": 2.0,
                              "bottle_volume_ml": 1000.0, "dimension": "volume"})
        db.create_stock_item({"name": "Cup", "abv": 0,
                              "bottle_price_eur": 0.4,
                              "bottle_volume_ml": 1.0, "dimension": "count"})
        spec = client.post("/api/specs", json={"name": "Flat White"}).json()
        sid = spec["id"]
        for name, ml, unit in [("Espresso beans", 9, "g"),
                               ("Milk", 60, "ml"),
                               ("Cup", 1, "piece")]:
            r = client.post(f"/api/specs/{sid}/lines",
                            json={"name": name, "amount_ml": ml, "unit": unit})
            assert r.status_code == 200, r.text
        detail = client.get(f"/api/specs/{sid}").json()
        # 9*18/1000 + 60*2/1000 + 0.4
        assert detail["summary"]["cost_eur"] == pytest.approx(
            9 * 18 / 1000 + 60 * 2 / 1000 + 0.4, abs=1e-3)
        assert detail["summary"]["total_ml"] == pytest.approx(60.0)
        # pricing suggests a menu price on the true cost
        assert detail["summary"]["cost_eur"] > 0.5
        assert detail["summary"]["suggested_price_eur"] > 0

    def test_dimension_mismatch_rejected(self):
        db.create_stock_item({"name": "Espresso beans", "abv": 0,
                              "bottle_price_eur": 18.0,
                              "bottle_volume_ml": 1000.0, "dimension": "weight"})
        # volume bottle line:
        spec = client.post("/api/specs", json={"name": "Bad"}).json()
        # 30 ml of a weight bag is nonsense -> 400
        r = client.post(f"/api/specs/{spec['id']}/lines",
                        json={"name": "Espresso beans", "amount_ml": 30,
                              "unit": "ml"})
        assert r.status_code == 400
        # unknown unit -> 400
        r2 = client.post(f"/api/specs/{spec['id']}/lines",
                         json={"name": "Espresso beans", "amount_ml": 9,
                               "unit": "gallons"})
        assert r2.status_code == 400

    def test_weight_item_excluded_from_stock_take(self):
        beans = db.create_stock_item({"name": "Espresso beans", "abv": 0,
                                      "bottle_price_eur": 18.0,
                                      "bottle_volume_ml": 1000.0,
                                      "dimension": "weight"})
        r = client.patch(f"/api/stock/{beans['id']}/par", json={"par_level": 2})
        assert r.status_code == 400
        sheet = client.get("/api/stock-takes/sheet").json()
        assert all(row["name"] != "Espresso beans" for row in sheet["rows"])
