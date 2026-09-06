# BarSpec — User Guide

Cocktail spec manager for bartenders and bar owners: store your recipes once,
link them to your real bottles, and let BarSpec do the costing, pricing and
stock-counting math. No spreadsheets, no hand-repricing when a bottle goes up.

**Read this if you run a bar.** It explains what the app does, how to use each
screen, and what the numbers mean. If you're a developer, the
[Developer Guide](DEV_GUIDE.md) explains how it's built and why.

---

## What BarSpec solves

| Job | Without BarSpec | With BarSpec |
|-----|-----------------|--------------|
| Cost of one drink | Guess, or Excel per recipe | Auto: bottle price ÷ bottle size × amount poured |
| Menu reprice when a bottle price changes | Recalculate every recipe by hand | Edit the bottle once — a ripple report lists every spec affected |
| What to charge | Gut feel | Target-margin slider → suggested price |
| Stock ordering | Count bottles on paper, guess what to buy | Count vs par → order list + cash-asleep total |
| What's selling vs sitting | Shelf memory | Movement between counts + dead-stock list |

---

## Core ideas (5 minutes)

**Spec** — one drink recipe: name, glass, method, garnish + ingredient lines.
Each line is an ingredient amount (e.g. 30 ml Campari).

**Stock** — one row per *real bottle you buy* (e.g. "Campari, 25% ABV,
€19 / 700 ml"). This is the single source of truth for price. Every spec line
*points at* a stock bottle instead of copying its price — so when Campari's
price changes, you edit it in exactly one place and every drink that uses it
updates automatically.

**Cost** — for each spec, BarSpec computes:
- **cost / serve** — what one drink costs you in ingredients
- **ABV** — the drink's real strength, volume-weighted across ingredients
- **volume** — total liquid per serve

**Gross-profit margin (GP %)** — the percentage of the *selling price* that is
profit: `(price − cost) ÷ price`. If a drink costs you €1.50 and sells for
€6.00, margin is 75%.

**Par level** — how many bottles of a spirit you want on the shelf (your
target). Bottles without a par are not part of the stock-count.

**Stock-take** — walking the shelf, counting what you actually have, and
comparing it against par. BarSpec turns each count into an **order list**:
what to buy, and how much cash is sitting *over* par ("cash asleep").

---

## The five screens

### Specs — your recipe book

Left column: every spec, searchable. Click one to open it. Each spec shows:

- **Cost / serve** and **batch cost** (type N servings to scale — handy for
  event batches)
- **ABV** and **volume**
- **Pricing panel** (see "Pricing a drink" below)
- **Ingredient table** — amount, ABV, cost of each line, plus a **cost-share
  bar** showing what % of the drink's cost each ingredient eats (that
  Negroni's vermouth is 21% of cost is the kind of thing this shows you)

Buttons: **Edit** (name/glass/method/garnish), **Ingredients** (add/remove
lines), **Duplicate** (copy as "(copy)"), **Delete**.

**Adding ingredients:** type the bottle name. If it's already in Stock it
links to the existing bottle (ABV/price/size fields hide — the bottle owns
them). If it's a name BarSpec doesn't know, it creates the bottle for you —
fill ABV/price/size now or later in Stock.

### Stock — the shared list (bottles, bags, pieces)

One row per item: name, ABV, price €, size, par. Everything edits inline —
click a field, change it, click away (or press Enter).

- **Kind matters** (top of the + Add form): **Bottle/keg** (volume, ABV),
  **Weight** (coffee, sugar — no ABV, size in g/kg) or **Per piece** (limes).
  Size is stored canonically (ml / g / pieces); you type it in whatever unit
  suits (700 ml or 0.7 l; 1 kg or 1000 g).
- **Used in** shows how many specs use that item.
- Items **no spec uses** are dimmed and can be deleted. Items in use can't be
  deleted (remove them from specs first).
- **Par** column: set how many you want on hand. Empty = not counted in
  stock-takes. Weight items sit out of the count walk — you count bottles and
  pieces, you *weigh* stock.
- **+ Add** for a new one. Name first — "price and size can wait until you
  have the receipt."

**The ripple report:** change an item's *price* and a panel appears listing
every spec whose cost moved, old → new per serve — **including specs that use
a house batch containing that item**. That's your "Campari went up €2 — what
does that do to my menu?" answer, instantly, through every layer.

### Batches — house-made syrups & infusions

Costing a homemade syrup as a vague "€1 guess" is how margins lie. A **batch**
is a mini-recipe: its cost is **derived from ingredients, never typed**.

- **+ New batch**: name, finished size (1 litre is the norm), shelf life in
  days, made date, method note.
- **Add ingredients** by name: if it's in Stock it **links live** (sugar by
  kg, Campari by ml — a price change flows into the batch automatically). If
  it isn't stock, type a **€ cost for that amount** (water = €0).
- The batch shows **total €**, **€ per litre**, and an **expiry chip** — days
  left, red past expiry, "keeps" with no shelf life.
- In a spec, pour it like any ingredient: pick the batch, type the amount.
  Cost = your pour × (batch total ÷ batch size).

A classic first batch: **1:1 simple syrup** — 500 g sugar (linked or €0.45)
+ 500 ml water (€0) → €0.45 per litre instead of €3+ for bought-in.

### Stock-take — count, order, trend

Three tabs:

**Count** — the walk. Every bottle *with a par* is listed, pre-filled with
your **last** count so you only correct what changed. For each bottle:

- Full bottles: type, or use − / + steppers
- Open bottles: fraction picker **0 / ¼ / ½ / ¾ / 1** (visual estimate of the
  open bottle — half a bottle of gin left counts as 0.5)
- Par editable inline on the row (change it mid-count if reality says so)
- FBE column: **full-bottle equivalents** = full + fraction (2 full + one at
  half = 2.5)

Hit **Save count** and BarSpec jumps to the order list.

**Order list** — from your latest count vs par:
- **To order**: bottles under par, with how many whole bottles to buy
  (a half-bottle gap still orders 1 — you buy bottles, not halves)
- **Over par — cash asleep**: what's above target, and the **€ tied up** in it
- **At par**: bottles exactly on target

**Trends & dead stock** — appears as history accrues:
- **Movement** between your last two counts: per bottle, what was used
  (before → now, in bottles, ml and €). Needs 2+ snapshots.
- **Dead stock**: bottles in your list that no spec uses — money on the
  shelf. Build a spec for them or stop buying them.

### Menu — price everything, then print

Every spec with cost, sell price and margin chip. Type a price right in the
row, or set it per-spec in Specs. **Only priced** checkbox filters. Then
**Print menu**:

- Prints **drink names + prices only**. Costs never appear on the sheet.
- Currency symbols are omitted on purpose — price cues suppress spending
  (menu psychology).
- Sidebar, buttons and search are hidden automatically in print.

---

## Pricing a drink (the buying moment)

Open a spec → the pricing panel has a **target margin slider** (40–95%).
BarSpec shows a **suggested price** for that margin — rounded **up** to the
nearest €0.50 so your real margin never dips below target.

1. Drag the slider to your target (cocktail bars typically run 70–80% GP).
2. Click **use** next to the suggested price, or type your own.
3. **Save price.** The margin chip colors the result:
   - 🟢 green = at/above target · 🟡 amber = within 10 pts below ·
   - 🔴 red = well under · grey = unpriced

The server is the authority: prices, costs and margins you see are computed
server-side, not by your browser.

---

## Units: display and entry

Top-right toggle: **ml / cl / oz** — converts display *and* volume entry
(material is always stored canonically, so flipping never changes your data).
On top of that, every spec line has its **own unit**: volumes take
ml/cl/oz, weight ingredients take **g/kg** (9 g of coffee is 9 g, not
"0 ml"), pieces take **piece**. Amounts convert in place when you flip a
line's unit — 30 ml becomes 3 cl, same pour, same cost. Weight and piece
amounts show their own unit inline in the table, because a single header
can't honestly cover a mixed-unit drink.

---

## First run & data

- First launch seeds **5 classic specs** (Negroni, Margarita, Old Fashioned,
  Espresso Martini, Aperol Spritz) with real bottle prices and sensible
  PT prices so costing *and* pricing demo immediately. Delete them whenever.
- Data lives in one SQLite file: `barspec.db` next to the app (override with
  the `BARSPEC_DB` environment variable). **Back up by copying that one file**
  — use SQLite's online backup or stop the app first; never `cp` a live DB.

### Run it

```bash
cd barspec
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

Docker (portable, data in `./data/`):

```bash
docker compose up -d --build   # serves on http://localhost:8780
```

---

## Good first workflows

**1. Cost a new drink** → Specs → + New spec → name it → Ingredients →
add each bottle (known names link, unknown names create bottles) → Save →
read cost/serve, ABV, and the cost-share bars.

**2. Make a house syrup and pour it** → Batches → + New batch (1 litre,
shelf 14–30 days) → add ingredients (stock names link; water is €0) → then
Specs → open any drink → Ingredients → pick your batch → 20 ml → the spec
costs the real syrup, not a guess.

**3. Reprice the menu after a price hike** → Stock → edit the bottle's price
→ read the ripple report → for each affected spec, drag the margin slider →
use suggested → Save.

**4. Set up ordering discipline** → Stock → set a par on every bottle you
count → Stock-take → Count (correct what changed) → Save count → Order list
gives you this week's shopping list and the cash-asleep figure.

**4. Find dead stock** → Stock-take → Trends (or read the dimmed rows in
Stock) → decide: spec it or stop buying it.

---

## FAQ

**"Ice dilution not included"?** ABV/cost assume the pour as spec'd. Ice melt
and wastage are real but variable — BarSpec deliberately doesn't guess them.
Known limitation, documented, not hidden.

**Can I undo a delete?** No. Deletes are immediate. Duplicate before you
experiment on a spec you love.

**Why can't I delete a bottle?** Because specs use it. Removing it would
silently break every drink it's in. Remove it from the specs first.

**Is my data safe if I upgrade?** Yes — schema changes are applied as ordered
migrations on startup. A fresh install runs the exact same upgrade path as an
old database (self-checking). Test suite covers replay from the original v0
schema.

**Multi-user? Cloud?** No — this is a local, single-user app today. One venue,
one file. That's a feature for the target market (offline, no subscription,
data you own), and the plan for multi-venue lives in the dev plan.

**What's next?** The units engine is in (costing handles weight/piece — g of
coffee, limes by the piece), but the on-screen entry for those is still
building; house syrups as costed batches, categories/search, PT-PT UI. See
the dev plan for the roadmap.
