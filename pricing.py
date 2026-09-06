"""BarSpec — pure cost/ABV/pricing math.

Single source of truth for the money. No I/O, no state: every function takes
plain dicts/lists and returns numbers. The JS frontend mirrors these formulas
for live preview only — the server is the authority (see math.js).

Conventions:
- money in EUR, floats kept in and out (visible, simple — rounding at the edge)
- rounding to cents via round(x, 2) on OUTPUT only
- suggested price rounds UP to the nearest 0.50 so margin never dips below target
"""


import math


# ---------- units engine (S2): dimensions + canonical conversion ----------

# A unit belongs to exactly one dimension. Canonical unit per dimension:
#   volume -> ml, weight -> g, count -> piece.
# UNIT_CANONICAL is the factor from the unit to its dimension's canonical unit.
# dash = 1 ml and barspoon = 5 ml are fixed volume sub-units (locked 2026-09-06)
# so bitters cost via the bottle instead of being ignored.
UNIT_DIMENSION = {
    "ml": "volume", "cl": "volume", "l": "volume", "oz": "volume",
    "dash": "volume", "barspoon": "volume",
    "g": "weight", "kg": "weight",
    "piece": "count", "each": "count",
}
UNIT_CANONICAL = {
    "ml": 1.0, "cl": 10.0, "l": 1000.0, "oz": 29.5735,
    "dash": 1.0, "barspoon": 5.0,
    "g": 1.0, "kg": 1000.0,
    "piece": 1.0, "each": 1.0,
}
CANONICAL_PER_DIMENSION = {"volume": "ml", "weight": "g", "count": "piece"}


def valid_unit(unit: str) -> bool:
    return unit in UNIT_CANONICAL


def canonical_amount(amount: float, unit: str) -> float:
    """Convert an amount expressed in `unit` to its dimension's canonical unit."""
    return amount * UNIT_CANONICAL.get(unit, 1.0)


def _cost_per_ml(bottle_price_eur: float, bottle_volume_ml: float) -> float:
    """EUR per ml of a bottle. Volume <= 0 means 'no price' -> 0 cost."""
    if bottle_volume_ml <= 0 or bottle_price_eur <= 0:
        return 0.0
    return bottle_price_eur / bottle_volume_ml


# ---------- batches (004): house-made syrups / infusions ----------

def batch_cost(lines: list[dict]) -> float:
    """Total ingredient cost of a batch across its lines, EUR (unrounded).
    Stock-linked lines derive through the units engine (sugar by kg, bitters
    by ml); free-text lines carry a typed cost_eur for their exact amount.
    Never typed as a total — the house-syrup cost hole fix."""
    total = 0.0
    for bl in lines:
        if bl.get("stock_item_id") is not None:
            total += line_cost(bl)
        else:
            total += float(bl.get("cost_eur", 0.0) or 0.0)
    return total


def batch_cost_per_ml(cost: float, batch_size_ml: float) -> float:
    if batch_size_ml <= 0:
        return 0.0
    return cost / batch_size_ml


def serve_batch_cost(amount: float, unit: str,
                     batch_cost_total: float, batch_size_ml: float) -> float:
    """Cost of pouring `amount` (a volume unit) of a finished batch into one
    serve: amount->canonical ml x (batch total ÷ batch size)."""
    if batch_size_ml <= 0:
        return 0.0
    ml = float(amount or 0.0) * UNIT_CANONICAL.get(unit, 1.0)
    return ml * batch_cost_total / batch_size_ml


def _line_volume_ml(line: dict) -> float:
    """Canonical ml of a volume-dimension line. Legacy rows (no unit key /
    unit 'ml', volume dimension) return the stored amount unchanged, so
    pre-engine volumes and ABV are byte-identical. Weight/count lines carry no
    drink volume: 9 g of coffee is not 9 ml of liquid."""
    unit = line.get("unit") or "ml"
    if UNIT_DIMENSION.get(unit, "volume") != "volume":
        return 0.0
    return float(line.get("amount_ml", 0.0) or 0.0) * UNIT_CANONICAL.get(unit, 1.0)


def line_cost(line: dict) -> float:
    """Cost of one line (one ingredient amount) in EUR, unrounded.

    The line's stock item is the price truth: bottle_price_eur = € per
    purchase, bottle_volume_ml = canonical amount per purchase (ml for
    volume, g for weight, pieces for count — dimension says which). The line's
    own amount_ml holds amount-in-unit; unit converts to canonical.

    Legacy ml/volume lines take the original formula path untouched. Spec
    lines that pour a house syrup carry serve_batch and cost amount ×
    (batch total ÷ size); batch ingredient rows keep their own batch_id
    (parent) and take the normal engine path.
    """
    if line.get("serve_batch"):
        return serve_batch_cost(
            line.get("amount_ml", 0.0), line.get("unit") or "ml",
            line.get("batch_cost_total", 0.0), line.get("batch_size_ml", 0.0))
    unit = str(line.get("unit") or "ml")
    dimension = UNIT_DIMENSION.get(unit, "volume")
    amount = float(line.get("amount_ml", 0.0) or 0.0)
    price = float(line.get("bottle_price_eur", 0.0) or 0.0)
    per = float(line.get("bottle_volume_ml", 0.0) or 0.0)
    if per <= 0 or price <= 0:
        return 0.0
    if dimension == "volume" and unit == "ml":
        return amount * _cost_per_ml(price, per)
    canonical = amount * UNIT_CANONICAL.get(unit, 1.0)
    return canonical * price / per


def drink_cost(lines: list[dict]) -> float:
    """Total cost of ONE serving across lines, EUR (unrounded)."""
    return sum(line_cost(l) for l in lines)


def drink_volume(lines: list[dict]) -> float:
    """Total canonical ml of volume-dimension lines (see _line_volume_ml)."""
    return sum(_line_volume_ml(l) for l in lines)


def drink_abv(lines: list[dict]) -> float:
    """Volume-weighted ABV % across lines. Ignores ice dilution (documented)."""
    total = drink_volume(lines)
    if total <= 0:
        return 0.0
    abv_vol = sum(
        _line_volume_ml(l) * (l.get("abv", 0.0) / 100.0) for l in lines
    )
    return abv_vol / total * 100.0


def summarize(lines: list[dict]) -> dict:
    """One-serving summary dict matching the old API shape."""
    cost = drink_cost(lines)
    total = drink_volume(lines)
    return {
        "total_ml": round(total, 1),
        "cost_eur": round(cost, 3),
        "abv": round(drink_abv(lines), 1),
    }


def row_pcts(lines: list[dict]) -> list[float]:
    """Each line's share of total drink cost, 0-100. Guarded vs zero cost."""
    total = drink_cost(lines)
    if total <= 0:
        return [0.0 for _ in lines]
    return [line_cost(l) / total * 100.0 for l in lines]


# ---------- pricing / menu engineering ----------

def suggested_price(cost_eur: float, target_gp_pct: float) -> float:
    """Price needed to hit target gross-profit %: price = cost / (1 - gp).

    Rounds UP to nearest 0.50 (menu-friendly: 6.5 / 7.0 / 12.5). If cost is 0
    (unpriced bottle) returns 0.0 so the UI can show 'set a bottle price'.
    """
    if cost_eur <= 0:
        return 0.0
    gp = max(0.0, min(target_gp_pct, 100.0)) / 100.0
    if gp >= 1.0:
        gp = 0.99
    raw = cost_eur / (1.0 - gp)
    # ceil to nearest 0.50 so the rounded price never dips below target margin
    return round(math.ceil(raw * 2) / 2, 2) if raw > 0 else 0.0


def margin_pct(price_eur: float, cost_eur: float) -> float:
    """Gross-profit % for a given price/cost. price<=0 -> 0 (not priced)."""
    if price_eur <= 0:
        return 0.0
    if cost_eur <= 0:
        return 100.0
    return (price_eur - cost_eur) / price_eur * 100.0


def margin_band(margin: float, target_gp_pct: float) -> str:
    """'good' | 'ok' | 'low' | 'unpriced' — drives the color coding."""
    if margin <= 0:
        return "unpriced"
    if margin >= target_gp_pct:
        return "good"
    if margin >= target_gp_pct - 10:
        return "ok"
    return "low"


def menu_round_up(x: float) -> float:
    """Nearest 0.50 above x (helper, same rule as suggested_price)."""
    return round(math.ceil(x * 2) / 2, 2)


# ---------- stock-take math (par levels, order list, cash asleep) ----------

# Visual 4-step estimate of an open bottle. All values exact in binary float.
OPEN_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


def fbe(full_bottles, open_fraction=0.0) -> float:
    """Full-bottle equivalents: full bottles + open-bottle fraction.

    The count unit of a stock-take: '2 full + one at half' = 2.5 FBE.
    """
    return float(full_bottles) + float(open_fraction)


def stock_ml(fbe_value: float, bottle_volume_ml: float) -> float:
    """Volume a count represents: FBE x bottle size (700 ml etc)."""
    return fbe_value * bottle_volume_ml


def order_shortfall(par_level: float, fbe_value: float) -> int:
    """Whole bottles to order to reach par: ceil(par - fbe), floored at 0.

    Par is a target in bottles; you order whole bottles. Ceil so a half-bottle
    gap ('par 3, have 2.5') still orders 1. Float noise guard: an exact par
    (par 2.0 vs fbe 2.0) must order 0, never 1.
    """
    gap = float(par_level) - float(fbe_value)
    if gap <= 1e-9:
        return 0
    return int(math.ceil(gap - 1e-9))


def excess_fbe(par_level: float, fbe_value: float) -> float:
    """FBE above par (the 'cash asleep' count), 0 when at or below par."""
    return max(0.0, float(fbe_value) - float(par_level))


def cash_asleep_eur(fbe_value: float, par_level: float, bottle_price_eur: float) -> float:
    """Euro of stock sitting above par: excess FBE x bottle price.

    Over-par stock is cash tied up in bottles instead of the bank. Raw value
    (round to cents on output, per module convention).
    """
    return excess_fbe(par_level, fbe_value) * bottle_price_eur
