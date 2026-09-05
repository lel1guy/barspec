-- 001_normalize_stock.sql
-- Normalize per-spec ingredient lines into a shared stock list.
-- One row per real bottle (stock_items); spec lines reference it (spec_lines).
-- Bottle price edited ONCE on stock_items -> every spec using it updates via JOIN.
--
-- Works from the v0 schema (specs + ingredients). On a fresh DB the base schema
-- is created first, then this migration runs the same path (self-checking).
--
-- Also adds optional menu fields to specs: price_eur (accepted sell price) and
-- target_gp (target gross-profit % used by the pricing slider).

CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    abv REAL DEFAULT 0,
    bottle_price_eur REAL DEFAULT 0,
    bottle_volume_ml REAL DEFAULT 700,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS spec_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
    stock_item_id INTEGER NOT NULL REFERENCES stock_items(id),
    amount_ml REAL NOT NULL
);

-- Dedupe ingredients into stock: one bottle per name (case-insensitive).
-- Prefer the row that carries a real price, else the first occurrence.
INSERT INTO stock_items (name, abv, bottle_price_eur, bottle_volume_ml, updated_at)
SELECT name, abv, bottle_price_eur, bottle_volume_ml, datetime('now')
FROM (
    SELECT name, abv, bottle_price_eur, bottle_volume_ml,
           ROW_NUMBER() OVER (
               PARTITION BY lower(name)
               ORDER BY (bottle_price_eur > 0) DESC, id
           ) AS rn
    FROM ingredients
) WHERE rn = 1;

-- Rebuild the per-spec lines against stock. Original rows preserved 1:1.
INSERT INTO spec_lines (spec_id, stock_item_id, amount_ml)
SELECT i.spec_id, s.id, i.amount_ml
FROM ingredients i
JOIN stock_items s ON lower(s.name) = lower(i.name);

-- Menu fields on specs.
ALTER TABLE specs ADD COLUMN price_eur REAL;
ALTER TABLE specs ADD COLUMN target_gp REAL DEFAULT 70;

-- Old denormalized table is gone: price truth now lives on stock_items.
DROP TABLE ingredients;
