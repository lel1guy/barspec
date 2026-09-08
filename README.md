# BarSpec

Cocktail spec manager for bartenders — store recipes, scale any drink to N
servings, see cost-per-drink and ABV, then **price the menu** and print it.

Built by Vitor Vareiro. Python +
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
- **Categories**: free-form menu sections on specs — filter chips over the
  spec list and grouped sections on the printable menu (60+ specs stay
  findable).
- **Dilution**: optional ice-melt % per spec (shake ≈ 20–25, stir ≈ 10–15).
  Served volume and served ABV tell the truth about what reaches the glass;
  cost stays the measured pour — water is free.
- **EN / PT-PT**: one-click language toggle (top bar, remembered per browser).
  All navigation, forms, buttons, hints and menus translate; numbers and €
  never do.
- **Export & share**: the whole spec book + stock to .xlsx or .csv (owner /
  accountant files, costs included), plus a menu QR — point a phone at it and
  the menu opens (`?view=menu` deep link).
- **Training cards**: print a spec-card deck (⤢ Cards) — one recipe per card,
  amounts + method + garnish, grouped by category, honoring the current
  filter/search. **Costs never appear** — these cards live on the floor.
- **Kitchen (K1)**: batches declare portions — a mayo batch that makes 20
  shows **€/portion** on the prep sheet (volume math still works). The loss
  log (+ Log loss) turns spills/waste/spoilage into visible lines with a
  reason — never a mystery at the next count.
- **Section P&L**: under the menu, margin % per category (green ≥60 /
  amber ≥40 / red below) plus **dead stock** — the purchase value of items
  no recipe touches, cash sitting on the shelf.
- **Allergens & diet (K3)**: every spec carries EU-14 allergen codes and
  V/VE/GF tags — picked as chips in the editor, shown as colour badges on
  the recipe, printed on the training cards, carried in the Excel export.
  Codes stay language-neutral; full names resolve EN/PT.
- **Settings**: one ⚙ dialog holds language (EN/PT), text size (A−/A/A+)
  and display unit (ml/cl/oz) — the header stays clean on every screen.
- **Owner PIN (S1)**: first run asks you to set a PIN (hashed with pbkdf2 —
  never stored plaintext). After that the app stays **locked** until the PIN
  is entered (signed cookie session, 14 days). A 🔒 Lock button in Settings
  locks it again. Security headers (CSP, frame-deny, nosniff) ride along on
  every response.
- **Suppliers (K4)**: each stock item names its supplier (free-form,
  suggested from what you already typed). The order list groups *To order*
  and *Over par* by supplier — one glance per supplier, one call per
  supplier.
- **Accessibility**: text scale A−/A/A+ (persisted, content-only zoom), skip
  link to content, visible focus rings, and aria-labels on every icon-only
  button (✕/✎ read their target name).
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
pytest            # 121 tests: pricing math, migrations, API, stock-take, units, batches, yield, categories, dilution
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
- `005_yield.sql` — `yield_frac` on stock_items (default 1.0, byte-identical
  legacy): usable/bought for trim & cook loss. €6 ÷ (1000 g × 0.80) prices
  trimmed meat honestly; flows through specs AND batches; ripple inherits.
- `006_categories.sql` — `category` on specs (free-form menu section) + an
  index. Chips in the spec list + grouped sections on the printable menu.
  Partial spec PUTs (menu price edits) never wipe it (exclude_unset);
  duplicates keep category and batch-pour lines.
- `007_dilution.sql` — `dilution_pct` on specs (default 0, byte-identical):
  ice melt during shake/stir. Served volume = recipe × (1 + pct/100), served
  ABV = recipe ABV ÷ (1 + pct/100); cost unchanged (water is free).
- `008_settings.sql` — venue profile key/value (name, IVA %) for the printed
  menu title + footer.
- `009_kitchen.sql` — kitchen prep truth: `servings` on batches (portion
  count → cost per portion on the prep sheet) + `stock_adjustments` loss log
  (signed canonical delta + reason: spills, waste, spoilage, corrections).
- `010_allergens.sql` — `allergens` + `dietary` code lists on specs (EU 14
  allergens, V/VE/GF); labels resolve per language at display/export.
- `011_supplier.sql` — `supplier` on stock items (free-form, datalist); the
  order list groups by supplier for one-tap-per-supplier ordering.

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
| GET | `/api/settings` · PUT `/api/settings` | venue profile (name, IVA %) |
| GET | `/api/report/pnl` | section P&L: margins per category + dead-stock € |
| GET | `/api/stock-adjustments` | recent loss-log lines |
| POST | `/api/stock/{id}/adjust` | log spillage/waste (signed delta + reason) |
| GET | `/api/batches` · POST `/api/batches` | list / create (with `servings`) |
| GET/PUT/DELETE | `/api/batches/{id}` | detail (cost, €/portion, expiry) / update / delete |
| POST/DELETE | `/api/batches/{id}/lines` | add / remove a batch ingredient |
| PUT | `/api/batches/lines/{id}` | edit a batch line |
| GET | `/api/export/specs.xlsx` · `/api/export/specs.csv` | spec book (owner file: costs, dietary, allergens) |
| GET | `/api/export/stock.xlsx` · `/api/export/stock.csv` | stock sheet (incl. supplier) |
| GET | `/api/export/menu-qr.svg?url=…` | SVG QR pointing at a menu deep link |

## Ops

- **Backups** — nightly at 03:17 via `barspec-backup.timer` (systemd): sqlite
  online snapshot to `backups/`, integrity-checked, 14 kept, log in
  `backups/backup.log`. Restore: `sudo ops/restore.sh backups/barspec-XXXX.db`
  (stops the service, keeps the current db aside, verifies on restart).
  Manual run: `python3 ops/backup.py`.

## Roadmap (not started)

- PWA offline read cache (service worker — needs HTTPS)
