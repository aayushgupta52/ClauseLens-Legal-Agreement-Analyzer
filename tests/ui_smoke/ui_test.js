const { JSDOM, VirtualConsole } = require("jsdom");
const BASE = process.env.CLAUSELENS_URL || "http://127.0.0.1:8000";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, label, ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { try { if (fn()) return; } catch (e) {} await sleep(100); }
  throw new Error("timeout waiting for: " + label);
}
(async () => {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { if (!/not implemented/i.test(String(e.message))) errors.push(String(e.message)); });
  const dom = await JSDOM.fromURL(BASE + "/", {
    runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, BASE), o); w.scrollTo = () => {}; },
  });
  const d = dom.window.document, $ = (id) => d.getElementById(id);
  const ok = (c, m) => { if (!c) throw new Error("FAILED: " + m); console.log("ok  -", m); };

  await waitFor(() => $("engine").textContent.includes("tfidf"), "engine label");
  ok(true, "page loads and shows engine: " + $("engine").textContent);

  $("loadSample").click();
  await waitFor(() => $("text").value.length > 500, "sample text");
  ok(/SECURITY DEPOSIT/.test($("text").value), "sample rent agreement loaded");

  $("lang").value = "hinglish"; $("analyze").click();
  await waitFor(() => !$("result").classList.contains("hidden"), "result");
  ok(d.querySelectorAll(".clause").length >= 10, "clause cards rendered: " + d.querySelectorAll(".clause").length);
  ok(/\d+/.test(d.querySelector(".big").textContent), "risk score shown: " + d.querySelector(".big").textContent);
  ok(d.querySelectorAll(".clause.red").length + d.querySelectorAll(".clause.amber").length > 0, "risky clauses are colour-coded");
  const total = d.querySelectorAll(".clause").length;
  d.querySelector('#filters button[data-f="red"]').click();
  ok(d.querySelectorAll(".clause").length < total && [...d.querySelectorAll(".clause")].every((c) => c.classList.contains("red")), "red filter works");
  d.querySelector('#filters button[data-f="all"]').click();
  ok(d.querySelectorAll(".clause").length === total, "all filter restores clauses");
  ok(/Dhyan|Zyada|Theek/.test(d.body.textContent), "Hinglish labels shown");

  $("q").value = "Security deposit kitna hai?"; $("askBtn").click();
  await waitFor(() => d.querySelectorAll(".msg.b").length === 1, "answer");
  ok(/deposit/i.test(d.querySelector(".msg.b").textContent), "Q&A answered with deposit clause");

  await waitFor(() => d.querySelectorAll("#history button").length >= 1, "history item");
  ok(true, "history lists saved report");

  // offer + bond sample: bond calculator
  $("sample").value = "offer_and_bond"; $("loadSample").click();
  await waitFor(() => /SERVICE BOND/.test($("text").value), "offer sample");
  $("lang").value = "en"; $("analyze").click();
  await waitFor(() => /offer and bond/i.test($("result").textContent), "offer result");
  ok(!$("bondCard").classList.contains("hidden"), "bond calculator visible for bond documents");
  $("bAmt").value = 120000; $("bMon").value = 12; $("bSrv").value = 3; $("bMode").value = "pro_rata"; $("bGo").click();
  await waitFor(() => /90,000/.test($("bOut").textContent), "bond result");
  ok(true, "bond calculator: " + $("bOut").textContent);

  // XSS: hostile text must be shown as text, never executed
  $("text").value = "1. SECURITY DEPOSIT: <img src=x onerror=window.__pwned=1> The Tenant pays a refundable security deposit of Rs. 50,000/- refunded within 30 days.\n";
  $("analyze").click();
  await waitFor(() => /img src/.test($("result").textContent), "xss result");
  ok(d.querySelectorAll("#result img").length === 0 && !dom.window.__pwned, "hostile HTML is escaped (no <img> created, no script run)");

  // Model Lab tab
  d.querySelector('nav button[data-view="lab"]').click();
  await waitFor(() => $("lab").textContent.length > 5 && !$("lab").textContent.includes("loading"), "lab");
  ok(true, "Model Lab tab renders: " + $("lab").textContent.slice(0, 50).replace(/\s+/g, " "));

  ok(errors.length === 0, "no JavaScript errors" + (errors.length ? ": " + errors.join(" | ") : ""));
  dom.window.close();
})().catch((e) => { console.error(String(e)); process.exit(1); });
