# BarSpec

Recipe and cost manager for **bars, pubs, cafés and restaurants** — store
your recipes (drinks *and* dishes) once, scale any pour to N servings, see
real per-drink cost and ABV, price the menu honestly, and never lose track of
what the shelf is doing.

Built by **Vitor Vareiro.** European Portuguese read this in
[Português](README.pt-PT.md).

## What it does

- **Recipes**: name, glass, method, garnish. Create / edit / duplicate /
  delete. Batch pours link to homemade syrups; allergens (EU-14) and dietary
  tags (V/VE/GF) ride along with badges.
- **Stock**: one line per real item — `Campari €19 / 700 ml`, coffee `€18 /
  1 kg`, limes `€3.60 / 12 pc`. Change a price **once** and every recipe
  using it recalculates — the impact report says which ones and by how much,
  even through batches.
- **Honest costing math**: cost is *derived*, never stored. Volume/weight/
  piece with yield %, dilution by ice, ABV weighted by volume. Price
  suggestions round **up** to €0.50 so the real margin never dips below your
  target (an invariant with a test).
- **Batches (house syrups, prep)**: cost per litre derives from the stock
  lines inside; `servings` = real cost per portion on the prep sheet.
- **Stock-take**: count in full bottles + open fractions, dated snapshots —
  trends, FBE/order list, dead-stock € (cash asleep on the shelf), "cash
  tied up" above par.
- **Kitchen lane**: loss log (signed adjustments with reasons), Sections P&L
  with margin chips, allergens, **suppliers** — the order list groups by
  supplier.
- **Menu**: priced, printable, grouped by section, venue name + IVA footer,
  QR deep-link share.
- **Sales → actual GP & shrinkage**: enter what you sold per spec per day;
  re-posting a day replaces it. Price/cost are **snapshots frozen at
  posting** (invoice semantics — future price changes never rewrite past GP).
  Shrinkage compares stock *used* between your last two counts vs what your
  sales *explain* — the leak in € is the headline number.
- **Summary (attention page)**: one glance on every visit — items below
  par from the latest count (with suppliers), batches expiring within a
  week, losses this month in €, and a "count again" nudge when the last
  count is older than 7 days. Cards jump straight to the relevant view.
- **First-run onboarding**: an empty venue opens into a 3-step wizard
  (add stock → create a recipe → set a price) with direct action buttons.
- **Exports & share**: spec book / stock as .xlsx + .csv, training cards
  (print a spec deck — never a cost), menu QR.
- **Owner security**: first run asks for a PIN (pbkdf2-hashed, never stored
  plaintext). After that everything is locked behind a signed session cookie
  (14 days). **Audit trail**: every price edit and delete is logged
  old → new with a timestamp (append-only).
- **Staff mode**: the owner can enable a staff PIN (Settings). Staff see
  recipes and the menu — **money is removed server-side** (costs, prices,
  margins stripped from the JSON, not just hidden in the UI). Stock, counts,
  sales, exports and every write return 403 to staff.
- **PT-PT**: the whole UI is bilingual EN/PT (menu prices in PT format
  €19,00), text size A−/A/A+, responsive mobile layout with a floor-friendly
  bottom bar.
- **Backups**: nightly online sqlite snapshot, 14 kept, with a tested
  restore script (local only by design).

## Tech

Python + FastAPI + SQLite + vanilla JS (no build step, no ORM). One data
file, one process, no external services. Full architecture rationale lives in
the [Developer Guide](docs/DEV_GUIDE.md).

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8777
```

Open `http://localhost:8777`. Or `docker compose up -d --build` (port 8780,
data in `./data`). First visit: set your owner PIN — the app stays open until
you do, by design.

## Tests

```bash
pytest            # 172 tests: pricing, migrations, API, counts, units, batches, yield, categories, dilution, kitchen, reports, allergens, suppliers, audit, auth (incl. brute-force brake), staff, sales, dashboard
npm run e2e       # real-browser smoke (Playwright, 11 flows): PIN, recipes, PT-PT, stock filter, sales view, menu
```

The migration tests build a real v0 database and upgrade it — if they pass,
every future venue file upgrades safely. Money tests cover cent-rounding,
unpriced bottles, price-ripple, FBE/par/order math and sales snapshots. The
e2e suite boots the real app on a throwaway DB and drives the owner flows in
headless Chromium (`npm install` + the Playwright cache in
`~/.cache/ms-playwright`).

## Schema / migrations

- `001_stock.sql` — normalize ingredients → stock_items + spec_lines;
  price_eur + target_gp on specs
- `002_stocktake.sql` — par levels + dated count snapshots
- `003_units.sql` — dimension (volume|weight|count), units engine
- `004_batches.sql` — homemade batches; exactly-one price source CHECK
- `005_yield.sql` — yield_frac (usable ÷ bought)
- `006_categories.sql` — menu sections; partial PUTs never wipe them
- `007_dilution.sql` — ice dilution % (served volume/ABV; cost unchanged)
- `008_settings.sql` — venue profile (name, IVA %)
- `009_kitchen.sql` — servings on batches + stock adjustments (loss log)
- `010_allergens.sql` — EU-14 + V/VE/GF code lists on specs
- `011_supplier.sql` — supplier per stock item
- `012_audit.sql` — append-only audit trail (old → new, when)
- `013_sales.sql` — daily sales per (day, spec); price/cost frozen at posting

DB file: `barspec.db` (override with `BARSPEC_DB=/path` for tests). Online
snapshots under `backups/` (nightly 03:17, 14 kept); restore:
`sudo ops/restore.sh backups/barspec-*.db`.

## API (main routes)

| Method | Path | Purpose |
|---|---|---|
| GET/POST/PUT/DELETE | `/api/specs`, `/api/specs/{id}`, `/api/specs/{id}/lines` | recipes, lines, duplicate |
| GET/POST/PUT/DELETE | `/api/stock`, `/api/stock/{id}` | items, price ripple, supplier |
| PATCH | `/api/stock/{id}/par` | count target |
| GET/POST/PUT/DELETE | `/api/batches`, `/api/batches/{id}`, lines | house syrups & prep |
| GET/POST | `/api/stock-takes`, `/api/stock-takes/{sheet\|last\|trends}` | count snapshots, order list, movement/dead stock |
| POST | `/api/stock-adjustments` | loss log (signed amounts + reason) |
| GET | `/api/menu` | printable priced menu |
| GET/PUT | `/api/settings` | venue profile (name, IVA) |
| GET | `/api/report/pnl` | Sections P&L + dead stock |
| GET | `/api/export/specs.xlsx\|.csv`, `/api/export/stock.xlsx\|.csv` | owner files (costs included deliberately) |
| GET | `/api/export/menu-qr.svg?url=…` | menu QR SVG |
| GET | `/api/audit` | recent audit trail lines |
| POST/GET/DELETE | `/api/sales`, `/api/sales/{id}` | post/list/delete a sales day |
| GET | `/api/sales/summary?from_day&to_day` | actual GP per spec + totals |
| GET | `/api/sales/shrinkage` | stock-vs-sales leak in € (last two counts) |
| GET | `/api/dashboard` | attention summary: below-par, expiring, losses €, count age |
| GET/POST/PUT | `/api/auth/status\|setup\|login\|logout\|staff-login\|staff-pin` | owner + staff PIN gate (protected routes 401 without a cookie; staff 403 outside read-only) |

## Operations

Live service runs under systemd as **system Python** (`/usr/bin/python3` —
SELinux blocks the repo venv, so live deps install via dnf; the venv is for
tests/dev). Deploys: snapshot the DB, restart, verify `:8777`, push. A
**health watchdog** (`ops/healthcheck.sh`, Hermes cron every 10 min) is
silent while the app answers and alerts if `:8777` goes down. Build history:
[CHANGELOG.md](CHANGELOG.md).

## Roadmap / status

Phase A complete (counting, units engine, batches, costing precision, PT-PT),
kitchen K1–K4, security S1/S2, sales & shrinkage, staff roles — all shipped
(2026-09-08, 172 tests). Phases B/C (multi-venue, VPS + Caddy, hosted
multi-tenant, PWA) are deliberately gated on a real paying venue. The full
product plan lives in the vault (`Projects/Bar-Tech-Venture/
BarSpec-Vision-and-Dev-Plan.md`).
