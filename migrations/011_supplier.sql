-- 011_supplier.sql
-- K4: supplier per stock item (free-form, datalist) — the order list groups
-- by supplier so one tap per supplier becomes possible.

ALTER TABLE stock_items ADD COLUMN supplier TEXT NOT NULL DEFAULT '';
