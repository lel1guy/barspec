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
    const e = new Error(msg);
    e.status = r.status;
    throw e;
  }
  return r.status === 204 ? null : r.json();
}
function toast(msg) {
  const t = $("#toast"); t.textContent = toastPT(msg); t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2600);
}
// PT sweep: every toast literal above is translated centrally — the callsites
// stay language-neutral, this map carries the PT voice.
const TOAST_PT = {
  "Duplicated": "Receita duplicada", "Price saved": "Preço guardado",
  "Name needed": "Falta o nome", "Saved": "Guardado",
  "Pick a batch": "Escolha um xarope", "Amount needed": "Falta a quantidade",
  "Name + amount needed": "Faltam o nome e a quantidade",
  "Name can't be empty": "O nome não pode ficar vazio",
  "Par must be a positive number — or empty to clear": "O par tem de ser positivo — ou vazio para limpar",
  "Deleted": "Apagado",
  "Size needed": "Falta o tamanho", "Item added": "Artigo adicionado",
  "Ingredient name needed": "Falta o nome do ingrediente",
  "Name + size needed": "Faltam o nome e o tamanho",
  "Par: positive number, or empty to clear": "Par: número positivo, ou vazio para limpar",
  "Par cleared — removed from the count": "Par limpo — removido da contagem",
  "Nothing to save": "Nada para guardar", "Logged": "Registado",
  "Failed: ": "Falhou: ", "Save failed: ": "Falha ao guardar: ",
  "Can't delete: ": "Não é possível apagar: ", "QR failed: ": "QR falhou: ",
};
function toastPT(msg) {
  if (lang !== "pt") return msg;
  for (const [en, pt] of Object.entries(TOAST_PT))
    if (msg.startsWith(en)) return pt + msg.slice(en.length);
  return msg;
}
const esc = (x) => String(x ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const eur = (v) => "€" + (Math.round((v || 0) * 100) / 100).toFixed(2);

// ---------- i18n (008): EN / PT-PT ----------
const I18N = {
  en: {
    "side.workspace": "Workspace", "nav.specs": "Specs", "nav.batches": "Batches",
    "nav.stock": "Stock", "nav.take": "Stock-take", "nav.menu": "Menu",
    "mhead.unitsTitle": "Display unit — values are stored in ml",
    "mhead.search": "Search specs…", "mhead.newSpec": "+ New spec",
    "mhead.settings": "⚙ Settings", "settings.title": "Settings",
    "settings.lang": "Language", "settings.text": "Text size", "settings.unit": "Display unit",
    "spec.cards": "⤢ Cards",
    "stock.sup": "Supplier", "stock.supPh": "Supplier — blank ok",
    "specs.emptyHint": "Pick a spec on the left, or create one.",
    "view.specs": "Specs", "view.batches": "Batches", "view.stock": "Stock",
    "view.take": "Stock-take", "view.menu": "Menu",
    "batches.title": "House batches", "batches.hint": "Simple syrups, infusions, mixes — cost is derived from ingredients, never typed.",
    "batches.new": "+ New batch", "batches.namePh": "Simple syrup 1:1", "batches.size": "Batch size",
    "batches.shelf": "Shelf life (days)", "batches.shelfPh": "30 (blank = keeps)", "batches.made": "Made",
    "batches.methodPh": "stir 2:1 sugar:water, no heat", "batches.empty": "No batches yet — a house syrup starts with a name and a pan of sugar.",
    "f.name": "Name", "f.method": "Method", "f.saveBatch": "Save batch", "f.save": "Save", "f.cancel": "Cancel",
    "stock.title": "Stock", "stock.hint": "One row per item — change the price once, every spec updates.",
    "stock.add": "+ Add item", "stock.thName": "Item", "stock.thAbv": "ABV %", "stock.thPrice": "Price €",
    "stock.thSize": "Size", "stock.thPar": "Par", "stock.thUsed": "Used in",
    "stock.newHint": "New item — name first; price and size can wait until you have the receipt.",
    "stock.kind": "Kind", "stock.kindVol": "Bottle / keg", "stock.kindW": "Weight (coffee, sugar)",
    "stock.kindC": "Per piece (limes)", "stock.abv": "ABV %", "stock.price": "Price €",
    "stock.sizePer": "Size per purchase", "stock.yield": "Yield %",
    "stock.yieldTitle": "Usable after trim/cook: pay for 1 kg, use 800 g -> 80",
    "stock.dimHint": "A bottle is € per 700 ml; coffee € per kg (g); limes € per box of pieces. Size is stored canonically (ml / g / pc).",
    "take.count": "Count", "take.order": "Order list", "take.trends": "Trends",
    "take.countTitle": "Count", "take.countHint": "Items with a par level — walk the shelf and correct what changed.",
    "take.save": "Save count", "take.orderTitle": "Order list", "take.orderHint": "From your latest count vs par.",
    "take.newCount": "+ New count", "take.trendsTitle": "Trends & dead stock",
    "take.trendsHint": "Movement between your last two counts — insight appears as history accrues.",
    "menu.title": "Menu", "menu.hint": "Price every spec, then print. Costs never appear on the sheet.",
    "menu.onlyPriced": "only priced", "menu.print": "⤢ Print menu", "menu.printTitle": "Cocktail Menu",
    "menu.empty": "No specs yet — create one in Specs.",
    "spec.edit": "Edit", "spec.ing": "Ingredients", "spec.dup": "Duplicate", "spec.del": "Delete",
    "spec.glass": "Glass", "spec.method": "Method", "spec.garnish": "Garnish", "spec.category": "Category",
    "spec.dilution": "Dilution %", "spec.newTitle": "New spec", "spec.editTitle": "Edit spec",
    "detail.thIng": "Ingredient", "detail.thAmt": "Amount", "detail.thBottle": "Bottle",
    "ing.ingredient": "Ingredient", "ing.bottle": "Bottle", "ing.addIng": "+ Add", "ing.addBatch": "+ Add syrup",
    "ing.houseBatch": "House batch", "ing.save": "Save changes", "ing.done": "Done",
    "ing.namePh": "Type or pick…", "ing.amountUnit": "Amount + unit",
    "ing.remove": "Remove",
    "ing.hintKnown": "Bottles live in Stock. Type a known name and it links to the existing bottle; a new name creates one (set its price later in Stock).",
    "specs.none": "No specs yet.", "detail.capServe": "cost / serve",
    "detail.capBatch1": "1 serve", "detail.capBatchN": "{n} serves",
    "detail.capAbv": "ABV", "detail.capVol": "volume",
    "detail.noLines": "No ingredients yet — add some.",
    "detail.servings": "Servings", "detail.thAmt": "Amount", "detail.thAbv": "ABV",
    "detail.thCost": "Cost",
    "detail.thShare": "Share of cost", "detail.foot": "Bottle prices live in Stock — edit once, every spec updates.",
    "stock.none": "No stock items yet.",
    "take.unsaved": "You have an unsaved count. Leave and lose it?",
    "del.spec": "Delete", "del.specQ": "Delete {n}?",
    "del.stockQ": "Delete {n}? (only possible when no spec uses it)",
    "del.batchQ": "Delete the batch \"{n}\"?",
    "batch.thIng": "Ingredient", "batch.thAmt": "Amount",
    "batch.addIng": "Add ingredient", "batch.ingPh": "Type a stock name… or free text",
    "batch.unitLbl": "Unit",
    "order.to": "To order", "order.over": "Over par — cash asleep",
    "order.par": "Par", "order.have": "Have", "order.order": "Order",
    "order.tied": "€ tied up", "order.overCol": "Over",
    "order.none": "Nothing to order — you're at or above par everywhere. Nice.",
    "order.noOver": "Nothing over par.",
    "order.atParB": "bottle", "order.atParBs": "bottles", "order.atPar": "exactly at par.",
    "pricing.target": "Target margin", "pricing.suggest": "Suggested for target:",
    "pricing.use": "use", "pricing.savePrice": "Save price",
    "pricing.unpriced": "unpriced",
    "all": "All", "uncat": "Uncategorised",
    "export.specs": "⤓ Specs .xlsx", "export.stock": "⤓ Stock .xlsx",
    "export.qr": "◈ Share / QR", "export.qrTitle": "Menu link",
    "export.qrHint": "Point a phone at it — opens this bar's menu.",
    "f.close": "Close",
    "venue.btn": "☰ Venue", "venue.hint": "Shown on the printed menu — costs stay hidden.",
    "venue.iva": "IVA %", "venue.footer": "All prices include IVA {p}%.",
    "venue.saved": "Venue saved",
    "kitchen.servings": "Servings (portions)", "kitchen.servingsPh": "20 — blank = volume only",
    "kitchen.adj": "+ Log loss", "kitchen.adjTitle": "Loss log",
    "kitchen.adjHint": "Spills, spoilage, trim waste — a signed amount in the item's canonical unit (ml / g / pc). Loss becomes a visible line.",
    "kitchen.reason": "Reason", "kitchen.note": "Note", "kitchen.log": "Log it",
    "kitchen.recent": "Recent adjustments", "kitchen.none": "Nothing logged yet.",
    "kitchen.adjSaved": "Logged", "kitchen.delta": "Amount (ml / g / pc)",
    "pnl.title": "Sections P&L", "pnl.thCat": "Section", "pnl.thSpecs": "Specs",
    "pnl.thCost": "Avg cost", "pnl.thPrice": "Avg price", "pnl.thMargin": "Margin",
    "pnl.dead": "Dead stock on the shelf: {n} items worth {e}", "pnl.empty": "Unpriced — no P&L yet.",
    "auth.generic": "Something failed — try again.",
    "auth.wrong": "Wrong PIN.", "auth.pinPh": "PIN",
    "auth.setTitle": "Set your PIN",
    "auth.setSub": "First run — choose a 4+ digit PIN. The app stays locked until someone enters it.",
    "auth.loginTitle": "BarSpec is locked", "auth.loginSub": "Enter the owner PIN to open the bar.",
    "auth.go": "Unlock", "auth.goSetup": "Set PIN", "auth.lock": "🔒 Lock",
    "audit.title": "Recent changes", "audit.none": "No edits logged yet.",
    "a11y.skip": "Skip to content",
    "a11y.fsS": "Text size: small", "a11y.fsM": "Text size: medium",
    "a11y.fsL": "Text size: large",
  },
  pt: {
    "side.workspace": "Área de trabalho", "nav.specs": "Receitas", "nav.batches": "Xaropes",
    "nav.stock": "Stock", "nav.take": "Contagens", "nav.menu": "Menu",
    "mhead.unitsTitle": "Unidade de apresentação — valores guardados em ml",
    "mhead.search": "Procurar receitas…", "mhead.newSpec": "+ Nova receita",
    "mhead.settings": "⚙ Definições", "settings.title": "Definições",
    "settings.lang": "Idioma", "settings.text": "Tamanho do texto", "settings.unit": "Unidade de apresentação",
    "spec.cards": "⤢ Fichas",
    "stock.sup": "Fornecedor", "stock.supPh": "Fornecedor — pode ficar vazio",
    "specs.emptyHint": "Escolha uma receita à esquerda, ou crie uma.",
    "view.specs": "Receitas", "view.batches": "Xaropes", "view.stock": "Stock",
    "view.take": "Contagens", "view.menu": "Menu",
    "batches.title": "Xaropes e preparados", "batches.hint": "Xaropes, infusões, misturas — o custo vem dos ingredientes, nunca é escrito à mão.",
    "batches.new": "+ Nova produção", "batches.namePh": "Xarope simples 1:1", "batches.size": "Tamanho do lote",
    "batches.shelf": "Validade (dias)", "batches.shelfPh": "30 (vazio = não expira)", "batches.made": "Feito em",
    "batches.methodPh": "mexer 2:1 açúcar:água, sem calor", "batches.empty": "Ainda sem produções — um xarope caseiro começa com um nome e uma panela de açúcar.",
    "f.name": "Nome", "f.method": "Método", "f.saveBatch": "Guardar produção", "f.save": "Guardar", "f.cancel": "Cancelar",
    "stock.title": "Stock", "stock.hint": "Uma linha por artigo — mude o preço uma vez e todas as receitas actualizam.",
    "stock.add": "+ Adicionar artigo", "stock.thName": "Artigo", "stock.thAbv": "Álcool %", "stock.thPrice": "Preço €",
    "stock.thSize": "Tamanho", "stock.thPar": "Par", "stock.thUsed": "Usado em",
    "stock.newHint": "Novo artigo — primeiro o nome; preço e tamanho podem esperar até ter a factura.",
    "stock.kind": "Tipo", "stock.kindVol": "Garrafa / barril", "stock.kindW": "Peso (café, açúcar)",
    "stock.kindC": "À unidade (limas)", "stock.abv": "Álcool %", "stock.price": "Preço €",
    "stock.sizePer": "Tamanho por compra", "stock.yield": "Rendimento %",
    "stock.yieldTitle": "Aproveitamento após limpar/cozinhar: paga 1 kg, usa 800 g -> 80",
    "stock.dimHint": "Uma garrafa é € por 700 ml; café € por kg (g); limas € por caixa de unidades. Tamanho guardado canónico (ml / g / pc).",
    "take.count": "Contagem", "take.order": "Lista de compras", "take.trends": "Tendências",
    "take.countTitle": "Contagem", "take.countHint": "Artigos com par — percorra o armário e corrija o que mudou.",
    "take.save": "Guardar contagem", "take.orderTitle": "Lista de compras", "take.orderHint": "Da sua última contagem vs par.",
    "take.newCount": "+ Nova contagem", "take.trendsTitle": "Tendências e stock parado",
    "take.trendsHint": "Movimento entre as duas últimas contagens — a visão aparece com o histórico.",
    "menu.title": "Menu", "menu.hint": "Dê preço a cada receita e imprima. Custos nunca aparecem na folha.",
    "menu.onlyPriced": "só com preço", "menu.print": "⤢ Imprimir menu", "menu.printTitle": "Carta de Cocktails",
    "menu.empty": "Ainda sem receitas — crie uma em Receitas.",
    "spec.edit": "Editar", "spec.ing": "Ingredientes", "spec.dup": "Duplicar", "spec.del": "Apagar",
    "spec.glass": "Copo", "spec.method": "Método", "spec.garnish": "Decoração", "spec.category": "Categoria",
    "spec.dilution": "Diluição %", "spec.newTitle": "Nova receita", "spec.editTitle": "Editar receita",
    "detail.thIng": "Ingrediente", "detail.thAmt": "Quantidade", "detail.thBottle": "Garrafa",
    "ing.ingredient": "Ingrediente", "ing.bottle": "Garrafa", "ing.addIng": "+ Adicionar", "ing.addBatch": "+ Adicionar xarope",
    "ing.houseBatch": "Xarope caseiro", "ing.save": "Guardar alterações", "ing.done": "Concluir",
    "ing.namePh": "Escreva ou escolha…", "ing.amountUnit": "Quantidade + unidade",
    "ing.remove": "Remover",
    "ing.hintKnown": "As garrafas vivem no Stock. Escreva um nome conhecido e liga à garrafa existente; um nome novo cria uma (defina o preço depois no Stock).",
    "specs.none": "Ainda sem receitas.", "detail.capServe": "custo / dose",
    "detail.capBatch1": "1 dose", "detail.capBatchN": "{n} doses",
    "detail.capAbv": "Álcool", "detail.capVol": "volume",
    "detail.noLines": "Sem ingredientes — adicione alguns.",
    "detail.servings": "Doses", "detail.thAmt": "Quantidade", "detail.thAbv": "Álcool",
    "detail.thCost": "Custo",
    "detail.thShare": "Parte do custo", "detail.foot": "Os preços vivem no Stock — edite uma vez, todas as receitas actualizam.",
    "stock.none": "Ainda sem artigos no stock.",
    "take.unsaved": "Tem uma contagem por guardar. Sair e perdê-la?",
    "del.spec": "Apagar", "del.specQ": "Apagar {n}?",
    "del.stockQ": "Apagar {n}? (só é possível quando nenhuma receita o usa)",
    "del.batchQ": "Apagar o xarope \"{n}\"?",
    "batch.thIng": "Ingrediente", "batch.thAmt": "Quantidade",
    "batch.addIng": "Adicionar ingrediente", "batch.ingPh": "Escreva um nome de stock… ou texto livre",
    "batch.unitLbl": "Unidade",
    "order.to": "A encomendar", "order.over": "Acima do par — dinheiro parado",
    "order.par": "Par", "order.have": "Tem", "order.order": "Encomendar",
    "order.tied": "€ parado", "order.overCol": "Acima",
    "order.none": "Nada a encomendar — está tudo no par ou acima. Boa.",
    "order.noOver": "Nada acima do par.",
    "order.atParB": "garrafa", "order.atParBs": "garrafas", "order.atPar": "exatamente no par.",
    "pricing.target": "Margem alvo", "pricing.suggest": "Sugerido para a margem:",
    "pricing.use": "usar", "pricing.savePrice": "Guardar preço",
    "pricing.unpriced": "sem preço",
    "all": "Todas", "uncat": "Sem categoria",
    "export.specs": "⤓ Receitas .xlsx", "export.stock": "⤓ Stock .xlsx",
    "export.qr": "◈ Partilhar / QR", "export.qrTitle": "Link do menu",
    "export.qrHint": "Aponte um telemóvel — abre o menu deste bar.",
    "f.close": "Fechar",
    "venue.btn": "☰ Espaço", "venue.hint": "Aparece no menu impresso — os custos ficam escondidos.",
    "venue.iva": "IVA %", "venue.footer": "Todos os preços incluem IVA {p}%.",
    "venue.saved": "Espaço guardado",
    "kitchen.servings": "Doses / porções", "kitchen.servingsPh": "20 — vazio = só volume",
    "kitchen.adj": "+ Registar perda", "kitchen.adjTitle": "Registo de perdas",
    "kitchen.adjHint": "Derrames, estragos, desperdício — valor assinado na unidade canónica (ml / g / pc). A perda torna-se uma linha visível.",
    "kitchen.reason": "Motivo", "kitchen.note": "Nota", "kitchen.log": "Registar",
    "kitchen.recent": "Perdas recentes", "kitchen.none": "Ainda nada registado.",
    "kitchen.adjSaved": "Registado", "kitchen.delta": "Quantidade (ml / g / pc)",
    "pnl.title": "P&L por secção", "pnl.thCat": "Secção", "pnl.thSpecs": "Receitas",
    "pnl.thCost": "Custo médio", "pnl.thPrice": "Preço médio", "pnl.thMargin": "Margem",
    "pnl.dead": "Stock parado na prateleira: {n} artigos no valor de {e}", "pnl.empty": "Sem preços — ainda sem P&L.",
    "auth.generic": "Algo falhou — tente outra vez.", "auth.wrong": "PIN errado.",
    "auth.pinPh": "PIN", "auth.setTitle": "Defina o seu PIN",
    "auth.setSub": "Primeira vez — escolha um PIN com 4+ dígitos. A app fica bloqueada até alguém o inserir.",
    "auth.loginTitle": "BarSpec bloqueado", "auth.loginSub": "Introduza o PIN do dono para abrir o bar.",
    "auth.go": "Desbloquear", "auth.goSetup": "Definir PIN", "auth.lock": "🔒 Bloquear",
    "audit.title": "Alterações recentes", "audit.none": "Ainda sem edições registadas.",
    "a11y.skip": "Saltar para o conteúdo",
    "a11y.fsS": "Tamanho do texto: pequeno", "a11y.fsM": "Tamanho do texto: médio",
    "a11y.fsL": "Tamanho do texto: grande",
  },
};
let lang = localStorage.getItem("barspec.lang") || "en";
const t = (k) => (I18N[lang] && I18N[lang][k]) || I18N.en[k] || k;
function applyI18n() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll(".setopt[data-lang]").forEach((b) =>
    b.classList.toggle("active", b.dataset.lang === lang));
}
function setLang(l) {
  lang = l;
  localStorage.setItem("barspec.lang", l);
  applyI18n();
  updateChrome();
  if (currentView === "specs") loadSpecs();
  else if (currentView === "batches") loadBatches();
  else if (currentView === "stock") renderStock();
  else if (currentView === "stocktake") loadStocktake();
  else if (currentView === "menu") renderMenu();
}
// text scale S/M/L (persisted); zoom on content, nav stays compact
let fs = localStorage.getItem("barspec.fontsize") || "m";
function applyFont() {
  document.documentElement.dataset.fs = fs;
  document.querySelectorAll(".fontbtn").forEach((b) => {
    const on = b.dataset.fs === fs;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on);
  });
}
function setFont(f) {
  fs = f;
  localStorage.setItem("barspec.fontsize", f);
  applyFont();
}
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

// K3 labels (EU 14 allergens + dietary tags)
const ALLERGEN_LABELS = {
  en: { cel: "celery", glu: "gluten (cereal)", cru: "crustaceans", egg: "eggs", fis: "fish",
        lup: "lupin", mil: "milk", mol: "molluscs", mus: "mustard", nut: "tree nuts",
        pea: "peanuts", ses: "sesame", soy: "soy", sul: "sulphites" },
  pt: { cel: "aipo", glu: "glúten (cereais)", cru: "crustáceos", egg: "ovos", fis: "peixe",
        lup: "tremoço", mil: "leite", mol: "moluscos", mus: "mostarda", nut: "frutos secos",
        pea: "amendoins", ses: "sésamo", soy: "soja", sul: "sulfitos" },
};
const DIET_LABELS = { en: { V: "Vegetarian", VE: "Vegan", GF: "Gluten-free" },
                      pt: { V: "Vegetariano", VE: "Vegan", GF: "Sem glúten" } };
function badgesHtml(s) {
  const diet = (s.dietary || "").split(",").filter(Boolean).map((c) =>
    `<span class="dim-tag diet">${esc(c)}</span>`).join("");
  const alg = (s.allergens || "").split(",").filter(Boolean).map((c) =>
    `<span class="dim-tag alg" title="${esc(ALLERGEN_LABELS[lang][c] || c)}">${esc(c.toUpperCase())}</span>`).join("");
  return diet || alg ? `<div class="spec-badges">${diet}${alg}</div>` : "";
}

// ---------- S1: owner PIN gate ----------
let authMode = "setup";
function showAuth(mode) {
  authMode = mode;
  const set = mode === "setup";
  const dl = $("#authTitle"), sb = $("#authSub"), go = $("#authGo"), err = $("#authErr");
  dl.dataset.i18n = set ? "auth.setTitle" : "auth.loginTitle";
  dl.textContent = t(set ? "auth.setTitle" : "auth.loginTitle");
  sb.dataset.i18n = set ? "auth.setSub" : "auth.loginSub";
  sb.textContent = t(set ? "auth.setSub" : "auth.loginSub");
  go.textContent = t(set ? "auth.goSetup" : "auth.go");
  err.style.display = "none";
  $("#authOverlay").classList.remove("hidden");
  $("#authPin").focus();
}
async function submitAuth() {
  const pin = $("#authPin").value;
  const err = $("#authErr");
  try {
    await api("/api/auth/" + (authMode === "setup" ? "setup" : "login"), "POST", { pin });
    location.reload();
  } catch (e) {
    err.textContent = t(e.status === 401 ? "auth.wrong" : "auth.generic");
    err.style.display = "block";
  }
}
$("#authForm").addEventListener("submit", (e) => { e.preventDefault(); submitAuth(); });
$("#authGo").addEventListener("click", submitAuth);

// ---------- views ----------
let currentCat = "__all__";   // filter state: __all__ | '' (uncategorized) | lower(category)
function renderChips(specs) {
  const box = $("#catChips");
  if (!box) return;
  const seen = new Map();          // lower -> { label, n }
  let uncat = 0;
  for (const s of specs) {
    if (s.category) {
      const k = s.category.toLowerCase();
      const e = seen.get(k) || { label: s.category, n: 0 };
      e.n += 1;
      seen.set(k, e);
    } else uncat += 1;
  }
  const cats = [...seen.values()].sort((a, b) => a.label.localeCompare(b.label));
  if (uncat) cats.push({ label: t("uncat"), n: uncat, k: "" });
  cats.forEach((c) => { if (c.k === undefined) c.k = c.label.toLowerCase(); });
  box.classList.toggle("hidden", cats.length === 0);
  box.innerHTML = [
    `<button class="chip ${currentCat === "__all__" ? "active" : ""}" data-cat="__all__">${t("all")} ${specs.length}</button>`,
    ...cats.map((c) =>
      `<button class="chip ${currentCat === c.k ? "active" : ""}" data-cat="${esc(c.k)}">${esc(c.label)} ${c.n}</button>`),
  ].join("");
  box.querySelectorAll(".chip").forEach((b) =>
    b.addEventListener("click", () => {
      currentCat = b.dataset.cat;
      box.querySelectorAll(".chip").forEach((x) => x.classList.toggle("active", x === b));
      applySearch();
    }));
}
function applySearch() {
  const q = ($("#specSearch").value || "").trim().toLowerCase();
  document.querySelectorAll("#specList .spec-item").forEach((el) => {
    const name = (el.querySelector(".spec-name")?.textContent || "").toLowerCase();
    const okCat = currentCat === "__all__" || el.dataset.catkey === currentCat;
    el.style.display = (okCat && (!q || name.includes(q))) ? "" : "none";
  });
}
const VIEWS = {
  specs: { title: "Specs", crumb: "SPECS", header: true },
  batches: { title: "Batches", crumb: "BATCHES", header: false },
  stock: { title: "Stock", crumb: "STOCK", header: false },
  stocktake: { title: "Stock-take", crumb: "STOCK-TAKE", header: false },
  menu:  { title: "Menu",  crumb: "MENU",  header: false },
};
const NAV_IDS = { specs: "navSpecs", batches: "navBatches", stock: "navStock",
                  stocktake: "navTake", menu: "navMenu" };
const VIEW_KEYS = { specs: "view.specs", batches: "view.batches", stock: "view.stock",
                    stocktake: "view.take", menu: "view.menu" };
function updateChrome() {
  $("#viewTitle").textContent = t(VIEW_KEYS[currentView]);
  $("#crumbLabel").textContent = "BARSPEC / " + t(VIEW_KEYS[currentView]).toUpperCase();
}
function showView(v) {
  if (v !== currentView && currentView === "stocktake" && takeDirty &&
      !confirm(t("take.unsaved"))) return;
  currentView = v;
  Object.keys(VIEWS).forEach((x) => {
    $("body").dataset.view = v;
    $("#view-" + x).classList.toggle("active", x === v);
    $("#" + NAV_IDS[x]).classList.toggle("active", x === v);
  });
  const meta = VIEWS[v];
  updateChrome();
  $("#newSpecBtn").classList.toggle("hidden", !meta.header);
  $("#searchBox").classList.toggle("hidden", !meta.header);
  $("#printCardsBtn").classList.toggle("hidden", !meta.header);
  if (v === "batches") loadBatches();
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
  if (!specs.length) { box.innerHTML = '<div class="edit-note">' + t("specs.none") + "</div>"; return; }
  for (const s of specs) {
    const el = document.createElement("div");
    el.className = "spec-item" + (s.id === currentSpec ? " active" : "");
    const meta = [s.method, s.price_eur ? eur(s.price_eur) : null].filter(Boolean).join(" · ");
    el.dataset.catkey = (s.category || "").toLowerCase();
    el.innerHTML = `<div>
        <div class="spec-name">${esc(s.name)}
          ${s.category ? `<span class="dim-tag">${esc(s.category)}</span>` : ""}</div>
        <div class="spec-meta">${esc(meta || "—")}</div>
      </div>
      <button class="ghost small" data-del="${s.id}" aria-label="${t("del.spec")} ${esc(s.name)}">✕</button>`;
    el.addEventListener("click", () => openSpec(s.id));
    el.querySelector("[data-del]").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(t("del.specQ").replace("{n}", s.name))) return;
      await api("/api/specs/" + s.id, "DELETE");
      if (currentSpec === s.id) { currentSpec = null; renderEmpty(); }
      loadSpecs();
    });
    box.appendChild(el);
  }
  if (keepOpen && currentSpec) openSpec(currentSpec);
  renderChips(specs);
  const dl = $("#catNames");
  if (dl) dl.innerHTML = [...new Set(specs.map((s) => s.category).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b)).map((c) => `<option value="${esc(c)}">`).join("");
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
        ${badgesHtml(s)}
      </div>
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button class="ghost small" id="editBtn">${t("spec.edit")}</button>
        <button class="ghost small" id="ingBtn">${t("spec.ing")}</button>
        <button class="ghost small" id="dupeBtn">${t("spec.dup")}</button>
        <button class="danger small" id="delBtn">${t("spec.del")}</button>
      </div>
    </div>
    <div class="stat-strip">
      <div class="stat"><div class="num" id="statServe">—</div><div class="cap">${t("detail.capServe")}</div></div>
      <div class="stat"><div class="num" id="statBatch">—</div><div class="cap">${t(servings === 1 ? "detail.capBatch1" : "detail.capBatchN").replace("{n}", servings)}</div></div>
      <div class="stat"><div class="num" id="statAbv">—</div><div class="cap">${t("detail.capAbv")}</div></div>
      <div class="stat"><div class="num" id="statVol">—</div><div class="cap">${t("detail.capVol")}</div></div>
    </div>

    <div class="pricing-panel" id="pricingPanel"></div>

    <div style="display:flex; gap:10px; margin:12px 0 4px; flex-wrap:wrap; align-items:end;">
      <div style="flex:1; min-width:140px;">
        <label for="servings">${t("detail.servings")}</label>
        <input type="number" id="servings" min="1" max="999" value="1">
      </div>
    </div>

    <table>
      <thead><tr><th>${t("detail.thIng")}</th><th class="num">${unitLabel()}</th><th class="num">${t("detail.thAbv")}</th>
          <th class="num">${t("detail.thCost")}</th><th style="width:120px;">${t("detail.thShare")}</th><th></th></tr></thead>
      <tbody id="ingBody"></tbody>
    </table>
    <div class="edit-note" data-i18n="detail.foot">Bottle prices live in Stock — edit once, every spec updates.</div>`;

  $("#servings").addEventListener("input", (e) => {
    servings = Math.max(1, parseInt(e.target.value) || 1);
    renderDetail(s);
  });
  $("#editBtn").addEventListener("click", () => editSpecForm(s));
  $("#ingBtn").addEventListener("click", () => editIngredientsForm(s));
  $("#delBtn").addEventListener("click", async () => {
    if (!confirm(t("del.specQ").replace("{n}", s.name))) return;
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
  const dil = sum.dilution_pct || 0;
  if (dil > 0) {
    // ice melt: what actually reaches the glass
    $("#statAbv").textContent = sum.served_abv + "%";
    $("#statVol").textContent = dispAmt(sum.served_ml) + " " + unitLabel();
    $("#statAbv").title = `Recipe ABV ${sum.abv}% before ${dil}% dilution`;
    $("#statVol").title = `Recipe ${fmtAmt(sum.total_ml)} ml + ${dil}% ice melt`;
  } else {
    $("#statAbv").textContent = sum.abv + "%";
    $("#statVol").textContent = dispAmt(sum.total_ml) + " " + unitLabel();
    $("#statAbv").title = "";
    $("#statVol").title = "";
  }

  const body = $("#ingBody");
  body.innerHTML = "";
  if (!s.lines.length) {
    body.innerHTML = `<tr><td colspan="6" class="edit-note">${t("detail.noLines")}</td></tr>`;
    return;
  }
  for (const l of s.lines) {
    const tr = document.createElement("tr");
    const sub = l.kind === "batch"
      ? `house batch · ${eur(l.batch_cost_total || 0)} / ${fmtAmt(l.batch_size_ml)} ml · `
        + (l.days_left === null ? "keeps"
           : l.days_left < 0 ? `<b>expired</b>` : `${l.days_left}d left`)
      : purchaseText(l);
    tr.innerHTML = `
      <td><span class="ing-name">${esc(l.name)}</span>
          ${l.kind === "batch" ? '<span class="dim-tag">batch</span>' : ""}
          <div class="edit-note">${sub}</div></td>
      <td class="num">${lineAmtHtml(l)}</td>
      <td class="num">${l.abv ? l.abv + "%" : "—"}</td>
      <td class="num">${l.row_cost_eur ? eur(l.row_cost_eur) : "—"}</td>
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
    <h2 style="margin-top:0">${s ? t("spec.editTitle") : t("spec.newTitle")}</h2>
    <label>${t("f.name")}</label><input id="fName" value="${esc(s ? s.name : "")}" placeholder="Negroni">
    <label>${t("spec.glass")}</label><input id="fGlass" value="${esc(s ? s.glass : "")}" placeholder="Rocks glass, big ice cube">
    <label>${t("spec.method")}</label><input id="fMethod" value="${esc(s ? s.method : "")}" placeholder="Stirred">
    <label>${t("spec.garnish")}</label><input id="fGarnish" value="${esc(s ? s.garnish : "")}" placeholder="Orange peel">
    <label>${t("spec.category")}</label><input id="fCat" list="catNames" value="${esc(s && s.category ? s.category : "")}" placeholder="Old Fashioneds · Martinis · Starters…">
    <label>${t("spec.dilution")}</label><input id="fDil" type="number" min="0" max="60" step="1" value="${s && s.dilution_pct ? s.dilution_pct : 0}"
           title="Ice melt adds water: hard shake ≈ 20–25%, stir ≈ 10–15%. 0 = served straight (default).">
    <div class="chipset">
      <div class="chipset-label">Diet</div>
      ${["V", "VE", "GF"].map((c) => `
        <label class="chip-check"><input type="checkbox" data-diet="${c}" ${(s && (s.dietary || "").split(",").includes(c)) ? "checked" : ""}> ${c}
          <em title="${esc(DIET_LABELS[lang][c])}"></em></label>`).join("")}
    </div>
    <div class="chipset">
      <div class="chipset-label">Allergens <span class="edit-note">(EU 14 — codes shown; full names on cards/export)</span></div>
      ${Object.keys(ALLERGEN_LABELS[lang]).map((c) => `
        <label class="chip-check" title="${esc(ALLERGEN_LABELS[lang][c])}">
          <input type="checkbox" data-alg="${c}" ${(s && (s.allergens || "").split(",").includes(c)) ? "checked" : ""}> ${c.toUpperCase()}
        </label>`).join("")}
    </div>
    <div style="display:flex; gap:8px; margin-top:16px;">
      <button id="saveSpec">${t("f.save")}</button>
      <button class="ghost" id="cancelEdit">${t("f.cancel")}</button>
    </div>`;
  $("#saveSpec").addEventListener("click", async () => {
    const data = {
      name: $("#fName").value.trim(),
      glass: $("#fGlass").value.trim(),
      method: $("#fMethod").value.trim(),
      garnish: $("#fGarnish").value.trim(),
      category: $("#fCat").value.trim() || null,
      dilution_pct: parseFloat($("#fDil").value) || 0,
      allergens: [...document.querySelectorAll("[data-alg]:checked")].map((b) => b.dataset.alg).join(","),
      dietary: [...document.querySelectorAll("[data-diet]:checked")].map((b) => b.dataset.diet).join(","),
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
    <h2 style="margin-top:0">${t("spec.ing")} — ${esc(s.name)}</h2>
    <div class="edit-note">${t("ing.hintKnown")}</div>
    <table>
      <thead><tr><th>${t("detail.thIng")}</th><th class="num">${t("detail.thAmt")}</th><th class="num">${t("detail.thBottle")}</th><th></th></tr></thead>
      <tbody id="editBody"></tbody>
    </table>
    <div class="edit-note" id="newHint" style="margin-top:10px;">Amount is in the unit you pick per row — a Margarita lime is "1 piece", bitters are "2 dash". New bottles (weight/count stock) are created in Stock first.</div>
    <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:end; margin-top:6px;">
      <div style="flex:2; min-width:150px;"><label>${t("f.name")}</label>
        <input id="addName" list="stockNames" data-i18n-ph="ing.namePh" placeholder="Type or pick…"></div>
      <div style="flex:1; min-width:170px;"><label>${t("ing.amountUnit")}</label>
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
      <button id="addLine">${t("ing.addIng")}</button>
    </div>
    <div id="addBatchRow" class="hidden" style="display:flex; gap:8px; flex-wrap:wrap; align-items:end; margin-top:8px; padding-top:8px; border-top:1px dashed var(--line2);">
      <div style="flex:2; min-width:170px;"><label>${t("ing.houseBatch")}</label>
        <select id="addBatchSel" style="width:100%;"></select></div>
      <div style="flex:1; min-width:110px;"><label>${t("detail.thAmt")}</label>
        <div style="display:flex; gap:4px;"><input id="addBAmt" type="number" value="20" min="0" step="0.5" style="flex:1;">
        <select id="addBUnit" style="width:80px;"><option>ml</option><option>cl</option><option>oz</option></select></div>
      </div>
      <button id="addBatchBtn">${t("ing.addBatch")}</button>
    </div>
    <div style="display:flex; gap:8px; margin-top:16px;">
      <button id="saveIngs">${t("ing.save")}</button>
      <button class="ghost" id="doneIng">${t("ing.done")}</button>
    </div>`;

  const unitOptions = (dim) => UNITS_FOR_DIM[dim] || ["ml"];
  const renderRows = () => {
    const body = $("#editBody");
    body.innerHTML = "";
    rows.forEach((l, i) => {
      const tr = document.createElement("tr");
      const stock = stockMap[(l.name || "").toLowerCase()];
      const isBatch = !!l.batch_id;
      const dim = isBatch ? "volume" : (stock ? stock.dimension : "volume");
      const opts = unitOptions(dim);
      // Stored unit must belong to this stock's dimension; else fall back to
      // the dimension's canonical unit (rename across dimensions = delete+add).
      if (!opts.includes(l.unit)) l.unit = dimCanonical(dim);
      const bottleTxt = isBatch ? "house batch — pour only"
        : stock && stock.bottle_price_eur ? purchaseText(stock)
        : (stock ? "no price yet" : "—");
      tr.innerHTML = `
        <td>${isBatch
          ? `<span class="ing-name">${esc(l.name)}</span><span class="dim-tag">batch</span><input data-k="name" value="${esc(l.name)}" style="display:none;">`
          : `<input data-i="${i}" data-k="name" value="${esc(l.name)}" list="stockNames" placeholder="Ingredient">`}
        </td>
        <td class="num"><span class="amt-cell">
          <input class="num" type="number" data-i="${i}" data-k="amount_ml" value="${fmtAmt(l.amount_ml)}" min="0" step="0.5" style="width:80px; text-align:right;">
          <select data-i="${i}" data-ku="unit" class="unitmini">${opts.map((u) =>
            `<option value="${u}" ${u === l.unit ? "selected" : ""}>${u}</option>`).join("")}</select>
        </span></td>
        <td class="edit-note">${esc(bottleTxt)}</td>
        <td><button class="danger small" data-rm="${i}" aria-label="${t("ing.remove")} ${esc(l.name || rows[i]?.name || "")}">✕</button></td>`;
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

  // House-batch picker: offer batches to pour into this spec (volume pour).
  api("/api/batches").then((bs) => {
    const sel = $("#addBatchSel");
    if (!sel) return;
    if (!bs.length) return;
    sel.innerHTML = bs.map((b) =>
      `<option value="${b.id}">${esc(b.name)} · ${eur(b.cost_eur)}/batch</option>`).join("");
    $("#addBatchRow").classList.remove("hidden");
  });
  $("#addBatchBtn").addEventListener("click", async () => {
    const sel = $("#addBatchSel");
    const bid = parseInt(sel.value, 10);
    if (!bid) return toast("Pick a batch");
    const amt = parseFloat($("#addBAmt").value) || 0;
    if (!amt) return toast("Amount needed");
    const unit = $("#addBUnit").value;
    const label = sel.options[sel.selectedIndex]?.textContent.split(" · ")[0] || "batch";
    rows.push({ id: null, kind: "batch", batch_id: bid, name: label,
                amount_ml: amt, unit, abv: 0, bottle_price_eur: null,
                bottle_volume_ml: null, bottleTxt: "house batch — pour only" });
    renderRows();
    $("#addBAmt").value = 20;
  });

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
        else if (l.batch_id) await api(`/api/specs/${s.id}/lines`, "POST", {
          batch_id: l.batch_id, amount_ml: l.amount_ml, unit: l.unit || "ml" });
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
  const dl = $("#supNames");
  if (dl) {
    const sups = [...new Set(items.map((i) => (i.supplier || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    dl.innerHTML = sups.map((s) => `<option value="${esc(s)}">`).join("");
  }
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
           <select class="unitmini" data-wunit><option value="g" ${wKg ? "" : "selected"}>g</option><option value="kg" ${wKg ? "selected" : ""}>kg</option></select>
           <input type="number" data-k="yield_frac" value="${Math.round((it.yield_frac ?? 1) * 100)}" min="1" max="100" step="1" style="width:54px;" title="Yield % — usable after trim/cook">&nbsp;%</span>`
        : `<span class="size-ctl"><input type="number" data-k="bottle_volume_ml" value="${fmtAmt(it.bottle_volume_ml)}" min="0" step="1" style="width:70px;"><span class="edit-note">pc</span></span>`;
    const abvCell = isVol
      ? `<input type="number" data-k="abv" value="${it.abv}" min="0" max="100" step="0.5" style="width:80px;">`
      : `<span class="edit-note">—</span>`;
    tr.innerHTML = `
      <td>
        <input data-k="name" value="${esc(it.name)}" ${dim === "volume" ? "" : `title="${dim}"`}>
        <input class="sup-in" data-k="supplier" list="supNames" value="${esc(it.supplier || "")}" data-i18n-ph="stock.sup" placeholder="Supplier — blank ok">
      </td>
      <td>${abvCell}</td>
      <td><input type="number" data-k="bottle_price_eur" value="${it.bottle_price_eur}" min="0" step="0.1" class="stock-price-input"></td>
      <td>${sizeCell}</td>
      <td><input type="number" data-par="${it.id}" value="${it.par_level ?? ""}" min="0" step="0.5"
                 placeholder="—" class="par-input" title="Par level — how many to keep on hand. Empty = not counted."></td>
      <td class="num"><span class="spec-badge" title="specs using this bottle">${it.spec_count}×</span></td>
      <td><button class="danger small" data-del="${it.id}" aria-label="${t("del.spec")} ${esc(it.name)}" ${it.spec_count ? "disabled title='Used by specs'" : ""}>✕</button></td>`;
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
        payload.yield_frac = (payload.yield_frac || 100) / 100;  // UI is percent
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
      if (!confirm(t("del.stockQ").replace("{n}", it.name))) return;
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
async function renderAdjList() {
  const list = await api("/api/stock-adjustments?limit=6");
  const box = $("#adjList");
  if (!list.length) { box.textContent = t("kitchen.none"); return; }
  box.innerHTML = list.map((a) =>
    `<div>${a.delta > 0 ? "+" : ""}${a.delta} ${esc(a.item_name)} — ${esc(a.reason)}${a.note ? " · " + esc(a.note) : ""} <span class="edit-note">${esc((a.created_at || "").slice(0, 16))}</span></div>`
  ).join("");
}
$("#adjToggle").addEventListener("click", async () => {
  const box = $("#adjBox");
  if (box.classList.contains("hidden")) {
    const sel = $("#adjItem");
    if (!sel.options.length) {
      const items = await api("/api/stock");
      sel.innerHTML = items.map((i) =>
        `<option value="${i.id}">${esc(i.name)}</option>`).join("");
    }
    box.classList.remove("hidden");
    renderAdjList();
  } else box.classList.add("hidden");
});
$("#adjSave").addEventListener("click", async () => {
  const delta = parseFloat($("#adjDelta").value);
  const item = $("#adjItem").value;
  try {
    if (!item) throw new Error(t("f.name") + "?");
    await api(`/api/stock/${item}/adjust`, "POST", {
      delta, reason: $("#adjReason").value, note: $("#adjNote").value.trim(),
    });
    $("#adjDelta").value = ""; $("#adjNote").value = "";
    toast(t("kitchen.adjSaved"));
    renderAdjList();
  } catch (e) { toast("Failed: " + (e.message || "")); }
});
$("#cancelStock").addEventListener("click", () => $("#addStockForm").classList.add("hidden"));

// Dimension picker drives which units + defaults the size field offers.
function syncStockDimForm() {
  const dim = $("#stDim").value;
  const abvW = $("#abvWrap");
  if (abvW) abvW.style.display = dim === "volume" ? "" : "none";
  const yW = $("#yieldWrap");
  if (yW) yW.style.display = dim === "weight" ? "" : "none";
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
    const payload = {
      name,
      supplier: $("#stSup").value.trim(),
      abv: dim === "volume" ? (parseFloat($("#stAbv").value) || 0) : 0,
      bottle_price_eur: parseFloat($("#stPrice").value) || 0,
      bottle_volume_ml: canonical,
      dimension: dim,
    };
    if (dim === "weight") payload.yield_frac = (parseFloat($("#stYield").value) || 100) / 100;
    await api("/api/stock", "POST", payload);
    toast("Item added");
    $("#stName").value = ""; $("#stSup").value = ""; $("#stAbv").value = 0; $("#stPrice").value = 0;
    $("#stVol").value = dim === "weight" ? 1 : dim === "count" ? 12 : 700;
    $("#addStockForm").classList.add("hidden");
    renderStock();
  } catch (err) { toast("Failed: " + err.message); }
});

// ---------- batches (004: house syrups / infusions) ----------

let batches = [];
let openBatch = null;
const batchExpiryHtml = (b) => {
  if (b.days_left === null) return '<span class="exp-chip ok">keeps</span>';
  if (b.days_left < 0) return `<span class="exp-chip bad">expired ${-b.days_left}d ago</span>`;
  if (b.days_left <= 3) return `<span class="exp-chip warn">${b.days_left}d left</span>`;
  return `<span class="exp-chip ok">${b.days_left}d left</span>`;
};
const perLitre = (b) => "€" + (b.cost_per_ml * 1000).toFixed(2);
async function loadBatches() {
  batches = await api("/api/batches");
  $("#countBatches").textContent = batches.length;
  $("#batchEmpty").classList.toggle("hidden", batches.length > 0);
  const box = $("#batchList");
  box.innerHTML = "";
  for (const b of batches) {
    const el = document.createElement("div");
    el.className = "batch-item" + (openBatch === b.id ? " active" : "");
    el.innerHTML = `
      <div style="flex:1; min-width:0;">
        <div class="spec-name">${esc(b.name)} <span class="edit-note">${esc(b.method || "")}</span></div>
        <div class="spec-meta">${fmtAmt(b.batch_size_ml)} ml batch · ${eur(b.cost_eur)} total
          ${b.cost_per_serve ? ` · ${eur(b.cost_per_serve)}/portion` : ""} · ${eur(b.cost_per_ml * 1000)}/litre · ${b.line_count} ingredients</div>
      </div>
      ${batchExpiryHtml(b)}
      <div style="display:flex; gap:4px; margin-left:10px;">
        <button class="ghost small" data-edit="${b.id}" aria-label="${t("spec.edit")}">✎</button>
        <button class="danger small" data-del="${b.id}" aria-label="${t("del.spec")} ${esc(b.name)}">✕</button>
      </div>`;
    el.addEventListener("click", (e) => {
      if (e.target.closest("[data-del]") || e.target.closest("[data-edit]")) return;
      openBatch = openBatch === b.id ? null : b.id;
      loadBatches(); renderBatchDetail();
    });
    el.querySelector("[data-edit]").addEventListener("click", (e) => {
      e.stopPropagation();
      $("#btName").value = b.name; $("#btSize").value = b.batch_size_ml;
      $("#btUnit").value = "ml";
      $("#btShelf").value = b.shelf_life_days ?? "";
      $("#btMade").value = b.made_date;
      $("#btServ").value = b.servings ?? "";
      $("#btMethod").value = b.method || "";
      $("#saveBatch").dataset.id = b.id;
      $("#newBatchBtn").textContent = "Cancel";
      $("#newBatchForm").classList.remove("hidden");
    });
    el.querySelector("[data-del]").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(t("del.batchQ").replace("{n}", b.name))) return;
      const res = await api("/api/batches/" + b.id, "DELETE");
      if (res && res.detail) { toast(res.detail); return; }
      if (openBatch === b.id) { openBatch = null; $("#batchDetail").innerHTML = ""; }
      loadBatches();
    });
    box.appendChild(el);
  }
  if (batches.length) refreshStockMap(); // batch editors resolve stock by name
  renderBatchDetail();
}

async function renderBatchDetail() {
  const box = $("#batchDetail");
  if (!openBatch) { box.innerHTML = ""; return; }
  const b = await api("/api/batches/" + openBatch);
  box.innerHTML = `
    <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:8px 0;">
      <strong style="font-family:var(--serif); font-size:18px;">${esc(b.name)}</strong>
      ${batchExpiryHtml(b)}
      <span class="edit-note">${esc(b.method || "")}</span>
      <div class="spacer"></div>
      <span class="edit-note">${fmtAmt(b.batch_size_ml)} ml · ${eur(b.cost_eur)} total
        ${b.cost_per_serve ? ` · ${eur(b.cost_per_serve)}/portion` : ""} · ${eur(b.cost_per_ml * 1000)}/litre</span>
    </div>
    <table>
      <thead><tr><th>${t("batch.thIng")}</th><th class="num">${t("batch.thAmt")}</th><th class="num">${t("detail.thCost")}</th><th></th></tr></thead>
      <tbody>${b.lines.map((l) => `
        <tr>
          <td>${esc(l.name)}</td>
          <td class="num">${fmtAmt(l.amount_ml)} ${esc(l.unit)}</td>
          <td class="num">${l.stock_item_id ? eur((l.amount_ml || 0) * (l.bottle_price_eur || 0) / (l.bottle_volume_ml || 1)) : eur(l.cost_eur || 0)}
            ${l.stock_item_id ? '<span class="edit-note">derived</span>' : ""}</td>
          <td><button class="danger small" data-bline="${l.id}" aria-label="${t("ing.remove")} ${esc(l.name)}">✕</button></td>
        </tr>`).join("")}
      </tbody>
    </table>
    <div class="formrow no-print" style="margin-top:10px;">
      <div style="flex:2; min-width:140px;"><label>${t("batch.addIng")}</label>
        <input id="blName" list="stockNames" data-i18n-ph="batch.ingPh" placeholder="Type a stock name… or free text"></div>
      <div style="flex:1; min-width:80px;"><label>${t("batch.thAmt")}</label><input id="blAmt" type="number" value="100" min="0" step="0.5"></div>
      <div style="flex:1; min-width:70px;"><label>${t("batch.unitLbl")}</label><select id="blUnit">
        <option value="g">g</option><option value="kg">kg</option><option value="ml">ml</option>
        <option value="l">l</option><option value="cl">cl</option><option value="piece">piece</option></select></div>
      <div style="flex:1; min-width:90px;"><label>€ cost if not stock</label><input id="blCost" type="number" step="0.01" placeholder="blank = from stock"></div>
      <button id="addBatchLine" class="btn">+ Add</button>
    </div>
    <div class="edit-note">Names in stock link live (price flows with the bottle); anything else needs its € cost for that amount — €0 is fine for water.</div>`;
  box.querySelectorAll("[data-bline]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api("/api/batches/lines/" + btn.dataset.bline, "DELETE");
      renderBatchDetail(); loadBatches();
    }));
  $("#addBatchLine").addEventListener("click", async () => {
    const name = $("#blName").value.trim();
    if (!name) return toast("Ingredient name needed");
    const payload = { name, amount_ml: parseFloat($("#blAmt").value) || 0,
                      unit: $("#blUnit").value };
    const cost = $("#blCost").value.trim();
    if (cost !== "") payload.cost_eur = parseFloat(cost);
    const res = await api(`/api/batches/${openBatch}/lines`, "POST", payload);
    if (res && res.detail) { toast(res.detail); return; }
    $("#blName").value = ""; $("#blCost").value = "";
    renderBatchDetail(); loadBatches();
  });
}

$("#newBatchBtn").addEventListener("click", () => {
  const form = $("#newBatchForm");
  const hiding = !form.classList.contains("hidden");
  form.classList.toggle("hidden");
  $("#newBatchBtn").textContent = hiding ? "+ New batch" : "Cancel";
  if (!hiding) {
    delete $("#saveBatch").dataset.id;
    $("#btName").value = ""; $("#btSize").value = 1000; $("#btUnit").value = "ml";
    $("#btShelf").value = ""; $("#btMade").value = new Date().toISOString().slice(0, 10);
    $("#btMethod").value = ""; $("#btServ").value = "";
    $("#btName").focus();
  }
});
$("#cancelBatch").addEventListener("click", () => {
  $("#newBatchForm").classList.add("hidden");
  $("#newBatchBtn").textContent = "+ New batch";
});
$("#saveBatch").addEventListener("click", async () => {
  const id = $("#saveBatch").dataset.id;
  const payload = {
    name: $("#btName").value.trim(),
    method: $("#btMethod").value.trim(),
    batch_size_ml: (parseFloat($("#btSize").value) || 0)
      * U_FACTOR[$("#btUnit").value],
    shelf_life_days: $("#btShelf").value === "" ? null : parseInt($("#btShelf").value, 10),
    made_date: $("#btMade").value || undefined,
    servings: parseInt($("#btServ").value, 10) > 0 ? parseInt($("#btServ").value, 10) : null,
  };
  if (!payload.name || !payload.batch_size_ml) return toast("Name + size needed");
  const res = id ? await api("/api/batches/" + id, "PUT", payload)
                 : await api("/api/batches", "POST", payload);
  if (res && res.detail) return toast(res.detail);
  $("#newBatchForm").classList.add("hidden");
  $("#newBatchBtn").textContent = "+ New batch";
  openBatch = res.id;
  loadBatches();
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

    const orderRowsHtml = (rows, fmt) => {
      const sorted = [...rows].sort((a, b) => (b.supplier ? 1 : 0) - (a.supplier ? 1 : 0)
        || (a.supplier || "").localeCompare(b.supplier || "")
        || a.name.localeCompare(b.name));
      let out = "", last = "~";
      for (const r of sorted) {
        const g = (r.supplier || "").trim().toLowerCase();
        if (g && g !== last) out += `<tr class="supplier-g"><td colspan="4">${esc(r.supplier)}</td></tr>`;
        out += fmt(r);
        last = g || "~";
      }
      return out;
    };

    box.appendChild(section(t("order.to"), short,
      (rows) => `<thead><tr><th>${t("detail.thBottle")}</th><th class="num">${t("order.par")}</th><th class="num">${t("order.have")}</th><th class="num">${t("order.order")}</th></tr></thead>
        <tbody>${orderRowsHtml(rows, (r) => `<tr>
          <td>${esc(r.name)}</td>
          <td class="num">${fmtFbe(r.par_level)}</td>
          <td class="num">${fmtFbe(r.fbe)}</td>
          <td class="num"><span class="order-chip">+${r.to_order}</span></td></tr>`)}</tbody>`,
      t("order.none")));

  box.appendChild(section(t("order.over"), over,
    (rows) => `<thead><tr><th>${t("detail.thBottle")}</th><th class="num">${t("order.par")}</th><th class="num">${t("order.have")}</th><th class="num">${t("order.overCol")}</th><th class="num">${t("order.tied")}</th></tr></thead>
      <tbody>${orderRowsHtml(rows, (r) => `<tr>
        <td>${esc(r.name)}</td>
        <td class="num">${fmtFbe(r.par_level)}</td>
        <td class="num">${fmtFbe(r.fbe)}</td>
        <td class="num">${fmtFbe(r.excess_fbe)}</td>
        <td class="num over-amt">${eur(r.cash_asleep_eur)}</td></tr>`)}</tbody>`,
    t("order.noOver")));

  if (atPar.length) {
    const note = document.createElement("p");
    note.className = "edit-note";
    const w = atPar.length === 1 ? t("order.atParB") : t("order.atParBs");
    note.textContent = `${atPar.length} ${w} ${t("order.atPar")}`;
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
let venueCache = null;
async function getVenue() {
  if (!venueCache) venueCache = await api("/api/settings");
  return venueCache;
}
async function renderMenu() {
  const v = await getVenue();
  const title = $("#menuPrintTitle");
  title.textContent = v.name || t("menu.printTitle");
  const footer = $("#menuFooter");
  if (v.iva_pct) {
    footer.textContent = t("venue.footer").replace("{p}", v.iva_pct);
    footer.style.display = "block";
  } else {
    footer.textContent = "";
    footer.style.display = "none";
  }
  const items = await api("/api/menu");
  const onlyPriced = $("#pricedOnly").checked;
  const body = $("#menuBody");  body.innerHTML = "";
  $("#menuEmpty").classList.toggle("hidden", items.length > 0);
  const list = onlyPriced ? items.filter((m) => m.priced) : items;
  if (!list.length) {
    body.innerHTML = '<div class="edit-note">' +
      (items.length ? "Nothing priced yet — set prices in a spec or right here." : "No specs yet.") + "</div>";
    renderPnl();
    return;
  }
  // menu sections: specs grouped by category, then alphabetically
  const sorted = [...list].sort((a, b) =>
    (a.category || "").localeCompare(b.category || "") || a.name.localeCompare(b.name));
  let lastCat = null;
  for (const m of sorted) {
    const cat = (m.category || "").toLowerCase();
    if (m.category && cat !== lastCat) {
      const h = document.createElement("div");
      h.className = "menu-cat";
      h.textContent = m.category;
      body.appendChild(h);
      lastCat = cat;
    }
    if (!m.category) lastCat = null;
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
  renderPnl();
}
async function renderPnl() {
  const box = $("#pnlBox");
  try {
    const r = await api("/api/report/pnl");
    box.classList.toggle("hidden", !r.sections.length);
    if (!r.sections.length) return;
    const rows = r.sections.map((s) => {
      const m = s.margin_pct;
      const tier = m === null ? "" : m >= 60 ? "hi" : m >= 40 ? "ok" : "lo";
      const mtxt = m === null ? "—" : Math.round(m) + "%";
      return `<tr>
        <td>${esc(s.category)} <span class="edit-note">${s.spec_count}×</span></td>
        <td class="num">${eur(s.avg_cost)}</td>
        <td class="num">${s.avg_price === null ? "—" : eur(s.avg_price)}</td>
        <td class="num"><span class="pnl-chip ${tier}">${mtxt}</span></td></tr>`;
    }).join("");
    const dead = t("pnl.dead").replace("{n}", r.dead_items.length)
      .replace("{e}", eur(r.dead_stock_eur));
    box.innerHTML = `<div class="hint" style="margin:14px 0 6px;">${t("pnl.title")}</div>
      <table class="pnl"><thead><tr><th>${t("pnl.thCat")}</th>
        <th class="num">${t("pnl.thCost")}</th><th class="num">${t("pnl.thPrice")}</th>
        <th class="num">${t("pnl.thMargin")}</th></tr></thead>
      <tbody>${rows}</tbody></table>
      ${r.dead_items.length ? `<div class="edit-note" style="margin-top:8px;">${esc(dead)}</div>` : ""}`;
  } catch (err) { /* non-fatal; menu still renders */ }
}

// ---------- wiring ----------
$("#newSpecBtn").addEventListener("click", () => { editSpecForm(null); });
$("#navSpecs").addEventListener("click", () => showView("specs"));
$("#navBatches").addEventListener("click", () => showView("batches"));
document.querySelectorAll(".setopt[data-lang]").forEach((b) =>
  b.addEventListener("click", () => setLang(b.dataset.lang)));
document.querySelectorAll("#fontBox .fontbtn").forEach((b) =>
  b.addEventListener("click", () => setFont(b.dataset.fs)));
$("#navStock").addEventListener("click", () => showView("stock"));
$("#navTake").addEventListener("click", () => showView("stocktake"));
$("#navMenu").addEventListener("click", () => showView("menu"));
$("#printMenuBtn").addEventListener("click", () => window.print());
$("#pricedOnly").addEventListener("change", renderMenu);
$("#venueBtn").addEventListener("click", async () => {
  const form = $("#venueForm");
  if (form.classList.contains("hidden")) {
    const v = await getVenue();
    $("#vName").value = v.name || "";
    $("#vIva").value = v.iva_pct ?? "";
    form.classList.remove("hidden");
  } else form.classList.add("hidden");
});
$("#saveVenue").addEventListener("click", async () => {
  const iva = parseFloat($("#vIva").value);
  venueCache = await api("/api/settings", "PUT", {
    name: $("#vName").value.trim(),
    iva_pct: isNaN(iva) ? null : iva,
  });
  $("#venueForm").classList.add("hidden");
  renderMenu();
  toast(t("venue.saved"));
});
$("#cancelVenue").addEventListener("click", () => $("#venueForm").classList.add("hidden"));
function dl(url, name) {
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
}
$("#exportSpecsBtn").addEventListener("click", () => dl("/api/export/specs.xlsx", "barspec-specs.xlsx"));
$("#exportStockBtn").addEventListener("click", () => dl("/api/export/stock.xlsx", "barspec-stock.xlsx"));
$("#qrMenuBtn").addEventListener("click", async () => {
  const url = location.origin + location.pathname + "?view=menu";
  try {
    const svg = await (await fetch("/api/export/menu-qr.svg?url=" + encodeURIComponent(url))).text();
    $("#qrSvg").innerHTML = svg;
    $("#qrUrl").textContent = url;
    $("#qrOverlay").classList.remove("hidden");
  } catch (err) { toast("QR failed: " + err.message); }
});
$("#qrClose").addEventListener("click", () => $("#qrOverlay").classList.add("hidden"));
$("#qrOverlay").addEventListener("click", (e) => {
  if (e.target.id === "qrOverlay") $("#qrOverlay").classList.add("hidden");
});

// ---------- training cards (011): print a deck, never a cost ----------
const cardAmt = (l) => `${fmtAmt(l.amount_ml)} ${l.unit || "ml"}`;
function cardHtml(d) {
  const facts = [d.glass, d.method, d.garnish].filter(Boolean).join(" · ");
  const dil = d.summary && d.summary.dilution_pct > 0
    ? ` · ~${d.summary.dilution_pct}% dilution` : "";
  const lines = d.lines.map((l) =>
    `<li><span class="card-amt">${esc(cardAmt(l))}</span> ${esc(l.name)}</li>`).join("");
  return `<div class="tcard">
    <div class="tcard-head"><b>${esc(d.name)}</b>
      ${d.category ? `<span class="tcard-cat">${esc(d.category)}</span>` : ""}</div>
    <div class="tcard-facts">${esc(facts)}${esc(dil)}</div>
    ${badgesHtml(d)}
    <ol class="tcard-lines">${lines}</ol>
  </div>`;
}
async function buildCardsDeck() {
  // honors the current chips filter + search box — the deck prints what you see
  const q = ($("#specSearch").value || "").trim().toLowerCase();
  const all = await api("/api/specs");
  const keep = all.filter((s) => {
    const okCat = currentCat === "__all__" || (s.category || "").toLowerCase() === currentCat;
    return okCat && (!q || s.name.toLowerCase().includes(q));
  });
  const full = [];
  for (const s of keep) full.push(await api("/api/specs/" + s.id));
  full.sort((a, b) =>
    (a.category || "").localeCompare(b.category || "") || a.name.localeCompare(b.name));
  let last = null, html = "";
  for (const d of full) {
    const cat = (d.category || "").toLowerCase();
    if (d.category && cat !== last) html += `<div class="tcard-group">${esc(d.category)}</div>`;
    if (!d.category) last = null;
    html += cardHtml(d);
    last = cat;
  }
  $("#cardsDeck").innerHTML = html;
}
$("#printCardsBtn").addEventListener("click", async () => {
  await buildCardsDeck();
  document.body.classList.add("printing-cards");
  window.print();
});
window.addEventListener("afterprint", () =>
  document.body.classList.remove("printing-cards"));
$("#specSearch").addEventListener("input", applySearch);
$("#tabCount").addEventListener("click", () => setTakeTab("count"));
$("#tabOrder").addEventListener("click", () => { setTakeTab("order"); loadLastOrder(); });
$("#tabTrends").addEventListener("click", () => { setTakeTab("trends"); renderTrends(); });
$("#saveTakeBtn").addEventListener("click", saveTake);
$("#newCountBtn").addEventListener("click", () => { loadStocktake(); setTakeTab("count"); });
$("#setBtn").addEventListener("click", async () => {
  applyUnitLabels();
  document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.unit === unit));
  renderAudit();
  $("#setOverlay").classList.remove("hidden");
});
const AUDIT_VERB = { price: "◈", spec_price: "◈", deleted: "✕", adjusted: "±", added: "+" };
async function renderAudit() {
  const box = $("#auditBox");
  try {
    const rows = await api("/api/audit?limit=6");
    box.innerHTML = rows.length
      ? rows.map((r) =>
          `<div class="audit-line">${AUDIT_VERB[r.action] || "•"}
            <span class="edit-note">${esc((r.created_at || "").slice(5, 16))}</span>
            ${esc(r.target)} <span class="edit-note">${esc(r.detail)}</span></div>`).join("")
      : `<div class="edit-note">${t("audit.none")}</div>`;
  } catch (err) { box.innerHTML = `<div class="edit-note">—</div>`; }
}
$("#setClose").addEventListener("click", () => $("#setOverlay").classList.add("hidden"));
$("#lockBtn").addEventListener("click", async () => {
  await api("/api/auth/logout", "POST").catch(() => {});
  location.reload();
});
$("#setOverlay").addEventListener("click", (e) => {
  if (e.target.id === "setOverlay") $("#setOverlay").classList.add("hidden");
});
document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
  b.addEventListener("click", () => setUnit(b.dataset.unit)));
window.addEventListener("beforeunload", (e) => {
  if (!takeDirty) return;
  e.preventDefault();
  e.returnValue = "";
});

window.addEventListener("load", async () => {
  applyI18n();
  applyFont();
  updateChrome();
  const st = await api("/api/auth/status").catch(() => ({ set: false }));
  if (!st.set) { showAuth("setup"); return; }
  try {
    await refreshStockMap();
    $("#authOverlay").classList.add("hidden");
  } catch (err) {
    if ((err.status || 0) === 401) { showAuth("login"); return; }
  }
  const qv = new URLSearchParams(location.search).get("view");
  document.querySelectorAll("#unitBox .unitbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.unit === unit));
  applyUnitLabels();
  await refreshStockMap();
  takeBadge();
  if (qv && VIEWS[qv]) { showView(qv); return; }
  loadSpecs(false);
  try {
    const m = await api("/api/menu");
    $("#countMenu").textContent = m.length;
  } catch (_) {}
});
