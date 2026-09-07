-- 010_allergens.sql
-- K3: allergen + dietary tags on specs (EU 14, restaurant compliance).
--
-- Stored as comma-separated code lists ('' = none):
--   allergens: cel glu cru egg fis lup mil mol mus nut pea ses soy sul
--   dietary:   V (vegetarian) VE (vegan) GF (gluten-free)
-- Codes are canonical and language-neutral; labels live in the UI per
-- language (EN/PT) and in exports.

ALTER TABLE specs ADD COLUMN allergens TEXT NOT NULL DEFAULT '';
ALTER TABLE specs ADD COLUMN dietary TEXT NOT NULL DEFAULT '';
