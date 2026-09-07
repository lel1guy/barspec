-- 008_settings.sql
-- Venue profile (Phase A.5 #6): name + IVA % for the printed menu.
-- Key/value so future venue fields ride the same table. Empty = unset.

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
