"""Settings (008): venue profile — name + IVA % for the printed menu."""
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def test_venue_defaults_empty():
    assert client.get("/api/settings").json() == {"name": "", "iva_pct": None}


def test_venue_round_trip():
    r = client.put("/api/settings", json={"name": "  Bar da Esquina  ", "iva_pct": 23})
    assert r.status_code == 200
    v = client.get("/api/settings").json()
    assert v["name"] == "Bar da Esquina"  # stripped
    assert v["iva_pct"] == 23.0


def test_iva_can_be_cleared():
    client.put("/api/settings", json={"name": "Bar", "iva_pct": 13})
    client.put("/api/settings", json={"name": "Bar", "iva_pct": None})
    assert client.get("/api/settings").json()["iva_pct"] is None


def test_iva_bounds():
    assert client.put("/api/settings", json={"name": "Bar", "iva_pct": 101}).status_code == 422
    assert client.put("/api/settings", json={"name": "Bar", "iva_pct": -1}).status_code == 422
