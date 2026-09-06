/* BarSpec frontend. Plain JS, no build step, no framework.
   Server (db.py/pricing.py) is the source of truth; these mirrors of the
   pricing math exist only for live slider preview. */

const $ = (s) => document.querySelector(s);
let currentSpec = null;      // open spec id
let servings = 1;
let stockMap = {};           // lower(name) -> stock item (for autocomplete + ripple)
let currentView = "specs";
// stock-take state (in-memory count grid; server is source of truth on save)
let takeRows = [];           // [{stock_item_id, name, par_level, bottle_price_eur, bottle_volume_ml, full_bottles, open_fraction}]
let takeDirty = false;       // unsaved edits -> confirm before leaving
let takeLast = null;         // review payload of the last saved/fetched snapshot
let takeTab = "count";

// ---------- tiny helpers ----------
async function api(url, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (!r.ok) {
    let msg = r.status;
    try { msg = (await r.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return r.status === 204 ? null : r.json();
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2600);
}
const esc = (x) => String(x ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const eur = (v) => "€" + (Math.round((v || 0) * 100) / 100).toFixed(2);

// ---------- display unit + units engine (S1 toggle + S3 pickers) ----------
// The server stores canonical amounts (ml for volume, g for weight, pieces for
// count); spec lines store amount-in-unit + unit. These helpers convert for
// display and entry only. Mirrors pricing.UNIT_CANONICAL/UNIT_DIMENSION.
let unit = localStorage.getItem("barspec.unit") || "ml";
const UNIT_ML = { ml: 1, cl: 10, oz: 29.5735 };      // canonical per display unit
const U_FACTOR = { ml: 1, cl: 10, l: 1000, oz: 29.5735, dash: 1, barspoon: 5,
                   g: 1, kg: 1000, piece: 1 };
const U_DIM = { ml: "volume", cl: "volume", l: "volume", oz: "volume",
                dash: "volume", barspoon: "volume", g: "weight", kg: "weight",
                piece: "count" };
const UNITS_FOR_DIM = { volume: ["ml", "cl", "oz", "dash", "barspoon"],
                        weight: ["g", "kg"], count: ["piece"] };
const dispAmt = (ml) => {                            // canonical ml -> display string
  const v = (ml || 0) / UNIT_ML[unit];
  return (Math.round(v * 100) / 100).toString();
};
const toMl = (v) => v * UNIT_ML[unit];               // display amount -> canonical ml
const unitLabel = () => unit;
const fmtAmt = (v) => (Math.round((v || 0) * 100) / 100).toString();  // raw trim
// Convert an amount between two units OF THE SAME DIMENSION (e.g. 30 ml -> 3 cl).
const convertUnit = (value, from, to) => value * U_FACTOR[from] / U_FACTOR[to];
const dimCanonical = (d) => d === "weight" ? "g" : d === "count" ? "piece" : "ml";
// A spec-line amount cell: ml/cl/oz follow the display toggle; fixed sub-units
// (dash, barspoon) and weight/count amounts show their own unit inline — a
// header can't cover a mixed-unit spec honestly.
const lineAmtHtml = (l) => {
  const u = l.unit || "ml";
  if (U_DIM[u] !== "volume" || u === "dash" || u === "barspoon") {
    return esc(fmtAmt(l.amount_ml)) + ' <span class="edit-note">' + esc(u) + "</span>";
  }
  return dispAmt((l.amount_ml || 0) * U_FACTOR[u]);
};
// Purchase summary for a stock item/line: "€22 / 70 cl" (volume follows the
// toggle) or "€18 / 1 kg" / "€3.60 / 12 pc" for the other dimensions.
const purchaseText = (it) => {
  if (!it || !it.bottle_price_eur) return "no price set";
  const dim = it.dimension || "volume";
  const size = dim === "volume"
    ? dispAmt(it.bottle_volume_ml) + " " + unitLabel()
    : fmtAmt(it.bottle_volume_ml) + " " + (dim === "weight" ? "g" : "pc");
  return eur(it.bottle_price_eur) + " / " + size;
};
function applyUnitLabels() {                         // static labels that carry a unit
  const th = document.getElementById("stockSizeTh");
  if (th) th.textContent = "Size";
  const lb = document.getElementById("stSizeLbl");
  if (lb) lb.textContent = "Size";
}
function setUnit(u) {
  unit = u;
  localStorage.setItem("barspec.unit", u);
  document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.unit === u));
  applyUnitLabels();
  if (currentView === "specs" && currentSpec) openSpec(currentSpec);
  else if (currentView === "specs") loadSpecs(false);
  else if (currentView === "stock") renderStock();
  else if (currentView === "stocktake") loadStocktake();
}

// JS mirrors of pricing.py (server stays authoritative).
const jsSuggested = (cost, gpPct) => cost > 0
  ? Math.ceil(cost / (1 - Math.min(gpPct, 99) / 100) * 2) / 2 : 0;
const jsMargin = (price, cost) => price > 0 ? (cost > 0 ? (price - cost) / price * 100 : 100) : 0;
const jsBand = (margin, gpPct) => margin <= 0 ? "unpriced"
  : margin >= gpPct ? "good" : margin >= gpPct - 10 ? "ok" : "low";

// ---------- views ----------
function applySearch() {
  const q = ($("#specSearch").value || "").trim().toLowerCase();
  document.querySelectorAll("#specList .spec-item").forEach((el) => {
    const name = (el.querySelector(".spec-name")?.textContent || "").toLowerCase();
    el.style.display = (!q || name.includes(q)) ? "" : "none";
  });
}
const VIEWS = {
  specs: { title: "Specs", crumb: "SPECS", header: true },
  stock: { title: "Stock", crumb: "STOCK", header: false },
  stocktake: { title: "Stock-take", crumb: "STOCK-TAKE", header: false },
  menu:  { title: "Menu",  crumb: "MENU",  header: false },
};
const NAV_IDS = { specs: "navSpecs", stock: "navStock", stocktake: "navTake", menu: "navMenu" };
function showView(v) {
  if (v !== currentView && currentView === "stocktake" && takeDirty &&
      !confirm("You have an unsaved count. Leave and lose it?")) return;
  currentView = v;
  Object.keys(VIEWS).forEach((x) => {
    $("#view-" + x).classList.toggle("active", x === v);
    $("#" + NAV_IDS[x]).classList.toggle("active", x === v);
  });
  const meta = VIEWS[v];
  $("#viewTitle").textContent = meta.title;
  $("#crumbLabel").textContent = "BARSPEC / " + meta.crumb;
  $("#newSpecBtn").classList.toggle("hidden", !meta.header);
  $("#searchBox").classList.toggle("hidden", !meta.header);
  if (v === "stock") renderStock();
  if (v === "stocktake") loadStocktake();
  if (v === "menu") renderMenu();
}

// ---------- spec list ----------
async function loadSpecs(keepOpen) {
  const specs = await api("/api/specs");
  $("#countSpecs").textContent = specs.length;
  const box = $("#specList");
  box.innerHTML = "";
  if (!specs.length) { box.innerHTML = '<div class="edit-note">No specs yet.</div>'; return; }
  for (const s of specs) {
    const el = document.createElement("div");
    el.className = "spec-item" + (s.id === currentSpec ? " active" : "");
    const meta = [s.method, s.price_eur ? eur(s.price_eur) : null].filter(Boolean).join(" · ");
    el.innerHTML = `<div>
        <div class="spec-name">${esc(s.name)}</div>
        <div class="spec-meta">${esc(meta || "—")}</div>
      </div>
      <button class="ghost small" data-del="${s.id}">✕</button>`;
    el.addEventListener("click", () => openSpec(s.id));
    el.querySelector("[data-del]").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Delete " + s.name + "?")) return;
      await api("/api/specs/" + s.id, "DELETE");
      if (currentSpec === s.id) { currentSpec = null; renderEmpty(); }
      loadSpecs();
    });
    box.appendChild(el);
  }
  if (keepOpen && currentSpec) openSpec(currentSpec);
  applySearch();
}
function renderEmpty() {
  if (!currentSpec) { $("#detail").classList.add("hidden"); $("#empty").classList.remove("hidden"); }
}

// ---------- spec detail ----------
async function openSpec(id) {
  currentSpec = id;
  const s = await api("/api/specs/" + id);
  $("#detail").classList.remove("hidden");
  $("#empty").classList.add("hidden");
  $("#detail").innerHTML = `
    <div class="spec-header">
      <div>
        <h2>${esc(s.name)}</h2>
        <div class="spec-facts">${esc(s.glass || "")}${s.garnish ? " · " + esc(s.garnish) : ""}</div>
      </div>
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button class="ghost small" id="editBtn">Edit</button>
        <button class="ghost small" id="ingBtn">Ingredients</button>
        <button class="ghost small" id="dupeBtn">Duplicate</button>
        <button class="danger small" id="delBtn">Delete</button>
      </div>
    </div>
    <div class="stat-strip">
      <div class="stat"><div class="num" id="statServe">—</div><div class="cap">cost / serve</div></div>
      <div class="stat"><div class="num" id="statBatch">—</div><div class="cap">batch (${servings})</div></div>
      <div class="stat"><div class="num" id="statAbv">—</div><div class="cap">ABV</div></div>
      <div class="stat"><div class="num" id="statVol">—</div><div class="cap">volume</div></div>
    </div>

    <div class="pricing-panel" id="pricingPanel"></div>

    <div style="display:flex; gap:10px; margin:12px 0 4px; flex-wrap:wrap; align-items:end;">
      <div style="flex:1; min-width:140px;">
        <label for="servings">Servings</label>
        <input type="number" id="servings" min="1" max="999" value="1">
      </div>
    </div>

    <table>
      <thead><tr><th>Ingredient</th><th class="num">${unitLabel()}</th><th class="num">ABV</th>
          <th class="num">Cost</th><th style="width:120px;">Share of cost</th><th></th></tr></thead>
      <tbody id="ingBody"></tbody>
    </table>
    <div class="edit-note">Bottle prices live in Stock — edit once, every spec updates. Ice dilution not included. Amounts show in ${unitLabel()} (ml stays canonical).</div>`;

  $("#servings").addEventListener("input", (e) => {
    servings = Math.max(1, parseInt(e.target.value) || 1);
    renderDetail(s);
  });
  $("#editBtn").addEventListener("click", () => editSpecForm(s));
  $("#ingBtn").addEventListener("click", () => editIngredientsForm(s));
  $("#delBtn").addEventListener("click", async () => {
    if (!confirm("Delete " + s.name + "?")) return;
    await api("/api/specs/" + s.id, "DELETE");
    currentSpec = null; renderEmpty(); loadSpecs();
  });
  $("#dupeBtn").addEventListener("click", async () => {
    const created = await api(`/api/specs/${s.id}/duplicate`, "POST");
    toast("Duplicated");
    loadSpecs();
    openSpec(created.id);
  });

  renderDetail(s);
  renderPricing(s);
  loadSpecs(false);
}

function renderDetail(s) {
  const sum = s.summary;
  $("#statServe").textContent = eur(sum.cost_eur);
  $("#statBatch").textContent = eur(sum.cost_eur * servings);
  $("#statAbv").textContent = sum.abv + "%";
  $("#statVol").textContent = dispAmt(sum.total_ml) + " " + unitLabel();

  const body = $("#ingBody");
  body.innerHTML = "";
  if (!s.lines.length) {
    body.innerHTML = '<tr><td colspan="6" class="edit-note">No ingredients yet — add some.</td></tr>';
    return;
  }
  for (const l of s.lines) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="ing-name">${esc(l.name)}</span>
          <div class="edit-note">${purchaseText(l)}</div></td>
      <td class="num">${lineAmtHtml(l)}</td>
      <td class="num">${l.abv ? l.abv + "%" : "—"}</td>
      <td class="num">${l.bottle_price_eur ? eur(l.row_cost_eur) : "—"}</td>
      <td><div class="costbar-wrap"><div class="costbar"><i style="width:${l.row_cost_pct}%"></i></div></div></td>
      <td class="num" style="font-size:14px;color:var(--muted);">${l.row_cost_pct}%</td>`;
    body.appendChild(tr);
  }
}

// ---------- pricing panel (the buying moment) ----------
function renderPricing(s) {
  const cost = s.summary.cost_eur;
  const box = $("#pricingPanel");
  const gp = s.summary.target_gp || 70;
  const price = s.price_eur || 0;
  const margin = jsMargin(price, cost);
  box.innerHTML = `
    <div class="row2">
      <div>
        <label>Target margin <span class="gp-val" id="gpVal">${gp}%</span></label>
        <input type="range" id="gpSlider" min="40" max="95" step="5" value="${gp}">
      </div>
      <div>
        <label>Suggested price</label>
        <div class="suggest" id="suggestVal">${cost > 0 ? eur(jsSuggested(cost, gp)) : "— set bottle prices first"}</div>
      </div>
      <div>
        <label>Sell price €</label>
        <div style="display:flex; gap:6px;">
          <input type="number" id="priceInput" min="0" step="0.5" placeholder="unpriced" value="${price || ""}">
          <button class="ghost small" id="useSuggest" ${cost > 0 ? "" : "disabled"}>use</button>
        </div>
      </div>
      <div>
        <label>Margin</label>
        <div><span class="margin-chip ${jsBand(margin, gp)}" id="marginChip">
          ${price > 0 ? Math.round(margin) + "%" : "no price"}</span></div>
      </div>
      <div style="flex:0;">
        <button id="savePrice" class="small">Save price</button>
      </div>
    </div>`;

  const update = () => {
    const g = parseInt($("#gpSlider").value);
    $("#gpVal").textContent = g + "%";
    if (cost > 0) $("#suggestVal").textContent = eur(jsSuggested(cost, g));
    const p = parseFloat($("#priceInput").value);
    const m = jsMargin(p || 0, cost);
    const chip = $("#marginChip");
    chip.className = "margin-chip " + jsBand(m, g);
    chip.textContent = p > 0 ? Math.round(m) + "%" : "no price";
  };
  $("#gpSlider").addEventListener("input", update);
  $("#priceInput").addEventListener("input", update);

  const persist = async (priceEur, gpPct) => {
    await api("/api/specs/" + s.id, "PUT", {
      name: s.name, glass: s.glass, method: s.method, garnish: s.garnish,
      price_eur: priceEur, target_gp: gpPct,
    });
    toast("Price saved");
    loadSpecs(false);
    openSpec(s.id);
  };
  $("#useSuggest").addEventListener("click", () => {
    const g = parseInt($("#gpSlider").value);
    $("#priceInput").value = jsSuggested(cost, g);
    persist(jsSuggested(cost, g), g);
  });
  $("#savePrice").addEventListener("click", () => {
    const g = parseInt($("#gpSlider").value);
    const v = parseFloat($("#priceInput").value);
    persist(isNaN(v) || v <= 0 ? null : v, g);
  });
}

// ---------- spec meta form ----------
function editSpecForm(s) {
  const d = $("#detail");
  d.innerHTML = `
    <h2 style="margin-top:0">${s ? "Edit" : "New"} spec</h2>
    <label>Name</label><input id="fName" value="${esc(s ? s.name : "")}" placeholder="Negroni">
    <label>Glass</label><input id="fGlass" value="${esc(s ? s.glass : "")}" placeholder="Rocks glass, big ice cube">
    <label>Method</label><input id="fMethod" value="${esc(s ? s.method : "")}" placeholder="Stirred">
    <label>Garnish</label><input id="fGarnish" value="${esc(s ? s.garnish : "")}" placeholder="Orange peel">
    <div style="display:flex; gap:8px; margin-top:16px;">
      <button id="saveSpec">Save</button>
      <button class="ghost" id="cancelEdit">Cancel</button>
    </div>`;
  $("#saveSpec").addEventListener("click", async () => {
    const data = {
      name: $("#fName").value.trim(),
      glass: $("#fGlass").value.trim(),
      method: $("#fMethod").value.trim(),
      garnish: $("#fGarnish").value.trim(),
      price_eur: s ? s.price_eur : null,
      target_gp: s ? (s.target_gp || 70) : 70,
    };
    if (!data.name) { toast("Name needed"); return; }
    if (s) { await api("/api/specs/" + s.id, "PUT", data); openSpec(s.id); }
    else {
      const created = await api("/api/specs", "POST", data);
      currentSpec = created.id;
      editIngredientsForm(created);
    }
    loadSpecs(false);
    toast("Saved");
  });
  if (s) $("#cancelEdit").addEventListener("click", () => openSpec(s.id));
}

// ---------- ingredient editor (stock-linked lines) ----------
function editIngredientsForm(s) {
  const d = $("#detail");
  const rows = s.lines.map((l) => ({ ...l }));
  d.innerHTML = `
    <h2 style="margin-top:0">Ingredients — ${esc(s.name)}</h2>
    <div class="edit-note">Bottles live in Stock. Type a known name and it links to the existing
      bottle; a new name creates one (set its price later in Stock).</div>
    <table>
      <thead><tr><th>Ingredient</th><th class="num">Amount</th><th class="num">Bottle</th><th></th></tr></thead>
      <tbody id="editBody"></tbody>
    </table>
    <div class="edit-note" id="newHint" style="margin-top:10px;">Amount is in the unit you pick per row — a Margarita lime is "1 piece", bitters are "2 dash". New bottles (weight/count stock) are created in Stock first.</div>
    <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:end; margin-top:6px;">
      <div style="flex:2; min-width:150px;"><label>Name</label>
        <input id="addName" list="stockNames" placeholder="Type or pick…"></div>
      <div style="flex:1; min-width:170px;"><label>Amount + unit</label>
        <div style="display:flex; gap:4px;">
          <input id="addMl" type="number" value="3" min="0" step="0.5" style="flex:1.4; min-width:80px;">
          <select id="addUnit" style="width:100px;"></select>
        </div>
      </div>
      <div id="advWrap" style="display:flex; gap:8px; flex-wrap:wrap;">
        <div style="width:70px;"><label>ABV %</label><input id="addAbv" type="number" value="0" min="0" max="100" step="0.5"></div>
        <div style="width:90px;"><label>Bottle €</label><input id="addPrice" type="number" value="0" min="0" step="0.1"></div>
        <div style="width:90px;"><label>Size ${unitLabel()}</label><input id="addVol" type="number" value="${dispAmt(700)}" min="0" step="1"></div>
      </div>
      <button id="addLine">+ Add</button>
    </div>
    <div style="display:flex; gap:8px; margin-top:16px;">
      <button id="saveIngs">Save changes</button>
      <button class="ghost" id="doneIng">Done</button>
    </div>`;

  const unitOptions = (dim) => UNITS_FOR_DIM[dim] || ["ml"];
  const renderRows = () => {
    const body = $("#editBody");
    body.innerHTML = "";
    rows.forEach((l, i) => {
      const tr = document.createElement("tr");
      const stock = stockMap[(l.name || "").toLowerCase()];
      const dim = stock ? stock.dimension : "volume";
      const opts = unitOptions(dim);
      // Stored unit must belong to this stock's dimension; else fall back to
      // the dimension's canonical unit (rename across dimensions = delete+add).
      if (!opts.includes(l.unit)) l.unit = dimCanonical(dim);
      const bottleTxt = stock && stock.bottle_price_eur
        ? purchaseText(stock)
        : (stock ? "no price yet" : "—");
      tr.innerHTML = `
        <td><input data-i="${i}" data-k="name" value="${esc(l.name)}" list="stockNames" placeholder="Ingredient"></td>
        <td class="num"><span class="amt-cell">
          <input class="num" type="number" data-i="${i}" data-k="amount_ml" value="${fmtAmt(l.amount_ml)}" min="0" step="0.5" style="width:80px; text-align:right;">
          <select data-i="${i}" data-ku="unit" class="unitmini">${opts.map((u) =>
            `<option value="${u}" ${u === l.unit ? "selected" : ""}>${u}</option>`).join("")}</select>
        </span></td>
        <td class="edit-note">${esc(bottleTxt)}</td>
        <td><button class="danger small" data-rm="${i}">✕</button></td>`;
      tr.querySelectorAll("input[data-k]").forEach((inp) => {
        inp.addEventListener("input", () => {
          const k = inp.dataset.k;
          if (k === "amount_ml") rows[+inp.dataset.i].amount_ml = parseFloat(inp.value) || 0;
          else rows[+inp.dataset.i][k] = inp.value.trim();
        });
      });
      tr.querySelectorAll("select[data-ku]").forEach((sel) => {
        sel.addEventListener("change", () => {
          const row = rows[+sel.dataset.i];
          const from = row.unit || dimCanonical(dim);
          const to = sel.value;
          const inp = tr.querySelector("input[data-k=amount_ml]");
          if (U_DIM[from] === U_DIM[to]) {            // same dimension: keep the amount
            const v = convertUnit(parseFloat(inp.value) || 0, from, to);
            inp.value = fmtAmt(v);
            row.amount_ml = v;
          } else {                                    // defensive: reset, user retypes
            inp.value = to === "g" ? 9 : to === "piece" ? 1 : 3;
            row.amount_ml = parseFloat(inp.value) || 0;
          }
          row.unit = to;
        });
      });
      tr.querySelector("[data-rm]").addEventListener("click", () => {
        const removed = rows.splice(+tr.querySelector("[data-rm]").dataset.rm, 1)[0];
        if (removed.id) api("/api/lines/" + removed.id, "DELETE").catch(() => {});
        renderRows();
      });
      body.appendChild(tr);
    });
  };
  renderRows();

  // Hide the advanced fields when the typed name is already in stock; drive the
  // add-line unit picker from the stock item's dimension (volume honours the
  // display toggle as the default entry unit).
  const onName = () => {
    const known = stockMap[($("#addName").value || "").trim().toLowerCase()];
    $("#advWrap").style.visibility = known ? "hidden" : "visible";
    const dim = known ? known.dimension : "volume";
    const sel = $("#addUnit");
    const want = dim === "volume" ? unit : dimCanonical(dim);
    const prevDim = sel.dataset.dim;
    sel.innerHTML = unitOptions(dim).map((u) =>
      `<option value="${u}" ${u === want ? "selected" : ""}>${u}</option>`).join("");
    sel.dataset.dim = dim;
    if (prevDim !== dim) {        // new dimension: reset to a sane starting amount
      $("#addMl").value = (want === "g" || want === "piece") ? 1
        : want === "kg" ? 1 : dispAmt(30);
    }
  };
  $("#addName").addEventListener("input", onName);
  onName();

  $("#addLine").addEventListener("click", () => {
    const name = $("#addName").value.trim();
    const amt = parseFloat($("#addMl").value) || 0;
    if (!name || !amt) { toast("Name + amount needed"); return; }
    const known = stockMap[name.toLowerCase()];
    const line = {
      name,
      amount_ml: amt,                          // amount in `unit`, not ml
      unit: $("#addUnit").value || "ml",
      abv: parseFloat($("#addAbv").value) || 0,
      bottle_price_eur: known ? 0 : parseFloat($("#addPrice").value) || 0,
      bottle_volume_ml: toMl(parseFloat($("#addVol").value) || 0) || 700,
    };
    rows.push(line);
    $("#addName").value = ""; $("#addAbv").value = 0;
    $("#addPrice").value = 0; $("#addVol").value = dispAmt(700);
    $("#addMl").value = "";
    renderRows(); onName();
  });

  const save = async (exit) => {
    const btn = $("#saveIngs"); if (btn) btn.disabled = true;
    try {
      for (const l of rows) {
        if (!l.name) continue;
        if (l.id) await api("/api/lines/" + l.id, "PUT",
                            { amount_ml: l.amount_ml, unit: l.unit || "ml" });
        else await api(`/api/specs/${s.id}/lines`, "POST", {
          name: l.name, amount_ml: l.amount_ml, unit: l.unit || "ml",
          abv: l.abv,
          bottle_price_eur: l.bottle_price_eur, bottle_volume_ml: l.bottle_volume_ml,
        });
      }
      toast("Saved");
      if (exit) openSpec(s.id); else openSpec(s.id);
    } catch (err) {
      toast("Save failed: " + err.message);
    }
  };
  $("#saveIngs").addEventListener("click", () => save(false));
  $("#doneIng").addEventListener("click", () => save(true));
}

// ---------- stock ----------
async function refreshStockMap() {
  const items = await api("/api/stock");
  stockMap = {};
  items.forEach((i) => {
    stockMap[i.name.toLowerCase()] = i;
  });
  $("#countStock").textContent = items.length;
  const dl = $("#stockNames");
  dl.innerHTML = "";
  items.forEach((i) => {
    const o = document.createElement("option");
    o.value = i.name; dl.appendChild(o);
  });
  return items;
}

async function renderStock() {
  const items = await refreshStockMap();
  applyUnitLabels();
  const body = $("#stockBody");
  body.innerHTML = "";
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="edit-note">No bottles yet.</td></tr>';
    return;
  }
  items.forEach((it) => {
    const tr = document.createElement("tr");
    tr.className = it.spec_count ? "" : "unused";
    const dim = it.dimension || "volume";
    const isVol = dim === "volume";
    const wKg = dim === "weight" && (it.bottle_volume_ml || 0) >= 1000;
    // Size cell: volume follows the display toggle (S1); weight gets a g/kg
    // picker; count is pieces. Entry converts to canonical on commit.
    const sizeCell = isVol
      ? `<input type="number" data-k="bottle_volume_ml" value="${dispAmt(it.bottle_volume_ml)}" min="0" step="1" style="width:90px;">`
      : dim === "weight"
        ? `<span class="size-ctl"><input type="number" data-k="bottle_volume_ml" value="${fmtAmt(it.bottle_volume_ml / (wKg ? 1000 : 1))}" min="0" step="0.1" style="width:70px;">
           <select class="unitmini" data-wunit><option value="g" ${wKg ? "" : "selected"}>g</option><option value="kg" ${wKg ? "selected" : ""}>kg</option></select></span>`
        : `<span class="size-ctl"><input type="number" data-k="bottle_volume_ml" value="${fmtAmt(it.bottle_volume_ml)}" min="0" step="1" style="width:70px;"><span class="edit-note">pc</span></span>`;
    const abvCell = isVol
      ? `<input type="number" data-k="abv" value="${it.abv}" min="0" max="100" step="0.5" style="width:80px;">`
      : `<span class="edit-note">—</span>`;
    tr.innerHTML = `
      <td><input data-k="name" value="${esc(it.name)}" ${dim === "volume" ? "" : `title="${dim}"`}></td>
      <td>${abvCell}</td>
      <td><input type="number" data-k="bottle_price_eur" value="${it.bottle_price_eur}" min="0" step="0.1" class="stock-price-input"></td>
      <td>${sizeCell}</td>
      <td><input type="number" data-par="${it.id}" value="${it.par_level ?? ""}" min="0" step="0.5"
                 placeholder="—" class="par-input" title="Par level — how many to keep on hand. Empty = not counted."></td>
      <td class="num"><span class="spec-badge" title="specs using this bottle">${it.spec_count}×</span></td>
      <td><button class="danger small" data-del="${it.id}" ${it.spec_count ? "disabled title='Used by specs'" : ""}>✕</button></td>`;
    const commit = async () => {
      const payload = { name: "", abv: 0, bottle_price_eur: 0, bottle_volume_ml: 700 };
      tr.querySelectorAll("input[data-k]").forEach((inp) => {
        const k = inp.dataset.k;
        payload[k] = inp.type === "number" ? (parseFloat(inp.value) || 0) : inp.value.trim();
      });
      const wsel = tr.querySelector("select[data-wunit]");
      if (wsel) {
        payload.bottle_volume_ml = payload.bottle_volume_ml * (wsel.value === "kg" ? 1000 : 1);
        payload.dimension = "weight";
      } else if (isVol) {
        payload.bottle_volume_ml = toMl(payload.bottle_volume_ml);
      } else {
        payload.dimension = "count";       // pieces stay canonical as typed
      }
      if (!payload.name) { toast("Name can't be empty"); renderStock(); return; }
      try {
        const res = await api("/api/stock/" + it.id, "PUT", payload);
        toast("Saved");
        if (res.impact && res.impact.length) showRipple(res.impact);
        if (currentSpec) openSpec(currentSpec);
        renderStock(); // refresh badges after renames
      } catch (err) { toast("Failed: " + err.message); }
    };
    tr.querySelectorAll("input").forEach((inp) => {
      if (inp.dataset.par !== undefined) return; // par commits via its own handler
      inp.addEventListener("change", commit);
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
    });
    const wsel = tr.querySelector("select[data-wunit]");
    if (wsel) {
      wsel.dataset.prev = wsel.value;
      wsel.addEventListener("change", () => {
        const inp = tr.querySelector("input[data-k=bottle_volume_ml]");
        const v = parseFloat(inp.value) || 0;
        const from = wsel.dataset.prev;
        inp.value = fmtAmt(from === "kg" && wsel.value === "g" ? v * 1000
          : from === "g" && wsel.value === "kg" ? v / 1000 : v);
        wsel.dataset.prev = wsel.value;
      });
    }
    const parInput = tr.querySelector("[data-par]");
    parInput.addEventListener("change", async () => {
      const raw = parInput.value.trim();
      const v = raw === "" ? null : parseFloat(raw);
      if (raw !== "" && (isNaN(v) || v <= 0)) { toast("Par must be a positive number — or empty to clear"); renderStock(); return; }
      try {
        await api(`/api/stock/${it.id}/par`, "PATCH", { par_level: v });
        toast(v ? `Par ${v} saved — counted in stock-take` : "Par cleared — not counted");
        renderStock();
      } catch (err) { toast("Failed: " + err.message); renderStock(); }
    });
    tr.querySelector("[data-del]").addEventListener("click", async () => {
      if (!confirm("Delete " + it.name + "? (only possible when no spec uses it)")) return;
      try { await api("/api/stock/" + it.id, "DELETE"); toast("Deleted"); renderStock(); }
      catch (err) { toast("Can't delete: " + err.message); }
    });
    body.appendChild(tr);
  });
}

function showRipple(impact) {
  const box = $("#stockRipple");
  const top = impact.slice(0, 5);
  box.innerHTML = `
    <strong>Price change affects ${impact.length} spec${impact.length === 1 ? "" : "s"}</strong>
    <button class="ghost small" id="rippleClose" style="float:right;">✕</button>
    <ul>${top.map((r) => `
      <li>${esc(r.name)}: <span class="delta-${r.cost_new >= r.cost_old ? "up" : "down"}">
        ${eur(r.cost_old)} → ${eur(r.cost_new)}</span> per serve</li>`).join("")}
    </ul>`;
  box.classList.remove("hidden");
  box.querySelector("#rippleClose").addEventListener("click", () => box.classList.add("hidden"));
}

$("#addStockBtn").addEventListener("click", () => {
  const show = $("#addStockForm").classList.toggle("hidden");
  if (!show) { syncStockDimForm(); $("#stName").focus(); }
});
$("#cancelStock").addEventListener("click", () => $("#addStockForm").classList.add("hidden"));

// Dimension picker drives which units + defaults the size field offers.
function syncStockDimForm() {
  const dim = $("#stDim").value;
  const abvW = $("#abvWrap");
  if (abvW) abvW.style.display = dim === "volume" ? "" : "none";
  const u = $("#stVolUnit");
  u.innerHTML = dim === "volume"
    ? '<option value="ml">ml</option><option value="l">l</option>'
    : dim === "weight"
      ? '<option value="g">g</option><option value="kg" selected>kg</option>'
      : '<option value="piece" selected>pc</option>';
  const sv = $("#stVol");
  sv.dataset.prev = u.value;
  // Default size per dimension; always reset on change so switching kind can
  // never carry a stale volume (700) into a weight/count item.
  sv.value = dim === "weight" ? 1 : dim === "count" ? 12 : 700;
}
$("#stDim").addEventListener("change", syncStockDimForm);
$("#stVolUnit").addEventListener("change", () => {
  const sv = $("#stVol");
  const from = sv.dataset.prev || "ml";
  const to = $("#stVolUnit").value;
  sv.value = fmtAmt(convertUnit(parseFloat(sv.value) || 0, from, to));
  sv.dataset.prev = to;
});

$("#saveStock").addEventListener("click", async () => {
  const name = $("#stName").value.trim();
  if (!name) { toast("Name needed"); return; }
  const dim = $("#stDim").value;
  const unit = $("#stVolUnit").value;
  const canonical = (parseFloat($("#stVol").value) || 0) * U_FACTOR[unit];
  if (!canonical) { toast("Size needed"); return; }
  try {
    await api("/api/stock", "POST", {
      name,
      abv: dim === "volume" ? (parseFloat($("#stAbv").value) || 0) : 0,
      bottle_price_eur: parseFloat($("#stPrice").value) || 0,
      bottle_volume_ml: canonical,
      dimension: dim,
    });
    toast("Item added");
    $("#stName").value = ""; $("#stAbv").value = 0; $("#stPrice").value = 0;
    $("#stVol").value = dim === "weight" ? 1 : dim === "count" ? 12 : 700;
    $("#addStockForm").classList.add("hidden");
    renderStock();
  } catch (err) { toast("Failed: " + err.message); }
});

// ---------- stock-take (count grid + order list + trends) ----------

const FRAC_OPTS = [[0, "—"], [0.25, "¼"], [0.5, "½"], [0.75, "¾"], [1, "full"]];
const fmtFbe = (v) => (Math.round(v * 100) / 100).toString();

function takeBadge() {
  const n = Object.values(stockMap).filter((i) => i.par_level).length;
  $("#countTake").textContent = n;
}

function setTakeTab(tab) {
  takeTab = tab;
  ["Count", "Order", "Trends"].forEach((label) => {
    const id = "tab" + label.replace(" ", "");
    $("#" + id).classList.toggle("active", tab === label.toLowerCase());
  });
  $("#countPanel").classList.toggle("hidden", tab !== "count");
  $("#orderPanel").classList.toggle("hidden", tab !== "order");
  $("#trendsPanel").classList.toggle("hidden", tab !== "trends");
}

async function loadStocktake() {
  const sheet = await api("/api/stock-takes/sheet");
  takeRows = sheet.rows.map((r) => ({
    stock_item_id: r.id, name: r.name, par_level: r.par_level,
    bottle_price_eur: r.bottle_price_eur, bottle_volume_ml: r.bottle_volume_ml,
    full_bottles: r.last_full_bottles ?? 0,
    open_fraction: r.last_open_fraction ?? 0,
  }));
  takeDirty = false;
  setTakeTab("count");
  renderCount();
  takeBadge();
}

function rowFbe(row) {
  return row.full_bottles + row.open_fraction;
}

function renderCount() {
  const box = $("#countBody");
  if (!takeRows.length) {
    box.innerHTML = `
      <div class="empty-note">
        <p><strong>No bottles have a par level yet.</strong></p>
        <p class="edit-note">A stock-take counts the bottles you set a target ("par") for.
        Set pars in Stock — one number per bottle you actually order. Everything with a par
        shows up here automatically.</p>
        <button class="btn" id="goStockBtn">Set par levels in Stock →</button>
      </div>`;
    $("#goStockBtn").addEventListener("click", () => showView("stock"));
    $("#saveTakeBtn").disabled = true;
    $("#countTotals").textContent = "";
    return;
  }
  $("#saveTakeBtn").disabled = false;
  const table = document.createElement("table");
  table.className = "take-table";
  table.innerHTML = `
    <thead><tr><th>Bottle</th><th class="num">Par</th><th class="num">Full</th>
      <th class="num">Open</th><th class="num">FBE</th></tr></thead>
    <tbody id="countBodyRows"></tbody>`;
  box.innerHTML = "";
  box.appendChild(table);
  const tbody = $("#countBodyRows");

  const updateTotals = () => {
    const totalFbe = takeRows.reduce((a, r) => a + rowFbe(r), 0);
    $("#countTotals").textContent = `${takeRows.length} bottles · ${fmtFbe(totalFbe)} FBE`;
  };

  takeRows.forEach((row, i) => {
    const tr = document.createElement("tr");
    const parChange = async (inp) => {
      const raw = inp.value.trim();
      const v = raw === "" ? null : parseFloat(raw);
      if (raw !== "" && (isNaN(v) || v <= 0)) { toast("Par: positive number, or empty to clear"); return; }
      try {
        await api(`/api/stock/${row.stock_item_id}/par`, "PATCH", { par_level: v });
        row.par_level = v;
        if (v === null) {
          takeRows.splice(i, 1);       // no par = drops off the count
          toast("Par cleared — removed from the count");
          renderCount();
        } else {
          toast(`Par ${v} set`);
        }
        takeBadge();
      } catch (err) { toast("Failed: " + err.message); }
    };
    tr.innerHTML = `
      <td><span class="ing-name">${esc(row.name)}</span>
          <div class="edit-note">${purchaseText(row)}</div></td>
      <td class="num"><input type="number" class="par-input take-par" value="${row.par_level ?? ""}"
          min="0" step="0.5" title="Par — bottles to keep on hand. Empty removes from the count."></td>
      <td class="num take-full">
        <button class="step" data-step="-1">−</button>
        <input type="number" class="full-input" value="${row.full_bottles}" min="0" max="999">
        <button class="step" data-step="1">+</button>
      </td>
      <td class="num">
        <select class="frac-select">${FRAC_OPTS.map(([v, lab]) =>
          `<option value="${v}" ${row.open_fraction === v ? "selected" : ""}>${lab}</option>`).join("")}</select>
      </td>
      <td class="num fbe-cell">${fmtFbe(rowFbe(row))}</td>`;
    const dirty = () => { takeDirty = true; };
    tr.querySelector("input.take-par").addEventListener("change", (e) => parChange(e.target));
    const fullInput = tr.querySelector("input.full-input");
    const syncFull = () => {
      let v = Math.max(0, Math.min(999, parseInt(fullInput.value) || 0));
      fullInput.value = v;
      row.full_bottles = v;
      tr.querySelector(".fbe-cell").textContent = fmtFbe(rowFbe(row));
      dirty(); updateTotals();
    };
    fullInput.addEventListener("change", syncFull);
    fullInput.addEventListener("keydown", (e) => { if (e.key === "Enter") fullInput.blur(); });
    tr.querySelectorAll("button.step").forEach((b) => {
      b.addEventListener("click", () => {
        const delta = parseInt(b.dataset.step);
        row.full_bottles = Math.max(0, Math.min(999, row.full_bottles + delta));
        fullInput.value = row.full_bottles;
        tr.querySelector(".fbe-cell").textContent = fmtFbe(rowFbe(row));
        dirty(); updateTotals();
      });
    });
    tr.querySelector("select.frac-select").addEventListener("change", (e) => {
      row.open_fraction = parseFloat(e.target.value);
      tr.querySelector(".fbe-cell").textContent = fmtFbe(rowFbe(row));
      dirty(); updateTotals();
    });
    tbody.appendChild(tr);
  });
  updateTotals();
}

async function saveTake() {
  if (!takeRows.length) { toast("Nothing to save"); return; }
  const lines = takeRows.map((r) => ({
    stock_item_id: r.stock_item_id,
    full_bottles: r.full_bottles,
    open_fraction: r.open_fraction,
  }));
  const btn = $("#saveTakeBtn");
  btn.disabled = true;
  try {
    takeLast = await api("/api/stock-takes", "POST", { lines });
    takeDirty = false;
    toast(`Count saved — ${takeLast.counted} bottles`);
    renderOrder(takeLast);
    setTakeTab("order");
    takeBadge();
  } catch (err) {
    toast("Save failed: " + err.message);
    btn.disabled = false;
  }
}

async function loadLastOrder() {
  try {
    takeLast = await api("/api/stock-takes/last");
    renderOrder(takeLast);
  } catch (err) {
    renderOrder(null);
  }
}

function renderOrder(payload) {
  const box = $("#orderBody");
  box.innerHTML = "";
  if (!payload) {
    box.innerHTML = '<div class="empty-note"><p><strong>No count saved yet.</strong></p>' +
      '<p class="edit-note">Save a count and your order list appears here: what to buy to reach par, ' +
      "and how much cash is sitting over it.</p></div>";
    return;
  }
  const when = payload.take.taken_at.replace("T", " ").slice(0, 16);
  $("#orderHint").textContent = `From your latest count (${when} UTC).`;
  const stats = document.createElement("div");
  stats.className = "stat-strip";
  stats.innerHTML = `
    <div class="stat"><div class="num">${payload.order_total}</div><div class="cap">to order</div></div>
    <div class="stat ${payload.cash_asleep_total > 0 ? "warn" : "good"}"><div class="num">${eur(payload.cash_asleep_total)}</div><div class="cap">cash asleep</div></div>
    <div class="stat"><div class="num">${payload.counted}</div><div class="cap">bottles counted</div></div>`;
  box.appendChild(stats);

  const short = payload.short || [];
  const over = payload.over || [];
  const atPar = payload.at_par || [];

  const section = (title, rows, rowHtml, emptyMsg) => {
    const wrap = document.createElement("div");
    wrap.className = "order-section";
    const h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    if (!rows.length) {
      const e = document.createElement("p");
      e.className = "edit-note";
      e.textContent = emptyMsg;
      wrap.appendChild(e);
      return wrap;
    }
    const t = document.createElement("table");
    t.innerHTML = rowHtml(rows);
    wrap.appendChild(t);
    return wrap;
  };

  box.appendChild(section("To order", short,
    (rows) => `<thead><tr><th>Bottle</th><th class="num">Par</th><th class="num">Have</th><th class="num">Order</th></tr></thead>
      <tbody>${rows.map((r) => `<tr>
        <td>${esc(r.name)}</td>
        <td class="num">${fmtFbe(r.par_level)}</td>
        <td class="num">${fmtFbe(r.fbe)}</td>
        <td class="num"><span class="order-chip">+${r.to_order}</span></td></tr>`).join("")}</tbody>`,
    "Nothing to order — you're at or above par everywhere. Nice."));

  box.appendChild(section("Over par — cash asleep", over,
    (rows) => `<thead><tr><th>Bottle</th><th class="num">Par</th><th class="num">Have</th><th class="num">Over</th><th class="num">€ tied up</th></tr></thead>
      <tbody>${rows.map((r) => `<tr>
        <td>${esc(r.name)}</td>
        <td class="num">${fmtFbe(r.par_level)}</td>
        <td class="num">${fmtFbe(r.fbe)}</td>
        <td class="num">${fmtFbe(r.excess_fbe)}</td>
        <td class="num over-amt">${eur(r.cash_asleep_eur)}</td></tr>`).join("")}</tbody>`,
    "Nothing over par."));

  if (atPar.length) {
    const note = document.createElement("p");
    note.className = "edit-note";
    note.textContent = `${atPar.length} bottle${atPar.length === 1 ? "" : "s"} exactly at par.`;
    box.appendChild(note);
  }
}

async function renderTrends() {
  const box = $("#trendsBody");
  box.innerHTML = "";
  const t = await api("/api/stock-takes/trends");
  if (t.takes_count < 2) {
    box.innerHTML = `
      <div class="empty-note">
        <p><strong>${t.takes_count === 0 ? "No snapshots yet." : "One snapshot saved — one more and movement appears."}</strong></p>
        <p class="edit-note">Trends need history: save a second count and this shows per-bottle movement between
        the two — what moved, what didn't, and in €.</p>
        <button class="btn" id="trendsGoCount">Start a count →</button>
      </div>`;
    $("#trendsGoCount").addEventListener("click", () => { loadStocktake(); setTakeTab("count"); });
  } else {
    const movement = t.movement || [];
    const states = { used: "used", unmoved: "unmoved", gained: "gained", first_count: "first count", not_counted: "not counted" };
    const tbl = document.createElement("table");
    tbl.innerHTML = `
      <thead><tr><th>Bottle</th><th class="num">Before</th><th class="num">Now</th>
        <th class="num">Used</th><th class="num">${unitLabel()}</th><th class="num">€</th><th>State</th></tr></thead>
      <tbody>${movement.map((m) => `
        <tr class="trend-${m.state}">
          <td>${esc(m.name)}</td>
          <td class="num">${m.prev_fbe === null ? "—" : fmtFbe(m.prev_fbe)}</td>
          <td class="num">${m.fbe === null ? "—" : fmtFbe(m.fbe)}</td>
          <td class="num">${m.used_fbe === null ? "—" : fmtFbe(m.used_fbe)}</td>
          <td class="num">${m.used_ml === null ? "—" : dispAmt(m.used_ml)}</td>
          <td class="num">${m.used_eur === null ? "—" : eur(m.used_eur)}</td>
          <td><span class="margin-chip ${m.state === "used" ? "good" : m.state === "unmoved" ? "unpriced" : m.state === "gained" ? "low" : "ok"}">${states[m.state] || m.state}</span></td>
        </tr>`).join("")}</tbody>`;
    box.appendChild(tbl);
    const note = document.createElement("p");
    note.className = "edit-note";
    note.textContent = "Between your last two counts. Deliveries between counts show as little or no movement — counts are still your fastest signal.";
    box.appendChild(note);
  }
  const dead = t.dead_stock || [];
  if (dead.length) {
    const wrap = document.createElement("div");
    wrap.className = "order-section";
    const h = document.createElement("h3");
    h.textContent = "Dead stock — in the list, in no spec";
    wrap.appendChild(h);
    const tbl = document.createElement("table");
    tbl.innerHTML = `<thead><tr><th>Bottle</th><th class="num">Price €</th><th class="num">Size ml</th><th class="num">Par</th></tr></thead>
      <tbody>${dead.map((d) => `<tr>
        <td>${esc(d.name)}</td>
        <td class="num">${d.bottle_price_eur ? eur(d.bottle_price_eur) : "—"}</td>
        <td class="num">${Math.round(d.bottle_volume_ml)}</td>
        <td class="num">${d.par_level ? fmtFbe(d.par_level) : "—"}</td></tr>`).join("")}</tbody>`;
    wrap.appendChild(tbl);
    const note = document.createElement("p");
    note.className = "edit-note";
    note.textContent = "Bottles no spec uses — either build a spec for them or stop buying them. Dead money on the shelf.";
    wrap.appendChild(note);
    box.appendChild(wrap);
  }
}
async function renderMenu() {
  const items = await api("/api/menu");
  const onlyPriced = $("#pricedOnly").checked;
  const body = $("#menuBody");
  body.innerHTML = "";
  $("#menuEmpty").classList.toggle("hidden", items.length > 0);
  const list = onlyPriced ? items.filter((m) => m.priced) : items;
  if (!list.length) {
    body.innerHTML = '<div class="edit-note">' +
      (items.length ? "Nothing priced yet — set prices in a spec or right here." : "No specs yet.") + "</div>";
    return;
  }
  for (const m of list) {
    const row = document.createElement("div");
    row.className = "menu-row" + (m.priced ? "" : " unpriced");
    const band = jsBand(m.price_eur ? m.margin : 0, m.target_gp || 70);
    row.innerHTML = `
      <div>
        <div class="m-name">${esc(m.name)}</div>
        <div class="m-meta">${esc([m.glass, m.method, m.garnish].filter(Boolean).join(" · ") || "")}</div>
      </div>
      <input type="number" class="m-price" data-id="${m.id}" min="0" step="0.5"
             value="${m.price_eur || ""}" placeholder="—">
      <span class="m-cost">cost ${eur(m.cost_eur)}</span>
      <span class="margin-chip ${band} no-print">${m.priced ? Math.round(m.margin) + "%" : "no price"}</span>`;
    row.querySelector(".m-price").addEventListener("change", async (e) => {
      const v = parseFloat(e.target.value);
      try {
        await api("/api/specs/" + m.id, "PUT", {
          name: m.name, glass: m.glass, method: m.method, garnish: m.garnish,
          price_eur: isNaN(v) || v <= 0 ? null : v, target_gp: m.target_gp || 70,
        });
        toast("Saved");
        renderMenu();
        if (currentSpec) openSpec(currentSpec);
      } catch (err) { toast("Failed: " + err.message); renderMenu(); }
    });
    body.appendChild(row);
  }
}

// ---------- wiring ----------
$("#newSpecBtn").addEventListener("click", () => { editSpecForm(null); });
$("#navSpecs").addEventListener("click", () => showView("specs"));
$("#navStock").addEventListener("click", () => showView("stock"));
$("#navTake").addEventListener("click", () => showView("stocktake"));
$("#navMenu").addEventListener("click", () => showView("menu"));
$("#printMenuBtn").addEventListener("click", () => window.print());
$("#pricedOnly").addEventListener("change", renderMenu);
$("#specSearch").addEventListener("input", applySearch);
$("#tabCount").addEventListener("click", () => setTakeTab("count"));
$("#tabOrder").addEventListener("click", () => { setTakeTab("order"); loadLastOrder(); });
$("#tabTrends").addEventListener("click", () => { setTakeTab("trends"); renderTrends(); });
$("#saveTakeBtn").addEventListener("click", saveTake);
$("#newCountBtn").addEventListener("click", () => { loadStocktake(); setTakeTab("count"); });
document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
  b.addEventListener("click", () => setUnit(b.dataset.unit)));
window.addEventListener("beforeunload", (e) => {
  if (!takeDirty) return;
  e.preventDefault();
  e.returnValue = "";
});

window.addEventListener("load", async () => {
  document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.unit === unit));
  applyUnitLabels();
  await refreshStockMap();
  takeBadge();
  loadSpecs(false);
  try {
    const m = await api("/api/menu");
    $("#countMenu").textContent = m.length;
  } catch (_) {}
});
