"""BarSpec demo bundle — The Argo (Vilamoura) signature menu.

Source: The_Argo_Menu_Cocktails_09_2026.pdf (public menu). Recipes are
INDICATIVE builds: the menu gives ingredients + serve size + ABV + price but
no amounts, so each spec's pours are solved so the computed ABV matches the
menu's declared ABV exactly (base spirit volume = linear solve). Purchase
prices are realistic PT retail approximations — swap them for the venue's
real invoices before a serious demo.

Usage:
    BARSPEC_DB=/tmp/argo-demo.db .venv/bin/python ops/seed_argo.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

# ---------------- stock catalogue ----------------
# key: (name, abv, price_eur, size_ml, kind vol|weight|count)
S = {
    # spirits (700 ml unless noted)
    "Premium Gin":        ("Premium Gin (Argo house)", 45.0, 38.0, 700, "volume"),
    "Bombay Grand Cru":   ("Bombay Sapphire Grand Cru", 47.0, 58.0, 700, "volume"),
    "Japanese gin":       ("Japanese gin (Roku)", 43.0, 31.0, 700, "volume"),
    "Nordés":             ("Nordés Gin", 40.0, 33.0, 700, "volume"),
    "Oxley":              ("Oxley Gin", 47.0, 34.0, 700, "volume"),
    "Westbourne":         ("Martin Miller's Westbourne", 45.2, 44.0, 700, "volume"),
    "Summerful":          ("Martin Miller's Summerful Gin", 45.0, 38.0, 700, "volume"),
    "Peach gin":          ("Premium peach gin", 40.0, 36.0, 700, "volume"),
    "Grey Goose":         ("Grey Goose Vodka", 40.0, 39.0, 700, "volume"),
    "GG Pear":            ("Grey Goose La Poire", 40.0, 44.0, 700, "volume"),
    "GG Lemon":           ("Grey Goose L'Orange Citron", 40.0, 44.0, 700, "volume"),
    "Vanilla vodka":      ("Vanilla vodka (Absolut Vanilia)", 35.0, 17.0, 700, "volume"),
    "Belvedere":          ("Belvedere Vodka", 40.0, 38.0, 700, "volume"),
    "Cachaça":            ("Leblon Cachaça", 40.0, 27.0, 700, "volume"),
    "Patrón Silver":      ("Patrón Silver Tequila", 40.0, 47.0, 700, "volume"),
    "Patrón Reposado":    ("Patrón Reposado Tequila", 40.0, 49.0, 700, "volume"),
    "Patrón XO Café":     ("Patrón XO Café", 35.0, 42.0, 700, "volume"),
    "Dewar's 12":         ("Dewar's 12 Whisky", 40.0, 29.0, 700, "volume"),
    "Jack Daniel's":      ("Jack Daniel's Old No.7", 40.0, 23.0, 700, "volume"),
    "Premium rum":        ("Premium rum (El Dorado 5)", 40.0, 32.0, 700, "volume"),
    "St-Germain":         ("St-Germain Elderflower", 20.0, 33.0, 700, "volume"),
    "Italicus":           ("Italicus Rosolio di Bergamotto", 20.0, 34.0, 700, "volume"),
    "Disaronno":          ("Disaronno Amaretto", 28.0, 21.0, 700, "volume"),
    "Tia Maria":          ("Tia Maria Coffee Liqueur", 20.0, 18.0, 700, "volume"),
    "Calvados":           ("Calvados Boulard VSOP", 40.0, 29.0, 700, "volume"),
    "Whisky liqueur":     ("Whisky liqueur (Drambuie)", 40.0, 28.0, 700, "volume"),
    "Lucano":             ("Amaro Lucano", 28.0, 22.0, 700, "volume"),
    "Mancino Sakura":     ("Mancino Sakura Vermouth", 17.0, 26.0, 750, "volume"),
    "Martini Floreale":   ("Martini Floreale (alc-free)", 0.0, 18.0, 750, "volume"),
    "Fino Sherry":        ("Fino Sherry (Tio Pepe)", 15.0, 14.0, 750, "volume"),
    "White Port 10":      ("10-year White Port", 19.5, 24.0, 750, "volume"),
    "Moscatel":           ("Moscatel de Setúbal", 17.5, 18.0, 750, "volume"),
    "Veuve Brut":         ("Veuve Clicquot Brut", 12.0, 62.0, 750, "volume"),
    "Cider vinegar":      ("Cider vinegar", 0.0, 4.0, 750, "volume"),
    "Umeshu":             ("Umeshu (Choya)", 15.0, 23.0, 720, "volume"),
    "Aperitif syrup":     ("Floral aperitif mix", 0.0, 14.0, 1000, "volume"),
    "Nordés 0.0":         ("Nordés Atlantic 0.0", 0.0, 24.0, 750, "volume"),
    "Sicilian lemon":     ("Sicilian lemon juice", 0.0, 8.0, 1000, "volume"),
    "Lime juice":         ("Lime juice", 0.0, 9.0, 1000, "volume"),
    "Lemon juice":        ("Lemon juice", 0.0, 7.0, 1000, "volume"),
    "Passion purée":      ("Passion fruit purée", 0.0, 13.0, 1000, "volume"),
    "Pineapple juice":    ("Pineapple juice", 0.0, 5.0, 1000, "volume"),
    "Melon purée":        ("Melon purée", 0.0, 11.0, 1000, "volume"),
    "Apple juice":        ("Green apple juice", 0.0, 6.0, 1000, "volume"),
    "Blueberry":          ("Blueberry purée", 0.0, 12.0, 1000, "volume"),
    "Apricot liqueur":    ("Apricot liqueur (Giffard)", 25.0, 20.0, 700, "volume"),
    "Coconut":            ("Coconut milk", 0.0, 4.0, 1000, "volume"),
    "Oat":                ("Oat milk", 0.0, 3.0, 1000, "volume"),
    "Yuzu":               ("Yuzu juice", 0.0, 14.0, 1000, "volume"),
    "Kalamansi":          ("Kalamansi juice", 0.0, 13.0, 1000, "volume"),
    "Sudachi":            ("Sudachi juice", 0.0, 15.0, 1000, "volume"),
    "Raspberry":          ("Raspberry purée", 0.0, 14.0, 1000, "volume"),
    "Cherry":             ("Cherry purée", 0.0, 13.0, 1000, "volume"),
    "Banana":             ("Banana purée", 0.0, 8.0, 1000, "volume"),
    "Corn":               ("Sweetcorn cordial", 0.0, 10.0, 1000, "volume"),
    "Lychee":             ("Lychee syrup", 0.0, 9.0, 1000, "volume"),
    "Gingerbread":        ("Gingerbread syrup", 0.0, 12.0, 1000, "volume"),
    "Cinnamon roll":      ("Cinnamon-roll syrup", 0.0, 12.0, 1000, "volume"),
    "Labdanum":           ("Labdanum tincture", 0.0, 16.0, 500, "volume"),
    "Chamomile":          ("Chamomile infusion", 0.0, 5.0, 1000, "volume"),
    "Rooibos tea":        ("Rooibos tea infusion", 0.0, 5.0, 1000, "volume"),
    "Earl Grey":          ("Earl Grey tea infusion", 0.0, 5.0, 1000, "volume"),
    "Coffee":             ("Espresso (double)", 0.0, 0.7, 1, "count"),
    "Vanilla pods":       ("Vanilla", 0.0, 12.0, 100, "weight"),
    "Miso":               ("White miso", 0.0, 9.0, 500, "weight"),
    "Mirin":              ("Mirin", 14.0, 6.0, 750, "volume"),
    "Rose water":         ("Rose water", 0.0, 8.0, 750, "volume"),
    "Vetiver":            ("Vetiver essence", 0.0, 20.0, 100, "volume"),
    "Saffron":            ("Saffron", 0.0, 120.0, 10, "weight"),
    "Ginger":             ("Ginger juice", 0.0, 8.0, 1000, "volume"),
    "Rose petals":        ("Rose petals", 0.0, 15.0, 100, "weight"),
    "Sea breeze":         ("Sea-breeze saline drops", 0.0, 9.0, 250, "volume"),
    "Umeboshi":           ("Umeboshi vinegar", 0.0, 13.0, 500, "volume"),
    "Plankton":           ("Marine plankton", 0.0, 28.0, 250, "volume"),
    "Inula":              ("Inula extract", 0.0, 22.0, 100, "volume"),
    "Sea fennel":         ("Sea fennel", 0.0, 14.0, 250, "volume"),
    "White chocolate":    ("White chocolate liqueur", 17.0, 15.0, 700, "volume"),
    "Caramel":            ("Caramel syrup", 0.0, 9.0, 1000, "volume"),
    "Sweet potato":       ("Sweet-potato syrup", 0.0, 10.0, 1000, "volume"),
    "Almond":             ("Almond orgeat", 0.0, 11.0, 1000, "volume"),
    "Vegetables":         ("Vegetable garden cordial", 0.0, 12.0, 1000, "volume"),
    "Peach zero mix":     ("Zero-proof peach mix", 0.0, 11.0, 1000, "volume"),
    "Rose fruit mix":     ("Rose fruit mix (zero)", 0.0, 10.0, 1000, "volume"),
    "Apple crumble":      ("Apple-crumble syrup", 0.0, 11.0, 1000, "volume"),
}

# Specs: (name, serve_cl, menu_abv, price, category, glass, method, garnish,
#         pours=[(stock_key, ml), ...]  base = first key with ml None)
SPECS = [
    ("THE ARGO", 10, 12.0, 25.0, "Saline",
     "Coupe", "Stirred, strained, served up", "Dill sprig + sea-fennel oil drop",
     [("Premium Gin", None), ("Lime juice", 10), ("Sea breeze", 4), ("Plankton", 2), ("Inula", 1), ("Sea fennel", 3)]),
    ("THE NECTAR OF SHIVA", 15, 10.0, 20.0, "Citrus",
     "Coupe", "Shaken, double-strained", "Melon fan + cherry",
     [("Bombay Grand Cru", None), ("St-Germain", 10), ("White Port 10", 8), ("Lime juice", 12),
      ("Melon purée", 18), ("Cherry", 10)]),
    ("THE IDOL", 10, 14.0, 20.0, "Tropical",
     "Coupe", "Shaken hard, double-strained", "Passion-fruit shell + coconut ash",
     [("Grey Goose", None), ("Italicus", 8), ("Passion purée", 14), ("Coconut", 12), ("Earl Grey", 8)]),
    ("THE RIEDEL", 10, 10.0, 20.0, "Citrus",
     "Coupe", "Shaken, strained over fresh ice shard", "Bay leaf + cucumber ribbon",
     [("Cachaça", None), ("Premium rum", 4), ("Fino Sherry", 4), ("Lucano", 3), ("Veuve Brut", 6),
      ("Lime juice", 8), ("Oat", 8)]),
    ("SOUL OF JAPAN", 10, 11.0, 20.0, "Umami",
     "Rocks", "Stirred, strained onto one big cube", "Umeboshi + sudachi wheel",
     [("GG Pear", None), ("Japanese gin", 5), ("Umeshu", 8), ("Sudachi", 10), ("Mirin", 4)]),
    ("DID YOU HAVE YOUR VEGGIES?", 10, 12.7, 19.0, "Vegetable",
     "Coupe", "Shaken with garden juice, double-strained", "Vegetable chip fan",
     [("Summerful", None), ("Vegetables", 22)]),
    ("HANSIK HERITAGE", 10, 12.0, 19.0, "Spicy",
     "Coupe", "Shaken, fine-strained", "Cinnamon-roll crumb rim",
     [("GG Lemon", None), ("Kalamansi", 10), ("Cinnamon roll", 8)]),
    ("THE ORIGIN", 10, 11.0, 18.0, "Creamy",
     "Coupe", "Shaken, double-strained", "Sweet-potato crisp + caramel",
     [("Vanilla vodka", None), ("Patrón XO Café", 8), ("White chocolate", 6), ("Caramel", 4), ("Sweet potato", 8)]),
    ("APICIUS", 10, 19.0, 17.0, "Full-bodied",
     "Coupe", "Stirred, strained up", "Banana-Brazil chip",
     [("Dewar's 12", None), ("Whisky liqueur", 3), ("Banana", 8), ("Pineapple juice", 6), ("Cider vinegar", 2)]),
    ("HUNGRY MONK LEGACY", 10, 15.0, 17.0, "Rich",
     "Coupe", "Shaken, strained over crushed speculoos rim", "Speculoos cookie",
     [("Dewar's 12", None), ("Disaronno", 5), ("Banana", 8), ("Caramel", 4)]),
    ("POPCORN & APPLES", 15, 9.0, 17.0, "Toasted",
     "Coupe", "Shaken with clarified popcorn, fine-strained", "Popcorn tuile + apple sliver",
     [("Jack Daniel's", None), ("Calvados", 6), ("Apple juice", 20), ("Rooibos tea", 15), ("Oat", 8), ("Caramel", 3)]),
    ("PICKLE-IN-THE-MIDDLE", 10, 12.0, 17.0, "Tangy",
     "Coupe", "Shaken, double-strained", "Rosemary sprig + red-pepper slice",
     [("Patrón Silver", None), ("Blueberry", 12), ("Moscatel", 8), ("Cider vinegar", 4)]),
    ("SILK & ZEST", 15, 6.0, 17.0, "Silky",
     "Coupe", "Shaken, fine-strained", "Gingerbread crumble rim",
     [("Patrón Reposado", None), ("Apricot liqueur", 8), ("Yuzu", 10), ("Oat", 16), ("Gingerbread", 6)]),
    ("BEYOND THE HORIZON", 12.5, 9.0, 16.0, "Tropical",
     "Coupe", "Shaken with pineapple, fine-strained", "Charred corn husk",
     [("Nordés", None), ("Fino Sherry", 4), ("Pineapple juice", 20), ("Corn", 10), ("Coconut", 10)]),
    ("COFFEE & ROSES", 10, 8.0, 16.0, "Floral",
     "Coupe", "Shaken, double-strained", "Rose petal + coffee bean",
     [("Grey Goose", None), ("Raspberry", 8), ("Tia Maria", 6), ("Oat", 10), ("Rose water", 2)]),
    ("CLARITY", 10, 12.0, 16.0, "Silky",
     "Coupe", "Clarified, shaken, fine-strained", "White-chocolate shard + almond",
     [("Oxley", None), ("Mancino Sakura", 8), ("Peach gin", 4), ("Almond", 6), ("White chocolate", 4)]),
    ("THE WHISPER", 10, 12.0, 15.0, "Delicate",
     "Coupe", "Stirred, strained up", "Bamboo leaf + lychee",
     [("Belvedere", None), ("Lychee", 8), ("Earl Grey", 8), ("Cider vinegar", 2)]),
    ("COAST TO COAST", 10, 12.0, 15.0, "Marine",
     "Coupe", "Shaken, double-strained", "Coriander leaf + lime zest",
     [("Westbourne", None), ("Lime juice", 8), ("Cider vinegar", 4), ("Sea breeze", 3)]),
    ("QUIRON", 13.5, 0.0, 14.0, "Zero",
     "Highball", "Built over ice, topped, stirred once", "Mint sprig + chamomile flower",
     [("Nordés 0.0", 30), ("Martini Floreale", 15), ("Aperitif syrup", 10), ("Chamomile", 35)]),
    ("FLORA", 18.5, 0.0, 14.0, "Zero",
     "Highball", "Shaken, strained over pebble ice", "Saffron thread + melon ball",
     [("Nordés 0.0", 40), ("Sicilian lemon", 15), ("Ginger", 8), ("Pineapple juice", 30), ("Melon purée", 20)]),
    ("MEMORIES", 10, 0.0, 14.0, "Zero",
     "Coupe", "Shaken, fine-strained", "Apple fan + crumble dust",
     [("Apple crumble", 25), ("Apple juice", 40), ("Lime juice", 10)]),
    ("CONNECTIONS", 13.5, 0.0, 14.0, "Zero",
     "Highball", "Shaken, strained over ice", "Rose petal + cherry",
     [("Rose fruit mix", 25), ("Vetiver", 1), ("Cherry", 15), ("Lemon juice", 12)]),
]

# zero-proof 'filtered water' filler keeps volumes honest when recipes are
# shorter than the declared serve (never affects ABV/cost maths)
WATER_KEY = "Filtered water"
def build() -> None:
    stock = {i["name"]: i for i in db.get_stock_items()}
    # filtered water filler (never stocked in a real venue bar, cost 0)
    if WATER_KEY not in stock:
        db.create_stock_item({"name": WATER_KEY, "abv": 0.0, "bottle_price_eur": 0.0,
                              "dimension": "volume", "bottle_volume_ml": 1000.0})
        stock = {i["name"]: i for i in db.get_stock_items()}
    for key, (name, abv, price, size, _kind) in S.items():
        if name not in stock:
            db.create_stock_item({"name": name, "abv": abv, "bottle_price_eur": price,
                                  "dimension": "volume", "bottle_volume_ml": size})
    stock = {i["name"]: i for i in db.get_stock_items()}

    existing_specs = {s["name"] for s in db.get_specs()}
    created, errs = 0, []
    for (name, cl, menu_abv, price, cat, glass, method, garnish, pours) in SPECS:
        if name in existing_specs:
            continue
        serve_ml = round(cl * 10)
        fixed = [(k, v) for (k, v) in pours if v is not None]
        base_key = next((k for (k, v) in pours if v is None), None)
        E = menu_abv * serve_ml
        mod_units = sum(S[k][1] * v for (k, v) in fixed if S[k][1] > 0)
        base_ml = 0.0
        if base_key is not None and E > mod_units:
            base_ml = (E - mod_units) / S[base_key][1]
        alc_vol = base_ml + sum(v for (k, v) in fixed if S[k][1] > 0)
        non_alc = sum(v for (k, v) in fixed if S[k][1] == 0)
        fill = serve_ml - alc_vol - non_alc
        if base_key is not None and (base_ml < 2 or fill < 0):
            errs.append((name, round(base_ml, 1), round(fill, 1)))
            continue
        spec_id = db.create_spec({"name": name, "category": cat, "glass": glass,
                                  "method": method, "garnish": garnish,
                                  "price_eur": price, "target_gp": 70})["id"]
        lines = ([(base_key, base_ml)] if base_key is not None and base_ml > 0 else []) + fixed
        if fill > 0.5:
            lines.append((WATER_KEY, round(fill, 1)))
        for (k, v) in lines:
            if round(v, 1) <= 0:
                continue
            db.add_line(spec_id, {"name": S[k][0] if k != WATER_KEY else WATER_KEY,
                                  "amount_ml": round(v, 1)})
        created += 1
    if errs:
        print("NEEDS TUNING (base/fill):")
        for e in errs:
            print("  ", e)
    print(f"seeded {created} Argo specs (menu: {len(SPECS)})")


# ---------------- full-month fabricator (demo: 30 days of real use) --------
import datetime as _dt
import random as _rnd

# Real PT supply mapping (venue-facing): brand houses where the label is
# unambiguous, wholesale (Makro) as the honest catch-all independents use.
_SUPPLIER_RULES = [
    # brand houses only where the owner is unambiguous; everything boutique
    # or uncertain falls through to the wholesale catch-all (Makro)
    (("Bombay", "Grey Goose", "Patrón", "Leblon", "Dewar",
      "Martini Floreale"), "Bacardi-Martini Portugal"),
    (("Absolut", "Italicus", "Mancino Sakura"), "Pernod Ricard Portugal"),
    (("Veuve Clicquot", "Belvedere"), "LVMH Moët Hennessy Portugal"),
    (("Jack Daniel", "Woodford"), "Brown-Forman Portugal"),
    (("Roku", "Japanese gin"), "Beam Suntory Portugal"),
    (("Sagres",), "Central de Cervejas (Heineken)"),
    (("Coca-Cola", "Fanta", "Sprite", "Schweppes"), "CCEP Portugal"),
    (("Compal", "Sumol"), "Sumol+Compal"),
    (("Delta",), "Delta Cafés"),
    (("Super Bock", "Luso", "Vitalis"), "Super Bock Group"),
]
_REASONS = ("Spillage", "Waste", "Spoilage", "Correction")


def _supplier_for(name: str) -> str:
    for tokens, sup in _SUPPLIER_RULES:
        if any(tok.lower() in name.lower() for tok in tokens):
            return sup
    return "Makro Cash & Carry"   # honest catch-all for the boutique shelf


def seed_month(force: bool = True) -> dict:
    """A plausible month behind the menu: weekly counts, daily sales, house
    batches, dated losses, suppliers + pars. Deterministic (seeded rng)."""
    rng = _rnd.Random(20260909)
    c = db._conn()
    items = db.get_stock_items()
    priced_specs = [s for s in db.get_specs() if s.get("price_eur")]
    if not items or not priced_specs:
        return {"error": "seed specs/stock first"}
    month_days = [(_dt.date.today() - _dt.timedelta(days=i)).isoformat()
                  for i in range(29, -1, -1)]     # oldest -> today
    # suppliers (deterministic) — already-signed rows untouched
    for it in items:
        if not (it.get("supplier") or "").strip():
            db.update_stock_item(it["id"],
                                 {"name": it["name"], "supplier": _supplier_for(it["name"])})
    items = db.get_stock_items()
    # weight items (coffee/kg) can't be stock-counted yet (db rule) — manage
    # the volume + count shelf only
    managed = [it for it in items
               if it["bottle_price_eur"] > 0 and it["name"] != "Filtered water"
               and it.get("dimension") in ("volume", "count")]
    # pars: buying-manager intuition on a 1-6 shelf
    for it in managed:
        db.set_stock_par(it["id"], float(rng.randint(1, 6)))
    # counts: 6 snapshots over the month (last one 4 days ago)
    count_dates = [(month_days[i]) for i in (0, 5, 11, 17, 23, 26)]
    inv = {it["id"]: (it.get("par_level") or 1) * rng.uniform(2.2, 3.4)
           for it in managed}
    take_rows = 0
    for d in count_dates:
        cur = c.execute("INSERT INTO stock_takes (taken_at) VALUES (?)",
                        (d + " 11:00:00",))
        tid = cur.lastrowid
        for it in managed:
            p = it.get("par_level") or 1
            inv[it["id"]] = max(0.0, inv[it["id"]] - rng.uniform(0.35, 1.1) * p)
            full = int(inv[it["id"]])
            if rng.random() < 0.85:      # a few items skipped on any count
                q = rng.choice((0.0, 0.25, 0.5, 0.75, 1.0))   # UI fractions only
                c.execute(
                    "INSERT INTO stock_take_lines (take_id, stock_item_id, full_bottles, open_fraction) "
                    "VALUES (?,?,?,?)", (tid, it["id"], full, q))
                take_rows += 1
    c.commit()     # release the write txn before the sales writer kicks in
    # sales: every day, several specs; star specs sell big
    by_id = {s["id"]: s for s in priced_specs}
    ids = list(by_id)
    stars = rng.sample(ids, min(5, len(ids)))
    days_with_sales = 0
    total_lines = 0
    for d in month_days:
        lines = []
        for sid in stars:
            if rng.random() < 0.8:
                lines.append({"spec_id": sid, "qty": rng.randint(4, 22)})
        for sid in rng.sample(ids, rng.randint(6, 14)):
            lines.append({"spec_id": sid, "qty": rng.randint(1, 9)})
        res = db.save_sales_day(d, lines)
        days_with_sales += 1
        total_lines += res.get("created", 0) + res.get("updated", 0)
    # house batches (dated, referenced nowhere = extra realism for Batches tab)
    batch_spec = [
        ("Salted citrus cordial", "Shake 30 s, rest 24 h, fine-strain",
         1000, 10,
         [("Sicilian lemon", 300), ("Lime juice", 300), ("Sea breeze", 40),
          ("Filtered water", 360)]),
        ("House vanilla caramel", "Simmer 20 min, cool, bottle", 900, 21,
         [("Caramel", 700), ("Filtered water", 200)]),
        ("Earl Grey infusion", "Cold-steep 6 h", 1000, 4,
         [("Earl Grey", 1000)]),
    ]
    batches_made = 0
    for (name, method, size, shelf, line_specs) in batch_spec:
        made = rng.choice(month_days[:24])
        try:
            b = db.create_batch({"name": name, "method": method,
                                 "batch_size_ml": size,
                                 "shelf_life_days": shelf, "made_date": made})
        except ValueError:
            continue
        for (k, ml) in line_specs:
            nm = k if k == WATER_KEY else S[k][0]
            db.add_batch_line(b["id"], {"name": nm, "amount_ml": ml, "unit": "ml"})
        batches_made += 1
    # dated losses (loss log + dashboard €) — current calendar month, bottle-scale
    losses = 0
    cur_month = _dt.date.today().strftime("%Y-%m")
    month_loss_days = [d for d in month_days if d.startswith(cur_month)] or month_days[-8:]
    pricey = [it for it in managed if (it.get("bottle_price_eur") or 0) > 10]
    pool = pricey or managed
    for _ in range(6):
        it = rng.choice(pool)
        size = it.get("bottle_volume_ml") or 700
        delta = -round(rng.uniform(size * 0.25, size * 1.1), 0)
        d = rng.choice(month_loss_days) + f" {rng.randint(10, 23):02d}:00:00"
        c.execute("INSERT INTO stock_adjustments (stock_item_id, delta, reason, note, created_at) "
                  "VALUES (?,?,?,?,?)",
                  (it["id"], delta, rng.choice(_REASONS), "demo month log", d))
        losses += 1
    c.commit()     # release before the PO writer opens its own connection
    # purchase loop: 2 open POs from below-par items + 1 fully received (history)
    pos_open = pos_done = 0
    par_items = [it for it in db.get_stock_items()
                 if (it.get("par_level") or 0) > 0
                 and (it.get("bottle_price_eur") or 0) > 0
                 and it.get("dimension") in ("volume", "count")]
    for idx in range(2):
        picks = rng.sample(par_items, min(3, len(par_items)))
        supplier = _supplier_for(picks[0]["name"])
        try:
            po = db.create_purchase_order(
                supplier, [{"stock_item_id": it["id"], "qty": float(rng.randint(1, 3))}
                           for it in picks])
            pos_open += 1
        except ValueError:
            continue
        if idx == 0:      # receive the first, keep the second open
            try:
                db.receive_purchase_order(po["id"])
                pos_done += 1
                pos_open -= 1
            except ValueError:
                pass
    c.commit()
    c.close()
    return {"count_dates": len(count_dates), "take_rows": take_rows,
            "days_with_sales": days_with_sales, "sales_lines": total_lines,
            "batches": batches_made, "losses": losses, "managed": len(managed),
            "pos_open": pos_open, "pos_received": pos_done}




# ---------------- pub / wine-bar / café shelf (014 breadth) ----------------
# stock: (name, abv, price_or_pack, size_units_canonical, dim, pack=(n, price, name))
_SHELF_STOCK = [
    ("Super Bock keg 30L", 5.1, 84.0, 30000, "volume", None),
    ("Super Bock can 33cl", 5.1, 15.36, 1, "count", (24, 15.36, "case")),
    ("Sagres keg 30L", 5.0, 79.0, 30000, "volume", None),
    ("Sagres can 33cl", 5.0, 14.16, 1, "count", (24, 14.16, "case")),
    ("Vinho Verde Loureiro 75cl", 11.0, 6.8, 750, "volume", None),
    ("Vinho Branco Regional 75cl", 12.5, 7.4, 750, "volume", None),
    ("Vinho Tinto Regional 75cl", 13.0, 8.6, 750, "volume", None),
    ("Coca-Cola can 33cl", 0.0, 14.16, 1, "count", (24, 14.16, "case")),
    ("Fanta can 33cl", 0.0, 14.16, 1, "count", (24, 14.16, "case")),
    ("Sumol ananás can 33cl", 0.0, 15.6, 1, "count", (24, 15.6, "case")),
    ("Schweppes tónica 20cl", 0.0, 13.2, 1, "count", (24, 13.2, "case")),
    ("Água Luso 50cl", 0.0, 2.1, 1, "count", (6, 2.1, "pack")),
    ("Luso gasosa 33cl", 0.0, 1.98, 1, "count", (6, 1.98, "pack")),
    ("Delta Plano café 1kg", 0.0, 13.9, 1000, "weight", None),
    ("Leite meio-gordo 1L", 0.0, 1.05, 1000, "volume", None),
]
# straight-serve / simple products: (name, stock_name, amount, unit, price, cat)
_SHELF_PROD = [
    ("Super Bock Imperial", "Super Bock keg 30L", 200, "ml", 2.0, "Cerveja"),
    ("Super Bock Caneca", "Super Bock keg 30L", 500, "ml", 4.2, "Cerveja"),
    ("Super Bock can", "Super Bock can 33cl", 1, "piece", 2.6, "Cerveja"),
    ("Sagres Imperial", "Sagres keg 30L", 200, "ml", 1.9, "Cerveja"),
    ("Sagres can", "Sagres can 33cl", 1, "piece", 2.5, "Cerveja"),
    ("Vinho Verde copo 15cl", "Vinho Verde Loureiro 75cl", 150, "ml", 3.8, "Vinho"),
    ("Vinho Verde garrafa", "Vinho Verde Loureiro 75cl", 750, "ml", 18.0, "Vinho"),
    ("Branco copo 15cl", "Vinho Branco Regional 75cl", 150, "ml", 4.0, "Vinho"),
    ("Branco garrafa", "Vinho Branco Regional 75cl", 750, "ml", 21.0, "Vinho"),
    ("Tinto copo 15cl", "Vinho Tinto Regional 75cl", 150, "ml", 4.2, "Vinho"),
    ("Tinto garrafa", "Vinho Tinto Regional 75cl", 750, "ml", 24.0, "Vinho"),
    ("Coca-Cola can", "Coca-Cola can 33cl", 1, "piece", 2.2, "Bebidas"),
    ("Fanta can", "Fanta can 33cl", 1, "piece", 2.2, "Bebidas"),
    ("Sumol can", "Sumol ananás can 33cl", 1, "piece", 2.2, "Bebidas"),
    ("Tónica", "Schweppes tónica 20cl", 1, "piece", 2.4, "Bebidas"),
    ("Água Luso", "Água Luso 50cl", 1, "piece", 1.5, "Água"),
    ("Luso gasosa", "Luso gasosa 33cl", 1, "piece", 1.5, "Água"),
]
# recipe-ish café drinks: (name, cat, price, [(stock, amount, unit)])
_SHELF_CAFE = [
    ("Café expresso", "Café", 1.2, [("Delta Plano café 1kg", 7, "g")]),
    ("Café duplo", "Café", 1.6, [("Delta Plano café 1kg", 14, "g")]),
    ("Meia de leite", "Café", 1.7, [("Delta Plano café 1kg", 7, "g"),
                                   ("Leite meio-gordo 1L", 120, "ml")]),
    ("Galão", "Café", 2.2, [("Delta Plano café 1kg", 14, "g"),
                            ("Leite meio-gordo 1L", 200, "ml")]),
]


def seed_shelf() -> dict:
    """Pub / wine / café shelf: pack-bought stock + straight-serve products."""
    stock = {i["name"]: i for i in db.get_stock_items()}
    specs = {s["name"] for s in db.get_specs()}
    made = {"stock": 0, "products": 0}
    for (name, abv, price, size, dim, pack) in _SHELF_STOCK:
        if name in stock:
            continue
        payload = {"name": name, "abv": abv, "bottle_volume_ml": size,
                   "dimension": dim, "bottle_price_eur": 0.0}
        if pack:
            payload["pack_size"], payload["pack_price_eur"] = pack[0], pack[1]
            payload["pack_name"] = pack[2]
        else:
            payload["bottle_price_eur"] = price
        db.create_stock_item(payload)
        made["stock"] += 1
    stock = {i["name"]: i for i in db.get_stock_items()}
    for (name, stock_name, amount, unit, price, cat) in _SHELF_PROD:
        if name in specs:
            continue
        sp = db.create_spec({"name": name, "category": cat, "price_eur": price,
                             "method": "Straight serve", "glass": ""})["id"]
        db.add_line(sp, {"name": stock_name, "amount_ml": amount, "unit": unit})
        specs.add(name)
        made["products"] += 1
    for (name, cat, price, lines) in _SHELF_CAFE:
        if name in specs:
            continue
        sp = db.create_spec({"name": name, "category": cat, "price_eur": price,
                             "method": "Espresso machine", "glass": ""})["id"]
        for (sn, amt, unit) in lines:
            db.add_line(sp, {"name": sn, "amount_ml": amt, "unit": unit})
        specs.add(name)
        made["products"] += 1
    return made


def _main():
    db.init_db()
    build()
    if "--month" in sys.argv:
        print("shelf:", seed_shelf())
        print("month:", seed_month())

if __name__ == "__main__":
    _main()
