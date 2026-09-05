"""SQLite layer for BarSpec.

Plain sqlite3 on purpose: no ORM, every query visible.
DB file location overridable with BARSPEC_DB env var (tests use a temp file).

Schema history lives in migrations/*.sql, applied in order and tracked with
PRAGMA user_version. A fresh install runs the same migration path as an old
database — every new venue file self-checks its own upgrade.
"""
import os
import sqlite3
from pathlib import Path

import pricing

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("BARSPEC_DB", BASE_DIR / "barspec.db"))
MIGRATIONS_DIR = BASE_DIR / "migrations"

# v0 base schema — intentionally the OLD shape so migration 001 (which drops
# `ingredients`) exercises on every install, fresh or upgraded.
SCHEMA = """
CREATE TABLE IF NOT EXISTS specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    glass TEXT DEFAULT '',
    method TEXT DEFAULT '',
    garnish TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount_ml REAL NOT NULL,
    abv REAL DEFAULT 0,
    bottle_price_eur REAL DEFAULT 0,
    bottle_volume_ml REAL DEFAULT 700
);
"""

SEED_SPECS = [
    {
        "name": "Negroni",
        "glass": "Rocks glass, big ice cube",
        "method": "Stirred",
        "garnish": "Orange peel",
        "price_eur": 9.0,
        "target_gp": 75,
        "ingredients": [
            {"name": "London dry gin", "amount_ml": 30, "abv": 40,
             "bottle_price_eur": 22.0, "bottle_volume_ml": 700},
            {"name": "Campari", "amount_ml": 30, "abv": 25,
             "bottle_price_eur": 19.0, "bottle_volume_ml": 700},
            {"name": "Sweet vermouth", "amount_ml": 30, "abv": 16,
             "bottle_price_eur": 11.0, "bottle_volume_ml": 750},
        ],
    },
    {
        "name": "Margarita",
        "glass": "Coupe, salt rim",
        "method": "Shaken",
        "garnish": "Lime wheel",
        "price_eur": 10.0,
        "ingredients": [
            {"name": "Blanco tequila", "amount_ml": 45, "abv": 40,
             "bottle_price_eur": 28.0, "bottle_volume_ml": 700},
            {"name": "Cointreau", "amount_ml": 20, "abv": 40,
             "bottle_price_eur": 30.0, "bottle_volume_ml": 700},
            {"name": "Fresh lime juice", "amount_ml": 20, "abv": 0,
             "bottle_price_eur": 2.5, "bottle_volume_ml": 1000},
        ],
    },
    {
        "name": "Old Fashioned",
        "glass": "Rocks glass, big ice cube",
        "method": "Stirred",
        "garnish": "Orange peel, cherry",
        "price_eur": 11.0,
        "ingredients": [
            {"name": "Bourbon", "amount_ml": 60, "abv": 45,
             "bottle_price_eur": 32.0, "bottle_volume_ml": 700},
            {"name": "Simple syrup (1:1)", "amount_ml": 10, "abv": 0,
             "bottle_price_eur": 3.0, "bottle_volume_ml": 1000},
            {"name": "Angostura bitters", "amount_ml": 1.5, "abv": 45,
             "bottle_price_eur": 16.0, "bottle_volume_ml": 200},
        ],
    },
    {
        "name": "Espresso Martini",
        "glass": "Coupe",
        "method": "Shaken hard",
        "garnish": "3 coffee beans",
        "price_eur": 10.0,
        "ingredients": [
            {"name": "Vodka", "amount_ml": 40, "abv": 40,
             "bottle_price_eur": 18.0, "bottle_volume_ml": 700},
            {"name": "Coffee liqueur (Kahlúa)", "amount_ml": 20, "abv": 20,
             "bottle_price_eur": 17.0, "bottle_volume_ml": 700},
            {"name": "Fresh espresso", "amount_ml": 30, "abv": 0,
             "bottle_price_eur": 6.0, "bottle_volume_ml": 1000},
        ],
    },
    {
        "name": "Aperol Spritz",
        "glass": "Wine glass, lots of ice",
        "method": "Built",
        "garnish": "Orange slice",
        "price_eur": 8.0,
        "ingredients": [
            {"name": "Aperol", "amount_ml": 60, "abv": 11,
             "bottle_price_eur": 15.0, "bottle_volume_ml": 700},
            {"name": "Prosecco", "amount_ml": 90, "abv": 11.5,
             "bottle_price_eur": 8.0, "bottle_volume_ml": 750},
            {"name": "Soda water", "amount_ml": 20, "abv": 0,
             "bottle_price_eur": 1.2, "bottle_volume_ml": 1500},
        ],
    },
]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _lastid(cur) -> int:
    """lastrowid is guaranteed after a successful INSERT; satisfies the type checker."""
    assert cur.lastrowid is not None
    return int(cur.lastrowid)


# ---------- migrations ----------

def _version(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn):
    """Apply migrations/*.sql with a higher number than the current user_version."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    current = _version(conn)
    for f in files:
        ver = int(f.name.split("_", 1)[0])
        if ver <= current:
            continue
        sql = f.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {ver}")
        conn.commit()


def init_db():
    conn = _conn()
    # Base schema only belongs on a v0 database: it contains the legacy
    # `ingredients` table that migration 001 drops. Re-running it on a migrated
    # DB would resurrect an empty ghost table.
    if _version(conn) == 0:
        conn.executescript(SCHEMA)
    migrate(conn)
    # Seed once, only when no specs exist. Seeds write through the NEW schema
    # (stock_items + spec_lines), so post-migration DBs with user data never reseed.
    count = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
    if count == 0:
        _seed(conn)
    conn.close()


def _seed(conn):
    for spec in SEED_SPECS:
        cur = conn.execute(
            """INSERT INTO specs (name, glass, method, garnish, price_eur, target_gp)
               VALUES (?,?,?,?,?,?)""",
            (spec["name"], spec["glass"], spec["method"], spec["garnish"],
             spec.get("price_eur"), spec.get("target_gp", 70)),
        )
        spec_id = cur.lastrowid
        for ing in spec["ingredients"]:
            stock = _resolve_stock(conn, ing["name"], ing["abv"],
                                   ing["bottle_price_eur"], ing["bottle_volume_ml"])
            conn.execute(
                "INSERT INTO spec_lines (spec_id, stock_item_id, amount_ml) VALUES (?,?,?)",
                (spec_id, stock["id"], ing["amount_ml"]),
            )
    conn.commit()


# ---------- stock items ----------

def _resolve_stock(conn, name, abv=0.0, bottle_price_eur=0.0, bottle_volume_ml=700.0):
    """Return the stock item for a name — create it if missing."""
    row = conn.execute(
        "SELECT * FROM stock_items WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if row:
        return row
    cur = conn.execute(
        """INSERT INTO stock_items (name, abv, bottle_price_eur, bottle_volume_ml)
           VALUES (?,?,?,?)""",
        (name.strip(), abv, bottle_price_eur, bottle_volume_ml),
    )
    conn.commit()
    return conn.execute("SELECT * FROM stock_items WHERE id=?", (cur.lastrowid,)).fetchone()


def _stock_usage_count(conn, stock_id):
    return conn.execute(
        """SELECT COUNT(DISTINCT spec_id) FROM spec_lines WHERE stock_item_id = ?""",
        (stock_id,),
    ).fetchone()[0]


def get_stock_items():
    conn = _conn()
    rows = conn.execute("SELECT * FROM stock_items ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["spec_count"] = _stock_usage_count(conn, r["id"])
        out.append(d)
    conn.close()
    return out


def get_stock_item(stock_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM stock_items WHERE id=?", (stock_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stock_item_by_name(name: str):
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM stock_items WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_stock_item(data: dict):
    conn = _conn()
    dup = conn.execute(
        "SELECT id FROM stock_items WHERE lower(name) = lower(?)", (data["name"],)
    ).fetchone()
    if dup:
        conn.close()
        raise ValueError("Stock item already exists")
    cur = conn.execute(
        """INSERT INTO stock_items (name, abv, bottle_price_eur, bottle_volume_ml)
           VALUES (?,?,?,?)""",
        (data["name"].strip(), data.get("abv", 0), data.get("bottle_price_eur", 0),
         data.get("bottle_volume_ml", 700)),
    )
    conn.commit()
    new_id = _lastid(cur)
    conn.close()
    return get_stock_item(new_id)


def update_stock_item(stock_id: int, data: dict):
    """Update a stock item. If the bottle price changed, returns ripple impact:
    [{'spec_id', 'name', 'cost_old', 'cost_new'}] for every spec that uses it.
    """
    conn = _conn()
    row = conn.execute("SELECT * FROM stock_items WHERE id=?", (stock_id,)).fetchone()
    if not row:
        conn.close()
        return None
    old_price = row["bottle_price_eur"]
    new_price = float(data.get("bottle_price_eur", old_price))

    # Ripple impact (only meaningful when the price actually moves).
    # Only lines using THIS stock item change; other lines keep their bottles.
    impact = []
    if abs(new_price - old_price) > 1e-9:
        for spec in _specs_using_stock(conn, stock_id):
            lines = _spec_lines_joined(conn, spec["id"])

            def cost_with(price):
                return pricing.drink_cost([
                    dict(l, bottle_price_eur=price)
                    if l["stock_item_id"] == stock_id else l
                    for l in lines
                ])

            impact.append({
                "spec_id": spec["id"],
                "name": spec["name"],
                "cost_old": round(cost_with(old_price), 3),
                "cost_new": round(cost_with(new_price), 3),
            })

    conn.execute(
        """UPDATE stock_items SET name=?, abv=?, bottle_price_eur=?, bottle_volume_ml=?,
           updated_at=datetime('now') WHERE id=?""",
        (data.get("name", row["name"]).strip(), data.get("abv", row["abv"]),
         new_price, data.get("bottle_volume_ml", row["bottle_volume_ml"]), stock_id),
    )
    conn.commit()
    conn.close()
    return {"impact": impact}


def delete_stock_item(stock_id: int):
    """Returns 'ok' | 'in-use' (blocked by spec lines)."""
    conn = _conn()
    used = conn.execute(
        "SELECT COUNT(*) FROM spec_lines WHERE stock_item_id=?", (stock_id,)
    ).fetchone()[0]
    if used:
        conn.close()
        return "in-use"
    conn.execute("DELETE FROM stock_items WHERE id=?", (stock_id,))
    conn.commit()
    conn.close()
    return "ok"


# ---------- specs ----------

def _spec_rows(conn, where="", params=()):
    rows = conn.execute(
        f"SELECT * FROM specs {where} ORDER BY name", params
    ).fetchall()
    return [dict(r) for r in rows]


def _spec_lines_joined(conn, spec_id, price_override=None):
    """All lines of a spec joined to stock, as pricing-ready dicts.

    price_override lets the ripple calculation replay a spec with an old/new
    bottle price without mutating anything.
    """
    rows = conn.execute(
        """SELECT sl.id, sl.spec_id, sl.stock_item_id, sl.amount_ml,
                  si.name, si.abv, si.bottle_price_eur, si.bottle_volume_ml
           FROM spec_lines sl
           JOIN stock_items si ON si.id = sl.stock_item_id
           WHERE sl.spec_id = ? ORDER BY sl.id""",
        (spec_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if price_override is not None:
            d["bottle_price_eur"] = price_override
        out.append(d)
    return out


def _specs_using_stock(conn, stock_id):
    return conn.execute(
        """SELECT DISTINCT s.id, s.name FROM spec_lines sl
           JOIN specs s ON s.id = sl.spec_id
           WHERE sl.stock_item_id = ? ORDER BY s.name""",
        (stock_id,),
    ).fetchall()


def get_specs():
    conn = _conn()
    specs = _spec_rows(conn)
    for s in specs:
        lines = _spec_lines_joined(conn, s["id"])
        s["cost_eur"] = round(pricing.drink_cost(lines), 3)
        s["margin"] = round(pricing.margin_pct(s.get("price_eur") or 0, s["cost_eur"]), 1)
    conn.close()
    return specs


def get_spec(spec_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM specs WHERE id=?", (spec_id,)).fetchone()
    if not row:
        conn.close()
        return None
    spec = dict(row)
    lines = _spec_lines_joined(conn, spec_id)
    pcts = pricing.row_pcts(lines)
    spec["lines"] = []
    for i, l in enumerate(lines):
        spec["lines"].append({
            "id": l["id"], "stock_item_id": l["stock_item_id"],
            "name": l["name"], "amount_ml": l["amount_ml"], "abv": l["abv"],
            "bottle_price_eur": l["bottle_price_eur"],
            "bottle_volume_ml": l["bottle_volume_ml"],
            "row_cost_eur": round(pricing.line_cost(l), 3),
            "row_cost_pct": round(pcts[i], 1),
        })
    cost = pricing.drink_cost(lines)
    gp = spec.get("target_gp") or 70
    spec["summary"] = {
        "total_ml": round(pricing.drink_volume(lines), 1),
        "cost_eur": round(cost, 3),
        "abv": round(pricing.drink_abv(lines), 1),
        "suggested_price_eur": pricing.suggested_price(cost, gp),
        "target_gp": gp,
        "margin": round(pricing.margin_pct(spec.get("price_eur") or 0, cost), 1),
    }
    conn.close()
    return spec


def create_spec(data: dict):
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO specs (name, glass, method, garnish, price_eur, target_gp)
           VALUES (?,?,?,?,?,?)""",
        (data["name"], data.get("glass", ""), data.get("method", ""),
         data.get("garnish", ""), data.get("price_eur"), data.get("target_gp", 70)),
    )
    conn.commit()
    new_id = _lastid(cur)
    conn.close()
    return get_spec(new_id)


def update_spec(spec_id: int, data: dict) -> bool:
    conn = _conn()
    cur = conn.execute(
        """UPDATE specs SET name=?, glass=?, method=?, garnish=?,
           price_eur=?, target_gp=? WHERE id=?""",
        (data["name"], data.get("glass", ""), data.get("method", ""),
         data.get("garnish", ""), data.get("price_eur"), data.get("target_gp", 70),
         spec_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def delete_spec(spec_id: int):
    conn = _conn()
    conn.execute("DELETE FROM specs WHERE id=?", (spec_id,))
    conn.commit()
    conn.close()


def duplicate_spec(spec_id: int):
    """Copy a spec + its lines onto a fresh stock-referencing spec."""
    src = get_spec(spec_id)
    if not src:
        return None
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO specs (name, glass, method, garnish, target_gp)
           VALUES (?,?,?,?,?)""",
        (src["name"] + " (copy)", src.get("glass", ""), src.get("method", ""),
         src.get("garnish", ""), src.get("target_gp", 70)),
    )
    new_id = cur.lastrowid
    for line in src["lines"]:
        conn.execute(
            "INSERT INTO spec_lines (spec_id, stock_item_id, amount_ml) VALUES (?,?,?)",
            (new_id, line["stock_item_id"], line["amount_ml"]),
        )
    conn.commit()
    conn.close()
    return get_spec(new_id)


# ---------- spec lines ----------

def add_line(spec_id: int, data: dict):
    """Add an ingredient line to a spec. Resolves the name against stock:
    existing bottle -> reuse it; new name -> create the stock item first."""
    conn = _conn()
    spec = conn.execute("SELECT id FROM specs WHERE id=?", (spec_id,)).fetchone()
    if not spec:
        conn.close()
        return None
    stock = _resolve_stock(conn, data["name"], data.get("abv", 0),
                           data.get("bottle_price_eur", 0),
                           data.get("bottle_volume_ml", 700))
    conn.execute(
        "INSERT INTO spec_lines (spec_id, stock_item_id, amount_ml) VALUES (?,?,?)",
        (spec_id, stock["id"], data["amount_ml"]),
    )
    conn.commit()
    conn.close()
    return get_spec(spec_id)


def update_line(line_id: int, amount_ml: float) -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE spec_lines SET amount_ml=? WHERE id=?", (amount_ml, line_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def delete_line(line_id: int) -> bool:
    conn = _conn()
    cur = conn.execute("DELETE FROM spec_lines WHERE id=?", (line_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


# ---------- menu ----------

def get_menu():
    """All specs with cost + price + margin, for the printable menu view."""
    conn = _conn()
    specs = _spec_rows(conn)
    menu = []
    for s in specs:
        lines = _spec_lines_joined(conn, s["id"])
        cost = pricing.drink_cost(lines)
        price = s.get("price_eur")
        menu.append({
            "id": s["id"], "name": s["name"], "glass": s.get("glass", ""),
            "method": s.get("method", ""), "garnish": s.get("garnish", ""),
            "cost_eur": round(cost, 3),
            "price_eur": price,
            "margin": round(pricing.margin_pct(price or 0, cost), 1),
            "target_gp": s.get("target_gp") or 70,
            "priced": price is not None and price > 0,
        })
    conn.close()
    return menu
