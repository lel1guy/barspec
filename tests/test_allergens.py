"""Kitchen K3 (migration 010): allergen + dietary tags on specs."""
import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def _negroni():
    return [s for s in client.get("/api/specs").json() if s["name"] == "Negroni"][0]


def test_round_trip_and_badges_in_detail():
    n = _negroni()
    r = client.put(f"/api/specs/{n['id']}",
                   json={"name": n["name"], "allergens": "cel,glu", "dietary": "V"})
    assert r.status_code == 200
    det = client.get(f"/api/specs/{n['id']}").json()
    assert det["allergens"] == "cel,glu"
    assert det["dietary"] == "V"


def test_unknown_codes_rejected():
    n = _negroni()
    assert client.put(f"/api/specs/{n['id']}",
                      json={"name": n["name"], "allergens": "gluten"}).status_code == 422
    assert client.put(f"/api/specs/{n['id']}",
                      json={"name": n["name"], "dietary": "X"}).status_code == 422


def test_partial_edit_preserves_tags():
    n = _negroni()
    client.put(f"/api/specs/{n['id']}",
               json={"name": n["name"], "allergens": "egg", "dietary": "VE"})
    client.put(f"/api/specs/{n['id']}", json={"name": n["name"], "glass": "Rocks"})
    det = client.get(f"/api/specs/{n['id']}").json()
    assert det["allergens"] == "egg" and det["dietary"] == "VE"
    assert det["glass"] == "Rocks"


def test_duplicate_copies_tags():
    n = _negroni()
    client.put(f"/api/specs/{n['id']}",
               json={"name": n["name"], "allergens": "ses", "dietary": "GF"})
    r = client.post(f"/api/specs/{n['id']}/duplicate")
    assert r.status_code == 200
    dupe = [s for s in client.get("/api/specs").json() if "copy" in s["name"]][0]
    assert dupe["allergens"] == "ses" and dupe["dietary"] == "GF"


def test_export_carries_columns():
    n = _negroni()
    client.put(f"/api/specs/{n['id']}",
               json={"name": n["name"], "allergens": "mil", "dietary": "V"})
    r = client.get("/api/export/specs.xlsx")
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb["Specs"]
    header = list(ws.values)[0]
    assert header[-2:] == ("Dietary", "Allergens")
    neg = [row for row in list(ws.values)[1:] if row[0] == "Negroni"][0]
    assert neg[-2:] == ("V", "mil")
