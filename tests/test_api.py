"""API smoke tests: routes, stock ripple, menu pricing, cascade rules."""
import pytest
from fastapi.testclient import TestClient

import main
import db

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


class TestSeed:
    def test_seed_loaded(self):
        assert len(client.get("/api/stock").json()) == 15
        specs = client.get("/api/specs").json()
        assert len(specs) == 5

    def test_negroni_detail(self):
        s = client.get("/api/specs/1").json()
        assert s["name"] == "Negroni"
        assert len(s["lines"]) == 3
        # gin 30ml @22/700 + campari 30 @19/700 + vermouth 30 @11/750
        assert s["summary"]["cost_eur"] == pytest.approx(
            round(30 * 22 / 700 + 30 * 19 / 700 + 30 * 11 / 750, 3))
        assert s["price_eur"] == 9.0
        assert s["summary"]["suggested_price_eur"] == 9.0  # 2.197/0.25 -> 9.0

    def test_line_rows_carry_stock(self):
        s = client.get("/api/specs/1").json()
        campari = [l for l in s["lines"] if l["name"] == "Campari"][0]
        assert campari["bottle_price_eur"] == 19.0
        assert campari["row_cost_pct"] == pytest.approx(
            round(30 * 19 / 700 / s["summary"]["cost_eur"] * 100, 1))


class TestSpecCRUD:
    def test_create_with_line_resolving_existing_stock(self):
        created = client.post("/api/specs", json={"name": "Test Drink"}).json()
        n_stock_before = len(client.get("/api/stock").json())
        # 'Campari' exists -> links to existing bottle, stock count unchanged
        resp = client.post(f"/api/specs/{created['id']}/lines",
                           json={"name": "Campari", "amount_ml": 45})
        assert resp.status_code == 200
        assert len(client.get("/api/stock").json()) == n_stock_before
        spec = client.get(f"/api/specs/{created['id']}").json()
        assert spec["lines"][0]["name"] == "Campari"
        assert spec["lines"][0]["bottle_price_eur"] == 19.0

    def test_new_name_creates_stock(self):
        created = client.post("/api/specs", json={"name": "Test 2"}).json()
        n_stock_before = len(client.get("/api/stock").json())
        client.post(f"/api/specs/{created['id']}/lines",
                    json={"name": "Banana liqueur", "amount_ml": 20,
                          "abv": 25, "bottle_price_eur": 22.0})
        stock = client.get("/api/stock").json()
        assert len(stock) == n_stock_before + 1
        new = [s for s in stock if s["name"] == "Banana liqueur"][0]
        assert new["bottle_price_eur"] == 22.0 and new["abv"] == 25

    def test_duplicate_copies_lines(self):
        before = len(client.get("/api/specs").json())
        dup = client.post("/api/specs/1/duplicate").json()
        assert len(client.get("/api/specs").json()) == before + 1
        assert len(dup["lines"]) == 3
        assert dup["name"] == "Negroni (copy)"

    def test_delete_cascades_lines(self):
        created = client.post("/api/specs", json={"name": "Doomed"}).json()
        client.post(f"/api/specs/{created['id']}/lines",
                    json={"name": "Vodka", "amount_ml": 40})
        assert client.delete(f"/api/specs/{created['id']}").status_code == 200
        assert client.get(f"/api/specs/{created['id']}").status_code == 404


class TestStockRipple:
    def test_price_change_reports_impact(self):
        stock = client.get("/api/stock").json()
        campari = [s for s in stock if s["name"] == "Campari"][0]
        before = client.get("/api/specs/1").json()["summary"]["cost_eur"]
        resp = client.put(f"/api/stock/{campari['id']}", json={
            "name": "Campari", "abv": 25, "bottle_price_eur": 25.0,
            "bottle_volume_ml": 700}).json()
        after = client.get("/api/specs/1").json()["summary"]["cost_eur"]
        negroni = [i for i in resp["impact"] if i["name"] == "Negroni"][0]
        assert negroni["cost_old"] == pytest.approx(before)
        assert negroni["cost_new"] == pytest.approx(after)
        assert after > before  # price went up

    def test_delete_in_use_blocked(self):
        stock = client.get("/api/stock").json()
        campari = [s for s in stock if s["name"] == "Campari"][0]
        assert client.delete(f"/api/stock/{campari['id']}").status_code == 409

    def test_delete_unused_ok(self):
        client.post("/api/stock", json={"name": "Ghost bottle"})
        ghost = [s for s in client.get("/api/stock").json()
                 if s["name"] == "Ghost bottle"][0]
        assert client.delete(f"/api/stock/{ghost['id']}").status_code == 200


class TestMenu:
    def test_menu_priced_seed(self):
        menu = client.get("/api/menu").json()
        negroni = [m for m in menu if m["name"] == "Negroni"][0]
        assert negroni["priced"] is True
        assert negroni["price_eur"] == 9.0
        assert negroni["margin"] == pytest.approx(round((9 - negroni["cost_eur"]) / 9 * 100, 1))

    def test_unpricing_a_spec(self):
        menu = client.get("/api/menu").json()
        negroni = [m for m in menu if m["name"] == "Negroni"][0]
        client.put("/api/specs/" + str(negroni["id"]), json={
            "name": "Negroni", "glass": "", "method": "Stirred", "garnish": "",
            "price_eur": None, "target_gp": 70})
        updated = [m for m in client.get("/api/menu").json() if m["name"] == "Negroni"][0]
        assert updated["priced"] is False
        assert updated["price_eur"] is None
