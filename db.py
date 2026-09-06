"""SQLite layer for BarSpec.

Plain sqlite3 on purpose: no ORM, every query visible.
DB file location overridable with BARSPEC_DB env var (tests use a temp file).

Schema history lives in migrations/*.sql, applied in order and tracked with
PRAGMA user_version. A fresh install runs the same migration path as an old
database — every new venue file self-checks its own upgrade.
"""
import os
import sqlite3
from datetime import date, timedelta
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
    dimension = data.get("dimension", "volume")
    if dimension not in ("volume", "weight", "count"):
        conn.close()
        raise ValueError(f"Dimension must be volume|weight|count, got {dimension}")
    cur = conn.execute(
        """INSERT INTO stock_items (name, abv, bottle_price_eur, bottle_volume_ml, dimension)
           VALUES (?,?,?,?,?)""",
        (data["name"].strip(), data.get("abv", 0), data.get("bottle_price_eur", 0),
         data.get("bottle_volume_ml", 700), dimension),
    )
    conn.commit()
    new_id = _lastid(cur)
    conn.close()
    return get_stock_item(new_id)


def update_stock_item(stock_id: int, data: dict):
    """Update a stock item. If the bottle price changed, returns ripple impact:
    [{'spec_id', 'name', 'cost_old', 'cost_new'}] for every spec that uses it.
    Dimension may only change while the item is unused by any spec line."""
    conn = _conn()
    row = conn.execute("SELECT * FROM stock_items WHERE id=?", (stock_id,)).fetchone()
    if not row:
        conn.close()
        return None
    old_price = row["bottle_price_eur"]
    new_price = float(data.get("bottle_price_eur", old_price))

    new_dim = data.get("dimension") or row["dimension"]
    if new_dim not in ("volume", "weight", "count"):
        conn.close()
        raise ValueError(f"Dimension must be volume|weight|count, got {new_dim}")
    if new_dim != row["dimension"] and _stock_usage_count(conn, stock_id) > 0:
        conn.close()
        raise ValueError(
            f"'{row['name']}' is used by specs — remove it from them before "
            "changing its dimension")

    # Ripple impact (only meaningful when the price actually moves).
    # Two levels: specs using the bottle directly AND specs using batches
    # that contain the bottle — one report, no stale costs through a layer.
    impact = []
    if abs(new_price - old_price) > 1e-9:
        for spec in _specs_using_stock(conn, stock_id):
            cost_old = pricing.drink_cost(_spec_lines_all(conn, spec["id"]))
            cost_new = pricing.drink_cost(
                _spec_lines_all(conn, spec["id"], override=(stock_id, new_price)))
            impact.append({
                "spec_id": spec["id"],
                "name": spec["name"],
                "cost_old": round(cost_old, 3),
                "cost_new": round(cost_new, 3),
            })

    conn.execute(
        """UPDATE stock_items SET name=?, abv=?, bottle_price_eur=?, bottle_volume_ml=?,
           dimension=?, updated_at=datetime('now') WHERE id=?""",
        (data.get("name", row["name"]).strip(), data.get("abv", row["abv"]),
         new_price, data.get("bottle_volume_ml", row["bottle_volume_ml"]),
         new_dim, stock_id),
    )
    conn.commit()
    conn.close()
    return {"impact": impact}


def delete_stock_item(stock_id: int):
    """Returns 'ok' | 'in-use' (blocked by spec lines or batch lines)."""
    conn = _conn()
    used = conn.execute(
        "SELECT COUNT(*) FROM spec_lines WHERE stock_item_id=?", (stock_id,)
    ).fetchone()[0]
    if not used:
        used = conn.execute(
            "SELECT COUNT(*) FROM batch_lines WHERE stock_item_id=?", (stock_id,)
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


def _batch_lines_joined(conn, batch_id, override=None):
    """batch_lines joined to stock (LEFT: free-text rows have no stock).
    override = (stock_id, price) replays a stock price change."""
    rows = conn.execute(
        """SELECT bl.id, bl.batch_id, bl.stock_item_id, bl.name, bl.amount_ml,
                  bl.unit, bl.abv, bl.cost_eur,
                  si.bottle_price_eur, si.bottle_volume_ml, si.dimension
           FROM batch_lines bl
           LEFT JOIN stock_items si ON si.id = bl.stock_item_id
           WHERE bl.batch_id = ? ORDER BY bl.sort, bl.id""",
        (batch_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if (d["stock_item_id"] is not None and override is not None
                and d["stock_item_id"] == override[0]):
            d["bottle_price_eur"] = override[1]
        out.append(d)
    return out


def _days_left(made_date, shelf_life_days):
    """None = no expiry (keeps forever). Otherwise days until expiry, negative
    once past — the red-past-expiry signal."""
    if not shelf_life_days:
        return None
    try:
        expiry = date.fromisoformat(made_date) + timedelta(days=int(shelf_life_days))
        return (expiry - date.today()).days
    except (ValueError, TypeError):
        return None


def _batch_payload(conn, batch_id, override=None, cache=None):
    """Full derived picture of one batch: meta + lines + cost/abv/expiry."""
    key = (batch_id, override)
    if cache is not None and key in cache:
        return cache[key]
    row = conn.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if not row:
        return None
    lines = _batch_lines_joined(conn, batch_id, override)
    total = pricing.batch_cost(lines)
    size = row["batch_size_ml"]
    per_ml = pricing.batch_cost_per_ml(total, size)
    # Batch ABV: alcohol from volume stock lines ÷ total batch volume —
    # computed like a drink, so a spec using 25 ml of an infused batch gets
    # its true alcohol share. Sugar/water lines carry none.
    alc = vol = 0.0
    for l in lines:
        if l["dimension"] != "volume":
            continue
        ml = float(l["amount_ml"] or 0) * pricing.UNIT_CANONICAL.get(l["unit"], 1.0)
        vol += ml
        alc += ml * (l.get("abv") or 0) / 100.0
    payload = {
        "id": row["id"], "name": row["name"], "method": row["method"],
        "batch_size_ml": size, "made_date": row["made_date"],
        "shelf_life_days": row["shelf_life_days"],
        "days_left": _days_left(row["made_date"], row["shelf_life_days"]),
        "cost_eur": round(total, 3),
        "cost_per_ml": round(per_ml, 6),
        "batch_abv": round(alc / vol * 100.0, 1) if vol > 0 else 0.0,
        "line_count": len(lines),
        "lines": lines,
    }
    if cache is not None:
        cache[key] = payload
    return payload


def _spec_lines_all(conn, spec_id, override=None):
    """All lines of a spec as pricing-ready dicts — bottle OR batch.

    Bottle lines carry the stock fields and ride the units engine exactly as
    before. Batch lines carry the batch's derived cost/abv/expiry so pricing
    resolves one level (spec → batch → stock) without nesting. `override`
    replays a stock price change for the ripple report."""
    rows = conn.execute(
        """SELECT sl.id, sl.spec_id, sl.stock_item_id, sl.batch_id,
                  sl.amount_ml, sl.unit,
                  si.name AS stock_name, si.abv AS stock_abv,
                  si.bottle_price_eur, si.bottle_volume_ml, si.dimension,
                  b.name AS batch_name
           FROM spec_lines sl
           LEFT JOIN stock_items si ON si.id = sl.stock_item_id
           LEFT JOIN batches b ON b.id = sl.batch_id
           WHERE sl.spec_id = ? ORDER BY sl.id""",
        (spec_id,),
    ).fetchall()
    cache = {}
    out = []
    for r in rows:
        if r["stock_item_id"] is not None:
            price = r["bottle_price_eur"]
            if override is not None and r["stock_item_id"] == override[0]:
                price = override[1]
            out.append({
                "id": r["id"], "spec_id": r["spec_id"], "kind": "bottle",
                "stock_item_id": r["stock_item_id"], "batch_id": None,
                "name": r["stock_name"], "amount_ml": r["amount_ml"],
                "abv": r["stock_abv"], "bottle_price_eur": price,
                "bottle_volume_ml": r["bottle_volume_ml"],
                "unit": r["unit"], "dimension": r["dimension"],
            })
        else:
            b = _batch_payload(conn, r["batch_id"], override, cache)
            out.append({
                "id": r["id"], "spec_id": r["spec_id"], "kind": "batch",
                "stock_item_id": None, "batch_id": r["batch_id"],
                "serve_batch": True,
                "name": b["name"], "amount_ml": r["amount_ml"],
                "abv": b["batch_abv"], "unit": r["unit"],
                "dimension": "volume",
                "bottle_price_eur": None, "bottle_volume_ml": None,
                "batch_size_ml": b["batch_size_ml"],
                "batch_cost_total": b["cost_eur"],
                "batch_cost_per_ml": b["cost_per_ml"],
                "days_left": b["days_left"],
            })
    return out


def _specs_using_stock(conn, stock_id):
    """Specs touched by a stock item: directly via bottle lines OR through
    batches that use it in their lines (two-level ripple)."""
    return conn.execute(
        """SELECT DISTINCT s.id, s.name FROM spec_lines sl
           JOIN specs s ON s.id = sl.spec_id
           WHERE sl.stock_item_id = ?
           UNION
           SELECT DISTINCT s.id, s.name FROM spec_lines sl
           JOIN specs s ON s.id = sl.spec_id
           JOIN batches b ON b.id = sl.batch_id
           JOIN batch_lines bl ON bl.batch_id = b.id
           WHERE bl.stock_item_id = ?
           ORDER BY name""",
        (stock_id, stock_id),
    ).fetchall()


def get_specs():
    conn = _conn()
    specs = _spec_rows(conn)
    for s in specs:
        lines = _spec_lines_all(conn, s["id"])
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
    lines = _spec_lines_all(conn, spec_id)
    pcts = pricing.row_pcts(lines)
    spec["lines"] = []
    for i, l in enumerate(lines):
        if l["kind"] == "bottle":
            spec["lines"].append({
                "id": l["id"], "kind": "bottle",
                "stock_item_id": l["stock_item_id"], "batch_id": None,
                "name": l["name"], "amount_ml": l["amount_ml"], "abv": l["abv"],
                "bottle_price_eur": l["bottle_price_eur"],
                "bottle_volume_ml": l["bottle_volume_ml"],
                "unit": l["unit"], "dimension": l["dimension"],
                "row_cost_eur": round(pricing.line_cost(l), 3),
                "row_cost_pct": round(pcts[i], 1),
            })
        else:
            spec["lines"].append({
                "id": l["id"], "kind": "batch",
                "stock_item_id": None, "batch_id": l["batch_id"],
                "name": l["name"], "amount_ml": l["amount_ml"],
                "abv": l["abv"], "unit": l["unit"], "dimension": "volume",
                "bottle_price_eur": None, "bottle_volume_ml": None,
                "batch_size_ml": l["batch_size_ml"],
                "batch_cost_total": l["batch_cost_total"],
                "batch_cost_per_ml": l["batch_cost_per_ml"],
                "days_left": l["days_left"],
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
    """Add an ingredient line to a spec: a stock bottle OR a house batch
    (batch_id set). Resolves the name against stock for bottle lines: existing
    item -> reuse; new name -> create the stock item first. The line unit must
    match the reference's dimension (batches are poured in volume units)."""
    conn = _conn()
    spec = conn.execute("SELECT id FROM specs WHERE id=?", (spec_id,)).fetchone()
    if not spec:
        conn.close()
        return None
    batch_id = data.get("batch_id")
    if batch_id is not None:
        unit = str(data.get("unit") or "ml")
        if not pricing.valid_unit(unit) or pricing.UNIT_DIMENSION[unit] != "volume":
            conn.close()
            raise ValueError("Batch pours use volume units (ml/cl/oz)")
        b = conn.execute("SELECT id FROM batches WHERE id=?", (batch_id,)).fetchone()
        if not b:
            conn.close()
            raise ValueError("Batch not found")
        conn.execute(
            "INSERT INTO spec_lines (spec_id, batch_id, amount_ml, unit) VALUES (?,?,?,?)",
            (spec_id, batch_id, data["amount_ml"], unit),
        )
        conn.commit()
        conn.close()
        return get_spec(spec_id)
    name = str(data.get("name") or "").strip()
    if not name:
        conn.close()
        raise ValueError("Line needs a stock name or a batch")
    stock = _resolve_stock(conn, name, data.get("abv", 0),
                           data.get("bottle_price_eur", 0),
                           data.get("bottle_volume_ml", 700))
    unit = str(data.get("unit") or "ml")
    if not pricing.valid_unit(unit):
        conn.close()
        raise ValueError(f"Unknown unit '{unit}'")
    if pricing.UNIT_DIMENSION[unit] != stock["dimension"]:
        conn.close()
        raise ValueError(
            f"Unit '{unit}' is {pricing.UNIT_DIMENSION[unit]}, but "
            f"'{stock['name']}' is measured in {stock['dimension']}")
    conn.execute(
        "INSERT INTO spec_lines (spec_id, stock_item_id, amount_ml, unit) VALUES (?,?,?,?)",
        (spec_id, stock["id"], data["amount_ml"], unit),
    )
    conn.commit()
    conn.close()
    return get_spec(spec_id)


def update_line(line_id: int, amount_ml: float, unit: str | None = None) -> bool:
    conn = _conn()
    if unit is not None:
        if not pricing.valid_unit(unit):
            conn.close()
            raise ValueError(f"Unknown unit '{unit}'")
        row = conn.execute(
            """SELECT sl.id, si.dimension, sl.stock_item_id, sl.batch_id
               FROM spec_lines sl
               LEFT JOIN stock_items si ON si.id = sl.stock_item_id
               WHERE sl.id=?""",
            (line_id,),
        ).fetchone()
        if not row:
            conn.close()
            return False
        # batch lines carry no stock row — they are volume pours by nature
        dim = row["dimension"] if row["stock_item_id"] is not None else "volume"
        if pricing.UNIT_DIMENSION[unit] != dim:
            conn.close()
            raise ValueError(
                f"Unit '{unit}' doesn't match this line's dimension ({dim})")
        cur = conn.execute(
            "UPDATE spec_lines SET amount_ml=?, unit=? WHERE id=?",
            (amount_ml, unit, line_id),
        )
    else:
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
        lines = _spec_lines_all(conn, s["id"])
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


# ---------- batches (004) ----------

def create_batch(data: dict):
    conn = _conn()
    dup = conn.execute(
        "SELECT id FROM batches WHERE lower(name)=lower(?)", (data["name"],)
    ).fetchone()
    if dup:
        conn.close()
        raise ValueError("Batch name already exists")
    size = float(data.get("batch_size_ml") or 0)
    if size <= 0:
        conn.close()
        raise ValueError("Batch size must be > 0")
    cur = conn.execute(
        """INSERT INTO batches (name, method, batch_size_ml, made_date, shelf_life_days)
           VALUES (?,?,?,?,?)""",
        (data["name"].strip(), data.get("method", ""), size,
         data.get("made_date") or date.today().isoformat(),
         data.get("shelf_life_days")),
    )
    conn.commit()
    new_id = _lastid(cur)
    conn.close()
    return get_batch(new_id)


def get_batches():
    conn = _conn()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM batches ORDER BY lower(name)")]
    out = [_batch_payload(conn, i) for i in ids]
    conn.close()
    return [b for b in out if b]


def get_batch(batch_id: int):
    conn = _conn()
    b = _batch_payload(conn, batch_id)
    conn.close()
    return b


def update_batch(batch_id: int, data: dict):
    conn = _conn()
    row = conn.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if not row:
        conn.close()
        return None
    name = str(data.get("name", row["name"])).strip()
    dup = conn.execute(
        "SELECT id FROM batches WHERE lower(name)=lower(?) AND id != ?",
        (name, batch_id)).fetchone()
    if dup:
        conn.close()
        raise ValueError("Batch name already exists")
    size = float(data.get("batch_size_ml", row["batch_size_ml"]) or 0)
    if size <= 0:
        conn.close()
        raise ValueError("Batch size must be > 0")
    shelf = data.get("shelf_life_days", row["shelf_life_days"])
    conn.execute(
        """UPDATE batches SET name=?, method=?, batch_size_ml=?, made_date=?,
           shelf_life_days=?, updated_at=datetime('now') WHERE id=?""",
        (name, data.get("method", row["method"]), size,
         data.get("made_date", row["made_date"]), shelf, batch_id),
    )
    conn.commit()
    conn.close()
    return get_batch(batch_id)


def delete_batch(batch_id: int):
    conn = _conn()
    used = conn.execute(
        "SELECT COUNT(*) FROM spec_lines WHERE batch_id=?", (batch_id,)
    ).fetchone()[0]
    if used:
        conn.close()
        raise ValueError("Batch is used by specs — remove it from them first")
    conn.execute("DELETE FROM batches WHERE id=?", (batch_id,))  # lines cascade
    conn.commit()
    conn.close()
    return True


def add_batch_line(batch_id: int, data: dict):
    """One ingredient of a batch. Two price sources, exactly one:
    - name matches existing stock (any dimension)  -> derives live;
    - otherwise free-text and cost_eur is required (may be €0: water)."""
    conn = _conn()
    if not conn.execute("SELECT id FROM batches WHERE id=?", (batch_id,)).fetchone():
        conn.close()
        return None
    name = str(data["name"]).strip()
    if not name:
        conn.close()
        raise ValueError("Ingredient name needed")
    unit = str(data.get("unit") or "g")
    if not pricing.valid_unit(unit):
        conn.close()
        raise ValueError(f"Unknown unit '{unit}'")
    amount = float(data.get("amount_ml") or 0)
    if amount <= 0:
        conn.close()
        raise ValueError("Amount must be > 0")
    stock = conn.execute(
        "SELECT * FROM stock_items WHERE lower(name)=lower(?) ORDER BY id LIMIT 1",
        (name,),
    ).fetchone()
    if stock:
        if pricing.UNIT_DIMENSION[unit] != stock["dimension"]:
            conn.close()
            raise ValueError(
                f"Unit '{unit}' doesn't match '{stock['name']}' "
                f"({stock['dimension']})")
        cur = conn.execute(
            """INSERT INTO batch_lines (batch_id, stock_item_id, name, amount_ml,
               unit, abv, cost_eur) VALUES (?,?,?,?,?,?,NULL)""",
            (batch_id, stock["id"], stock["name"], amount, unit,
             stock["abv"] or 0),
        )
    else:
        cost = data.get("cost_eur")
        if cost is None:
            conn.close()
            raise ValueError(
                f"'{name}' isn't in stock — add a typed € cost for this amount "
                "(€0 is fine for water)")
        cur = conn.execute(
            """INSERT INTO batch_lines (batch_id, stock_item_id, name, amount_ml,
               unit, abv, cost_eur) VALUES (?,NULL,?,?,?,?,?)""",
            (batch_id, name, amount, unit, data.get("abv", 0), float(cost)),
        )
    conn.commit()
    conn.close()
    return get_batch(batch_id)


def delete_batch_line(line_id: int) -> bool:
    conn = _conn()
    cur = conn.execute("DELETE FROM batch_lines WHERE id=?", (line_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


# ---------- stock-take (par levels + dated snapshots) ----------

def set_stock_par(stock_id: int, par_level: float | None) -> bool:
    """Set (or clear, with None) a bottle's par level. Par <= 0 is treated as
    'not counted' (stored NULL) — a zero target makes no sense on a bar floor.
    Weight items (kg bags etc) are excluded from the count walk in v1: you
    count bottles and pieces, you weigh stock — different job, later design."""
    conn = _conn()
    row = conn.execute(
        "SELECT dimension FROM stock_items WHERE id=?", (stock_id,)
    ).fetchone()
    if not row:
        conn.close()
        return False
    if row["dimension"] == "weight":
        conn.close()
        raise ValueError("Weight items (kg/g) aren't counted in the stock-take yet")
    par = par_level
    if par is None or par <= 0:
        par = None
    cur = conn.execute(
        "UPDATE stock_items SET par_level=?, updated_at=datetime('now') WHERE id=?",
        (par, stock_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def _fractions() -> tuple:
    return pricing.OPEN_FRACTIONS


def get_take_sheet():
    """The count list: every bottle with a par, prefilled with the values from
    the most recent snapshot (correct only what changed). No par = not counted.

    Returns {"last_take": {id, taken_at} | None, "rows": [stock items with
    par_level plus last_full_bottles / last_open_fraction (None when the item
    was never counted)]}.
    """
    conn = _conn()
    last = conn.execute(
        "SELECT id, taken_at FROM stock_takes ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_vals = {}
    if last:
        for r in conn.execute(
            """SELECT stock_item_id, full_bottles, open_fraction
               FROM stock_take_lines WHERE take_id=?""",
            (last["id"],),
        ):
            last_vals[r["stock_item_id"]] = dict(r)
    rows = []
    for r in conn.execute(
        "SELECT * FROM stock_items WHERE par_level IS NOT NULL "
        "AND dimension IN ('volume','count') ORDER BY lower(name)"
    ):
        d = dict(r)
        prev = last_vals.get(d["id"])
        d["last_full_bottles"] = prev["full_bottles"] if prev else None
        d["last_open_fraction"] = prev["open_fraction"] if prev else None
        rows.append(d)
    conn.close()
    return {"last_take": dict(last) if last else None, "rows": rows}


def _review_rows(conn, lines):
    """lines: [{stock_item_id, full_bottles, open_fraction}] already validated.
    Builds the order-list rows: FBE, shortfall to order, cash asleep — all via
    pricing.py. Bottle metadata joined live so prices/pars are never stale."""
    rows = []
    for ln in lines:
        stock = conn.execute(
            "SELECT id, name, bottle_price_eur, bottle_volume_ml, par_level "
            "FROM stock_items WHERE id=?",
            (ln["stock_item_id"],),
        ).fetchone()
        if not stock:
            continue  # bottle deleted mid-count; drop the line, keep the take
        par = stock["par_level"]
        if par is None:
            continue  # par cleared mid-count; nothing to order against
        fb = ln["full_bottles"]
        frac = ln["open_fraction"]
        fbe_val = pricing.fbe(fb, frac)
        rows.append({
            "stock_item_id": stock["id"],
            "name": stock["name"],
            "bottle_price_eur": stock["bottle_price_eur"],
            "bottle_volume_ml": stock["bottle_volume_ml"],
            "par_level": par,
            "full_bottles": fb,
            "open_fraction": frac,
            "fbe": round(fbe_val, 2),
            "to_order": pricing.order_shortfall(par, fbe_val),
            "excess_fbe": round(pricing.excess_fbe(par, fbe_val), 2),
            "cash_asleep_eur": round(
                pricing.cash_asleep_eur(fbe_val, par, stock["bottle_price_eur"] or 0), 2),
        })
    return rows


def _review_payload(take_id, taken_at, rows):
    order_total = sum(r["to_order"] for r in rows)
    asleep_total = round(sum(r["cash_asleep_eur"] for r in rows), 2)
    short = [r for r in rows if r["to_order"] > 0]
    over = [r for r in rows if r["excess_fbe"] > 0]
    at_par = [r for r in rows if r["to_order"] == 0 and r["excess_fbe"] <= 0]
    return {
        "take": {"id": take_id, "taken_at": taken_at},
        "counted": len(rows),
        "order_total": order_total,
        "cash_asleep_total": asleep_total,
        "short": short,
        "over": over,
        "at_par": at_par,
    }


def save_stock_take(lines: list[dict]) -> dict:
    """Persist one dated snapshot. lines must reference bottles that have a par
    set; fractions must be in the allowed set. Returns the review payload
    computed from the saved snapshot (single round-trip for the UI)."""
    if not lines:
        raise ValueError("Nothing to count — set par levels first")
    conn = _conn()
    try:
        seen = set()
        clean = []
        for ln in lines:
            sid = int(ln["stock_item_id"])
            fb = int(ln.get("full_bottles", 0) or 0)
            frac = float(ln.get("open_fraction", 0) or 0)
            if fb < 0:
                raise ValueError(f"Full bottles can't be negative ({fb})")
            if frac not in _fractions():
                raise ValueError(f"Open fraction must be one of {_fractions()}, got {frac}")
            stock = conn.execute(
                "SELECT par_level FROM stock_items WHERE id=?", (sid,)
            ).fetchone()
            if not stock:
                raise ValueError(f"Unknown bottle id {sid}")
            if stock["par_level"] is None:
                raise ValueError(f"'{sid}' has no par level — set one before counting")
            if sid in seen:
                continue  # duplicate line for same bottle: last write wins
            seen.add(sid)
            clean.append({"stock_item_id": sid, "full_bottles": fb, "open_fraction": frac})

        cur = conn.execute("INSERT INTO stock_takes (taken_at) VALUES (datetime('now'))")
        take_id = _lastid(cur)
        conn.executemany(
            "INSERT INTO stock_take_lines (take_id, stock_item_id, full_bottles, open_fraction) "
            "VALUES (?,?,?,?)",
            [(take_id, ln["stock_item_id"], ln["full_bottles"], ln["open_fraction"])
             for ln in clean],
        )
        conn.commit()
        taken_at = conn.execute(
            "SELECT taken_at FROM stock_takes WHERE id=?", (take_id,)
        ).fetchone()["taken_at"]
        rows = _review_rows(conn, clean)
        conn.close()
        return _review_payload(take_id=take_id, taken_at=taken_at, rows=rows)
    except ValueError:
        conn.close()
        raise


def get_last_stock_take() -> dict | None:
    """The most recent snapshot's order-list review (what the Order tab shows
    after a reload). None when no snapshot exists yet."""
    conn = _conn()
    last = conn.execute(
        "SELECT id, taken_at FROM stock_takes ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not last:
        conn.close()
        return None
    lines = [
        dict(r) for r in conn.execute(
            "SELECT stock_item_id, full_bottles, open_fraction "
            "FROM stock_take_lines WHERE take_id=? ORDER BY id",
            (last["id"],),
        )
    ]
    rows = _review_rows(conn, lines)
    payload = _review_payload(last["id"], last["taken_at"], rows)
    conn.close()
    return payload


def get_stock_trends() -> dict:
    """Movement between the two latest snapshots + dead-stock list.

    Movement needs 2+ snapshots (views gate on history): FBE delta per bottle
    between the last two takes. Positive = consumed. When a bottle appears in
    only one of the two, it's flagged rather than guessed.
    Dead stock (spec_count == 0) works immediately, no history needed.
    """
    conn = _conn()
    takes = conn.execute(
        "SELECT id, taken_at FROM stock_takes ORDER BY id DESC LIMIT 2"
    ).fetchall()
    movement = []
    if len(takes) == 2:
        newest, older = takes[0], takes[1]

        def counts_of(take_id):
            return {
                r["stock_item_id"]: dict(r) for r in conn.execute(
                    "SELECT stock_item_id, full_bottles, open_fraction "
                    "FROM stock_take_lines WHERE take_id=?", (take_id,))
            }

        nc, oc = counts_of(newest["id"]), counts_of(older["id"])
        for sid in sorted(set(nc) | set(oc)):
            stock = conn.execute(
                "SELECT name, bottle_price_eur, bottle_volume_ml FROM stock_items WHERE id=?",
                (sid,),
            ).fetchone()
            if not stock:
                continue
            new_line, old_line = nc.get(sid), oc.get(sid)
            new_fbe = pricing.fbe(new_line["full_bottles"], new_line["open_fraction"]) if new_line else None
            old_fbe = pricing.fbe(old_line["full_bottles"], old_line["open_fraction"]) if old_line else None
            if old_line and new_line:
                used = round(old_fbe - new_fbe, 2)
                movement.append({
                    "stock_item_id": sid, "name": stock["name"],
                    "bottle_price_eur": stock["bottle_price_eur"],
                    "bottle_volume_ml": stock["bottle_volume_ml"],
                    "prev_fbe": old_fbe, "fbe": new_fbe,
                    "used_fbe": used,
                    "used_ml": round(used * stock["bottle_volume_ml"], 0),
                    "used_eur": round(used * (stock["bottle_price_eur"] or 0), 2),
                    "state": "used" if used > 0.001 else ("unmoved" if abs(used) <= 0.001 else "gained"),
                })
            else:
                movement.append({
                    "stock_item_id": sid, "name": stock["name"],
                    "bottle_price_eur": stock["bottle_price_eur"],
                    "bottle_volume_ml": stock["bottle_volume_ml"],
                    "prev_fbe": old_fbe, "fbe": new_fbe,
                    "used_fbe": None, "used_ml": None, "used_eur": None,
                    "state": "first_count" if new_line else "not_counted",
                })
    # Dead stock: bottles in the list that no spec uses. Works from day one.
    dead = []
    for r in conn.execute(
        "SELECT id, name, abv, bottle_price_eur, bottle_volume_ml, par_level "
        "FROM stock_items ORDER BY lower(name)"
    ):
        if _stock_usage_count(conn, r["id"]) == 0:
            dead.append(dict(r))
    conn.close()
    return {
        "takes_count": len(takes),
        "movement": movement,
        "dead_stock": dead,
    }
