# BarSpec — Changelog

Timeline of shipped builds (v1.1 era). User docs: [README](README.md).

## 2026-09-09 — 030: demo bundle (The Argo, Vilamoura)
- `ops/seed_argo.py`: builds a demo DB from The Argo's public signature menu
  (22 specs: 18 signatures + 4 zero-proof). Every spec's pours are solved so
  the computed ABV equals the menu's declared ABV exactly; purchase prices
  are realistic PT retail approximations; ~100 stock items with suppliers
  empty; categories by flavour profile. Recipes are indicative — the menu
  lists ingredients + serve size + ABV, not amounts.
- Margins land at realistic premium-venue levels (THE ARGO €2.30 cost on
  €25 → ~91% GP). Reseed anytime: `BARSPEC_DB=... .venv/bin/python
  ops/seed_argo.py` (rerun-safe: skips existing specs/stock).

## 2026-09-08 — 026: Summary dashboard + first-run onboarding
- **Summary (◫ Resumo)**: attention page — below-par items from the latest
  count (supplier chips, "need n · fbe/par"), batches expiring ≤7 days,
  losses this month in €, last-count age with a "count again" call >7 days.
  Cards jump to Stock/Batches/Count. `GET /api/dashboard` (+3 tests).
  Owner-only (staff 403 by whitelist).
- **First-run onboarding**: empty venue opens into a 3-step wizard with
  direct "+ Add stock" / "+ Create recipe" actions (persisted dismiss).
- Mobile nits: 44px row buttons, empty-state proportions, nav-label guard.
- Static assets cache-busted (`?v=20260908c`). 172 pytest + 11 e2e.

## 2026-09-08 — 025: QA pass
- Vendas visibility bug fixed (hidden class), login double-fire fixed,
  specs refresh on view entry, sales panel re-renders on language switch.
  e2e net grew to 11 flows and caught a missing-i18n regression.
- Security: brute-force brake on PIN login (5/IP → 60 s).
- Ops: backups chmod 600/700; health watchdog cron (10 min).
- 024: audit-pass visual polish + empty-state guides + CHANGELOG start.

## 2026-09-08 — 022: staff read-only mode
Recipes + menu without money (server-side stripping), owner + staff PINs,
403 outside read-only, dedicated staff screen. 168 tests.

## 2026-09-08 — 021: A.7 daily sales
Migration 013: sales per (day, spec) with frozen price/cost snapshots →
actual GP per spec/period + shrinkage vs the last two counts (leak in €).

## 2026-09-08 — 020: polish
v1.1 tag, stock search, PT euro format (€19,00), loss-log reasons PT.

## 2026-09-08 — 019/018: S2 audit trail, S1 owner PIN + headers
## 2026-09-07 — 017–014: K4 suppliers, K3 allergens, K2 section P&L, K1 portions
## 2026-09-07 — 013–009: venue profile, a11y, training cards, exports/QR, mobile, backups
## 2026-09-06 — 008–004: PT-PT, dilution, categories, yield, batches
## 2026-09-05 — 003–001: units engine, stock-take, stock normalization

## 2026-09-09 — 031: purchase packs + straight-serve products (014)
- Stock items now know how they're BOUGHT: optional pack (case of 24,
  6-bottle case, 30 L keg). When pack price + size are set the per-unit
  price of truth is DERIVED (€18/24 = €0.75) and cost maths stay
  untouched; pack edits ripple into every spec like any price change.
- New-stock form gains "Buy in packs?" (pack name/size/price).
- "+ Product" quick creator: pick a stock item + serve size + price →
  a straight-serve product (beer can, wine by glass or bottle, soda) is
  created in two calls, opening the spec with its honest margin.
- migration 014 (additive). 176 pytest (172+4 pack tests) + 12/12 e2e.

## 2026-09-09 — 032: demo = a full month of use
- `ops/seed_argo.py --month` fabricates 30 days of real operation behind
  the Argo menu (deterministic rng, rerun-safe): 6 weekly stock counts
  (514 lines), daily sales for the full month (~430 lines, ~€39k revenue,
  star specs selling hard), 3 dated house batches (citrus cordial, vanilla
  caramel, Earl Grey), bottle-scale losses this month (~€100 across 6
  entries), suppliers (6) and par levels on ~99 managed items.
- Result: Resumo, Trends/orders-by-supplier, Vendas → actual GP over the
  month, shrinkage with a real count window and a leak story all demo
  immediately. Verified via API: dashboard low=8 age=3d, losses €99.89,
  shrinkage rows=47.


## 2026-09-09 - 033: real PT supplier mapping in the demo
- seed_month no longer randomises suppliers: brand houses where ownership is
  unambiguous (Bacardi-Martini, Pernod Ricard, LVMH Moet Hennessy,
  Brown-Forman, Beam Suntory, Super Bock Group, SCC, CCEP, Sumol+Compal,
  Delta Cafes), everything boutique/uncertain (Angostura, St-Germain,
  Disaronno...) falls through to Makro Cash and Carry - the honest
  catch-all independents actually use.


## 2026-09-09 - 034: fullest demo - pub/wine/cafe shelf + 30-day month
- seed_shelf() adds the 014 breadth: 15 stock items bought the way venues
  buy (Super Bock + Sagres kegs, cans by the case of 24, Luso water by the
  6-pack, Delta Plano coffee by the kg) and 21 straight-serve products:
  draught Imperial/Caneca from the keg, cans, wine by glass AND bottle
  (same bottle stock, two products), Coca-Cola/Fanta/Sumol/tonica, water,
  and espresso drinks (expresso, duplo, meia de leite, galao).
- Full month now runs across 113 managed items (volume+count shelf), 6
  counts / 582 lines, 30 sales days, 3 batches, 6 bottle-scale losses.
- Verified: 48 sellable specs on one menu; costs exact (keg 200 ml = 0.56,
  can 0.64, wine glass 1.48/1.72, espresso 0.097, galao 0.405); margins
  venue-realistic (wine glass 59-65%, espresso 92%); Delta coffee lands on
  Delta Cafes; dashboard low=8 / losses 101.60 / count age 3 days.


## 2026-09-09 - 035: polish - pack labels + demo self-check
- Stock rows show how an item is bought (e.g. a case of 24 at EUR 15.36,
  unit price beneath); order rows now carry pack fields so a shortfall
  reads "~1 x case de 24 (5 un)" instead of raw units.
- Review/sheet rows now include pack_size/pack_price_eur/pack_name
  (verified: Super Bock can shortfall row carries pack_size 24).
- GET /api/demo/status (owner) - 7 checks, counts only (no money figures):
  specs >= 40, stock >= 100, counts >= 4 with last date, sales month
  days, zero unpriced specs, loss-log entries, batches. Green on the
  full-month demo DB; 401 to anonymous once a PIN is set.
- Tests: 178 total (176 + 2 demo-status). Cache-bust 20260908g.


## 2026-09-09 - 036: purchase orders + receiving (the buy loop, 015)
- POs by supplier with unit prices FROZEN at order time (invoice-line
  honesty like sales snapshots); open/received states; partial receive
  keeps a PO open; full receive closes it (audited).
- Receiving reports price DRIFT (stored cost vs frozen invoice price)
  with one-click apply through the normal stock PUT (ripple included);
  every received line feeds GET /api/stock/{id}/price-history.
- POs are the money trail only: counts stay the owners of physical
  stock (no phantom on-hand column). Owner-gated routes (403 staff,
  401 anonymous once a PIN is set).
- UI: header Orders (Compras) overlay - open POs with lines + receive,
  new-order editor (supplier + stock/qty lines), received history.
  Hidden from staff (money-adjacent).
- Demo month now seeds 1 open PO + 1 received (history + price history
  populated out of the box). Migration 015; 183 pytest (178+5) and
  12/12 e2e; cache-bust 20260908h.
