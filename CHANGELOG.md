# BarSpec — Changelog

Timeline of shipped builds (v1.1 era). User docs: [README](README.md).

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
