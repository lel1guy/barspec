/* BarSpec frontend. Plain JS, no build step, no framework.
   Server (db.py/pricing.py) is the source of truth; these mirrors of the
   pricing math exist only for live slider preview. */

const $ = (s) => document.querySelector(s);
let currentSpec = null;      // open spec id
let servings = 1;
let stockMap = {};           // lower(name) -> stock item (for autocomplete + ripple)
let currentView = "specs";

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
  menu:  { title: "Menu",  crumb: "MENU",  header: false },
};
function showView(v) {
  currentView = v;
  ["specs", "stock", "menu"].forEach((x) => {
    $("#view-" + x).classList.toggle("active", x === v);
    $("#nav" + x[0].toUpperCase() + x.slice(1)).classList.toggle("active", x === v);
  });
  const meta = VIEWS[v];
  $("#viewTitle").textContent = meta.title;
  $("#crumbLabel").textContent = "BARSPEC / " + meta.crumb;
  $("#newSpecBtn").classList.toggle("hidden", !meta.header);
  $("#searchBox").classList.toggle("hidden", !meta.header);
  if (v === "stock") renderStock();
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
      <thead><tr><th>Ingredient</th><th class="num">ml</th><th class="num">ABV</th>
          <th class="num">Cost</th><th style="width:120px;">Share of cost</th><th></th></tr></thead>
      <tbody id="ingBody"></tbody>
    </table>
    <div class="edit-note">Bottle prices live in Stock — edit once, every spec updates. Ice dilution not included.</div>`;

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
  $("#statVol").textContent = Math.round(sum.total_ml) + " ml";

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
          <div class="edit-note">${l.bottle_price_eur ? eur(l.bottle_price_eur) + " / " + Math.round(l.bottle_volume_ml) + " ml" : "no bottle price set"}</div></td>
      <td class="num">${l.amount_ml}</td>
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
      <thead><tr><th>Ingredient</th><th class="num">ml</th><th class="num">Bottle</th><th></th></tr></thead>
      <tbody id="editBody"></tbody>
    </table>
    <div class="edit-note" id="newHint" style="margin-top:10px;">New bottle — ABV/price/size only matter if it isn't in stock yet.</div>
    <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:end; margin-top:6px;">
      <div style="flex:2; min-width:150px;"><label>Name</label>
        <input id="addName" list="stockNames" placeholder="Type or pick…"></div>
      <div style="flex:1; min-width:70px;"><label>ml</label><input id="addMl" type="number" value="30" min="0" step="0.5"></div>
      <div id="advWrap" style="display:flex; gap:8px; flex-wrap:wrap;">
        <div style="width:70px;"><label>ABV %</label><input id="addAbv" type="number" value="0" min="0" max="100" step="0.5"></div>
        <div style="width:90px;"><label>Bottle €</label><input id="addPrice" type="number" value="0" min="0" step="0.1"></div>
        <div style="width:90px;"><label>Size ml</label><input id="addVol" type="number" value="700" min="0" step="50"></div>
      </div>
      <button id="addLine">+ Add</button>
    </div>
    <div style="display:flex; gap:8px; margin-top:16px;">
      <button id="saveIngs">Save changes</button>
      <button class="ghost" id="doneIng">Done</button>
    </div>`;

  // Hide the advanced fields when the typed name is already in stock.
  const onName = () => {
    const known = stockMap[($("#addName").value || "").trim().toLowerCase()];
    $("#advWrap").style.visibility = known ? "hidden" : "visible";
  };
  $("#addName").addEventListener("input", onName);
  onName();

  const renderRows = () => {
    const body = $("#editBody");
    body.innerHTML = "";
    rows.forEach((l, i) => {
      const tr = document.createElement("tr");
      const stock = stockMap[(l.name || "").toLowerCase()];
      const bottleTxt = stock && stock.bottle_price_eur
        ? `${eur(stock.bottle_price_eur)} · ${Math.round(stock.bottle_volume_ml)} ml`
        : (stock ? "no price yet" : "—");
      tr.innerHTML = `
        <td><input data-i="${i}" data-k="name" value="${esc(l.name)}" list="stockNames" placeholder="Ingredient"></td>
        <td><input class="num" type="number" data-i="${i}" data-k="amount_ml" value="${l.amount_ml}" min="0" step="0.5" style="width:90px; text-align:right;"></td>
        <td class="edit-note">${esc(bottleTxt)}</td>
        <td><button class="danger small" data-rm="${i}">✕</button></td>`;
      tr.querySelectorAll("input").forEach((inp) => {
        inp.addEventListener("input", () => {
          const k = inp.dataset.k;
          rows[+inp.dataset.i][k] = inp.type === "number" ? (parseFloat(inp.value) || 0) : inp.value.trim();
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

  $("#addLine").addEventListener("click", () => {
    const name = $("#addName").value.trim();
    const ml = parseFloat($("#addMl").value);
    if (!name || !ml) { toast("Name + ml needed"); return; }
    const known = stockMap[name.toLowerCase()];
    const line = {
      name,
      amount_ml: ml,
      abv: parseFloat($("#addAbv").value) || 0,
      bottle_price_eur: known ? 0 : parseFloat($("#addPrice").value) || 0,
      bottle_volume_ml: parseFloat($("#addVol").value) || 700,
    };
    rows.push(line);
    $("#addName").value = ""; $("#addMl").value = 30; $("#addAbv").value = 0;
    $("#addPrice").value = 0; $("#addVol").value = 700;
    renderRows(); onName();
  });

  const save = async (exit) => {
    const btn = $("#saveIngs"); if (btn) btn.disabled = true;
    try {
      for (const l of rows) {
        if (!l.name) continue;
        if (l.id) await api("/api/lines/" + l.id, "PUT", { amount_ml: l.amount_ml });
        else await api(`/api/specs/${s.id}/lines`, "POST", {
          name: l.name, amount_ml: l.amount_ml, abv: l.abv,
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
  const body = $("#stockBody");
  body.innerHTML = "";
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="6" class="edit-note">No bottles yet.</td></tr>';
    return;
  }
  items.forEach((it) => {
    const tr = document.createElement("tr");
    tr.className = it.spec_count ? "" : "unused";
    tr.innerHTML = `
      <td><input data-k="name" value="${esc(it.name)}"></td>
      <td><input type="number" data-k="abv" value="${it.abv}" min="0" max="100" step="0.5" style="width:80px;"></td>
      <td><input type="number" data-k="bottle_price_eur" value="${it.bottle_price_eur}" min="0" step="0.1" class="stock-price-input"></td>
      <td><input type="number" data-k="bottle_volume_ml" value="${it.bottle_volume_ml}" min="0" step="50" style="width:90px;"></td>
      <td class="num"><span class="spec-badge" title="specs using this bottle">${it.spec_count}×</span></td>
      <td><button class="danger small" data-del="${it.id}" ${it.spec_count ? "disabled title='Used by specs'" : ""}>✕</button></td>`;
    const commit = async () => {
      const payload = { name: "", abv: 0, bottle_price_eur: 0, bottle_volume_ml: 700 };
      tr.querySelectorAll("input[data-k]").forEach((inp) => {
        const k = inp.dataset.k;
        payload[k] = inp.type === "number" ? (parseFloat(inp.value) || 0) : inp.value.trim();
      });
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
      inp.addEventListener("change", commit);
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
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
  $("#addStockForm").classList.toggle("hidden");
  if (!$("#addStockForm").classList.contains("hidden")) $("#stName").focus();
});
$("#cancelStock").addEventListener("click", () => $("#addStockForm").classList.add("hidden"));
$("#saveStock").addEventListener("click", async () => {
  const name = $("#stName").value.trim();
  if (!name) { toast("Name needed"); return; }
  try {
    await api("/api/stock", "POST", {
      name,
      abv: parseFloat($("#stAbv").value) || 0,
      bottle_price_eur: parseFloat($("#stPrice").value) || 0,
      bottle_volume_ml: parseFloat($("#stVol").value) || 700,
    });
    toast("Bottle added");
    $("#stName").value = ""; $("#stAbv").value = 0; $("#stPrice").value = 0; $("#stVol").value = 700;
    $("#addStockForm").classList.add("hidden");
    renderStock();
  } catch (err) { toast("Failed: " + err.message); }
});

// ---------- menu (pricing + print) ----------
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
$("#navMenu").addEventListener("click", () => showView("menu"));
$("#printMenuBtn").addEventListener("click", () => window.print());
$("#pricedOnly").addEventListener("change", renderMenu);
$("#specSearch").addEventListener("input", applySearch);

window.addEventListener("load", async () => {
  await refreshStockMap();
  loadSpecs(false);
  try {
    const m = await api("/api/menu");
    $("#countMenu").textContent = m.length;
  } catch (_) {}
});
