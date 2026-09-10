"""Shared demo-data engine.

One venue-agnostic month fabricator, used by every `ops/seed_*.py` demo
seeder (the Argo bundle, the fictional venue). Given a catalogue already in
the DB, it writes: suppliers, pars, six weekly counts, thirty days of sales,
house batches, dated losses and the purchase loop (one PO received, one open).

Deterministic: same rng seed → same month, every run.
"""
from __future__ import annotations

import datetime as dt
import random

import db

# Fictional wholesalers — deliberately generic so demo data never claims a
# real company's prices or assortment.
DEFAULT_SUPPLIER_RULES: list[tuple[tuple[str, ...], str]] = [
    (("gin", "vodka", "rum", "cachaça", "tequila", "bourbon", "whisky",
      "licor", "aperitivo", "bitter", "espumante"), "Distri-Bebidas"),
    (("vinho", "verde", "rosé", "porto", "barril", "lager"), "Adega Regional"),
    (("grão", "café"), "Grãos & Companhia"),
    (("pão", "queijo", "fiambre", "manteiga", "bife", "frango", "batata",
      "alface", "tomate", "alho", "ovo", "hortelã"), "Mercado Fresco"),
    (("água", "gelo"), "Gelo & Cia"),
    (("açúcar", "azeite", "cola", "laranjada", "néctar", "tónica",
      "ginger", "leite"), "Grossista Central"),
]
DEFAULT_REASONS = ("Spillage", "Waste", "Spoilage", "Correction")


def supplier_for(name: str, rules=None) -> str:
    for tokens, sup in (rules or DEFAULT_SUPPLIER_RULES):
        if any(tok.lower() in name.lower() for tok in tokens):
            return sup
    return "Grossista Central"


def seed_month(batch_specs: list[dict], *, rng_seed: int = 20260909,
               supplier: callable = supplier_for, reasons=DEFAULT_REASONS,
               skip_names=("Água filtrada", "Água da casa"),
               loss_threshold: float = 10.0, n_po: int = 2) -> dict:
    """Write the month. Returns a stats dict (safe to print)."""
    rng = random.Random(rng_seed)
    c = db._conn()
    items = db.get_stock_items()
    priced_specs = [s for s in db.get_specs() if s.get("price_eur")]
    if not items or not priced_specs:
        return {"error": "seed specs/stock first"}
    month_days = [(dt.date.today() - dt.timedelta(days=i)).isoformat()
                  for i in range(29, -1, -1)]      # oldest -> today

    for it in items:                                # suppliers (deterministic)
        if not (it.get("supplier") or "").strip():
            db.update_stock_item(it["id"], {"name": it["name"],
                                            "supplier": supplier(it["name"])})
    items = db.get_stock_items()
    # weight items can't be stock-counted (db rule) — manage volume + count only
    managed = [it for it in items
               if (it.get("bottle_price_eur") or 0) > 0
               and it.get("dimension") in ("volume", "count")
               and it["name"] not in skip_names]

    for it in managed:                              # pars: 1–6 shelf
        db.set_stock_par(it["id"], float(rng.randint(1, 6)))

    count_dates = [month_days[i] for i in (0, 5, 11, 17, 23, 26)]
    inv = {it["id"]: (it.get("par_level") or 1) * rng.uniform(2.2, 3.4)
           for it in managed}
    take_rows = 0
    for d in count_dates:
        tid = c.execute("INSERT INTO stock_takes (taken_at) VALUES (?)",
                        (d + " 11:00:00",)).lastrowid
        for it in managed:
            p = it.get("par_level") or 1
            inv[it["id"]] = max(0.0, inv[it["id"]] - rng.uniform(0.35, 1.1) * p)
            if rng.random() < 0.85:                 # a few skipped per count
                c.execute(
                    "INSERT INTO stock_take_lines "
                    "(take_id, stock_item_id, full_bottles, open_fraction) "
                    "VALUES (?,?,?,?)",
                    (tid, it["id"], int(inv[it["id"]]),
                     rng.choice((0.0, 0.25, 0.5, 0.75, 1.0))))
                take_rows += 1
    c.commit()                                      # release before sales writer

    ids = list({s["id"]: s for s in priced_specs})
    stars = rng.sample(ids, min(5, len(ids)))
    days_with_sales = total_lines = 0
    for d in month_days:
        lines = [{"spec_id": sid, "qty": rng.randint(4, 22)}
                 for sid in stars if rng.random() < 0.8]
        lines += [{"spec_id": sid, "qty": rng.randint(1, 9)}
                  for sid in rng.sample(ids, rng.randint(6, 14))]
        res = db.save_sales_day(d, lines)
        days_with_sales += 1
        total_lines += res.get("created", 0) + res.get("updated", 0)

    batches_made = 0
    existing_batches = {b["name"] for b in db.get_batches()}
    for spec in batch_specs:                        # dated house batches
        if spec["name"] in existing_batches:
            batches_made += 1                       # already built (e.g. in build())
            continue
        try:
            b = db.create_batch({"name": spec["name"], "method": spec["method"],
                                 "batch_size_ml": spec["size"],
                                 "shelf_life_days": spec["shelf"],
                                 "made_date": rng.choice(month_days[:24])})
        except ValueError:
            continue
        for (nm, amount, unit) in spec["lines"]:
            db.add_batch_line(b["id"], {"name": nm, "amount_ml": amount,
                                        "unit": unit})
        batches_made += 1

    losses = 0                                      # dated losses (this month)
    cur_month = dt.date.today().strftime("%Y-%m")
    loss_days = ([d for d in month_days if d.startswith(cur_month)]
                 or month_days[-8:])
    pool = [it for it in managed if (it.get("bottle_price_eur") or 0) > loss_threshold] or managed
    if pool:
        for _ in range(6):
            it = rng.choice(pool)
            size = it.get("bottle_volume_ml") or 700
            c.execute(
                "INSERT INTO stock_adjustments "
                "(stock_item_id, delta, reason, note, created_at) "
                "VALUES (?,?,?,?,?)",
                (it["id"], -round(rng.uniform(size * 0.25, size * 1.1)),
                 rng.choice(reasons), "demo month log",
                 rng.choice(loss_days) + f" {rng.randint(10, 23):02d}:00:00"))
            losses += 1
    c.commit()

    pos_open = pos_done = 0                         # purchase loop
    par_items = [it for it in db.get_stock_items()
                 if (it.get("par_level") or 0) > 0
                 and (it.get("bottle_price_eur") or 0) > 0
                 and it.get("dimension") in ("volume", "count")]
    for idx in range(n_po):
        if not par_items:
            break
        picks = rng.sample(par_items, min(3, len(par_items)))
        try:
            po = db.create_purchase_order(
                supplier(picks[0]["name"]),
                [{"stock_item_id": it["id"], "qty": float(rng.randint(1, 3))}
                 for it in picks])
        except ValueError:
            continue
        pos_open += 1
        if idx == 0:                                # receive the first only
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
