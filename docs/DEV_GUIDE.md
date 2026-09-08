User-facing docs: [User Guide](USER_GUIDE.md) · [Guia do utilizador (PT)](USER_GUIDE.pt-PT.md)

# BarSpec — Developer Guide (how it's built & why)

A guided tour of the BarSpec code: what each file does, the design
decisions and — most importantly — **why** it is built the way it is. Written
for developers and for anyone learning how to build a real, useful web
application from scratch.

Companion docs: the [User Guide](USER_GUIDE.md) is for *using* the app;
`README.md` is the quick reference for running/testing/API.

> **Status (2026-09-08, v1.1):** migrations 001–013 shipped — units engine,
> dimension UI, batches/syrups (004), yield % (005), categories (006),
> dilution (007), venue profile (008), kitchen K1–K4 (009–011: servings +
> loss log, Sections P&L, allergens, suppliers), audit (012), and **A.7 daily
> sales / actual GP / shrinkage (013)**. Phase A + kitchen K1–K4 + security
> S1/S2 shipped, plus the **staff read-only role (022)**: recipes and menu
> without money, money stripped server-side. **172 pytest tests green.**
> Backups: local only (V's decision — offsite S3 cancelled).

---

## 1. What you're looking at

```
barspec/
├── main.py            FastAPI app: HTTP routes, validation, error mapping
├── db.py              SQLite layer: every query + the migration runner
├── pricing.py         PURE €/ABV math — no I/O, no state
├── auth.py            Owner PIN (pbkdf2) + staff PIN + signed-cookie sessions
├── exporters.py       .xlsx/.csv/QR — owner files (costs included)
├── migrations/        *.sql schema evolution, applied in order
├── static/            No-build frontend: index.html, app.js, style.css
├── tests/             pytest: math, migrations, API, counts, sales, …
├── barspec.db         SQLite data file (created on first run)
├── Dockerfile / docker-compose.yml   portable execution
└── docs/              This guide + the user guides (EN and PT-PT)
```

**Stack:** Python + FastAPI + SQLite + vanilla JavaScript. No ORM, no build
step, no frontend framework, no database server. A handful of Python files,
three frontend files. That is the point.

---

## 2. The architecture, and why it is what it is

BarSpec is a **layered app with a pure core**:

```
Browser (static/index.html + app.js)
        │  fetch() JSON
        ▼
main.py  ─── routes, Pydantic validation, HTTP status mapping
        │
        ▼
db.py    ─── SQLite: reads/writes, JOINs, migrations, price impact
        │
        ▼
pricing.py ─── PURE FUNCTIONS: cost, ABV, margin, suggested price, FBE
```

Two rules govern everything:

### Rule 1 — money math is pure and lives in one file

`pricing.py` **has no I/O, does not import db, has no state**. Every function
takes plain dicts/lists and returns numbers. `line_cost()` has no idea what a
database is; it receives a line dict with `amount_ml`,
`bottle_price_eur`, `bottle_volume_ml` and returns €.

Why:
- **Testable.** The money tests (`tests/test_pricing.py`) call functions
  directly — no DB, no HTTP, no setup.
  `assert line_cost(...) == approx(...)`.
- **Single source of truth.** Cost is never stored — it is *derived* from
  bottle price ÷ size × pour. If the cost were stored on the recipe, a price
  change would rot every stored number. Deriving turns the impact report into
  a simple "recompute with the new price", not a hunt for stale rows.
- **Auditable.** Every € is produced by code you can read and test. That is
  the core trust requirement of a bar owner.

The JS frontend **mirrors** a few formulas (suggested price, margin, band)
for live preview as the cursor moves — but the server is the authority; the
comment in `pricing.py` says exactly that. The duplication is a deliberate
trade: instant UI feedback without a round-trip, with the real answer always
recomputed server-side on save.

### Rule 2 — price truth lives on the bottle, not on the recipe

The original v0 schema stored each ingredient *on the recipe* together with
its price (the `ingredients` table). Two recipes using Campari each carried a
Campari price. Price change? Update every line that said "Campari". Rename?
Every line. That is the denormalisation trap, and migration 001 exists to get
out of it.

Now: **`stock_items` = one row per real bottle you buy. `spec_lines` merely
points at it.** The JOIN in `_spec_lines_joined()` re-attaches
name/ABV/price/size on read. Consequences:

- A price edit happens **once** on the bottle → every recipe using it updates
  (JOIN).
- The **impact report** (PUT `/api/stock/{id}` → `impact[]`) is computed by
  re-running the cost of each affected recipe with the old vs the new price —
  zero mutation, pure recomputation.
- Deleting a bottle that is in use is refused (409) — that JOIN would break
  silently.

### Why SQLite and no ORM

- **No server to run.** The whole app is one file. Owners back up by copying
  a file; an install at a venue is a folder + a process.
- **No ORM means every query is visible.** `db.py` is explicit SQL. For
  teaching code this is gold — you read exactly what touches the disk.
- **SQLite is enough.** One user, one venue, hundreds of rows. PostgreSQL
  here would be architectural theatre. (Anti-goal: see §9.)

### Why migrations instead of "recreate the database"

`PRAGMA user_version` tracks the schema version. On startup `db.migrate()`
walks `migrations/*.sql`, applies each numbered file above the current
version — each inside a transaction — and then bumps the version.

The subtle move: **a fresh install walks exactly the same path as an
upgrade.** The `SCHEMA` in `db.py` is deliberately the *old* v0 shape (with
the legacy `ingredients` table) — so migration 001 (which normalises and
removes `ingredients`) is exercised on every install, new or old. There is no
"setup" path and a separate "migrate" path that could diverge.
Self-verifying.

Seed data only runs when `specs` is empty and writes through the *new*
schema — an old database with real data is never re-seeded, and a fresh
database gets 5 demo recipes so cost and price demonstrate themselves
immediately.

### Why a no-build frontend

`index.html` + `app.js` (vanilla JS) + `style.css`. No React, no bundler, no
npm install. Why:

- **The server renders nothing** — it is a JSON API; the frontend is a thin
  `fetch()` client. A framework would add tooling weight, not value.
- **Zero build = zero supply chain, zero upgrades that break**, trivial to
  debug, and any developer can read it.
- **One HTML page, five views** toggled from JS (`showView()`) — simple
  enough that the whole UI fits in one readable file. When that stops being
  true, the plan says *then* revisit — not before.

The JS mirrors some pricing math (§ Rule 1) and keeps the display-unit
conversion (ml ↔ cl ↔ oz) client-side only — the API only ever sees ml.

---

## 3. The data model, evolved

**v0 (base schema, kept as `SCHEMA` to exercise migrations):** `specs` +
`ingredients` (denormalised prices — the trap).

**Migration 001 — normalise stock.** Creates `stock_items` (one row per
bottle, `name UNIQUE COLLATE NOCASE`) and `spec_lines` (spec → stock_item +
`amount_ml`). Deduplicates ingredients into bottles case-insensitively,
preferring rows that carry a real price; rebuilds lines 1:1 against the JOIN;
adds `price_eur` + `target_gp` to specs; drops `ingredients`. Idempotent,
data-preserving.

**Migration 002 — stock-takes.** Adds `par_level REAL NULL` on stock_items
(NULL = "not counted") and **dated snapshots**: `stock_takes(id, taken_at)`
and `stock_take_lines(take_id, stock_item_id, full_bottles, open_fraction)`.
`open_fraction` is constrained to `(0, .25, .5, .75, 1)` — a CHECK, safe
because those values are exact in binary floating point.

A design decision worth underlining: **snapshots, not state.** A count is a
dated row in history — "what we had on Monday" — not an overwrite of "what we
have now". Two snapshots = trends, movement, dead-stock signal. Throwaway UI
state could never answer "what moved this week". (The trends endpoint says it
plainly: *the insight arrives as history grows.*)

**Migration 003 — units engine (shipped 2026-09-06).** Adds `dimension`
(volume|weight|count) to stock_items and `unit` to spec_lines, with the
canonical conversion tables in `pricing.py` (cl→10 ml, oz→29,5735 ml,
dash=1 ml fixed, barspoon=5 ml fixed, kg→1000 g, piece=1). One costing rule
for every dimension — a coffee espresso is 9 g of beans + 60 ml of milk + 1
piece of cup. Legacy lines backfill as volume/ml — the migration test proves
0 cents move for pre-engine data. The API now accepts `LineIn.unit` and
`StockIn.dimension` and rejects dimension mismatches (400).

**Migration 004 — house batches (shipped 2026-09-06).** `batches` (name,
method, size_ml, date, shelf_life_days) + `batch_lines`; `spec_lines` gains a
nullable `batch_id` and a table CHECK that **exactly one** of
stock_item_id/batch_id is set (the rebuild renames and recreates the table,
copying lines 1:1). A batch line is either **stock-linked**
(stock_item_id → cost derives through the engine, so sugar by kg and Campari
by ml both work) or **free text** with `cost_eur` typed for that exact
quantity (water is €0 — the CHECK forces a price source: linked XOR cost).
Cost per pour = `quantity × (batch total ÷ size_ml)`; batches never nest.
`shelf_life_days` + `made_date` produce `days_left` (negative = past its
date; NULL = keeps indefinitely). Recipe pour lines carry an explicit
`serve_batch` marker because a batch-ingredient line legitimately shares its
parent's `batch_id` — pricing must not confuse the two (a key-collision bug
caught in QA, regression-tested).

**Migrations 005–007 (costing precision, shipped 2026-09-06/07):**
`yield_frac` (usable yield of what you buy: €6 ÷ (1000 g × 0.80) prices
trimmed meat), `category` on specs (menu sections; partial PUTs don't wipe it
— `exclude_unset`), `dilution_pct` (ice: served volume = recipe ×
(1 + pct/100), served ABV = ABV ÷ (1 + pct/100); cost unchanged).

**Migrations 008–012 (venue + kitchen + security, shipped 2026-09-07/08):**
venue profile (name, VAT % — title and footer of the printed menu);
`servings` on batches (cost per portion on the prep sheet) +
`stock_adjustments` (loss log: signed canonical delta + reason); `allergens`
+ `dietary` code lists (EU-14, V/VE/GF — neutral codes, names per language);
`supplier` on stock items (order list grouped by supplier); and the
append-only `audit_log` (every old → new price with date/time).

**Migration 013 — daily sales / actual GP / shrinkage (A.7, shipped
2026-09-08).** Sales are posted per (day, spec) via `/api/sales`; re-posting
a day *replaces* it (idempotent, never duplicates). Price and cost are
**snapshots frozen at posting** — invoice semantics, so a later price change
never rewrites past GP. The summary endpoint (`/api/sales/summary`) reports
actual GP per spec plus totals, and `/api/sales/shrinkage` compares the stock
*used* between your last two counts against what your sales *explain* — the
leak in € is the headline number.

---

## 4. The € and ABV math (the pure core)

Everything lives in `pricing.py`. The conventions at the top of the file
matter — read them:

- Money comes in and out as float, **rounded only at the edge**
  (`round(x, 2)`). Intermediate precision is never destroyed early.
- Volume ≤ 0 or price ≤ 0 ⇒ cost 0. An unpriced bottle costs zero and
  *never breaks the math* — the UI then shows "set the bottle price".
- **Suggested price** = `cost ÷ (1 − target_gp)` rounded **up** to the
  nearest €0.50 (`math.ceil(raw * 2) / 2`). Why ceil, not round? A price
  rounded down could dip below the target margin. Ceil guarantees: **if you
  sell at the suggested price, your real margin ≥ target.** That invariant
  has a test (`test_never_dips_below_target`).
- **ABV** is weighted by volume: Σ(volume × abv) ÷ Σ(volume). Water/juice
  lines dilute correctly. Ice dilution is deliberately excluded —
  documented, not faked.
- **Margin band** (`good|ok|low|unpriced`) drives the green/amber/red chips:
  ≥ target = good; up to 10 points below = ok; otherwise low.

**Stock-take math** (same file, second half):
- **FBE** (full-bottle equivalents) = `full_bottles + open_fraction`.
  A count of "2 full + half" = 2.5 FBE.
- **Order shortfall** = `ceil(par − FBE)`, min 0. Par 3, you have 2.5 ⇒
  order 1. The `1e-9` epsilon guard kills float noise so that *exactly at
  par* orders 0, never 1 (tested: `2.9999999999` ⇒ 0).
- **Cash asleep** = excess FBE × bottle price — stock above par is money
  tied up in bottles instead of the bank. That number is the "so what?" of
  the count.

---

## 5. The API (`main.py`)

Thin by design: Pydantic models validate the request, one `db.*` call does
the work, exceptions become HTTP statuses. Notable mappings:

| Situation | Status |
|---|---|
| Recipe/bottle/line not found | 404 |
| Duplicate bottle name | 409 |
| Deleting a bottle still used by recipes | 409 |
| Unknown unit / dimension mismatch / par on a weight item | 400 |
| Bad count (no par, bad fraction, negative fulls) | 400 |
| Missing PIN (S1 gate) | 401 |
| Unknown allergen/dietary code | 422 |
| Staff token on a write, or staff login before a staff PIN is enabled | 403 / 409 |

Error messages are human sentences (FastAPI puts them in `detail`) and the
frontend shows them in a toast — the browser never has to guess.

Routes group by resource and read like the domain: `/api/specs`,
`/api/specs/{id}/lines`, `/api/stock`, `/api/stock/{id}/par`,
`/api/batches`, `/api/batches/{id}/lines`, `/api/stock-takes/{sheet|last|trends}`,
`/api/stock-adjustments`, `/api/sales` + `/api/sales/summary` +
`/api/sales/shrinkage`, `/api/menu`, `/api/settings`, `/api/report/pnl`, plus
exports, audit and the `/api/auth/*` gate.
`GET /api/menu` is the **printable** view (names + prices only — costs and
chips excluded, currency symbols omitted by menu psychology).

**Security gate (S1, middleware, now role-aware):** once the owner PIN is set
(pbkdf2 hash, per-PIN salt, 260k iterations), *every* `/api` route returns
401 without a valid session cookie (HMAC-signed, 14 days);
`/api/auth/*`, `/static` and `/` stay open. The signing secret is random,
generated at first setup and persisted in settings. `auth.py` now carries
**two roles**: the owner token and a staff token — the owner can enable a
staff PIN under Settings, and `/api/auth/staff-login` swaps it for a signed
staff cookie. Staff are read-only by enforcement, not by UI: **money is
stripped server-side** (costs, prices and margins removed from the JSON for
staff), and every write returns 403. The S2 audit writes from inside the
`db.py` mutators themselves (old → new price compared against the pre-edit
row; silent no-ops).

---

## 6. How a request flows (read this twice)

`PUT /api/stock/{id}` — "Campari went from €19 to €25":

1. `main.py` validates `StockIn` (Pydantic; `dimension` is a `Literal`, so an
   absurd dimension is a 422 before the db layer — QA once caught it
   reporting a misleading 409).
2. `db.update_stock_item()` loads the current row and records `old_price`.
3. Price moved → for every recipe touched — **directly through the bottle
   line OR through a batch that lists the bottle** (two levels, one impact
   report) — re-run `drink_cost()` with the old and the new price **in
   memory** (`_spec_lines_all(..., override=(stock_id, price))` →
   `impact[]`). Batch costs recompute from their stock links, so a recipe
   pouring 30 ml of a Campari-based batch moves too.
4. The UPDATE runs, commits, closes. Returns `{"ok": True, "impact": [...]}`.
5. The frontend sees `impact.length > 0` → `showRipple()` renders "The price
   change affects N recipes: Negroni €2.20 → €2.45 per pour" (real seed math:
   gin 30 ml @ €22/700 + Campari 30 ml @ €19/700→€25/700 + vermouth 30 ml @
   €11/750 = €2.197 → €2.454, rounded to 3 places by the API).

No stored cost was updated anywhere. That is Rule 1 paying the rent.

---

## 7. Test strategy (why it has this shape)

`conftest.py` does two clever things:

1. It sets `BARSPEC_DB` to a temp path **before any db/main import** — a test
   import can never touch the real `barspec.db`.
2. It exposes two fixtures:
   - `fresh_db` — a new database built through the **full init path** (base
     schema → every migration → seed), per test. Exercises the real upgrade
     machinery on every run.
   - `legacy_db` — builds a **real v0 database** (with `ingredients`, with a
     "Campari/campari" duplicate where only one row has a price) and then
     runs `init_db()`. It is the money test: if the migration replay passes
     here, every future venue file upgrades safely.

Suite map (172 green tests at HEAD, v1.1):

| File | Protects |
|---|---|
| `test_pricing.py` | Pure math: cost, ABV weighting, ceil-0.50 never below target, margin bands, FBE/order/cash-asleep |
| `test_migrations.py` | v0→latest replay (001→013) byte-identical, dedupe, 1:1 preservation, idempotence, no re-seed |
| `test_api.py` | Smoke: seed state, CRUD, resolve-vs-create on lines, impact, cascade rules |
| `test_stocktake.py` | Par gate, pre-fill, order math, fraction validation, trends/dead stock |
| `test_units.py` | Canonical conversion, dimension guards (in-use 400, junk 422), the coffee proof |
| `test_batches.py` | Derived batch cost, two-level impact, shelf life, guards |
| `test_yield.py` | Yield math + API round-trip |
| `test_categories.py` | Preservation on partial PUT, duplicates, menu grouping |
| `test_dilution.py` | Dilution math + served values in the summary |
| `test_exports.py` | .xlsx/.csv parity, QR SVG |
| `test_settings.py` | Venue profile round-trip + VAT bounds |
| `test_kitchen.py` | Servings → €/portion, loss-log guards |
| `test_report.py` | Sections P&L margins + dead stock |
| `test_allergens.py` | EU-14/dietary codes: 422s, preservation, duplicate, export |
| `test_supplier.py` | Supplier CRUD, order lines carry it, column in the export |
| `test_audit.py` | Append-only trail: old→new detail, silent no-ops, deletions |
| `test_auth.py` | S1 gate: open without PIN, 401 with PIN, login/logout flow, headers |
| `test_sales.py` | A.7: posting/re-posting a sales day (re-post replaces, never duplicates), actual-GP summary, snapshot freeze — price edits after posting never rewrite past GP, shrinkage |
| `test_staff.py` | Staff read-only role (022): 409 until a staff PIN is enabled, money stripped server-side (recursive check), 403 on every write |

The three-layer split (pure math / migrations / API) means a failure says
*which* layer is wrong before you start reading.

---

## 8. Things that look simple but were decisions

- **A missing static mount was a real bug** (commit history): assets 404'd
  and the app served unstyled until `app.mount("/static", ...)` landed. The
  lesson: every layer of a "simple" stack still has to be wired up.
- **The ¼/½/¾ open-bottle fractions are exact in binary floating point** —
  that is why the CHECK is safe (0.1 would not be). Choosing friendly values
  made schema-level validation possible.
- **Par ≤ 0 or empty = not counted** (stored NULL). A zero target makes no
  sense behind a bar, so the model refuses to represent it.
- **Weight items stay out of the count path** (you count bottles, *weigh*
  stock — different work). The code makes the boundary explicit: par on a
  weight item is a 400 instead of silently counting something that should be
  weighed.
- **The printed menu hides currency symbols** — a domain decision (price cues
  suppress consumption) implemented as a `no-print` CSS class system.
- **Duplicated recipe = " (copy)" suffix**, lines re-pointed at the same
  stock bottles. Cheap, and testers love it.
- **Unsaved-count guards** (`beforeunload` + confirmation on view switch)
  exist because half a shelf count lost is exactly what a bar manager would
  hate to lose. Small UX, real domain empathy.
- **Bilingual EN/PT UI via key dictionaries** (toasts included — one central
  map translates the feedback literals without touching the call sites); the
  README and the guides ship in EN and PT-PT.

---

## 9. Anti-goals (restraint as architecture)

From the development plan, and honoured in the code: **Postgres · ORM ·
Alembic · React/Vue + build step · Redis · inventory/POS · multi-user
features · Stripe**. Each was considered and rejected for a single-venue,
offline-friendly product with its data in one file. The discipline is not
"we can't" — it is "not yet, and only when a paying venue demands it" (the
Phase B/C gates in the plan).

---

## 10. Operations (deploy)

- **Dev:** uvicorn with `--reload`; the DB file sits next to the app.
- **Docker:** `docker compose up -d --build` — the image copies the Python
  files + migrations + static; data stays mounted as a plain SQLite file in
  `./data/` (healthcheck hits `/api/specs`). Host port 8780 so it doesn't
  collide with the homelab systemd unit on 8777.
- **Production (homelab):** systemd unit running **/usr/bin/python3** (SELinux
  blocks the system from executing the venv — 203/EXEC); new Python
  dependencies install via dnf, never through the venv (the venv is for
  tests only). Deploy rhythm: snapshot the DB, restart, verify `:8777`,
  push. Owner PIN: on the first visit after an S1 deploy the app asks you to
  set it; until then it stays open on purpose.
- **Backups:** every night at 03:17 (`barspec-backup.timer`) — online sqlite
  snapshot into `backups/`, 14 kept, logged in `backups/backup.log`. Restore:
  `sudo ops/restore.sh backups/barspec-*.db`.
- **Data:** one file, override `BARSPEC_DB` for the path. Back up = online
  snapshot of that file; restore = put the file back. Local only by decision
  — the offsite S3 leg was cancelled.

---

## 11. What to learn from this code

If you are learning to build apps like this, study in this order:

1. **`pricing.py` first.** Pure functions over plain data — the easiest
   surface to understand, and it holds the whole domain's math. Learn:
   *derive, don't store*; round only at the edge; pure = testable.
2. **`tests/test_pricing.py`** — see how the math is pinned down, including
   the invariant tests (never below target margin, float noise at par).
3. **The `db.py` schema + `migrations/001`** — the normalisation story is the
   most transferable lesson: *one truth per concept, references not copies*.
4. **`main.py`** — the thin HTTP layer: validation at the door, domain call,
   status at the exit.
5. **`auth.py`** — the owner/staff gate: pbkdf2 hashes in settings, HMAC
   cookie sessions, middleware protecting everything but the public routes,
   server-side money stripping for the staff role.
6. **`app.js`** — fetch client, view switching, the deliberate JS mirrors.
7. **`conftest.py`** — environment isolation + legacy-database replay. That
   is how you change schemas without fear.

The stack is deliberately learnable: Python logic → SQL/SQLite → FastAPI →
plain HTML/CSS/JS. Four layers, each with one clear job. Build the habit of
asking "**which layer owns this?**" — if the answer is fuzzy, the design is
fuzzy.

---

## 12. Roadmap pointers

The product direction, market reasoning and phased plan live in the vault's
development plan (`Projects/Bar-Tech-Venture/BarSpec-Vision-and-Dev-Plan.md`):
Phase A is closed (counts, units engine, batches, costing precision, PT-PT)
with kitchen K1–K4, security S1/S2, A.7 daily sales / actual GP / shrinkage,
and the staff read-only role (022) shipped — backups stay local (V's
decision; offsite S3 cancelled). Phases B/C (multi-venue, VPS+Caddy,
role-based hosted access, PWA) are deliberately gated on a real paying
venue. Update this document when that happens — the code will have changed
shape.
