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


def _cost_per_ml(bottle_price_eur: float, bottle_volume_ml: float) -> float:
    """EUR per ml of a bottle. Volume <= 0 means 'no price' -> 0 cost."""
    if bottle_volume_ml <= 0 or bottle_price_eur <= 0:
        return 0.0
    return bottle_price_eur / bottle_volume_ml


def line_cost(line: dict) -> float:
    """Cost of one line (one ingredient amount) in EUR, unrounded."""
    return line["amount_ml"] * _cost_per_ml(
        line.get("bottle_price_eur", 0.0), line.get("bottle_volume_ml", 0.0)
    )


def drink_cost(lines: list[dict]) -> float:
    """Total cost of ONE serving across lines, EUR (unrounded)."""
    return sum(line_cost(l) for l in lines)


def drink_volume(lines: list[dict]) -> float:
    return sum(l["amount_ml"] for l in lines)


def drink_abv(lines: list[dict]) -> float:
    """Volume-weighted ABV % across lines. Ignores ice dilution (documented)."""
    total = drink_volume(lines)
    if total <= 0:
        return 0.0
    abv_vol = sum(l["amount_ml"] * (l.get("abv", 0.0) / 100.0) for l in lines)
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
