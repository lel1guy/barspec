"""BarSpec — cocktail spec manager with scaling + cost/ABV.

Single-user local web app. SQLite via stdlib (no ORM — you can read every query).
Run:  uvicorn main:app --reload   then open http://127.0.0.1:8000
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db

app = FastAPI(title="BarSpec")

BASE_DIR = Path(__file__).resolve().parent
db.init_db()


# ---------- Pydantic models (validates what the browser sends) ----------

class SpecIn(BaseModel):
    name: str
    glass: str = ""
    method: str = ""          # "stirred", "shaken", "built"...
    garnish: str = ""

class IngredientIn(BaseModel):
    name: str
    amount_ml: float
    abv: float = 0.0          # 0-100. 0 = mixer (lime, syrup, soda)
    bottle_price_eur: float = 0.0
    bottle_volume_ml: float = 700.0  # default: 70cl bottle


# ---------- Pages ----------

@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


# ---------- Specs ----------

@app.get("/api/specs")
def list_specs():
    return db.get_specs()

@app.post("/api/specs")
def create_spec(spec: SpecIn):
    return db.create_spec(spec.model_dump())

@app.get("/api/specs/{spec_id}")
def get_spec(spec_id: int):
    s = db.get_spec(spec_id)
    if not s:
        raise HTTPException(404, "Spec not found")
    return s

@app.put("/api/specs/{spec_id}")
def update_spec(spec_id: int, spec: SpecIn):
    ok = db.update_spec(spec_id, spec.model_dump())
    if not ok:
        raise HTTPException(404, "Spec not found")
    return {"ok": True}

@app.delete("/api/specs/{spec_id}")
def delete_spec(spec_id: int):
    db.delete_spec(spec_id)
    return {"ok": True}


# ---------- Ingredients ----------

@app.post("/api/specs/{spec_id}/ingredients")
def add_ingredient(spec_id: int, ing: IngredientIn):
    return db.add_ingredient(spec_id, ing.model_dump())

@app.put("/api/ingredients/{ing_id}")
def update_ingredient(ing_id: int, ing: IngredientIn):
    ok = db.update_ingredient(ing_id, ing.model_dump())
    if not ok:
        raise HTTPException(404, "Ingredient not found")
    return {"ok": True}

@app.delete("/api/ingredients/{ing_id}")
def delete_ingredient(ing_id: int):
    db.delete_ingredient(ing_id)
    return {"ok": True}
