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

## The screens (desktop sidebar / mobile bottom bar)

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
6. **Sales (Vendas)** — post what you sold per day, read actual GP and the
   shrinkage leak. Full walkthrough in *Sales & shrinkage* below.
7. **Summary (Resumo)** — the homepage: below-par items with suppliers,
   batches expiring this week, losses this month in €, a count-age nudge —
   plus 30-day revenue and GP-by-category charts. Cards jump to the view
   that fixes the problem.

8. **Settings (⚙)** — its own page in the navigation: language, text size,
   display unit, staff PIN, the audit trail, Help, and Lock. Reference at the
   end of this guide.

One place is not in the sidebar:

- **📥 Orders** (header button) — purchase orders and receiving; see
  *Orders — buying and receiving* below. Owner-only.

---

## Your first 30 minutes

*This guide is task-based (how-to). The reasoning behind the design —
derived costs, frozen snapshots, why purchase orders don't move stock — is in
[WHY.md](WHY.md); the code-level reference is the [Developer Guide](DEV_GUIDE.md).*

**Fast track (5 minutes, no typing):** run the month demo and follow along with
real data — 48 items, 30 days of counts and sales, and a €100 leak hiding in
the shrinkage report:

```bash
BARSPEC_DB=/tmp/argo-demo.db .venv/bin/python ops/seed_argo.py --month
BARSPEC_DB=/tmp/argo-demo.db .venv/bin/python -m uvicorn main:app --port 8791
```

**From zero to a priced menu (30 minutes):**

1. **Set your owner PIN** *(1 min).* The app stays open until you do, on
   purpose — you can't lock yourself out. After that, wrong PIN = nothing.
   🔒 in Settings logs out.
2. **Name the venue** *(1 min)* — Menu → ☰ Venue; it prints on the menu.
3. **Add real stock** *(10 min)* — Stock → **+ Add item**, one line per thing
   you buy: a bottle (name, ABV, price, size — e.g. gin €23 / 700 ml), coffee
   by the kilo (*Weight* + yield % if trimming matters), a case of beer
   (*Per piece*, size 1, then **Buy in packs?** 24 @ €15.36 → cost per can
   derives itself), a 30 L keg, wine by the bottle. Add the **supplier** as
   you go — the order list groups by it.
4. **Create your first specs** *(8 min)* — Specs → **+ New spec**: name,
   glass, method, then ingredient lines (ml/cl/oz/g/dash/piece — all
   convert). Faster for simple things: **+ Product** (pick the stock item,
   the serve size, the price — a soda or a wine glass in three fields).
5. **Price honestly** *(2 min)* — set the **target margin** (e.g. 75%) and
   hit *suggested*: BarSpec rounds **up** to the nearest €0.50 so the real
   margin never dips below your target. The margin chip reads green ≥ target,
   amber close, red low.
6. **Set pars and do your first count** *(5 min)* — Stock-take: par = what
   you want on the shelf, count in full bottles + open fractions, save. The
   **order list** appears immediately, grouped by supplier, with dead-stock €.
7. **Order and receive** *(2 min)* — 📥 **Orders**: create a PO (prices freeze
   at that moment), and when the delivery arrives hit **Receive**. If the
   invoice price moved, BarSpec asks "stored €11.00 → invoice €11.80?" — one
   click applies it and ripples through every recipe.
8. **Post a day of sales** *(1 min)* — Vendas: enter what you sold per spec;
   re-posting a day replaces it (never rewrites history). Your **actual GP**
   and the **shrinkage** number appear — stock used between counts vs what
   sales explain.
9. **Invite the team safely** *(1 min)* — Settings → Staff PIN. Staff see
   recipes and the menu; costs, prices and margins are removed in the API —
   never sent to their browser at all.

When the month fills up, the Summary homepage becomes the first thing you see:
below-par items with suppliers, batches expiring this week, losses in €, a
count-age nudge — plus 30-day revenue and GP-by-category charts.

Optional but worth it: press **+ Product** and add the boring 60% of the menu
(cans, softs, water, coffee) — the app only earns its keep when the *whole*
bar is in it, not just the cocktails.

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

### Orders — buying and receiving

The order list tells you *what* to buy; this is where you actually buy it.

1. **Create a PO** — 📥 Orders → *+ New order* → supplier (free text, it
   autocompletes from your stock), add lines (item + how many you're
   buying), *Create order*. The unit price is **frozen at that moment** —
   if a supplier changes prices next month, this order still reads today's
   numbers.
2. **Receive the delivery** — when it arrives, open 📥 Orders → **Receive**
   on that order. BarSpec logs it (with an audit entry) and closes the PO.
   *Partial delivery?* Enter only what arrived; the PO stays open for the
   rest — but note the receive button takes the full remaining order, so
   for a partial delivery create a smaller order or adjust after.
3. **Price drift** — if the invoice price differs from what you have stored
   for that item, BarSpec asks: *"Sweet vermouth — stored €11.00 → invoice
   €11.80?"* One click applies it and the price ripple updates every recipe
   that uses it (with the impact report). If you don't apply, nothing
   changes — the PO still records what you actually paid.
4. **Price history** — every received line is remembered per item, so you
   can answer *"what did I pay for gin in March?"* (API:
   `GET /api/stock/{id}/price-history`).

What receiving does **not** do: change your stock levels. Counts own the
physical numbers, orders own the money trail — that's what keeps shrinkage
honest. Future deliveries just mean one more PO.

### Summary — reading the attention page

The homepage answers one question: *what needs me today?*

- **Below par** — items under their target from the last count, with the
  supplier name (so you know who to call). Click a row to open Stock already
  filtered to that item.
- **Expiring** — batches (house syrups, prep) whose shelf life ends within
  7 days; ≤2 days shows red.
- **Losses this month** — the € logged in the loss register (spillages,
  waste, spoilage).
- **Count age** — "counted 3 days ago" or a nudge when it's been over a week.
- **Charts** — daily revenue for the last 30 days and GP% by category
  (green ≥60%, amber ≥40%, red below), with the window's total revenue in
  the card header.

If a card says nothing is wrong: good, go serve drinks.

### Printing, exports and training cards

- **Menu** — *print* for the wall/table, or share the **QR** so customers
  open it on their phone. Set the venue name and IVA % first (Menu → ☰).
- **Specs / Stock exports** — .xlsx and .csv for your accountant or a
  spreadsheet-minded manager. Owner-only (they contain costs).
- **Training cards** — print a spec deck from Specs: ingredients, method,
  glass, garnish — **never costs or prices**, safe to leave on the bar.
- **In-app Help** — Settings → Help: a short PT/EN FAQ for the floor,
  money-free by design.

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

## Settings page (⚙)

- **Owner PIN** — set on first run. 🔒 logs the session out. There is no
  "forgot PIN" e-mail: recovery means stopping the app and clearing the PIN
  in the database (ops job) — write the PIN down somewhere safe.
- **Staff PIN** — enable it so the team can look up recipes and the menu
  without seeing money. Costs, prices and margins are removed **at the API**
  (they never reach the staff browser), and every write returns 403.
- **Venue name + IVA %** — prints on the menu.
- **Language** — EN / PT-PT, per browser. Prices format correctly in both
  (€9.50 vs €9,50).
- **Text size** — A− / A / A+ for the screen on the bar; the whole layout
  scales, nothing is cut off.
- **Audit trail** — the last price edits and deletes, old → new, with a
  timestamp and the user. Append-only: nothing is ever rewritten.
- **Help** — the in-app FAQ (see above).

## Backups and restore

Nightly the app snapshots its single SQLite file (`barspec.db`) into
`backups/` (14 kept) with no downtime. Restoring is one command, listed in
the Developer Guide (`ops/restore.sh`). Because the whole venue lives in one
file, "backup" also means: copy that file to a USB stick before anything
scary. (Runs by the owner/ops, not in the UI.)

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

## Troubleshooting

- **"It looks old / a button does nothing after an update"** — the browser
  cached the old code. Hard-refresh (Ctrl+Shift+R / Cmd+Shift+R).
- **"A cost is €0.00"** — that ingredient's stock item has no price, or the
  spec line is free text. Open Stock, add the price; every recipe using it
  updates instantly.
- **"The order list is empty"** — you need a count first (or pars set).
  Count items only appear if they have a par level above 0.
- **"Shrinkage shows a big number"** — check three things in order: were both
  counts done at a similar time of day (before/after service)? Did you post
  the sales for the whole window? Was there a delivery you didn't record as
  a PO? If all three are clean, the leak is real — that's the point.
- **"Staff can't see prices"** — correct, by design. Staff mode has no money.
- **"Wrong language / prices look odd"** — Settings → language; formatting is
  per-browser, so each device remembers its own.
- **"I forgot the PIN"** — see Settings reference: it's an ops reset, not a
  UI flow.
- **"Numbers look stale"** — Summary refreshes on every visit; other views
  refresh when you open them. If in doubt, hard-refresh.

## Glossary

| Term | Meaning |
|---|---|
| **Par** | The stock level you want to keep on the shelf. The order list is par minus what you have. |
| **FBE** | *Full-bottle equivalent* — whole bottles + the fraction of an open one (¾ bottle = 0.75). |
| **Dead stock** | Items sitting in your list that no recipe uses — money asleep in the store. |
| **Shrinkage** | Stock used between two counts vs what your sales explain. The difference, in €, is your leak. |
| **GP / margin** | Gross profit: (price − cost) ÷ price. The chips go green ≥ your target, amber near, red below. |
| **ABV** | Alcohol by volume. BarSpec weights it across the spec (dilution included) so you see the serve you really pour. |
| **Dilution** | Ice melt added to a drink — raises volume, lowers ABV, doesn't change cost. |
| **Yield %** | Usable portion ÷ bought (trimming, cooking loss). 1 kg bought at 80% yield = 800 g usable. |
| **Batch** | A house-made preparation (syrup, infusion, mix) with its own recipe; specs can pour from it. |
| **PO** | Purchase order — what you're buying from a supplier, at prices frozen when you create it. |
| **Price drift** | The invoice price disagreeing with your stored price when you receive a PO. |

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
