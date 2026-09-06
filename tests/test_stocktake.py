"""Stock-take: par levels, dated snapshots, order list, cash asleep, trends.

Numbers hand-computed from the seed bottles:
  London dry gin   22.0 / 700 ml
  Campari          19.0 / 700 ml
  Soda water        1.2 / 1500 ml
"""
import pytest
from fastapi.testclient import TestClient

import main
import db

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _stock_id(name):
    stock = client.get("/api/stock").json()
    return [s for s in stock if s["name"] == name][0]["id"]


def _set_par(name, par):
    r = client.patch(f"/api/stock/{_stock_id(name)}/par", json={"par_level": par})
    assert r.status_code == 200, r.text


class TestParLevels:
    def test_sheet_empty_until_par_set(self):
        sheet = client.get("/api/stock-takes/sheet").json()
        assert sheet["rows"] == [] and sheet["last_take"] is None

    def test_sheet_lists_only_pard_bottles(self):
        _set_par("London dry gin", 3)
        _set_par("Campari", 2)
        sheet = client.get("/api/stock-takes/sheet").json()
        names = [r["name"] for r in sheet["rows"]]
        assert names == ["Campari", "London dry gin"]  # ordered by name
        gin = [r for r in sheet["rows"] if r["name"] == "London dry gin"][0]
        assert gin["par_level"] == 3
        assert gin["last_full_bottles"] is None  # never counted yet

    def test_clear_par_removes_from_sheet(self):
        _set_par("London dry gin", 3)
        _set_par("London dry gin", None)
        sheet = client.get("/api/stock-takes/sheet").json()
        assert sheet["rows"] == []

    def test_par_zero_means_not_counted(self):
        _set_par("London dry gin", 0)
        sheet = client.get("/api/stock-takes/sheet").json()
        assert sheet["rows"] == []

    def test_par_on_unknown_bottle_404(self):
        assert client.patch("/api/stock/9999/par", json={"par_level": 2}).status_code == 404


class TestSaveTake:
    def _seed_three_pars(self):
        _set_par("London dry gin", 3)
        _set_par("Campari", 2)
        _set_par("Soda water", 4)

    def test_save_returns_order_list(self):
        self._seed_three_pars()
        gin, campari, soda = _stock_id("London dry gin"), _stock_id("Campari"), _stock_id("Soda water")
        # gin 2 full + 1 at half = 2.5 FBE vs par 3  -> order 1
        # campari 3 full = 3.0 FBE vs par 2          -> 1.0 FBE over = 19.00 asleep
        # soda 4 full = 4.0 FBE vs par 4             -> exactly at par
        resp = client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 2, "open_fraction": 0.5},
            {"stock_item_id": campari, "full_bottles": 3, "open_fraction": 0},
            {"stock_item_id": soda, "full_bottles": 4, "open_fraction": 0},
        ]})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["counted"] == 3
        assert body["order_total"] == 1
        assert body["cash_asleep_total"] == pytest.approx(19.0)
        assert [r["name"] for r in body["short"]] == ["London dry gin"]
        assert body["short"][0]["to_order"] == 1
        assert [r["name"] for r in body["over"]] == ["Campari"]
        assert body["over"][0]["cash_asleep_eur"] == pytest.approx(19.0)
        assert [r["name"] for r in body["at_par"]] == ["Soda water"]

    def test_last_take_roundtrip_and_prefill(self):
        self._seed_three_pars()
        gin = _stock_id("London dry gin")
        client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 2, "open_fraction": 0.5}]})
        last = client.get("/api/stock-takes/last")
        assert last.status_code == 200
        assert last.json()["take"]["id"] == 1
        assert last.json()["short"][0]["name"] == "London dry gin"
        # the count screen now prefills from the snapshot
        sheet = client.get("/api/stock-takes/sheet").json()
        gin_row = [r for r in sheet["rows"] if r["name"] == "London dry gin"][0]
        assert gin_row["last_full_bottles"] == 2
        assert gin_row["last_open_fraction"] == 0.5

    def test_last_take_404_when_none(self):
        assert client.get("/api/stock-takes/last").status_code == 404

    def test_rejects_bottle_without_par(self):
        _set_par("London dry gin", 3)
        soda = _stock_id("Soda water")  # no par
        resp = client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": soda, "full_bottles": 1, "open_fraction": 0}]})
        assert resp.status_code == 400

    def test_rejects_bad_fraction(self):
        _set_par("London dry gin", 3)
        gin = _stock_id("London dry gin")
        resp = client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 1, "open_fraction": 0.4}]})
        assert resp.status_code == 400

    def test_rejects_unknown_bottle(self):
        resp = client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": 9999, "full_bottles": 1, "open_fraction": 0}]})
        assert resp.status_code == 400

    def test_rejects_negative_full(self):
        _set_par("London dry gin", 3)
        gin = _stock_id("London dry gin")
        resp = client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": -1, "open_fraction": 0}]})
        assert resp.status_code == 422  # pydantic Field(ge=0)

    def test_empty_lines_400(self):
        assert client.post("/api/stock-takes", json={"lines": []}).status_code == 400


class TestTrends:
    def test_trends_before_any_take(self):
        body = client.get("/api/stock-takes/trends").json()
        assert body["takes_count"] == 0
        assert body["movement"] == []

    def test_movement_needs_two_snapshots(self):
        _set_par("London dry gin", 3)
        gin = _stock_id("London dry gin")
        client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 3, "open_fraction": 0}]})
        body = client.get("/api/stock-takes/trends").json()
        assert body["takes_count"] == 1
        assert body["movement"] == []  # gated on history

    def test_movement_between_two_takes(self):
        _set_par("London dry gin", 3)
        gin = _stock_id("London dry gin")
        client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 3, "open_fraction": 0}]})
        client.post("/api/stock-takes", json={"lines": [
            {"stock_item_id": gin, "full_bottles": 2, "open_fraction": 0.5}]})
        body = client.get("/api/stock-takes/trends").json()
        assert body["takes_count"] == 2
        gin_row = [m for m in body["movement"] if m["name"] == "London dry gin"][0]
        assert gin_row["prev_fbe"] == 3.0
        assert gin_row["fbe"] == 2.5
        assert gin_row["used_fbe"] == pytest.approx(0.5)
        assert gin_row["used_ml"] == pytest.approx(350.0)
        assert gin_row["used_eur"] == pytest.approx(11.0)  # 0.5 FBE x 22.0
        assert gin_row["state"] == "used"

    def test_dead_stock_lists_unused_bottles(self):
        # every seed bottle is used by exactly one spec -> none dead
        body = client.get("/api/stock-takes/trends").json()
        assert body["dead_stock"] == []
        client.post("/api/stock", json={"name": "Ghost bottle", "bottle_price_eur": 9.0})
        body = client.get("/api/stock-takes/trends").json()
        dead_names = [d["name"] for d in body["dead_stock"]]
        assert "Ghost bottle" in dead_names


class TestUnmovedFlag:
    def test_unmoved_when_count_identical(self):
        _set_par("London dry gin", 3)
        gin = _stock_id("London dry gin")
        for _ in range(2):
            client.post("/api/stock-takes", json={"lines": [
                {"stock_item_id": gin, "full_bottles": 3, "open_fraction": 0}]})
        body = client.get("/api/stock-takes/trends").json()
        gin_row = [m for m in body["movement"] if m["name"] == "London dry gin"][0]
        assert gin_row["used_fbe"] == 0.0
        assert gin_row["state"] == "unmoved"
