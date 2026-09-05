"""SQLite layer for BarSpec.

Plain sqlite3 on purpose: no ORM, every query visible.
DB file lives in this folder as barspec.db (created on first run).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "barspec.db"

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
    return conn


def init_db():
    conn = _conn()
    conn.executescript(SCHEMA)
    # Seed once: only if the specs table is empty.
    count = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
    if count == 0:
        for spec in SEED_SPECS:
            cur = conn.execute(
                "INSERT INTO specs (name, glass, method, garnish) VALUES (?,?,?,?)",
                (spec["name"], spec["glass"], spec["method"], spec["garnish"]),
            )
            spec_id = cur.lastrowid
            for ing in spec["ingredients"]:
                conn.execute(
                    """INSERT INTO ingredients
                       (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml)
                       VALUES (?,?,?,?,?,?)""",
                    (spec_id, ing["name"], ing["amount_ml"], ing["abv"],
                     ing["bottle_price_eur"], ing["bottle_volume_ml"]),
                )
        conn.commit()
    conn.close()


def _spec_row_to_dict(row):
    return {
        "id": row["id"], "name": row["name"], "glass": row["glass"],
        "method": row["method"], "garnish": row["garnish"],
    }


def get_specs():
    conn = _conn()
    rows = conn.execute("SELECT * FROM specs ORDER BY name").fetchall()
    conn.close()
    return [_spec_row_to_dict(r) for r in rows]


def get_spec(spec_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM specs WHERE id=?", (spec_id,)).fetchone()
    if not row:
        conn.close()
        return None
    spec = _spec_row_to_dict(row)
    ing_rows = conn.execute(
        "SELECT * FROM ingredients WHERE spec_id=? ORDER BY id", (spec_id,)
    ).fetchall()
    spec["ingredients"] = [
        {
            "id": i["id"], "name": i["name"], "amount_ml": i["amount_ml"],
            "abv": i["abv"], "bottle_price_eur": i["bottle_price_eur"],
            "bottle_volume_ml": i["bottle_volume_ml"],
        }
        for i in ing_rows
    ]
    spec["summary"] = _summarize(spec["ingredients"])
    conn.close()
    return spec


def create_spec(data: dict):
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO specs (name, glass, method, garnish) VALUES (?,?,?,?)",
        (data["name"], data["glass"], data["method"], data["garnish"]),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_spec(new_id)


def update_spec(spec_id: int, data: dict) -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE specs SET name=?, glass=?, method=?, garnish=? WHERE id=?",
        (data["name"], data["glass"], data["method"], data["garnish"], spec_id),
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


def add_ingredient(spec_id: int, data: dict):
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO ingredients
           (spec_id, name, amount_ml, abv, bottle_price_eur, bottle_volume_ml)
           VALUES (?,?,?,?,?,?)""",
        (spec_id, data["name"], data["amount_ml"], data["abv"],
         data["bottle_price_eur"], data["bottle_volume_ml"]),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_spec(spec_id)


def update_ingredient(ing_id: int, data: dict) -> bool:
    conn = _conn()
    cur = conn.execute(
        """UPDATE ingredients SET name=?, amount_ml=?, abv=?,
           bottle_price_eur=?, bottle_volume_ml=? WHERE id=?""",
        (data["name"], data["amount_ml"], data["abv"],
         data["bottle_price_eur"], data["bottle_volume_ml"], ing_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def delete_ingredient(ing_id: int):
    conn = _conn()
    conn.execute("DELETE FROM ingredients WHERE id=?", (ing_id,))
    conn.commit()
    conn.close()


# ---------- Cost / ABV math ----------

def _summarize(ingredients: list[dict]) -> dict:
    """Cost and ABV for ONE serving, pre-dilution.

    cost/ml of an ingredient = bottle_price / bottle_volume.
    Drink ABV = volume-weighted average across ingredients.
    """
    total_ml = 0.0
    total_cost = 0.0
    abv_volume = 0.0
    for i in ingredients:
        amount = i["amount_ml"]
        total_ml += amount
        if i["bottle_volume_ml"] > 0:
            cost_per_ml = i["bottle_price_eur"] / i["bottle_volume_ml"]
            total_cost += amount * cost_per_ml
        abv_volume += amount * (i["abv"] / 100.0)
    abv = (abv_volume / total_ml * 100.0) if total_ml > 0 else 0.0
    return {
        "total_ml": round(total_ml, 1),
        "cost_eur": round(total_cost, 3),
        "abv": round(abv, 1),
    }
