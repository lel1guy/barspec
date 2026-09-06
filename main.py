"""BarSpec — cocktail spec manager with scaling + cost/ABV + menu pricing.

Single-user local web app. SQLite via stdlib (no ORM — you can read every query).
Run:  uvicorn main:app --reload   then open http://127.0.0.1:8000
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db

app = FastAPI(title="BarSpec")

BASE_DIR = Path(__file__).resolve().parent
db.init_db()

# Static assets (style.css, app.js) — was missing: assets 404'd, app served unstyled.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---------- Pydantic models (validates what the browser sends) ----------

class SpecIn(BaseModel):
    name: str
    glass: str = ""
    method: str = ""
    garnish: str = ""
    price_eur: float | None = None       # accepted sell price (menu)
    target_gp: float = 70                # target gross-profit % for pricing


class LineIn(BaseModel):
    name: str
    amount_ml: float = Field(gt=0)
    abv: float = 0.0                     # used only when creating a NEW stock item
    bottle_price_eur: float = 0.0
    bottle_volume_ml: float = 700.0
    unit: str = "ml"                     # ml|cl|l|oz|dash|barspoon|g|kg|piece|each


class LineUpdate(BaseModel):
    amount_ml: float = Field(gt=0)


class StockIn(BaseModel):
    name: str
    abv: float = 0.0
    bottle_price_eur: float = 0.0
    bottle_volume_ml: float = 700.0
    dimension: str = "volume"            # volume (ml) | weight (g) | count (piece)


class ParIn(BaseModel):
    """Par level for one bottle. None (or absent) clears it -> not counted."""
    par_level: float | None = None


class TakeLineIn(BaseModel):
    stock_item_id: int
    full_bottles: int = Field(0, ge=0)
    open_fraction: float = Field(0, ge=0, le=1)


class StockTakeIn(BaseModel):
    lines: list[TakeLineIn]


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
    if not db.update_spec(spec_id, spec.model_dump()):
        raise HTTPException(404, "Spec not found")
    return {"ok": True}


@app.delete("/api/specs/{spec_id}")
def delete_spec(spec_id: int):
    db.delete_spec(spec_id)
    return {"ok": True}


@app.post("/api/specs/{spec_id}/duplicate")
def duplicate_spec(spec_id: int):
    s = db.duplicate_spec(spec_id)
    if not s:
        raise HTTPException(404, "Spec not found")
    return s


# ---------- Spec lines ----------

@app.post("/api/specs/{spec_id}/lines")
def add_line(spec_id: int, line: LineIn):
    """Add an ingredient to a spec. Name resolves against stock; unknown names
    create the stock item (bottle) automatically. Unit must match the stock
    item's dimension."""
    try:
        s = db.add_line(spec_id, line.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not s:
        raise HTTPException(404, "Spec not found")
    return s


@app.put("/api/lines/{line_id}")
def update_line(line_id: int, upd: LineUpdate):
    if not db.update_line(line_id, upd.amount_ml):
        raise HTTPException(404, "Line not found")
    return {"ok": True}


@app.delete("/api/lines/{line_id}")
def delete_line(line_id: int):
    if not db.delete_line(line_id):
        raise HTTPException(404, "Line not found")
    return {"ok": True}


# ---------- Stock (the shared bottle list) ----------

@app.get("/api/stock")
def list_stock():
    return db.get_stock_items()


@app.post("/api/stock")
def create_stock(item: StockIn):
    try:
        return db.create_stock_item(item.model_dump())
    except ValueError:
        raise HTTPException(409, "Stock item already exists")


@app.put("/api/stock/{stock_id}")
def update_stock(stock_id: int, item: StockIn):
    """Bottle price edited once. If the price moved, the response carries the
    ripple: every spec whose drink cost changed, old -> new."""
    result = db.update_stock_item(stock_id, item.model_dump())
    if result is None:
        raise HTTPException(404, "Stock item not found")
    return {"ok": True, "impact": result["impact"]}


@app.delete("/api/stock/{stock_id}")
def delete_stock(stock_id: int):
    state = db.delete_stock_item(stock_id)
    if state == "in-use":
        raise HTTPException(409, "Bottle is used by specs — remove it from them first")
    return {"ok": True}


# ---------- Menu (printable pricing view) ----------

@app.get("/api/menu")
def menu():
    return db.get_menu()


# ---------- Stock-take (par levels + snapshots) ----------

@app.patch("/api/stock/{stock_id}/par")
def set_par(stock_id: int, par: ParIn):
    """Set (or clear) a bottle's par level. Par <= 0 or null = not counted."""
    try:
        ok = db.set_stock_par(stock_id, par.par_level)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "Stock item not found")
    return {"ok": True}


@app.get("/api/stock-takes/sheet")
def take_sheet():
    """The count list: bottles with a par, prefilled from the last snapshot."""
    return db.get_take_sheet()


@app.post("/api/stock-takes")
def save_take(take: StockTakeIn):
    """Persist one snapshot. Returns the order-list review for the UI."""
    try:
        return db.save_stock_take([ln.model_dump() for ln in take.lines])
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/stock-takes/last")
def last_take():
    """The most recent snapshot's order-list review (Order tab after reload)."""
    payload = db.get_last_stock_take()
    if payload is None:
        raise HTTPException(404, "No stock-take saved yet")
    return payload


@app.get("/api/stock-takes/trends")
def stock_trends():
    """Movement between the last two snapshots + dead-stock list."""
    return db.get_stock_trends()
