// BarSpec end-to-end smoke — the regression net the manual browser QA used
// to be. Boots the real app (main.py) against a throwaway DB, drives the UI
// through the owner flows, asserts, tears down. Exit 0 = everything works.
//
// Run:  npm run e2e        (needs node + the ms-playwright chromium cache)
import { spawn } from "node:child_process";
import { existsSync, readdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright-core";

const REPO = new URL("..", import.meta.url).pathname;
const PORT = 8891;
const BASE = `http://127.0.0.1:${PORT}`;

function findChromium() {
  const cache = join(process.env.HOME, ".cache", "ms-playwright");
  for (const dir of readdirSync(cache)) {
    if (!dir.startsWith("chromium-")) continue;
    for (const name of ["chrome-linux64/chrome", "chrome-linux/chrome"]) {
      const p = join(cache, dir, name);
      if (existsSync(p)) return p;
    }
  }
  throw new Error("chromium not found in ~/.cache/ms-playwright");
}

let server, page, passed = 0, failed = 0;
const results = [];
function ok(name, cond, extra = "") {
  (cond ? (passed++, results.push(`  ✅ ${name}`))
        : (failed++, results.push(`  ❌ ${name} ${extra}`)));
}

// launch the app on a fresh temp DB
async function boot() {
  const db = join(mkdtempSync(join(tmpdir(), "bs-e2e-")), "e2e.db");
  server = spawn(".venv/bin/python", ["-m", "uvicorn", "main:app",
    "--host", "127.0.0.1", "--port", String(PORT)], {
    cwd: REPO, env: { ...process.env, BARSPEC_DB: db }, stdio: "ignore",
  });
  for (let i = 0; i < 40; i++) {
    try { await fetch(BASE + "/api/auth/status"); return; } catch { await sleep(500); }
  }
  throw new Error("server did not come up");
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function txt(sel) {
  const el = await page.$(sel);
  return el ? (await el.innerText()).trim() : null;
}

const flows = [
  {
    name: "PIN setup locks then unlocks",
    run: async () => {
      ok("setup overlay shows (fresh DB, no PIN)",
        (await txt("#authTitle")).includes("PIN"));
      await page.fill("#authPin", "4321");
      await page.click("#authGo");
      // setup POST -> location.reload(): wait across the reload, not before it
      await page.waitForFunction(() =>
        document.querySelectorAll("#specList .spec-item").length === 5,
        { timeout: 15000 });
      ok("unlocks to the app", await page.$("#specList .spec-item") !== null);
      const specCount = await page.$$eval("#specList .spec-item", (x) => x.length);
      ok("seed: 5 specs", specCount === 5, `(got ${specCount})`);
      // Summary is the homepage now — go to Specs to work with the list
      ok("homepage is the Summary view", (await page.$eval("body", (b) => b.dataset.view)) === "resumo");
      await page.click("#navSpecs");
      await page.waitForSelector("#specList .spec-item", { state: "visible", timeout: 6000 });
    },
  },
  {
    name: "open a spec, read the honest numbers",
    run: async () => {
      const negroni = page.locator("#specList .spec-item").filter({ hasText: "Negroni" }).first();
      ok("Negroni is seeded", (await negroni.count()) === 1);
      await negroni.click();
      await page.waitForSelector("#detail", { timeout: 8000 });
      await sleep(400);
      const cost = await txt("#detail");
      ok("detail shows a € cost", (cost || "").includes("€"));
    },
  },
  {
    name: "PT toggle: chrome + € comma",
    run: async () => {
      await page.click("#setBtn");
      await sleep(300);
      await page.click(".setopt[data-lang=pt]");
      await sleep(1500);
      const titleTxt = (await txt("#viewTitle")) || "";
      ok("title flips to Receitas", titleTxt.includes("Receitas"), `(got '${titleTxt}')`);
      const listText = await page.$eval("#specList", (el) => el.innerText);
      ok("PT euro comma (€8,00)", /€\d+,\d{2}/.test(listText), `(${listText.slice(0, 60)})`);
      await page.click("#setClose");   // close the dialog or it blocks nav clicks
      await sleep(300);
    },
  },
  {
    name: "stock filter finds gin only",
    run: async () => {
      await page.click("#navStock");
      await page.waitForSelector("#stockBody tr", { timeout: 6000 });
      await page.fill("#stockSearch", "gin");
      await sleep(200);
      const visible = await page.$$eval("#stockBody tr",
        (rows) => rows.filter((r) => r.style.display !== "none").length);
      ok("filter: 1 row for 'gin'", visible === 1, `(got ${visible})`);
      const name = await page.$eval("#stockBody tr",
        (tr) => {
          const vis = [...document.querySelectorAll("#stockBody tr")]
            .find((r) => r.style.display !== "none");
          return vis?.querySelector("input[data-k=name]")?.value || "";
        });
      ok("that row is London dry gin", name.includes("gin"), `(got '${name}')`);
    },
  },
  {
    name: "sales view is visible and lists priced specs",
    run: async () => {
      await page.click("#navSales");
      await page.waitForSelector("#view-sales", { state: "visible", timeout: 6000 });
      await page.waitForSelector("#sSpec", { state: "visible", timeout: 6000 });
      await page.waitForFunction(() => document.querySelectorAll("#sSpec option").length > 0,
        null, { timeout: 6000 });
      const opts = await page.$$eval("#sSpec option", (os) => os.length);
      ok("sales view visible with spec options", opts >= 5, `(got ${opts})`);
      await page.click("#navSpecs");
    },
  },
  {
    name: "menu renders grouped categories",
    run: async () => {
      await page.click("#navMenu");
      await page.waitForSelector("#menuBody .m-name", { timeout: 6000 });
      const rows = await page.$$eval("#menuBody .m-name", (xs) => xs.length);
      ok("menu lists specs", rows >= 4, `(got ${rows})`);
    },
  },
  {
    // 039 regression: openPOOverlay used to call renderPO() while the overlay
    // was still hidden, and renderPO early-returns when hidden -> the Orders
    // panel always opened EMPTY. Assert it renders an open PO with a Receive
    // button, using the page's own owner session.
    name: "orders overlay renders an open PO (regression)",
    run: async () => {
      const made = await page.evaluate(async () => {
        const items = await api("/api/stock");
        const res = await api("/api/pos", "POST",
          { supplier: "E2E Supplier", lines: [{ stock_item_id: items[0].id, qty: 2 }] });
        return !!res && res.status === "open";
      });
      ok("PO created via API", made);
      await page.click("#poBtn");
      await page.waitForSelector("#poOverlay:not(.hidden)", { timeout: 6000 });
      await page.waitForTimeout(900);
      const box = await page.$eval("#poOpen", (el) => el.innerText || "");
      ok("open PO row visible", box.includes("E2E Supplier"), box.slice(0, 60));
      ok("receive button present", await page.$("#poOpen [data-rec-po]") !== null);
      await page.click("#poClose");
    },
  },
];

async function main() {
  const browser = await chromium.launch({ executablePath: findChromium() });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  page = await ctx.newPage();
  await boot();
  await page.goto(BASE + "/", { waitUntil: "load" });
  for (const f of flows) {
    try { await f.run(); } catch (e) { failed++; results.push(`  ❌ ${f.name}: ${e.message}`); }
  }
  await browser.close();
  server.kill();
  console.log(`\nBarSpec e2e — ${passed} passed, ${failed} failed`);
  console.log(results.join("\n"));
  process.exit(failed ? 1 : 0);
}
main().catch(async (e) => { console.error("e2e crashed:", e.message); server?.kill(); process.exit(2); });
