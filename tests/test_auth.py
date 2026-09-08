"""S1: owner PIN gate + security headers."""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _c():
    return TestClient(main.app)   # fresh cookie jar per step


def test_open_when_no_pin():
    c = _c()
    assert c.get("/api/auth/status").json() == {"set": False}
    assert c.get("/api/specs").status_code == 200   # gate off pre-setup


def test_setup_then_gate_engages():
    c = _c()
    r = c.post("/api/auth/setup", json={"pin": "4321"})
    assert r.status_code == 200
    assert "barspec_sesh=" in r.headers.get("set-cookie", "")
    # fresh jar: no cookie -> 401 on protected routes, auth stays open
    anon = _c()
    assert anon.get("/api/specs").status_code == 401
    assert anon.get("/api/export/specs.xlsx").status_code == 401
    assert anon.get("/api/auth/status").status_code == 200


def test_login_flow():
    _c().post("/api/auth/setup", json={"pin": "4321"})
    anon = _c()
    assert anon.post("/api/auth/login", json={"pin": "0000"}).status_code == 401
    assert anon.get("/api/specs").status_code == 401
    ok = anon.post("/api/auth/login", json={"pin": "4321"})
    assert ok.status_code == 200
    assert "barspec_sesh=" in ok.headers.get("set-cookie", "")
    assert anon.get("/api/specs").status_code == 200     # jar now holds cookie
    assert anon.post("/api/auth/logout").status_code == 200
    assert anon.get("/api/specs").status_code == 401     # cleared again


def test_short_pin_and_double_setup_rejected():
    c = _c()
    assert c.post("/api/auth/setup", json={"pin": "12"}).status_code == 400
    c.post("/api/auth/setup", json={"pin": "4321"})
    assert _c().post("/api/auth/setup", json={"pin": "9999"}).status_code == 409


def test_headers_present():
    c = _c()
    r = c.get("/")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
