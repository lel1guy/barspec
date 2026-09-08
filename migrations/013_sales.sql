-- 013_sales.sql
-- Phase A.7: daily sales capture -> actual GP + shrinkage.
--
-- One row per (day, spec) sold. qty is re-entered idempotently (POST the
-- same day+spec again = replace). price_eur/cost_eur are SNAPSHOTS frozen
-- at posting time — like an invoice line: later price changes never rewrite
-- past GP (the derived-not-stored rule governs *current* truth; a sales
-- history is a record of what happened, so it freezes).

CREATE TABLE sales_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,                       -- YYYY-MM-DD
    spec_id INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
    qty INTEGER NOT NULL CHECK (qty >= 1),
    price_eur REAL NOT NULL,                 -- snapshot: menu price that day
    cost_eur REAL NOT NULL,                  -- snapshot: derived cost that day
    UNIQUE (day, spec_id)
);
CREATE INDEX idx_sales_day ON sales_lines (day);
