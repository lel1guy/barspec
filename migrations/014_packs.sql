-- 014: purchase units (packs). A stock item keeps its canonical unit
-- (bottle / can / keg / kg-carton) as the buy-and-count unit; pack_*
-- describe how it's PURCHASED when that differs (case of 24 cans, 6-bottle
-- case, 30 L keg) and let the UI derive the per-unit price from the pack.
-- bottle_price_eur stays the per-unit price of truth (cost maths untouched);
-- the API recomputes it from pack fields when a pack is set.
ALTER TABLE stock_items ADD COLUMN pack_size REAL DEFAULT 1;
ALTER TABLE stock_items ADD COLUMN pack_price_eur REAL DEFAULT NULL;
ALTER TABLE stock_items ADD COLUMN pack_name TEXT DEFAULT '';
