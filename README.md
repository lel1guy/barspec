# BarSpec

Cocktail spec manager for bartenders — store recipes, scale any drink to N
servings, see cost-per-drink and ABV, then **price the menu** and print it.

Built solo by lel1guy — an ex-bartender scratching his own itch. Python +
FastAPI + SQLite + vanilla JS.
No build step, no ORM — every query is visible in `db.py`, every € is computed
in `pricing.py` (pure functions, unit-tested).

## Docs

- **[User Guide](docs/USER_GUIDE.md)** — what the app does, how to use each
  screen, what the numbers mean. For bar staff and owners.
- **[Developer Guide](docs/DEV_GUIDE.md)** — architecture, design decisions
  and the *why* behind them; a teaching walkthrough for developers and
  learners.

## What it does

- **Specs**: name, glass, method, garnish. Add / edit / duplicate / delete.
- **Stock**: one row per real item — `Campari €19 / 700 ml`, coffee `€18 /
  1 kg`, limes `€3.60 / 12 pc`. Change a price **once**, and every spec using
  it updates — the ripple report tells you which specs moved and by how much,
  even through a house batch.
- **Spec lines** reference stock (name + amount per line; amounts are
  unit-aware: 30 ml, 2 dash, 9 g, 1 piece) OR a house batch. Unknown names
  create the stock item automatically; price/ABV/size live on the item only.
- **Batches**: house-made syrups & infusions costed as mini-recipes — total €
  derived from ingredients (stock-linked lines price live; water is €0),
  €/litre, expiry days, and you pour them into specs like any bottle.
- **Stock-take**: set a par per bottle, count the shelf (full + ¼/½/¾/open),
  get the order list (what to buy, cash asleep) and week-to-week trends.
- **Cost & ABV**: cost = amount × (price ÷ purchase size) across ml/g/pieces;
  drink cost = Σ lines; ABV = volume-weighted. Cost math lives in
  `pricing.py`, mirrored in JS only for live preview. Ice dilution NOT included.
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
pytest            # 98 tests: pricing math, migration replay, API smoke, stock-take, units engine, batches
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
- `004_batches.sql` — house-made batches: `batches` (name, method,
  batch_size_ml, made_date, shelf_life_days) + `batch_lines` (stock-linked
  rows derive through the engine, free-text rows carry a typed € cost);
  `spec_lines` gains nullable `batch_id` + a CHECK enforcing exactly one of
  bottle/batch per line. Spec pour = amount × (batch total ÷ size); two-level
  price ripple walks bottle → batches → specs.

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
| POST | `/api/specs/{id}/lines` | add line (`name` resolves/creates stock, or `batch_id` for a house batch; `unit` optional) |
| PUT | `/api/lines/{id}` | change amount (and unit) |
| DELETE | `/api/lines/{id}` | remove line |
| GET | `/api/stock` | items + usage count |
| POST | `/api/stock` | add item (`dimension`: volume\|weight\|count; 409 if duplicate) |
| PUT | `/api/stock/{id}` | edit item — **price ripple in response** (through batches too) |
| DELETE | `/api/stock/{id}` | delete (409 if any spec or batch uses it) |
| PATCH | `/api/stock/{id}/par` | set/clear par level |
| GET | `/api/batches` | batches + derived cost, €/ml, ABV, expiry |
| POST | `/api/batches` | create batch |
| GET/PUT/DELETE | `/api/batches/{id}` | detail / edit meta / delete (400 if used by specs) |
| POST | `/api/batches/{id}/lines` | add ingredient (stock name links live; free-text needs `cost_eur`) |
| DELETE | `/api/batches/lines/{id}` | remove batch line |
| GET | `/api/stock-takes/sheet` | count list: par'd items prefilled from last snapshot |
| POST | `/api/stock-takes` | save a count snapshot → returns the order-list review |
| GET | `/api/stock-takes/last` | latest snapshot's order review (to-order + cash asleep) |
| GET | `/api/stock-takes/trends` | movement between last two counts + dead-stock list |
| GET | `/api/menu` | priced menu view |

## Roadmap (not started)

- dilution % per spec (shaken vs stirred)
- categories + search (60+ specs breaks the flat list)
- Portuguese UI (PT-PT) — ml/EUR already native
- PWA offline read cache (service worker — needs HTTPS)
