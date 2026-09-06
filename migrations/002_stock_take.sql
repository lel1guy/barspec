-- 002_stock_take.sql
-- Par levels + dated stock-take snapshots.
--
-- par_level (nullable, bottles): the target stock level a bar manager wants
--   on hand. NULL = bottle not counted / no par yet -> excluded from the
--   count sheet. Only bottles WITH a par drive a stock-take.
--
-- A stock-take = one dated snapshot (stock_takes) with one row per counted
--   bottle (stock_take_lines: full bottles + open-bottle fraction). Storing
--   snapshots instead of throwaway UI state gives history: two snapshots =
--   movement/trends; the order list derives from the latest snapshot vs par.
--
-- open_fraction is a visual 4-step estimate of an open bottle:
--   0.25 / 0.5 / 0.75 / 1.0  (all exact in binary float -> CHECK is safe).
-- FBE (full-bottle equivalents) = full_bottles + open_fraction. Money and
-- order math live in pricing.py, never in the schema.

ALTER TABLE stock_items ADD COLUMN par_level REAL;

CREATE TABLE IF NOT EXISTS stock_takes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock_take_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    take_id INTEGER NOT NULL REFERENCES stock_takes(id) ON DELETE CASCADE,
    stock_item_id INTEGER NOT NULL REFERENCES stock_items(id),
    full_bottles INTEGER NOT NULL DEFAULT 0 CHECK (full_bottles >= 0),
    open_fraction REAL NOT NULL DEFAULT 0 CHECK (open_fraction IN (0, 0.25, 0.5, 0.75, 1)),
    UNIQUE (take_id, stock_item_id)
);
