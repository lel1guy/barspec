-- 007_dilution.sql
-- Optional per-spec dilution: ice melt during shake/stir adds water.
-- dilution_pct = water added as % of the recipe's pre-dilution volume.
--
-- Why a spec field and not a global: a Martini (stirred, ~10-15%) dilutes
-- far less than a Margarita (hard shake, ~20-25%), and a served-straight
-- liqueur is 0. Default 0 keeps every existing spec byte-identical — ABV
-- and volume math only change when the bartender sets the field.
--
-- Effects (pure, in pricing.py):
--   served volume = pre x (1 + pct/100)      (water is free — cost unchanged)
--   served ABV    = pre-ABV / (1 + pct/100)  (the same alcohol in more liquid)
-- Cost per serve is untouched on purpose: the recipe volume is the measured
-- pour; dilution only tells the truth about what reaches the glass.

ALTER TABLE specs ADD COLUMN dilution_pct REAL NOT NULL DEFAULT 0;
