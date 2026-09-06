-- 004_batches.sql
-- Syrups / infusions as mini-recipes (LOCKED 2026-09-06 — V: "Onto 004").
--
-- batches: a house-made batch (simple syrup, orgeat, infusion...). Cost is
--   DERIVED from batch_lines, never typed. batch_size_ml = the finished
--   batch's volume; per-ml cost = Σ lines / batch_size_ml. made_date +
--   shelf_life_days drive the expiry view (NULL shelf = keeps forever).
--
-- batch_lines: one ingredient of the batch. Two price sources, exactly one:
--   - stock-linked (stock_item_id NOT NULL, cost_eur NULL): derives live from
--     the stock item through the units engine — sugar by kg, bitters by ml —
--     so a bottle price change flows through the batch automatically.
--   - free-text (stock_item_id NULL, cost_eur NOT NULL): typed € cost for
--     that exact amount (water €0, a spice cup €2). Names are free so a batch
--     can say "500 g white sugar" without inventing a stock item.
--
-- spec_lines: lines can now reference a batch instead of a bottle. stock_item_id
--   goes nullable + batch_id added; a CHECK enforces exactly-one. Existing rows
--   are copied over as bottle lines, byte-identical. Batches never nest
--   (batch_lines has no batch_id) — one level of resolution, deliberate.

CREATE TABLE batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    method TEXT NOT NULL DEFAULT '',
    batch_size_ml REAL NOT NULL DEFAULT 1000 CHECK (batch_size_ml > 0),
    made_date TEXT NOT NULL DEFAULT (date('now')),
    shelf_life_days INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE batch_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    stock_item_id INTEGER REFERENCES stock_items(id),
    name TEXT NOT NULL,
    amount_ml REAL NOT NULL CHECK (amount_ml > 0),
    unit TEXT NOT NULL DEFAULT 'g',
    abv REAL NOT NULL DEFAULT 0,
    cost_eur REAL,
    sort INTEGER NOT NULL DEFAULT 0,
    CHECK ((stock_item_id IS NULL) != (cost_eur IS NULL))
);

-- spec_lines: rebuild to allow bottle OR batch reference.
ALTER TABLE spec_lines RENAME TO spec_lines_old;
CREATE TABLE spec_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
    stock_item_id INTEGER REFERENCES stock_items(id),
    batch_id INTEGER REFERENCES batches(id),
    amount_ml REAL NOT NULL,
    unit TEXT NOT NULL DEFAULT 'ml',
    CHECK ((stock_item_id IS NULL) != (batch_id IS NULL))
);
INSERT INTO spec_lines (id, spec_id, stock_item_id, batch_id, amount_ml, unit)
    SELECT id, spec_id, stock_item_id, NULL, amount_ml, unit FROM spec_lines_old;
DROP TABLE spec_lines_old;
