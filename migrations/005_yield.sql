-- 005_yield.sql
-- Yield fraction on stock items — the restaurant unlock (LOCKED 2026-09-06).
--
-- Meat loses trim/cook mass, veg loses peel: buy 1 kg of pork @ €6, use
-- 800 g after prep. yield_frac = usable ÷ bought (0.80). The cost engine
-- divides by it, so the effective per-purchase is size × yield:
--   €6 ÷ (1000 g × 0.80) = €0.0075/g instead of €0.006/g.
--
-- Default 1.0 = no yield loss: every existing row (and every bar/pub volume
-- item) is byte-identical — the migration test proves 0 cents move. Yield
-- flows automatically through specs AND batches (stock-linked lines join it),
-- and the price ripple inherits it with no extra code. Free-text batch lines
-- have no stock, so no yield — you typed their cost already.
--
-- Validated 0 < yield_frac <= 1 in the app layer (Pydantic), not in schema.

ALTER TABLE stock_items ADD COLUMN yield_frac REAL NOT NULL DEFAULT 1.0;
