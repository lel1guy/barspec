-- 009_kitchen.sql
-- K1: kitchen prep truth — batch portions + stock adjustments.
--
-- batches.servings: a batch isn't just ml — a mayo batch makes 20 portions.
-- servings > 0 means the kitchen reads cost-per-portion on the sheet:
--   cost_per_serve = batch cost / servings   (ml math still works too)
-- NULL/0 = volume-only use (syrups), unchanged behaviour.
--
-- stock_adjustments: loss log. Kitchens throw away, bars spill — a signed
-- canonical-unit delta with a reason turns shrinkage into a visible line
-- instead of a mystery at the next count. Only adjustments; count snapshots
-- (stock_takes) are untouched and still authoritative for par math.

ALTER TABLE batches ADD COLUMN servings INTEGER;
CREATE TABLE stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_item_id INTEGER NOT NULL REFERENCES stock_items(id),
    delta REAL NOT NULL CHECK (delta != 0),      -- canonical units of the item
    reason TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_adjustments_item ON stock_adjustments (stock_item_id, created_at);
