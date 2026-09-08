"""BarSpec — cocktail spec manager with scaling + cost/ABV + menu pricing.

Single-user local web app. SQLite via stdlib (no ORM — you can read every query).
Run:  uvicorn main:app --reload   then open http://127.0.0.1:8000
"""
from pathlib import Path
from typing import Literal
import csv
import io

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import db
import exporters
import pricing
app = FastAPI(title="BarSpec")

BASE_DIR = Path(__file__).resolve().parent
db.init_db()

# Static assets (style.css, app.js) — was missing: assets 404'd, app served unstyled.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---------- Pydantic models (validates what the browser sends) ----------

ALLERGEN_CODES = {"cel", "glu", "cru", "egg", "fis", "lup", "mil", "mol",
                  "mus", "nut", "pea", "ses", "soy", "sul"}
DIETARY_CODES = {"V", "VE", "GF"}


class SpecIn(BaseModel):
    name: str
    glass: str = ""
    method: str = ""
    garnish: str = ""
    category: str | None = None          # menu section (free-form, datalist)
    dilution_pct: float = 0.0            # ice melt: shaken ~20-25, stirred ~10-15
    allergens: str = ""                  # K3: comma codes from ALLERGEN_CODES
    dietary: str = ""                    # K3: comma codes from DIETARY_CODES
    price_eur: float | None = None
    target_gp: float = 70.0

    @field_validator("allergens")
    @classmethod
    def _chk_allergens(cls, v: str) -> str:
        bad = {c.strip() for c in v.split(",") if c.strip()} - ALLERGEN_CODES
        if bad:
            raise ValueError(f"Unknown allergen codes: {sorted(bad)}")
        return ",".join(c.strip() for c in v.split(",") if c.strip())

    @field_validator("dietary")
    @classmethod
    def _chk_dietary(cls, v: str) -> str:
        bad = {c.strip() for c in v.split(",") if c.strip()} - DIETARY_CODES
        if bad:
            raise ValueError(f"Unknown dietary codes: {sorted(bad)}")
        return ",".join(c.strip() for c in v.split(",") if c.strip())


class LineIn(BaseModel):
    name: str | None = None           # stock name; None when batch_id is used
    batch_id: int | None = None       # house batch reference (bottle OR batch)
    amount_ml: float = Field(gt=0)
    abv: float = 0.0                     # used only when creating a NEW stock item
    bottle_price_eur: float = 0.0
    bottle_volume_ml: float = 700.0
    unit: str = "ml"                     # ml|cl|l|oz|dash|barspoon|g|kg|piece|each


class LineUpdate(BaseModel):
    amount_ml: float = Field(gt=0)
    unit: str | None = None            # set to change a line's unit (ml -> cl etc)


class StockIn(BaseModel):
    name: str
    abv: float = 0.0
    bottle_price_eur: float = 0.0
    bottle_volume_ml: float = 700.0
    dimension: Literal["volume", "weight", "count"] = "volume"
    yield_frac: float = Field(1.0, gt=0, le=1.0)   # 005: usable/bought
    supplier: str = ""                       # K4: free-form, order-list grouping


class ParIn(BaseModel):
    """Par level for one bottle. None (or absent) clears it -> not counted."""
    par_level: float | None = None


class BatchIn(BaseModel):
    name: str
    method: str = ""
    batch_size_ml: float = 1000.0
    made_date: str | None = None
    shelf_life_days: int | None = None
    servings: int | None = Field(None, gt=0)   # kitchen: portions the batch makes


class BatchLineIn(BaseModel):
    name: str
    amount_ml: float = Field(gt=0)
    unit: str = "g"
    abv: float = 0.0
    cost_eur: float | None = None   # required when the name isn't in stock


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
    # exclude_unset: partial PUTs (menu price edits) must not wipe category
    if not db.update_spec(spec_id, spec.model_dump(exclude_unset=True)):
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
    try:
        ok = db.update_line(line_id, upd.amount_ml, upd.unit)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
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
    except ValueError as e:
        msg = str(e)
        # duplicate name vs validation error are different failures
        raise HTTPException(409 if msg == "Stock item already exists" else 400, msg)


@app.put("/api/stock/{stock_id}")
def update_stock(stock_id: int, item: StockIn):
    """Bottle price edited once. If the price moved, the response carries the
    ripple: every spec whose drink cost changed, old -> new. exclude_unset:
    the frontend edits one field at a time — dimension only moves when sent."""
    try:
        result = db.update_stock_item(
            stock_id, item.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(400, str(e))
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


# ---------- Batches (004: house-made syrups / infusions) ----------

@app.get("/api/batches")
def list_batches():
    """Every batch with its derived cost, per-ml, abv and expiry."""
    return db.get_batches()


@app.post("/api/batches")
def create_batch(batch: BatchIn):
    try:
        return db.create_batch(batch.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: int):
    b = db.get_batch(batch_id)
    if not b:
        raise HTTPException(404, "Batch not found")
    return b


@app.put("/api/batches/{batch_id}")
def update_batch(batch_id: int, batch: BatchIn):
    try:
        # exclude_unset: serving-only or size-only edits must not wipe the other
        b = db.update_batch(batch_id, batch.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not b:
        raise HTTPException(404, "Batch not found")
    return b


@app.delete("/api/batches/{batch_id}")
def delete_batch(batch_id: int):
    try:
        db.delete_batch(batch_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/batches/{batch_id}/lines")
def add_batch_line(batch_id: int, line: BatchLineIn):
    try:
        b = db.add_batch_line(batch_id, line.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not b:
        raise HTTPException(404, "Batch not found")
    return b


@app.delete("/api/batches/lines/{line_id}")
def delete_batch_line(line_id: int):
    if not db.delete_batch_line(line_id):
        raise HTTPException(404, "Batch line not found")
    return {"ok": True}


# ---------- Exports (010): owner-facing files + menu QR ----------

def _specs_full():
    return [db.get_spec(s["id"]) for s in db.get_specs()]


def _csv_bytes(header: list, rows: list) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _dl(resp, filename: str, media: str):
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@app.get("/api/export/specs.xlsx")
def export_specs_xlsx():
    buf = exporters.specs_workbook(_specs_full())
    return _dl(StreamingResponse(iter([buf.getvalue()]), media_type=
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
               "barspec-specs.xlsx", "")


@app.get("/api/export/stock.xlsx")
def export_stock_xlsx():
    buf = exporters.stock_workbook(db.get_stock_items())
    return _dl(StreamingResponse(iter([buf.getvalue()]), media_type=
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
               "barspec-stock.xlsx", "")


@app.get("/api/export/specs.csv")
def export_specs_csv():
    specs = _specs_full()
    rows = [[s["name"], s.get("category") or "", s.get("glass", ""),
             s.get("method", ""), s.get("garnish", ""),
             s["summary"].get("served_ml", s["summary"]["total_ml"]),
             s["summary"].get("served_abv", s["summary"]["abv"]),
             s["summary"]["cost_eur"], s.get("price_eur") or "",
             s["summary"]["margin"]] for s in specs]
    return _dl(Response(content=_csv_bytes(
        ["Name", "Category", "Glass", "Method", "Garnish", "Served ml",
         "ABV %", "Cost €", "Sell €", "Margin %"], rows),
        media_type="text/csv"), "barspec-specs.csv", "")


@app.get("/api/export/stock.csv")
def export_stock_csv():
    items = db.get_stock_items()
    unit = {"volume": "ml", "weight": "g", "count": "pc"}
    rows = [[i["name"], i.get("dimension", "volume"), i.get("abv", 0),
             i.get("bottle_price_eur"), i.get("bottle_volume_ml"),
             unit.get(i.get("dimension"), "ml"),
             round((i.get("yield_frac") or 1) * 100), i.get("par_level") or ""]
            for i in items]
    return _dl(Response(content=_csv_bytes(
        ["Item", "Kind", "ABV %", "Price €", "Size", "Unit", "Yield %", "Par"],
        rows), media_type="text/csv"), "barspec-stock.csv", "")


@app.get("/api/export/menu-qr.svg")
def export_menu_qr(url: str = Query(..., description="absolute menu URL")):
    return Response(content=exporters.menu_qr_svg(url),
                    media_type="image/svg+xml")


# ---------- Settings (008): venue profile ----------

class VenueIn(BaseModel):
    name: str = ""
    iva_pct: float | None = Field(None, ge=0, le=100)


@app.get("/api/settings")
def get_settings():
    return db.get_venue()


@app.put("/api/settings")
def put_settings(v: VenueIn):
    return db.save_venue(v.name.strip(), v.iva_pct)


# ---------- Adjustments (009 kitchen): loss log ----------

class AdjustIn(BaseModel):
    delta: float                              # signed, canonical units
    reason: str = "Other"
    note: str = ""


@app.post("/api/stock/{stock_id}/adjust")
def log_adjustment(stock_id: int, a: AdjustIn):
    try:
        return db.add_adjustment(stock_id, a.delta, a.reason, a.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/stock-adjustments")
def list_adjustments(limit: int = 25):
    return db.get_adjustments(limit=max(1, min(limit, 200)))


# ---------- Reports (K2): section P&L ----------

@app.get("/api/report/pnl")
def report_pnl():
    return db.report_pnl()


# ---------- S1: owner PIN gate + security headers ----------

import auth as authmod
from fastapi import Request
from fastapi.responses import JSONResponse


class PinIn(BaseModel):
    pin: str


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; frame-ancestors 'none'; "
        "connect-src 'self'"
    )
    return resp


@app.middleware("http")
async def pin_gate(request: Request, call_next):
    path = request.url.path
    public = (path.startswith("/static")
              or path.startswith("/api/auth/")
              or path in ("/", "/favicon.ico"))
    if public or not authmod.pin_is_set():
        return await call_next(request)
    if authmod.cookie_valid(request.cookies.get(authmod._COOKIE)):
        return await call_next(request)
    return JSONResponse({"detail": "PIN required"}, status_code=401)


@app.get("/api/auth/status")
def auth_status():
    return {"set": authmod.pin_is_set()}


@app.post("/api/auth/setup")
def auth_setup(pin: PinIn):
    if authmod.pin_is_set():
        raise HTTPException(409, "PIN already set")
    if len(pin.pin) < 4:
        raise HTTPException(400, "PIN must be at least 4 characters")
    db.set_setting_value(authmod.PIN_KEY, authmod.hash_pin(pin.pin))
    resp = JSONResponse({"ok": True})
    resp.headers.append("Set-Cookie", authmod.make_cookie())
    return resp


@app.post("/api/auth/login")
def auth_login(pin: PinIn):
    if not authmod.pin_is_set():
        raise HTTPException(409, "No PIN set yet")
    if not authmod.verify_pin(pin.pin, db.get_setting(authmod.PIN_KEY) or ""):
        raise HTTPException(401, "Wrong PIN")
    resp = JSONResponse({"ok": True})
    resp.headers.append("Set-Cookie", authmod.make_cookie())
    return resp


@app.post("/api/auth/logout")
def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.headers.append("Set-Cookie", authmod.clear_cookie())
    return resp


# ---------- Audit (S2): receipts book ----------

@app.get("/api/audit")
def audit_list(limit: int = 25):
    return db.get_audit(limit=max(1, min(limit, 200)))
