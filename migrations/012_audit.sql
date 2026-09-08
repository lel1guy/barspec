-- 012_audit.sql
-- S2: append-only audit trail for money-touching edits.
-- Rows are never edited or deleted; the log is the receipts book.
-- action: price | spec_price | added | deleted | adjusted
-- target: the human name; detail: "old -> new" summary (JSON-safe text).

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_audit_at ON audit_log (created_at);
