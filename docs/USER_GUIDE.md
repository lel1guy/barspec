# BarSpec — User Guide

Recipe and cost manager for **bars, pubs, cafés and restaurants**: store your
recipes (drinks *and* dishes) once, link them to what you actually buy — by
the bottle, the kilo or the piece — and let BarSpec do the costing, pricing
and stock-counting math. No more spreadsheet guesswork.

Read this in [Português](USER_GUIDE.pt-PT.md). The [Developer Guide](DEV_GUIDE.md)
explains how it's built; the README is the quick reference.

**Read this if you run a bar, a kitchen, or both.**

---

## What problem does it solve?

| You used to… | BarSpec |
|---|---|
| Price a drink from memory | Real cost per serve, from real bottle prices |
| Update every recipe by hand when Campari goes up | One price change ripples everywhere, with an impact report |
| Guess what your stock is worth | Count once, see par gaps, order lists, dead stock in € |
| Wonder why you're not making money | Actual GP from posted sales + shrinkage (stock vs sales) |
| Hand a recipe book to a new bartender | Searchable specs + printable training cards |

The core rule worth understanding: **BarSpec never stores a cost** — it
*derives* every cost from what you actually pay for the bottle/bag/box. Change
a purchase price and every recipe that touches it updates instantly.

---

## The five screens (desktop sidebar / mobile bottom bar)

1. **Specs** — your recipe book. Each spec (cocktail, dish, drink) has a
   name, glass, method, garnish, its ingredient lines, cost per serve and —
   once you price it — its margin. Menu sections (categories), dilution %,
   allergens and dietary tags ride along.
2. **Batches** — house syrups, infusions, prep (a batch of mayonnaise, a jug
   of margarita mix). You give the batch its ingredients and size; BarSpec
   derives cost per litre and per portion. Specs can pour from a batch
   instead of a single bottle.
3. **Stock** — every physical item you buy, one row: name, price, size, ABV
   (drinks), type (bottle / weight / per piece), yield, par level and
   supplier. Add items inline or via the form; filter as the list grows.
4. **Stock-take** — count the shelf: whole bottles + open fractions
   (¼/½/¾/1). Each count is a dated snapshot. The **order list** groups
   what's below par (and over) per supplier; **trends** show movement
   between counts and dead stock — items sitting in the list but in no
   recipe.
5. **Menu** — the printable, priced view grouped by section, with your venue
   name and IVA footer. Share it via QR; print it when prices change.

Plus a sixth view, **Vendas** (Sales) — see the Sales section below.

---

## Getting started (about 10 minutes)

1. **First visit: set your owner PIN.** The app stays open until you do, on
   purpose — you can't lock yourself out. After that, anyone who opens the
   app gets the PIN screen (wrong PIN = nothing). 🔒 Lock in Settings logs
   out.
2. **Add a venue name (optional):** Menu → ☰ Venue. It prints on your menu.
3. **Add your real stock** — Stock → **+ Add item**:
   - a bottle: name, ABV %, price paid, size (e.g. 700 ml) — kind *Bottle*
   - coffee/beans/flour: price per kg — kind *Weight*, with yield % if
     trimming matters
   - limes: price per box of 12 — kind *Per piece*
   - add the **supplier** name while you're there (the order list will group
     by it)
4. **Enter your first specs** — Specs → **+ New spec**: name, glass, method;
   then add ingredient lines: pick a stock item (or type free text with a
   cost) and the amount per serve. Amounts can be ml, cl, oz, g, kg, dash,
   barspoon or pieces — they convert to a canonical unit underneath.
5. **Price your specs** — in the spec detail, set the **target margin**
   (e.g. 75%) and hit *suggested*; BarSpec rounds **up** to the nearest
   €0.50 so the real margin never dips below your target. Or type a price
   and read the actual margin chip (green ≥ target, amber close, red low).
6. **Do your first count** — Stock-take: set a *par* (what you want on the
   shelf) on the items you count, then count. The order list appears
   immediately.

Optional but powerful: **enable a Staff PIN** (Settings → Staff PIN) so the
team can look up recipes without ever seeing costs — money is removed
server-side, not just hidden.

---

## Workflows that make the numbers honest

### The price-change ripple
A supplier raises gin €22 → €24. In **Stock**, edit the price once, save —
BarSpec shows the impact: *"affects N recipes: Negroni €2.20 → €2.45 per
serve"*. Nothing else to update, ever. Every price edit is also written to
the **audit trail** (Settings → Recent changes): old → new, when.

### House syrup (batch)
1. Batches → **+ New batch**: name, size, shelf life.
2. Add ingredients — sugar by kg, water €0 — the cost per litre derives.
3. In a spec, add an ingredient line and pick *your batch* instead of a
   stock item.
4. Later, add **servings** to the batch (e.g. 40) — the prep sheet then shows
   the true **€/portion**.

### Losses (kitchen lane)
Something spilled, spoiled, trimmed away? **Stock → + Log loss**: item,
signed amount, reason (spillage / waste / spoilage / correction / other),
note. It writes a visible line — repeatable losses become a story, not a
hunch. Losses adjust stock between counts; the count snapshots stay the
authority.

### Sales & shrinkage (the money view)
1. **Vendas → Registar**: every day (or shift), enter what you sold per spec:
   pick the recipe, type the qty, add lines, **Guardar dia**. Re-saving the
   same day replaces it. Price and cost are **frozen at that moment** — a
   later price change never rewrites past GP.
2. **GP real**: pick a date range and read actual revenue, cost, GP € and
   margin % per spec — and the totals. That's what you *actually* made,
   from posted sales.
3. **Encolhimento (shrinkage)**: stock used between your last two counts vs
   what your sales explain. More used than sold = the leak in € (overpours,
   spills, theft, untracked comps). For it to mean something: **count
   weekly, post sales daily** — the count window is the anchor.

### Menu day
Menu → venue name on, priced specs only, print (or PDF) — prices include
your IVA % when set. Share the QR so a phone opens the live menu.

---

## Everyday tips

- **Search** filters specs (and stock) as you type — essential once the
  list is real-sized.
- **Units**: display ml / cl / oz per your crowd (Settings → Display unit).
  Stored canonically underneath — switching never changes a number's truth.
- **PT-PT**: full language switch in Settings; prices render €19,00 in
  Portuguese.
- **Text size**: A− / A / A+ in Settings for low-light shifts.
- **Backups run themselves**: nightly at 03:17, 14 kept, local. Restore:
  `sudo ops/restore.sh backups/barspec-*.db`. Your data file is one SQLite
  file — copy it anywhere.
- **Exports**: Specs .xlsx / Stock .xlsx / CSVs in the Specs & Stock headers
  (owner files — they include costs deliberately). **Cards** prints a
  training deck of the current filter: recipe, method, amounts — never a
  cost, floor-safe.

---

## Safety model in plain words

- **Owner PIN** opens everything; sessions last 14 days.
- **Staff PIN** (optional, enabled by the owner) opens a read-only recipe +
  menu screen. Staff never receive costs: the server removes every money
  field from the response, and any staff request outside the read-only area
  is refused (403).
- **Audit trail** records every price/delete edit, old → new, append-only.
- No internet exposure by design — it runs on your LAN; share over VPN if a
  remote look is ever needed.

---

## FAQ

**Do I need internet?** No. BarSpec runs on a machine on your network —
laptops, tablets and phones on the same wifi reach it. The app is single-
venue by design.

**Can staff enter sales or do counts?** Today staff view is read-only —
the owner (or the person with the owner PIN) posts sales and runs counts.
Shift-based staff access is a deliberate Phase B item.

**What if I make a mistake in a sales day?** Re-save the same day with the
right quantities — it replaces. To remove a line entirely, delete it from
the list behind the summary.

**What's next?** The roadmap: onboarding polish, a fictional demo bundle
(40–60 specs) so the app shows at real scale, and — after a real paying
venue — Phase B (multi-venue, hosted, deeper staff roles). Full plan in the
vault: `Projects/Bar-Tech-Venture/BarSpec-Vision-and-Dev-Plan.md`.
