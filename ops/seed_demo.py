"""Fictional demo venue — "The Prancing Pony".

A classic neighbourhood bar *with a kitchen*: classic cocktails, draught and
canned beer, wines by the glass and the bottle, sodas, coffee and a short
snack menu. Entirely invented: no real bar's name, menu or supplier prices.

    BARSPEC_DB=/tmp/demo.db python -m ops.seed_demo --month
    BARSPEC_DB=/tmp/demo.db .venv/bin/python ops/seed_demo.py --month

Deterministic — same data every run (see ops/seed_common.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # ops/ (seed_common)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # repo root (db, auth)

import db
from seed_common import seed_month, supplier_for

VENUE = {"name": "The Prancing Pony", "iva": 23,
         "owner_pin": "1234", "staff_pin": "2468"}

# (name, abv, price, size_canonical, dimension, pack=(qty, price, label), yield)
STOCK = [
    # ---- spirits (700 ml) ----
    ("Gin seco",                40.0, 17.00,  700, "volume", None, None),
    ("Vodka",                   40.0, 15.00,  700, "volume", None, None),
    ("Rum branco",              40.0, 16.00,  700, "volume", None, None),
    ("Rum escuro",              40.0, 18.00,  700, "volume", None, None),
    ("Cachaça",                 41.0, 14.00,  700, "volume", None, None),
    ("Tequila",                 38.0, 23.00,  700, "volume", None, None),
    ("Bourbon",                 43.0, 24.00,  700, "volume", None, None),
    ("Whisky escocês",          40.0, 20.00,  700, "volume", None, None),
    ("Vermute tinto",           16.0,  9.00, 1000, "volume", None, None),
    ("Vermute branco",          15.0,  8.00, 1000, "volume", None, None),
    ("Bitter vermelho",         25.0, 18.00, 1000, "volume", None, None),
    ("Aperitivo laranja",       11.0, 15.00, 1000, "volume", None, None),
    ("Triple sec",              40.0, 13.00,  700, "volume", None, None),
    ("Licor de café",           20.0, 16.00,  700, "volume", None, None),
    ("Licor de amêndoa",        28.0, 15.00,  700, "volume", None, None),
    ("Vinho do Porto",          20.0, 13.00,  750, "volume", None, None),
    ("Bitter aromático",        44.7, 11.00,  200, "volume", None, None),
    # ---- juices, syrups, mixers ----
    ("Sumo de limão",            0.0,  3.50, 1000, "volume", None, None),
    ("Sumo de lima",             0.0,  4.00, 1000, "volume", None, None),
    ("Groselha",                 0.0,  6.00, 1000, "volume", None, None),
    ("Leite de coco",            0.0,  3.20, 1000, "volume", None, None),
    ("Sumo de ananás",           0.0,  3.00, 1000, "volume", None, None),
    ("Sumo de laranja",          0.0,  2.60, 1000, "volume", None, None),
    ("Espumante branco",        11.0,  6.80,  750, "volume", None, None),
    ("Tónica lata 20cl",         0.0, 13.20,    1, "count", (24, 13.20, "caixa"), None),
    ("Ginger beer lata 33cl",    0.0, 21.60,    1, "count", (24, 21.60, "caixa"), None),
    ("Cola lata 33cl",           0.0, 13.44,    1, "count", (24, 13.44, "caixa"), None),
    ("Laranjada lata 33cl",      0.0, 13.44,    1, "count", (24, 13.44, "caixa"), None),
    ("Néctar de pêssego 33cl",   0.0, 12.96,    1, "count", (24, 12.96, "caixa"), None),
    ("Água",                     0.0,  0.00, 1000, "volume", None, None),
    ("Água com gás (garrafa 1L)", 0.0, 0.95, 1000, "volume", None, None),
    ("Tónica (garrafa 1L)",      0.0,  1.20, 1000, "volume", None, None),
    ("Ginger beer (garrafa 1L)", 0.0,  2.60, 1000, "volume", None, None),
    ("Água 50cl",                0.0,  4.20,    1, "count", (12,  4.20, "caixa"), None),
    ("Água com gás 50cl",        0.0,  4.68,    1, "count", (12,  4.68, "caixa"), None),
    ("Açúcar",                   0.0,  1.20, 1000, "weight", None, None),
    ("Azeite",                   0.0,  6.20, 1000, "volume", None, None),
    ("Leite meio-gordo",         0.0,  1.00, 1000, "volume", None, None),
    # ---- beer ----
    ("Barril lager 30L",         5.0, 80.00,30000, "volume", None, None),
    ("Lager lata 33cl",          5.0, 15.12,    1, "count", (24, 15.12, "caixa"), None),
    ("Stout garrafa 33cl",       4.2, 14.40,    1, "count", (12, 14.40, "caixa"), None),
    ("Cerveja sem álcool 33cl",  0.5, 11.40,    1, "count", (12, 11.40, "caixa"), None),
    # ---- wine ----
    ("Vinho branco regional",   12.0,  6.50,  750, "volume", None, None),
    ("Vinho tinto regional",    13.0,  7.20,  750, "volume", None, None),
    ("Vinho verde",             10.5,  6.00,  750, "volume", None, None),
    ("Vinho rosé",              12.0,  6.40,  750, "volume", None, None),
    # ---- coffee ----
    ("Café em grão",             0.0, 13.50, 1000, "weight", None, None),
    # ---- kitchen ----
    ("Pão",                      0.0,  8.00,   20, "count", None, None),
    ("Queijo flamengo",          0.0,  8.50, 1000, "weight", None, 1.0),
    ("Fiambre",                  0.0,  7.50, 1000, "weight", None, 1.0),
    ("Manteiga",                 0.0,  6.50, 1000, "weight", None, 1.0),
    ("Bife de vaca",             0.0, 11.50, 1000, "weight", None, 0.90),
    ("Peito de frango",          0.0,  7.00, 1000, "weight", None, 0.95),
    ("Batata",                   0.0,  1.10, 1000, "weight", None, 0.85),
    ("Alface",                   0.0,  1.20,    1, "count", None, None),
    ("Tomate",                   0.0,  1.80, 1000, "weight", None, None),
    ("Alho",                     0.0,  4.50, 1000, "weight", None, None),
    ("Hortelã",                  0.0,  6.00,   10, "count", None, None),
    ("Ovo",                      0.0,  2.40,   12, "count", None, None),
]

W = "Água"          # poured water placeholder is not needed — classics use real mixers

# (name, category, glass, method, garnish, price, [(stock, amount, unit)])
COCKTAILS = [
    ("Negroni", "Cocktails Clássicos", "copo baixo", "Misturar no copo", "Casca de laranja", 8.50,
     [("Gin seco", 30, "ml"), ("Vermute tinto", 30, "ml"), ("Bitter vermelho", 30, "ml")]),
    ("Margarita", "Cocktails Clássicos", "copo coupe", "Agitar com gelo", "Borda de sal", 8.50,
     [("Tequila", 50, "ml"), ("Triple sec", 20, "ml"), ("Sumo de lima", 25, "ml")]),
    ("Daiquiri", "Cocktails Clássicos", "copo coupe", "Agitar com gelo", "Roda de lima", 7.50,
     [("Rum branco", 50, "ml"), ("Sumo de lima", 25, "ml"), ("@Xarope simples", 15, "ml")]),
    ("Mojito", "Cocktails Clássicos", "copo alto", "Macerar, gelo, completar", "Ramo de hortelã", 8.00,
     [("Rum branco", 50, "ml"), ("Sumo de lima", 25, "ml"), ("@Xarope simples", 20, "ml"),
      ("Hortelã", 1, "piece"), ("Água com gás (garrafa 1L)", 60, "ml")]),
    ("Caipirinha", "Cocktails Clássicos", "copo baixo", "Macerar com açúcar", "Roda de lima", 7.50,
     [("Cachaça", 60, "ml"), ("Sumo de lima", 40, "ml"), ("Açúcar", 15, "g")]),
    ("Old Fashioned", "Cocktails Clássicos", "copo baixo", "Mexer no copo", "Casca de laranja", 9.00,
     [("Bourbon", 60, "ml"), ("@Xarope simples", 5, "ml"), ("Bitter aromático", 1, "ml")]),
    ("Whiskey Sour", "Cocktails Clássicos", "copo baixo", "Agitar com gelo", "Cereja", 8.50,
     [("Bourbon", 50, "ml"), ("Sumo de limão", 25, "ml"), ("@Xarope simples", 20, "ml")]),
    ("Moscow Mule", "Cocktails Clássicos", "caneca de cobre", "Construir no gelo", "Roda de lima", 8.00,
     [("Vodka", 50, "ml"), ("Ginger beer (garrafa 1L)", 100, "ml"), ("Sumo de lima", 15, "ml")]),
    ("Spritz Aperitivo", "Cocktails Clássicos", "copo de vinho", "Construir no gelo", "Roda de laranja", 7.50,
     [("Aperitivo laranja", 60, "ml"), ("Espumante branco", 90, "ml"), ("Água com gás (garrafa 1L)", 30, "ml")]),
    ("Gin Tónico", "Cocktails Clássicos", "copo alto", "Construir no gelo", "Ramo de zimbro", 8.00,
     [("Gin seco", 50, "ml"), ("Tónica (garrafa 1L)", 200, "ml"), ("Sumo de lima", 10, "ml")]),
    ("Espresso Martini", "Cocktails Clássicos", "copo martini", "Agitar com gelo", "Grãos de café", 8.50,
     [("Vodka", 40, "ml"), ("Licor de café", 20, "ml"), ("Café em grão", 8, "g")]),
    ("Piña Colada", "Cocktails Clássicos", "copo alto", "Agitar com gelo", "Roda de ananás", 8.50,
     [("Rum escuro", 50, "ml"), ("Leite de coco", 50, "ml"), ("Sumo de ananás", 90, "ml")]),
    ("Porto Tónico", "Cocktails Clássicos", "copo alto", "Construir no gelo", "Casca de laranja", 7.50,
     [("Vinho do Porto", 60, "ml"), ("Tónica (garrafa 1L)", 200, "ml"), ("Sumo de lima", 10, "ml")]),
    ("Sangria (jarra 1L)", "Cocktails Clássicos", "jarra", "Misturar e refrigerar", "Fruta da estação", 14.00,
     [("Vinho tinto regional", 750, "ml"), ("Sumo de laranja", 150, "ml"),
      ("Groselha", 20, "ml"), ("Açúcar", 40, "g")]),
]

# straight serves: (name, category, price, stock, amount, unit)
PRODUCTS = [
    # beer
    ("Imperial (20cl)", "Cerveja", 1.80, "Barril lager 30L", 200, "ml"),
    ("Caneca (50cl)", "Cerveja", 4.20, "Barril lager 30L", 500, "ml"),
    ("Lager lata 33cl", "Cerveja", 2.60, "Lager lata 33cl", 1, "piece"),
    ("Stout garrafa 33cl", "Cerveja", 3.20, "Stout garrafa 33cl", 1, "piece"),
    ("Cerveja sem álcool", "Cerveja", 2.20, "Cerveja sem álcool 33cl", 1, "piece"),
    # wine
    ("Branco copo 15cl", "Vinho", 3.50, "Vinho branco regional", 150, "ml"),
    ("Branco garrafa", "Vinho", 16.00, "Vinho branco regional", 750, "ml"),
    ("Tinto copo 15cl", "Vinho", 3.50, "Vinho tinto regional", 150, "ml"),
    ("Tinto garrafa", "Vinho", 16.00, "Vinho tinto regional", 750, "ml"),
    ("Verde copo 15cl", "Vinho", 3.20, "Vinho verde", 150, "ml"),
    ("Verde garrafa", "Vinho", 14.00, "Vinho verde", 750, "ml"),
    ("Rosé copo 15cl", "Vinho", 3.50, "Vinho rosé", 150, "ml"),
    ("Rosé garrafa", "Vinho", 15.00, "Vinho rosé", 750, "ml"),
    ("Espumante copo 12cl", "Vinho", 4.00, "Espumante branco", 120, "ml"),
    ("Espumante garrafa", "Vinho", 22.00, "Espumante branco", 750, "ml"),
    # soft drinks
    ("Cola", "Bebidas", 2.20, "Cola lata 33cl", 1, "piece"),
    ("Laranjada", "Bebidas", 2.20, "Laranjada lata 33cl", 1, "piece"),
    ("Néctar de pêssego", "Bebidas", 2.50, "Néctar de pêssego 33cl", 1, "piece"),
    ("Tónica", "Bebidas", 2.40, "Tónica lata 20cl", 1, "piece"),
    ("Água 50cl", "Bebidas", 1.50, "Água 50cl", 1, "piece"),
    ("Água com gás 50cl", "Bebidas", 1.60, "Água com gás 50cl", 1, "piece"),
    ("Sumo de laranja 25cl", "Bebidas", 3.00, "Sumo de laranja", 250, "ml"),
    # coffee
    ("Expresso", "Café", 1.20, "Café em grão", 8, "g"),
    ("Duplo", "Café", 1.60, "Café em grão", 16, "g"),
]

# kitchen: multi-line specs (name, category, price, [(stock, amount, unit)])
KITCHEN = [
    ("Meia de leite", "Café", 1.70,
     [("Café em grão", 8, "g"), ("Leite meio-gordo", 120, "ml")]),
    ("Galão", "Café", 2.20,
     [("Café em grão", 16, "g"), ("Leite meio-gordo", 200, "ml")]),
    ("Tosta mista", "Cozinha", 4.50,
     [("Pão", 2, "piece"), ("Queijo flamengo", 40, "g"), ("Fiambre", 40, "g"),
      ("Manteiga", 10, "g")]),
    ("Prego no pão", "Cozinha", 7.00,
     [("Pão", 1, "piece"), ("Bife de vaca", 120, "g"), ("Alho", 5, "g"),
      ("Manteiga", 10, "g")]),
    ("Pica-pau", "Cozinha", 9.50,
     [("Bife de vaca", 150, "g"), ("Alho", 8, "g"), ("Azeite", 15, "ml"),
      ("Pão", 1, "piece")]),
    ("Batata frita", "Cozinha", 3.50,
     [("Batata", 200, "g"), ("Azeite", 20, "ml")]),
    ("Salada de alface e tomate", "Cozinha", 4.00,
     [("Alface", 1, "piece"), ("Tomate", 120, "g"), ("Azeite", 10, "ml")]),
    ("Frango grelhado no pão", "Cozinha", 6.50,
     [("Pão", 1, "piece"), ("Peito de frango", 120, "g"), ("Alface", 1, "piece")]),
]

BATCHES = [
    {"name": "Xarope simples", "method": "Açúcar + água a ferver, 1:1, arrefecer",
     "size": 2000, "shelf": 30,
     "lines": [("Açúcar", 1000, "g"), ("Água", 1000, "ml")]},
    {"name": "Xarope de gengibre", "method": "Gengibre fresco + açúcar, 30 min",
     "size": 1000, "shelf": 14,
     "lines": [("Açúcar", 600, "g"), ("Ginger beer (garrafa 1L)", 400, "ml")]},
    {"name": "Cordial de groselha", "method": "Groselha + água + açúcar",
     "size": 1000, "shelf": 21,
     "lines": [("Groselha", 500, "ml"), ("Água", 400, "ml"), ("Açúcar", 100, "g")]},
]


def _settings() -> None:
    db.set_setting_value("venue.name", VENUE["name"])
    db.set_setting_value("venue.iva_pct", str(VENUE["iva"]))
    try:
        import auth
        if not db.get_setting(auth.PIN_KEY):                 # demo door: 1234
            db.set_setting_value(auth.PIN_KEY, auth.hash_pin(VENUE["owner_pin"]))
        if not db.get_setting(auth.STAFF_PIN_KEY):           # staff door: 2468
            db.set_setting_value(auth.STAFF_PIN_KEY, auth.hash_pin(VENUE["staff_pin"]))
    except Exception as exc:                     # pins are a demo nicety
        print("pins skipped:", exc)


def build() -> None:
    stock = {i["name"]: i for i in db.get_stock_items()}
    for (name, abv, price, size, dim, pack, yield_frac) in STOCK:
        if name in stock:
            continue
        data = {"name": name, "abv": abv, "bottle_price_eur": price,
                "bottle_volume_ml": float(size), "dimension": dim}
        if yield_frac is not None:
            data["yield_frac"] = yield_frac
        if pack:
            data.update({"pack_size": float(pack[0]), "pack_price_eur": pack[1],
                         "pack_name": pack[2]})
        db.create_stock_item(data)
    stock = {i["name"]: i for i in db.get_stock_items()}

    # house batches first (cocktails pour from them)
    batches = {b["name"]: b for b in db.get_batches()}
    for spec in BATCHES:
        if spec["name"] in batches:
            continue
        b = db.create_batch({"name": spec["name"], "method": spec["method"],
                             "batch_size_ml": spec["size"],
                             "shelf_life_days": spec["shelf"]})
        for (nm, amount, unit) in spec["lines"]:
            db.add_batch_line(b["id"], {"name": nm, "amount_ml": amount, "unit": unit})
        batches = {x["name"]: x for x in db.get_batches()}

    existing = {s["name"] for s in db.get_specs()}
    made = 0

    def add_lines(spec_id, lines):
        for (nm, amount, unit) in lines:
            if nm.startswith("@"):                       # batch pour
                b = batches.get(nm[1:])
                if not b:
                    continue
                db.add_line(spec_id, {"batch_id": b["id"], "amount_ml": amount,
                                      "unit": unit})
            else:
                db.add_line(spec_id, {"name": nm, "amount_ml": amount, "unit": unit})

    for (name, cat, glass, method, garnish, price, lines) in COCKTAILS:
        if name in existing:
            continue
        sid = db.create_spec({"name": name, "category": cat, "glass": glass,
                              "method": method, "garnish": garnish,
                              "price_eur": price, "target_gp": 70})["id"]
        add_lines(sid, lines)
        made += 1
    for (name, cat, price, stock_name, amount, unit) in PRODUCTS:
        if name in existing:
            continue
        sid = db.create_spec({"name": name, "category": cat, "glass": "",
                              "method": "Servir", "price_eur": price,
                              "target_gp": 70})["id"]
        add_lines(sid, [(stock_name, amount, unit)])
        made += 1
    for (name, cat, price, lines) in KITCHEN:
        if name in existing:
            continue
        sid = db.create_spec({"name": name, "category": cat, "glass": "",
                              "method": "Cozinha", "price_eur": price,
                              "target_gp": 65})["id"]
        add_lines(sid, lines)
        made += 1
    print(f"seeded {made} specs (menu: {len(COCKTAILS) + len(PRODUCTS) + len(KITCHEN)})")


def _clean_slate() -> None:
    """A fresh DB is pre-seeded with the app's 5 template specs (and the brand
    stock they reference). A fictional venue must not inherit them."""
    try:
        seed_names = {s["name"] for s in db.SEED_SPECS}
    except AttributeError:
        return
    have = {s["name"] for s in db.get_specs()}
    if have and have <= seed_names:
        conn = db._conn()
        conn.execute("DELETE FROM spec_lines")
        conn.execute("DELETE FROM specs")
        conn.execute("DELETE FROM stock_items")
        conn.commit()
        conn.close()
        print(f"cleared {len(have)} template specs + their stock")


def _main() -> None:
    db.init_db()
    _clean_slate()
    _settings()
    build()
    if "--month" in sys.argv:
        print("month:", seed_month(BATCHES, rng_seed=20260909,
                                   supplier=lambda n: supplier_for(n)))


if __name__ == "__main__":
    _main()
