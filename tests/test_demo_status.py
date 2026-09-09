"""Demo self-check endpoint (owner-gated; counts only, no money)."""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    yield


def test_demo_status_shape_when_empty():
    client.post("/api/auth/setup", json={"pin": "4321"})
    r = client.get("/api/demo/status")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["checks"], list) and len(body["checks"]) >= 6
    assert body["ok"] is False            # fresh db has no month data yet


def test_demo_status_gate_blocks_anonymous():
    client.post("/api/auth/setup", json={"pin": "4321"})
    anon = TestClient(main.app)           # no cookie → auth gate
    assert anon.get("/api/demo/status").status_code == 401
