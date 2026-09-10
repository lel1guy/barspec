# Why BarSpec works this way

Short explanations for the design decisions that aren't obvious from the
code. Each entry: the decision, the reason, and what it costs us. These are
the answers to "why don't you just…" questions.

## 1. Cost is derived, never stored

**Decision.** Recipes store *amounts*, stock stores *prices and sizes*, and
`pricing.py` computes cost on every read (`cost_eur` is never a column on a
spec).

**Why.** A stored cost is a lie the moment a supplier changes a price. If
cost were stored, every old recipe would keep yesterday's purchase price and
the margin you see would be fiction. Deriving it means one price edit is
immediately and honestly reflected everywhere — which is also what makes the
price-ripple report possible (we can compute old vs new for every affected
recipe, including through batches).

**Cost.** More compute per read and a hard rule: no handler may write a cost
into a spec. Price and cost *snapshots* are stored in exactly two places
where history must be frozen (sales lines and PO lines) — deliberately, and
documented.

## Why only the owner/manager posts sales

Sales posting is the one place where a mistake (or a "helpful" adjustment)
moves real money numbers: revenue, GP and the shrinkage window all read from
it. Keeping it behind the owner PIN means the money lane has one pair of
hands, and the audit trail has one author. Staff get the recipes and the
menu — everything they need to serve — with costs and prices stripped at the
server.

**Cost:** the owner has to spend a few minutes a day (or a week) posting
sales. If a pilot venue says that's too much, the scoped fix is a
staff-sales-only role — still zero money visibility — not opening the
existing role wider.

## 2. Sales and purchase lines freeze their numbers

**Decision.** When you post a sales day, the spec's price and cost at that
moment are copied into `sales_lines`. When you open a PO, the unit price at
that moment is copied into `purchase_order_lines`.

**Why.** Actual GP must be *historical truth*, not today's arithmetic.
If margins were computed from live prices, raising a price today would
retroactively improve last month's GP — and the shrinkage report (usage vs
sales) would be meaningless. Freezing at posting time is the same rule an
invoice follows.

**Cost.** Two snapshot columns to keep in mind, and re-posting a day is the
honest way to fix a mistake (it replaces the day, never edits history in
place).

## 3. Purchase orders never move stock

**Decision.** Receiving a PO records the delivery, the invoice price and the
price history — but does not increase any on-hand quantity.

**Why.** BarSpec has no phantom "on-hand" column. Physical stock is owned by
**stock-takes**: you count, and the count is the truth. Inventing a second
source of quantity (received minus sold) guarantees a drift between the two,
and then neither is trustworthy. POs are the *money trail*; counts are the
*physical truth*; shrinkage is precisely the difference between them.

**Cost.** Receiving doesn't give you a running "bottles in the fridge"
number — by design. The order list works off the last count, which is the
number you actually verified with your own hands.

## 4. Suggested prices round **up** to €0.50

**Decision.** The suggested price for a target margin is rounded upward to
the next 50 cents, not to the nearest.

**Why.** Target margin is a floor, not a wish. Rounding to nearest would
sometimes land *below* the target (a 74.9% margin when you asked for 75%),
which erodes silently across a menu. Rounding up makes "never below your
target" an invariant — and it's tested.

**Cost.** Occasionally a drink is priced 20–30 cents above the mathematically
perfect margin. Owners keep the invariant; nobody has ever complained about
the extra 20 cents.

## 5. `amount_ml` stores the amount, the `unit` column stores the meaning

**Decision.** Every spec line stores its amount in a single column (legacy
name `amount_ml`) with a `unit` marker (`ml`, `cl`, `oz`, `g`, `kg`,
`piece`, `dash`). The unit engine converts to canonical (ml / g / pieces)
at the boundary.

**Why.** One column, one conversion point, no per-unit columns. Adding a
unit later is a lookup-table change, not a migration. The ugly column name
is a legacy tax we accepted rather than renaming data across 15 migrations
for cosmetics.

**Cost.** The name misleads readers exactly once (this paragraph), and
`pricing.py` must never be bypassed. Both are cheaper than the migration.

## 6. Staff mode strips money server-side

**Decision.** The staff role gets JSON with costs, prices and margins
*removed in the API layer* — not hidden with CSS.

**Why.** A staff screen that merely hides numbers is a screenshot away from
leaking your margins. Removing them at the boundary means the browser never
receives them: devtools shows nothing, and a shared tablet can't be poked
into revealing the bar's GP.

**Cost.** Two serializers (`_strip_money`) and every new money-bearing
endpoint must pass through them (there's a test for the shape).

## 7. One SQLite file, one process

**Decision.** No ORM, no external database, no message queue, no build step.

**Why.** A venue is one machine in one back office. A single file is a
backup strategy you can explain to a bar owner in one sentence ("copy this
file"), and SQLite's WAL mode handles the write volume of a restaurant
comfortably. Vanilla JS means the app runs from a Raspberry Pi with no
toolchain.

**Cost.** Multi-venue and multi-user concurrency are future problems this
design doesn't solve yet — they're deliberately gated on a real paying venue
(see the roadmap in the README).

---

*Disagree with one of these? Good — that's the point of writing them down.*
*Each entry names its cost so a future decision can be made with the
trade-off visible.*
