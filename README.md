# BarSpec

Cocktail spec manager for bartenders — store recipes, scale any drink to N
servings, see cost-per-drink and ABV, then **price the menu** and print it.

Built for Vitor, by lel1guy. Python + FastAPI + SQLite + vanilla JS.
No build step, no ORM — every query is visible in `db.py`, every € is computed
in `pricing.py` (pure functions, unit-tested).

## What it does

- **Specs**: name, glass, method, garnish. Add / edit / duplicate / delete.
- **Stock** (the shared bottle list): every real bottle is one row —
  `Campari €19 / 700 ml`. Change a bottle price **once**, and every spec using
  it updates (ripple report tells you which specs moved and by how much).
- **Spec lines** reference stock bottles: name + ml per line. Unknown names
  create the bottle automatically; price/ABV/size live on the bottle only.
- **Cost & ABV**: cost/ml = bottle price / bottle size; drink cost = Σ lines;
  ABV = volume-weighted. Cost math lives in `pricing.py`, mirrored in JS only
  for live preview. Ice dilution NOT included.
- **Pricing** (the buying moment): target margin slider → suggested price
  (ceil to €0.50, so margin never dips below target) → save the sell price.
  Margin color-coded: green ≥ target, amber within 10 pts, red below.
- **Menu print**: price every spec (right in the menu view or per spec), print.
  The printed sheet shows names + prices only — costs stay off the paper.
  Currency symbols are omitted on purpose (menu psychology: price cues
  suppress spend).

## Run it (dev)

```bash
cd barspec
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

First run seeds 5 classic specs with real bottle prices + sensible PT prices
(Negroni €9, Margarita €10…) so costing AND pricing demo immediately.

## Tests

```bash
pytest            # 81 tests: pricing math, migration replay, API smoke, stock-take, units engine
```

The migration test builds a real v0 database and upgrades it — if that passes,
every future venue file upgrades safely. Money tests cover cent-rounding,
unpriced bottles, price-update propagation, FBE/par order math.

## Schema / migrations

Base schema + `migrations/*.sql`, tracked by `PRAGMA user_version`. On startup
`db.migrate()` applies pending files in order, each inside one transaction.
A fresh install runs the same path as an upgrade — self-checking.

- `001_normalize_stock.sql` — `ingredients` (per-spec duplicated prices) →
  `stock_items` + `spec_lines`. Idempotent, data-preserving.
- `002_stock_take.sql` — `par_level` on stock_items (NULL = not counted) +
  `stock_takes`/`stock_take_lines` dated snapshots (full bottles + open
  fraction 0/¼/½/¾/1). Count history, not throwaway UI state.
- `003_units.sql` — `dimension` on stock_items (volume|weight|count) +
  `unit` on spec_lines (default ml, legacy byte-identical). Canonical units:
  volume→ml, weight→g, count→piece. dash = 1 ml, barspoon = 5 ml. Allowed
  units + conversion factors live in `pricing.py` (single source of truth).

DB file: `barspec.db` (override with `BARSPEC_DB=/path` for tests).

## API

| Method | Path | What |
|--------|------|------|
| GET | `/api/specs` | list (+ cost, price, margin) |
| POST | `/api/specs` | create |
| GET | `/api/specs/{id}` | detail + joined lines + summary + suggested price |
| PUT | `/api/specs/{id}` | update (incl. `price_eur`, `target_gp`) |
| DELETE | `/api/specs/{id}` | delete (cascades lines) |
| POST | `/api/specs/{id}/duplicate` | copy spec + lines |
| POST | `/api/specs/{id}/lines` | add line (`name` resolves/creates stock) |
| PUT | `/api/lines/{id}` | change amount |
| DELETE | `/api/lines/{id}` | remove line |
| GET | `/api/stock` | bottles + usage count |
| POST | `/api/stock` | add bottle (409 if duplicate name) |
| PUT | `/api/stock/{id}` | edit bottle — **price ripple in response** |
| DELETE | `/api/stock/{id}` | delete (409 if any spec uses it) |
| PATCH | `/api/stock/{id}/par` | set/clear par level (bottles to keep on hand) |
| GET | `/api/stock-takes/sheet` | count list: par'd bottles prefilled from last snapshot |
| POST | `/api/stock-takes` | save a count snapshot → returns the order-list review |
| GET | `/api/stock-takes/last` | latest snapshot's order review (to-order + cash asleep) |
| GET | `/api/stock-takes/trends` | movement between last two counts + dead-stock list |
| GET | `/api/menu` | priced menu view |

## Roadmap (not started)

- units engine entry UI (S3): dimension picker on stock, unit picker on lines
  — engine + API land it already, S1 cl/oz/ml display toggle is live
- dilution % per spec (shaken vs stirred)
- categories + search (60+ specs breaks the flat list)
- syrups / infusions as batches (migration 004 — see vault dev plan)
- Portuguese UI (PT-PT) — ml/EUR already native
- PWA offline read cache (service worker — needs HTTPS)
