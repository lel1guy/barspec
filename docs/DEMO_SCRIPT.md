# BarSpec — demo script (10 minutes)

Setup once, then this is the same walk every time. The demo venue is
**The Prancing Pony** — a fictional bar with a kitchen — with a full month
of use already in it.

- URL: **http://192.168.1.77:8791** · owner PIN **1234**, staff PIN **2468**
- Reset it any time: `ops/demo_reset.sh` (fresh, deterministic month)
- Before a meeting: `GET /api/demo/status` → 7/7 checks (owner session)

---

## The three moments (in this order — they build)

### 1. The money view — "this is what the month actually did" (~2 min)
**Homepage** (first nav item).

> "This is the homepage: what needs you today. Below-par items with the
> supplier to call, batches expiring this week, the € that leaked this
> month, and how old the last count is. And down here — 30 days of revenue
> and the gross profit of every category."

Point at the two charts: **daily revenue** and **GP by category** (wine ~60%,
beer ~75%, coffee ~90%).

### 2. Where it leaks — "and here's the money that walked out" (~2 min)
**Vendas (Sales)** → the shrinkage window.

> "Two counts and the sales in between. Whatever the shelf used that the
> till can't explain shows up here — in euros, sometimes in stock and
> sometimes in money. That's the leak. Every bar has one; most owners only
> find out at the end of the year."

Then **Menu** → the dead-stock line ("€45 sitting in the store that no
recipe uses").

### 3. The buying loop — "and it catches the supplier, not you" (~3 min)
**📥 Orders** (header).

> "These are purchase orders. The price is frozen when you order. When the
> delivery arrives you receive it — line by line, because deliveries are
> always partial."

Type a smaller number on one line → **Receive**.
> "The order stays open with the rest outstanding."

Receive the rest. If the invoice price differs from what's stored:
> "It asks: stored €11, invoice €11.80 — apply? One click updates every
> recipe that uses it, and the audit log records old → new."

### Close (~1 min)
**⚙ Settings** → staff PIN:
> "Your team opens the same URL, logs in with this PIN, and sees recipes and
> the menu — with every price, cost and margin stripped at the server, not
> hidden in the browser. Sales are posted by the owner or manager."

Then: *"Thirty days, one venue, free. You keep counting yourself; I set it up
and call you once a week. At the end you tell me honestly if you'd pay for
it — and what it's worth to you."*

---

## Answers to the questions they always ask

| Question | Short answer |
|---|---|
| "Does it talk to my POS?" | Not needed today: counts + sales posting give the shrinkage number without an integration. Integration is a later phase. |
| "Where does the data live?" | One SQLite file on your machine, backed up nightly. No cloud, no monthly platform risk. |
| "Who can see prices?" | Owner PIN only. Staff mode is stripped server-side (never sent to the phone). |
| "What if my menu changes?" | Add the item in Specs, price it, print the menu — minutes. |
| "Can I use it for the kitchen too?" | Yes — yields, weight items and plate costs are in the same engine (see the Cozinha section). |
| "Price?" | (Pilot answer) "Setup is done by me for the pilot; after it, plans are €X/month or a one-off setup + support." — decide X before the meeting. |
