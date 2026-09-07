-- 006_categories.sql
-- Menu sections on specs: category TEXT (nullable, free-form, case-insensitive
-- for grouping). 60+ specs break the flat list; categories restore order.
--
-- The bar decides the taxonomy (Old Fashioneds / Martinis / Zero-proof /
-- Drafts / Starters / Mains...), so it is free text with a datalist, not an
-- enum. NULL = uncategorised (the flat list still works). Used for filter
-- chips in the spec list AND menu sections on the printable sheet.
--
-- Additive column with NULL default: existing rows are untouched — the
-- migration test proves replay safety.

ALTER TABLE specs ADD COLUMN category TEXT;
CREATE INDEX idx_specs_category ON specs (category);
