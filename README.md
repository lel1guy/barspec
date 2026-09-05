# BarSpec

Cocktail spec manager for bartenders. Store your recipes, then scale any
drink to N servings and see cost-per-drink and ABV instantly.

Built for Vitor, by lel1guy. Python + FastAPI + SQLite + vanilla JS.
No build step, no ORM — every query is visible in `db.py`.

## Run it

```bash
cd barspec
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

First run seeds 5 classic specs (Negroni, Margarita, Old Fashioned,
Espresso Martini, Aperol Spritz) with realistic bottle prices so the
cost math demos immediately.

## What it does

- Specs: name, glass, method, garnish. Add / edit / duplicate / delete.
- Ingredients: amount in ml, ABV %, bottle price (€), bottle size (ml).
- Servings slider: scales every amount and shows batch cost.
- Cost-per-drink = Σ (amount / bottle_size × bottle_price).
- ABV = volume-weighted average. Dilution from ice NOT included — real
  shaking adds ~20% water, so a stirred Negroni reads ~27% ABV before ice.

## API

| Method | Path | What |
|--------|------|------|
| GET | `/api/specs` | list |
| POST | `/api/specs` | create |
| GET | `/api/specs/{id}` | detail + ingredients + summary |
| PUT | `/api/specs/{id}` | update |
| DELETE | `/api/specs/{id}` | delete (cascades) |
| POST | `/api/specs/{id}/ingredients` | add ingredient |
| PUT | `/api/ingredients/{id}` | update ingredient |
| DELETE | `/api/ingredients/{id}` | delete ingredient |

## Roadmap (not started)

- oz / cl unit toggle
- dilution % per spec (shaken vs stirred)
- PDF menu + pricing sheet export (the money feature for bar owners)
- ingredient "stock" list shared across specs (bottle prices updated once)
