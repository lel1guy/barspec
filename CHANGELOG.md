# BarSpec — Changelog

Timeline of shipped builds (v1.1 era). User docs: [README](README.md).

## 2026-09-08 — build 023+ (audit pass, in progress)
- **Visual polish (audit pass)**: header search alignment, subtle steel chip
  active state (no more stark white tab), empty states now *teach* with a
  3-step setup guide (no more "choose on the left" on phones — copy fixed for
  mobile), brighter secondary text + borders (contrast pass), touch targets
  ≥42–46px on rows/inputs, supplier field reads as an input, mobile nav
  badges no longer overlap icons.
- **Vendas fix (023)**: dropdown lists all specs (unpriced labelled "— sem
  preço") with an actionable hint instead of an empty dead-end; static
  assets now cache-busted (`?v=…`) so stale JS can't fake blank screens.
- **Security**: brute-force brake on PIN login (5 misses per IP → 60 s
  lockout, 429).
- **Ops**: backup files chmod 600 / dir 700; `ops/healthcheck.sh` watchdog
  for the live service (Hermes cron alerts on down).

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
