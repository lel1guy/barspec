-- 003_units.sql
-- Units engine (S2): dimensions on stock items + per-line units on specs.
--
-- stock_items.dimension: what the item IS measured in —
--   'volume' (canonical ml; the only one until now: bottles, kegs),
--   'weight' (canonical g: coffee beans, sugar bought by kg),
--   'count'  (canonical piece: limes, eggs, garnish).
--   The legacy columns carry the meaning of price-per-purchase and
--   canonical-amount-per-purchase: for volume a 700 ml €22 bottle is
--   volume/700/22; a 5 l keg volume/5000/€; a 1 kg coffee bag weight/1000/€;
--   a 12-lime box count/12/€. Names stay (zero data rewrite); dimension says
--   what the numbers mean.
--
-- spec_lines.unit: the unit the bartender entered the amount in. Default 'ml'
--   keeps every legacy row byte-identical. dash = 1 ml, barspoon = 5 ml
--   (fixed volume sub-units, locked 2026-09-06 — bitters cost via the bottle).
--   The physical amount column stores amount-in-unit; unit defines the
--   conversion to canonical. Allowed units + dimensions live in pricing.py
--   (single source of truth); the app validates there, not in schema.

ALTER TABLE stock_items ADD COLUMN dimension TEXT NOT NULL DEFAULT 'volume';
ALTER TABLE spec_lines ADD COLUMN unit TEXT NOT NULL DEFAULT 'ml';
