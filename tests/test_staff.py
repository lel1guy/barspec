"""Staff read-only role (022): recipes + menu WITHOUT money."""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _owner():
    c = TestClient(main.app)
    c.post("/api/auth/setup", json={"pin": "4321"})   # jar now holds owner cookie
    return c


def _staff(c):
    s = TestClient(main.app)
    assert s.post("/api/auth/staff-login", json={"pin": "7788"}).status_code == 200
    return s


def _staff_pin_on(owner):
    assert owner.put("/api/auth/staff-pin", json={"pin": "7788"}).status_code == 200


def _has_money(payload):
    """Recursively true if any cost/margin/price number survives."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k in ("cost_eur", "margin", "suggested", "bottle_price_eur") and v not in (None, ""):
                return True
            if _has_money(v):
                return True
    elif isinstance(payload, list):
        return any(_has_money(x) for x in payload)
    return False


def test_staff_login_needs_enabled_pin():
    owner = _owner()
    assert TestClient(main.app).post("/api/auth/staff-login",
                                     json={"pin": "7788"}).status_code == 409
    _staff_pin_on(owner)
    bad = TestClient(main.app)
    assert bad.post("/api/auth/staff-login", json={"pin": "0000"}).status_code == 401
    assert bad.post("/api/auth/staff-login", json={"pin": "7788"}).status_code == 200


def test_staff_reads_specs_without_any_money():
    owner = _owner()
    _staff_pin_on(owner)
    s = _staff(owner)
    specs = s.get("/api/specs").json()
    assert len(specs) == 5
    assert not _has_money(specs)
    detail = s.get(f"/api/specs/{specs[0]['id']}").json()
    assert detail["price_eur"] is None
    assert not _has_money(detail)
    assert detail["method"]                    # the recipe itself still there
    assert detail["lines"]                     # amounts included


def test_staff_blocked_from_owner_areas():
    owner = _owner()
    _staff_pin_on(owner)
    s = _staff(owner)
    assert s.get("/api/stock").status_code == 403
    assert s.get("/api/batches").status_code == 403
    assert s.get("/api/sales/summary").status_code == 403
    assert s.get("/api/export/specs.xlsx").status_code == 403
    spec = s.get("/api/specs").json()[0]
    assert s.put(f"/api/specs/{spec['id']}", json={"name": spec["name"]}).status_code == 403
    assert s.post("/api/specs", json={"name": "Hack"}).status_code == 403


def test_staff_menu_has_prices_but_no_costs():
    owner = _owner()
    _staff_pin_on(owner)
    # price a seed spec as owner first
    spec = owner.get("/api/specs").json()[0]
    owner.put(f"/api/specs/{spec['id']}",
              json={"name": spec["name"], "price_eur": 9.0})
    s = _staff(owner)
    menu = s.get("/api/menu").json()
    items = menu if isinstance(menu, list) else menu.get("items", [])
    assert any(i.get("price_eur") for i in items)
    assert not _has_money(items)


def test_staff_pin_management_is_owner_only():
    owner = _owner()
    assert owner.put("/api/auth/staff-pin", json={"pin": "7788"}).status_code == 200
    staff = _staff(owner)
    assert staff.put("/api/auth/staff-pin", json={"pin": "9999"}).status_code == 403
    assert staff.put("/api/auth/staff-pin", json={"pin": ""}).status_code == 403
    owner.put("/api/auth/staff-pin", json={"pin": ""})
    assert TestClient(main.app).post("/api/auth/staff-login",
                                     json={"pin": "7788"}).status_code == 409
