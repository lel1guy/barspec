"""Shared pytest fixtures for BarSpec.

CRITICAL: the temp DB env var is set BEFORE any import of db/main so a test
import can never touch the real barspec.db. Each test then re-points db.DB_PATH
at its own temp file via the `fresh_db` fixture.
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# Must run before `import db` / `import main` anywhere.
os.environ["BARSPEC_DB"] = str(
    Path(tempfile.mkdtemp(prefix="barspec-test-")) / "barspec.db"
)

import pytest  # noqa: E402

import db  # noqa: E402

# The v0 schema — what a pre-migration database looked like. Used to build
# legacy DBs so the migration replay test exercises a real upgrade path.
LEGACY_SCHEMA = """
CREATE TABLE specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    glass TEXT DEFAULT '',
    method TEXT DEFAULT '',
    garnish TEXT DEFAULT ''
);
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount_ml REAL NOT NULL,
    abv REAL DEFAULT 0,
    bottle_price_eur REAL DEFAULT 0,
    bottle_volume_ml REAL DEFAULT 700
);
"""


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Every test gets a brand-new DB built through the full init path
    (base schema -> migrations -> seed)."""
    p = tmp_path / "barspec.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db()
    return p


@pytest.fixture()
def legacy_db(tmp_path, monkeypatch):
    """Build a v0 (pre-migration) database with known data, then run init_db()
    so migration 001 replays over it. Returns the db module (already migrated)."""
    p = tmp_path / "legacy.db"
    conn = sqlite3.connect(p)
    conn.executescript(LEGACY_SCHEMA)
    # Two specs sharing one bottle name in different cases -> must dedupe to ONE
    # stock item. Prices differ across rows: 'campari' has no price, 'Campari' does.
    conn.execute(
        "INSERT INTO specs (name) VALUES ('Negroni')")
    conn.execute(
        "INSERT INTO specs (name) VALUES ('Campari Spritz')")
    conn.execute(
        "INSERT INTO ingredients (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml) "
        "VALUES (1, 'Gin', 30, 40, 22.0, 700)")
    conn.execute(
        "INSERT INTO ingredients (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml) "
        "VALUES (1, 'Campari', 30, 25, 19.0, 700)")
    conn.execute(
        "INSERT INTO ingredients (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml) "
        "VALUES (1, 'Vermouth', 30, 16, 11.0, 750)")
    conn.execute(
        "INSERT INTO ingredients (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml) "
        "VALUES (2, 'campari', 60, 25, 0.0, 700)")   # dup, lowercase, no price
    conn.execute(
        "INSERT INTO ingredients (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml) "
        "VALUES (2, 'Prosecco', 90, 11.5, 8.0, 750)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db()
    return db
