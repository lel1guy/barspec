# BarSpec — Developer Guide (how it's built & why)

A teaching walkthrough of BarSpec's codebase: what each file does, the design
decisions, and — most importantly — **why** it's built this way. Written for
developers and for people learning to build a real, useful web app from
scratch.

Companion docs: [User Guide](USER_GUIDE.md) for how to *use* the app,
`README.md` for run/test/API quick reference.

> **Status note (2026-09-06):** this documents the shipped architecture
> (migrations 001–002 + S1 display toggle). A units engine (migration 003 —
> weight/piece dimensions) is mid-flight on branch `feat/units-s2`,
> **uncommitted**: schema file + pricing tables + tests exist, the live DB is
> still at version 2, and one café-proof test is red. Sections affected are
> marked **S2 in progress**.

---

## 1. What you're looking at

```
barspec/
├── main.py            FastAPI app: HTTP routes, validation, error mapping
├── db.py              SQLite layer: every query, plus migration runner
├── pricing.py         PURE money/ABV math — no I/O, no state
├── migrations/        *.sql schema evolution, applied in order
├── static/            No-build frontend: index.html, app.js, style.css
├── tests/             pytest: pricing math, migrations, API, stock-take
├── barspec.db         SQLite data file (created on first run)
├── Dockerfile / docker-compose.yml   portable deployment
└── docs/              This guide + the user guide
```

**Stack:** Python + FastAPI + SQLite + vanilla JS. No ORM, no build step,
no frontend framework, no database server. Four files of Python, three of
frontend. That is the point.

---

## 2. The architecture, and why it looks like this

BarSpec is a **layered app with a pure core**:

```
Browser (static/index.html + app.js)
        │  fetch() JSON
        ▼
main.py  ─── routes, Pydantic validation, HTTP status mapping
        │
        ▼
db.py    ─── SQLite: reads/writes, JOINs, migrations, ripple impact
        │
        ▼
pricing.py ─── PURE FUNCTIONS: cost, ABV, margin, suggested price, FBE
```

Two rules drive everything:

### Rule 1 — the money math is pure and lives in one file

`pricing.py` has **no I/O, no imports of db, no state**. Every function takes
plain dicts/lists and returns numbers. `line_cost()` doesn't know what a
database is; it gets a line dict with `amount_ml`, `bottle_price_eur`,
`bottle_volume_ml` and returns €.

Why:
- **Testable.** The money tests (`tests/test_pricing.py`) call functions
  directly — no DB, no HTTP, no setup. `assert line_cost(...) == approx(...)`.
- **One source of truth.** Cost is never stored — it's *derived* from
  bottle price ÷ size × pour. If you stored cost on the spec, a bottle price
  change would rot every stored number. Deriving means the ripple report is
  just "recompute with the new price", not "hunt down stale rows".
- **Auditable.** Every € is computed by code you can read and test. That's
  the bar-owner's core trust requirement.

The JS frontend **mirrors** a few formulas (suggested price, margin, band)
for live slider preview — but the server is authoritative; the comment in
`pricing.py` says exactly this. Duplication is a deliberate trade: instant
UI feedback without a round-trip, with the real answer always recomputed
server-side on save.

### Rule 2 — price truth lives on the bottle, not the recipe

The original v0 schema stored each ingredient *inline on the spec* with its
own price (`ingredients` table). Two specs using Campari each carried a
Campari price. Price change? Update every row that said "Campari". Rename?
Every row. This is the denormalization trap, and migration 001 exists to
walk out of it.

Now: **`stock_items` = one row per real bottle you buy. `spec_lines` just
point at it.** The JOIN in `_spec_lines_joined()` reattaches name/ABV/price/
size at read time. Consequences:

- Price edited **once** on the bottle → every spec using it updates (JOIN).
- The **ripple report** (PUT `/api/stock/{id}` → `impact[]`) is computed by
  replaying each affected spec's cost with old vs new price — zero mutation,
  pure recomputation.
- Deleting a bottle in use is refused (409) — that JOIN would silently break
  otherwise.

### Why SQLite + no ORM

- **No server to run.** The whole app is a file. Bar owners back up by
  copying one file; a venue install is a folder + a process.
- **No ORM means every query is visible.** `db.py` is 800 lines of explicit
  SQL. For a teaching codebase this is gold — you can read exactly what hits
  the disk. (The README says it plainly: "no ORM — you can read every query".)
- **SQLite is enough.** Single user, one venue, hundreds of rows. PostgreSQL
  here would be architecture theatre. (Anti-goal: see §9.)

### Why migrations instead of "just recreate the DB"

`PRAGMA user_version` tracks schema version. On startup `db.migrate()` scans
`migrations/*.sql`, applies every file numbered higher than the current
version, each inside one transaction, then bumps the version.

The subtle move: **a fresh install runs the exact same path as an upgrade.**
`SCHEMA` in `db.py` is deliberately the *old* v0 shape (with the legacy
`ingredients` table) — so migration 001 (which normalizes away `ingredients`)
exercises on every single install, fresh or ancient. There is no separate
"setup" and "migrate" code path to drift apart. Self-checking.

Seed data only runs when `specs` is empty and writes through the *new*
schema — so an old DB with real data never gets re-seeded, and a fresh DB
gets 5 demo specs that make costing + pricing demo immediately.

### Why the frontend has no build step

`index.html` + `app.js` (vanilla JS) + `style.css`. No React, no bundler,
no npm install. Why:

- **The server renders nothing** — it's a JSON API; the frontend is a thin
  client over `fetch()`. A framework would add toolchain weight, not value.
- **Zero build = zero supply chain, zero breaking upgrades**, trivially
  debuggable, and any dev can read it.
- **One HTML page, four views** toggled by JS (`showView()`) — simple enough
  that the whole UI fits in one readable file. When this outgrows itself
  (categories/search/PT-PT), the dev plan says *then* revisit — not before.

The JS does mirror some pricing math (§ Rule 1) and holds the display-unit
conversion (ml ↔ cl ↔ oz) purely client-side — the API only ever sees ml.

---

## 3. The data model, evolved

**v0 (base schema, kept as `SCHEMA` for migration testing):**
`specs` + `ingredients` (denormalized prices — the trap).

**Migration 001 — normalize stock.** Creates `stock_items` (one row per
bottle, `name UNIQUE COLLATE NOCASE`) and `spec_lines` (spec → stock_item +
`amount_ml`). Dedupes ingredients into bottles case-insensitively, preferring
rows that carry a real price; rebuilds lines 1:1 against the JOIN; adds
`price_eur` + `target_gp` to specs; drops `ingredients`. Idempotent,
data-preserving.

**Migration 002 — stock-take.** Adds `par_level REAL NULL` on stock_items
(NULL = "not counted"), plus **dated snapshots**:
`stock_takes(id, taken_at)` and `stock_take_lines(take_id, stock_item_id,
full_bottles, open_fraction)`. `open_fraction` is constrained to
`(0, .25, .5, .75, 1)` — a CHECK, safe because those values are exact in
binary float.

Design decision worth dwelling on: **snapshots, not state.** A stock-take is
a dated row in history — "what did we have on Monday" — not an overwrite of
"what we have now". Two snapshots = trends, movement, dead-stock signal.
Throwaway UI state could never answer "what moved this week". (The trend
endpoint says: *insight appears as history accrues.*)

**S2 in progress — migration 003 (units engine).** Adds `dimension`
(volume|weight|count) to stock_items and `unit` to spec_lines, with
canonical-conversion tables in `pricing.py` (cl→10 ml, oz→29.5735 ml,
dash=1 ml fixed, barspoon=5 ml fixed, kg→1000 g, piece=1). Design intent
(from the dev plan): one cost rule across dimensions — a café espresso is
9 g beans + 60 ml milk + 1 piece cup. Currently **uncommitted on
`feat/units-s2`**, DB still at v2, one café-proof test failing on the API
response shape (line rows not yet exposing `unit`/`dimension`).

---

## 4. Money & ABV math (the pure core)

All in `pricing.py`. Conventions at the top of the file matter — read them:

- Money floats in and out, **rounded only on output** (`round(x, 2)`).
  Intermediate precision is never destroyed early.
- Volume ≤ 0 or price ≤ 0 ⇒ cost 0. An unpriced bottle costs nothing and
  *never crashes math* — the UI then shows "set a bottle price".
- **Suggested price** = `cost ÷ (1 − target_gp)` rounded **up to the nearest
  €0.50** (`math.ceil(raw * 2) / 2`). Why ceil, not round? A rounded-down
  price could dip below the target margin. Ceiling guarantees: **if you sell
  at the suggested price, your real margin ≥ target.** That invariant has a
  test (`test_never_dips_below_target`).
- **ABV** is volume-weighted: Σ(volume × abv) ÷ Σ(volume). Water/juice lines
  dilute correctly. Ice dilution is deliberately excluded — documented,
  not faked.
- **Margin band** (`good|ok|low|unpriced`) drives the green/amber/red chips:
  ≥ target = good; within 10 pts below = ok; else low.

**Stock-take math** (same file, second half):
- **FBE** (full-bottle equivalents) = `full_bottles + open_fraction`. A count
  of "2 full + one at half" = 2.5 FBE.
- **Order shortfall** = `ceil(par − FBE)`, floored at 0. Par 3, have 2.5 ⇒
  order 1. The `1e-9` epsilon guard kills float noise so *exactly at par*
  orders 0, never 1 (tested: `2.9999999999` ⇒ 0).
- **Cash asleep** = excess FBE × bottle price — stock sitting above par is
  money tied up in bottles instead of the bank. This number is the
  stock-take's "so what".

---

## 5. The API (`main.py`)

Thin by design: Pydantic models validate the request, one `db.*` call does
the work, exceptions become HTTP statuses. Notable mappings:

| Situation | Status |
|---|---|
| Spec/bottle/line not found | 404 |
| Duplicate bottle name | 409 |
| Delete bottle still used by specs | 409 |
| Unknown unit / dimension mismatch / par on weight item (**S2**) | 400 |
| Bad count (no par, bad fraction, negative full) | 400 |

Error messages are human sentences (FastAPI puts them in `detail`), and the
frontend surfaces them in a toast — the browser never has to guess.

Routes group by resource and read like the domain:
`/api/specs`, `/api/specs/{id}/lines`, `/api/stock`, `/api/stock/{id}/par`,
`/api/stock-takes/{sheet|last|trends}`, `/api/menu`. `GET /api/menu` is the
**printable** view (names + prices only — costs and chips excluded, currency
symbols omitted for menu psychology).

---

## 6. How one request flows (read this twice)

`PUT /api/stock/{id}` — "Campari went from €19 to €25":

1. `main.py` validates `StockIn` (Pydantic).
2. `db.update_stock_item()` loads the current row, notes `old_price`.
3. Price moved → for each spec using this bottle, it replays `drink_cost()`
   with old and new price **in memory** (`price_override`) → `impact[]`.
4. UPDATE executes, commit, close. Returns `{"ok": True, "impact": [...]}`.
5. Frontend sees `impact.length > 0` → `showRipple()` renders "Price change
   affects N specs: Negroni €1.37 → €1.72 per serve".

No stored cost was updated anywhere. That's Rule 1 paying rent.

---

## 7. Testing strategy (why it's shaped like this)

`conftest.py` does two clever things:

1. Sets `BARSPEC_DB` to a temp path **before any import of db/main** — a test
   import can never touch the real `barspec.db`.
2. Exposes two fixtures:
   - `fresh_db` — a brand-new DB built through the **full init path**
     (base schema → all migrations → seed), per test. Exercises the real
     upgrade machinery on every run.
   - `legacy_db` — builds an actual **v0 database** (with `ingredients`, with
     a case-duplicate "Campari/campari" where only one row has a price) then
     runs `init_db()`. This is the money test: if migration replay passes
     here, every future venue file upgrades safely.

Suite map (~66 tests, growing with S2):

| File | Guards |
|---|---|
| `test_pricing.py` | Pure math: cost, ABV weighting, ceil-to-0.50 never below target, margin bands, FBE/order/cash-asleep |
| `test_migrations.py` | v0→latest replay, dedupe correctness, 1:1 line preservation, idempotence, no-reseed |
| `test_api.py` | Smoke: seed state, CRUD, resolve-vs-create on lines, ripple impact, cascade rules |
| `test_stocktake.py` | Par gating, sheet prefill, order-list math, fraction validation, trends/dead-stock |
| `test_units.py` (**S2 WIP**) | Unit tables, canonical conversion, café proof — 1 red test |

The three-layer split (pure math / migrations / API) means a failure tells
you *which* layer is wrong before you start reading.

---

## 8. Things that look simple but were decisions

- **Missing static mount was a real bug** (commit history): assets 404'd and
  the app served unstyled until `app.mount("/static", ...)` landed. The
  lesson: every layer of a "simple" stack still has to be wired.
- **The ¼/½/¾ open-bottle fractions are exact in binary float** — that's why
  the CHECK constraint is safe (0.1 would not be). Picking friendly values
  made schema-level validation possible.
- **Par ≤ 0 or empty = not counted** (stored NULL). A zero target is
  meaningless on a bar floor, so the data model refuses to represent it.
- **Weight items are excluded from the count walk in v1** (you count bottles,
  you *weigh* stock — a different job). That boundary is explicit in code,
  not an accident. (**S2** codifies it: par on a weight item raises 400.)
- **Menu print hides currency symbols** — a domain decision (price cues
  suppress spend) implemented as a `no-print` CSS class system.
- **Duplicate spec = " (copy)" suffix**, lines re-pointed at the same stock
  bottles. Cheap, and testers love it.
- **Unsaved-count guard** (`beforeunload` + view-switch confirm) exists
  because a half-done shelf count is exactly what a bar manager would rage
  about losing. Small UX, real domain empathy.

---

## 9. Anti-goals (restraint as architecture)

From the dev plan, and honored in the code: **Postgres · ORM · Alembic ·
React/Vue + build step · Redis · inventory/POS · multi-user roles · Stripe**.
Every one of those was considered and rejected for a single-venue, offline-
friendly, one-file-data product. The discipline isn't "we can't" — it's
"not yet, and only when a paying venue demands it" (Phase B/C gates in the
dev plan).

---

## 10. Deployment

- **Dev:** uvicorn with `--reload`; DB file next to the app.
- **Docker:** `docker compose up -d --build` — image copies the four Python
  files + migrations + static; data bind-mounted as a plain SQLite file in
  `./data/` (healthcheck hits `/api/specs`). Host port 8780 so it doesn't
  clash with the homelab systemd unit on 8777.
- **Data:** one file, `BARSPEC_DB` override for path. Backup = online-backup
  snapshot of that file; restore = drop the file in.

---

## 11. What to learn from this codebase

If you're learning to build apps like this, study in this order:

1. **`pricing.py` first.** It's pure functions over plain data — the easiest
   possible surface to understand, and it holds the entire domain model's
   math. Learn: *derive, don't store*; round on output only; pure = testable.
2. **`tests/test_pricing.py`** — see how the math is locked down, including
   the invariant tests (never below target margin, float-noise-at-par).
3. **`db.py` schema + `migrations/001`** — the normalization story is the
   single most transferable lesson: *one truth per concept, references not
   copies*.
4. **`main.py`** — thin HTTP layer: validation in, domain call, status out.
5. **`app.js`** — fetch client, view switching, the deliberate JS mirrors.
6. **`conftest.py`** — env isolation + legacy-DB replay. This is how you make
   schema changes without fear.

The stack is deliberately learnable: Python logic → SQL/SQLite → FastAPI →
HTML/CSS/vanilla JS. Four layers, each with one clear job. Build the habit of
asking "**which layer owns this?**" — if the answer is fuzzy, the design is
fuzzy.

---

## 12. Roadmap pointers

The product direction, market reasoning and phased plan live in the vault
dev plan (`Projects/Bar-Tech-Venture/BarSpec-Vision-and-Dev-Plan.md`):
Phase A = stock-take ✅ → units engine (**S2/S3 in flight**) → syrups as
costed batches (migration 004) → categories/search → PT-PT UI. Phase B/C
(tenancy, VPS+Caddy, auth, PWA) are deliberately gated on a real paying
venue. Update this doc when those land — the code will have changed shape.
