"use strict";

// ---- state ----
const state = {
  token: localStorage.getItem("token") || null,
  role: localStorage.getItem("role") || null,
  username: localStorage.getItem("username") || null,
  mfaUserId: null,
  currentOrderId: null,
};

// ---- api helper ----
async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });
  let data = null;
  const text = await res.text();
  if (text) { try { data = JSON.parse(text); } catch { data = text; } }
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : res.statusText;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status; err.detail = detail;
    throw err;
  }
  return data;
}

// ---- ui helpers ----
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function toast(msg, kind = "") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + kind;
  setTimeout(() => t.classList.add("hidden"), 3200);
}
function setMsg(sel, msg, kind = "") { const el = $(sel); if (el) { el.textContent = msg; el.className = "msg " + kind; } }
function pill(state) { return `<span class="pill ${state}">${state}</span>`; }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function showView(name) {
  $$(".view").forEach(v => v.classList.add("hidden"));
  const view = $("#view-" + name);
  if (view) view.classList.remove("hidden");
  $$(".navbtn").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  if (name === "orders") loadOrders();
  if (name === "catalog") loadCatalog();
  if (name === "admin") loadConfig();
}

function applyAuthUI() {
  const authed = !!state.token;
  $("#topbar").classList.toggle("hidden", !authed);
  $("#view-login").classList.toggle("hidden", authed);
  $("#whoami").textContent = authed ? `${state.username} (${state.role})` : "";
  $$(".admin-only").forEach(el => el.classList.toggle("hidden", state.role !== "ADMIN"));
  if (authed) showView("orders"); else { $$(".view").forEach(v => v.classList.add("hidden")); $("#view-login").classList.remove("hidden"); }
}

// decode role from JWT payload (no verification, just display/gating convenience)
function roleFromToken(token) {
  try { return JSON.parse(atob(token.split(".")[1])).role || "CLIENT_USER"; }
  catch { return "CLIENT_USER"; }
}

// ---- auth ----
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  setMsg("#loginMsg", "");
  const f = e.target;
  try {
    const r = await api("/auth/login", { method: "POST", auth: false, body: { username: f.username.value, password: f.password.value } });
    if (r.mfa_required) {
      state.mfaUserId = r.user_id;
      $("#mfaBlock").classList.remove("hidden");
      setMsg("#loginMsg", "MFA required — enter your code.", "");
      return;
    }
    finishLogin(r.token, f.username.value);
  } catch (err) { setMsg("#loginMsg", err.message, "err"); }
});

$("#mfaForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await api("/auth/mfa/verify", { method: "POST", auth: false, body: { user_id: state.mfaUserId, code: e.target.code.value } });
    finishLogin(r.token, $("#loginForm").username.value);
  } catch (err) { setMsg("#loginMsg", err.message, "err"); }
});

function finishLogin(token, username) {
  state.token = token;
  state.username = username;
  state.role = roleFromToken(token);
  localStorage.setItem("token", token);
  localStorage.setItem("username", username);
  localStorage.setItem("role", state.role);
  $("#mfaBlock").classList.add("hidden");
  applyAuthUI();
  toast("Signed in as " + username, "ok");
}

$("#logoutBtn").addEventListener("click", () => {
  state.token = state.role = state.username = null;
  localStorage.clear();
  applyAuthUI();
});

// ---- nav ----
$$(".navbtn").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));

// ---- orders ----
async function loadOrders() {
  const body = $("#ordersBody");
  body.innerHTML = `<tr><td colspan="5" class="empty">Loading...</td></tr>`;
  try {
    const orders = await api("/orders");
    if (!orders.length) { body.innerHTML = `<tr><td colspan="5" class="empty">No orders yet. Use "New Order".</td></tr>`; return; }
    body.innerHTML = orders.map(o => `
      <tr>
        <td><code>${esc(o.order_id).slice(0, 8)}</code></td>
        <td>${esc(o.client_reference)}</td>
        <td>${pill(o.lifecycle_state)}</td>
        <td>${esc(o.erp_reference || "—")}</td>
        <td><button class="link" data-open="${esc(o.order_id)}">View</button></td>
      </tr>`).join("");
    $$("[data-open]").forEach(b => b.addEventListener("click", () => openOrder(b.dataset.open)));
  } catch (err) { body.innerHTML = `<tr><td colspan="5" class="empty">${esc(err.message)}</td></tr>`; }
}
$("#refreshOrders").addEventListener("click", loadOrders);

async function openOrder(id) {
  state.currentOrderId = id;
  try {
    const o = await api("/orders/" + id);
    const h = await api("/orders/" + id + "/history");
    $("#orderDetail").classList.remove("hidden");
    $("#detailBody").innerHTML = `
      <div class="kv"><b>Order ID:</b> ${esc(o.order_id)}</div>
      <div class="kv"><b>Reference:</b> ${esc(o.client_reference)}</div>
      <div class="kv"><b>State:</b> ${pill(o.lifecycle_state)}</div>
      <div class="kv"><b>ERP reference:</b> ${esc(o.erp_reference || "—")}</div>`;
    $("#historyList").innerHTML = (h.history || []).map(e =>
      `<li>${pill(e.state)}<span class="ts">${esc(e.occurred_at)}</span>${e.reason ? `<span class="reason">${esc(e.reason)}</span>` : ""}</li>`
    ).join("") || `<li class="hint">No history yet.</li>`;
    setMsg("#detailMsg", "");
  } catch (err) { toast(err.message, "err"); }
}
$("#closeDetail").addEventListener("click", () => $("#orderDetail").classList.add("hidden"));

$$("#orderDetail [data-action]").forEach(btn => btn.addEventListener("click", async () => {
  const action = btn.dataset.action;
  if (!state.currentOrderId) return;
  if (action === "amend") { showView("place"); prepAmend(state.currentOrderId); return; }
  try {
    await api(`/orders/${state.currentOrderId}/${action}`, { method: "POST" });
    setMsg("#detailMsg", `${action} accepted — worker will process it shortly.`, "ok");
    toast(`${action} accepted`, "ok");
    setTimeout(() => { openOrder(state.currentOrderId); loadOrders(); }, 1500);
  } catch (err) { setMsg("#detailMsg", err.message, "err"); }
}));

// ---- place / amend order ----
let amendId = null;
function addLine(pk = "P1", qty = 1, uom = "EA") {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input class="li-pk" value="${esc(pk)}" /></td>
                  <td><input class="li-qty" type="number" min="1" value="${esc(qty)}" style="width:90px" /></td>
                  <td><input class="li-uom" value="${esc(uom)}" style="width:90px" /></td>
                  <td><button type="button" class="link li-del">remove</button></td>`;
  $("#linesBody").appendChild(tr);
  tr.querySelector(".li-del").addEventListener("click", () => tr.remove());
}
$("#addLine").addEventListener("click", () => addLine());

function prepAmend(id) {
  amendId = id;
  $("#amendNote").classList.remove("hidden");
  $("#amendNote").textContent = `Amending order ${id.slice(0, 8)} — submit to send amendment.`;
}

$("#orderForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const lines = $$("#linesBody tr").map(tr => ({
    product_key: tr.querySelector(".li-pk").value,
    quantity: Number(tr.querySelector(".li-qty").value),
    unit_of_measure: tr.querySelector(".li-uom").value,
  }));
  const payload = {
    client_reference: f.client_reference.value,
    order_date: f.order_date.value,
    currency: f.currency.value,
    notes: f.notes.value || null,
    ship_to: {
      name: f.st_name.value, lines: [f.st_line.value], city: f.st_city.value,
      region: f.st_region.value || null, postal_code: f.st_postal.value || null, country: f.st_country.value,
    },
    line_items: lines,
  };
  try {
    if (amendId) {
      await api(`/orders/${amendId}/amend`, { method: "POST", body: payload });
      setMsg("#orderMsg", "Amendment accepted.", "ok"); toast("Amendment accepted", "ok");
      amendId = null; $("#amendNote").classList.add("hidden");
    } else {
      const r = await api("/orders", { method: "POST", body: payload });
      setMsg("#orderMsg", `Order ${r.order_id.slice(0, 8)} placed (${r.lifecycle_state}).`, "ok");
      toast("Order placed", "ok");
    }
    setTimeout(() => showView("orders"), 900);
  } catch (err) {
    const d = err.detail;
    const msg = Array.isArray(d) ? d.map(x => `${x.path}: ${x.message}`).join("; ") : err.message;
    setMsg("#orderMsg", msg, "err");
  }
});

// ---- catalog ----
async function loadCatalog() {
  const q = $("#catalogSearch").value.trim();
  const body = $("#catalogBody");
  body.innerHTML = `<tr><td colspan="4" class="empty">Loading...</td></tr>`;
  try {
    const products = await api("/catalog" + (q ? "?q=" + encodeURIComponent(q) : ""));
    if (!products.length) { body.innerHTML = `<tr><td colspan="4" class="empty">No products.</td></tr>`; return; }
    body.innerHTML = products.map(p => `
      <tr>
        <td><code>${esc(p.product_key)}</code></td>
        <td>${esc(p.name)}</td>
        <td>${esc(p.description || "")}</td>
        <td><span data-inv="${esc(p.product_key)}" class="hint">check...</span></td>
      </tr>`).join("");
    // fetch inventory per product
    for (const el of $$("[data-inv]")) {
      const key = el.getAttribute("data-inv");
      try { const inv = await api("/inventory/" + encodeURIComponent(key)); el.textContent = `${inv.available_quantity} ${inv.unit_of_measure}`; el.className = ""; }
      catch { el.textContent = "unavailable"; }
    }
  } catch (err) { body.innerHTML = `<tr><td colspan="4" class="empty">${esc(err.message)}</td></tr>`; }
}
$("#catalogSearchBtn").addEventListener("click", loadCatalog);

// ---- admin ----
$("#instanceForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  try {
    const r = await api("/admin/instances", { method: "POST", body: { erp_type: f.erp_type.value, display_name: f.display_name.value, connection_ref: f.connection_ref.value } });
    setMsg("#instMsg", `Registered ${r.instance_id}`, "ok"); toast("Instance registered", "ok");
    loadConfig();
  } catch (err) { setMsg("#instMsg", err.message, "err"); }
});

$("#ruleForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  let value = f.value.value;
  if (f.operator.value === "IN") value = value.split(",").map(s => s.trim());
  const payload = { order_index: Number(f.order_index.value), conditions: [{ field: f.field.value, operator: f.operator.value, value }], target_instance_id: f.target_instance_id.value, enabled: true };
  try {
    const r = await api("/admin/routing-rules", { method: "POST", body: payload });
    setMsg("#ruleMsg", `Rule ${r.rule_id} added`, "ok"); toast("Routing rule added", "ok");
    loadConfig();
  } catch (err) { setMsg("#ruleMsg", err.message, "err"); }
});

$("#mappingForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  const entries = f.entries.value.split("\n").map(l => l.trim()).filter(Boolean).map(l => {
    const [src, tgt] = l.split(":"); return { source_path: (src || "").trim(), target_path: (tgt || "").trim() };
  });
  try {
    const r = await api("/admin/mappings", { method: "POST", body: { instance_id: f.instance_id.value, data_type: f.data_type.value, direction: f.direction.value, field_entries: entries } });
    const warn = r.warnings && r.warnings.length ? " Warnings: " + r.warnings.join("; ") : "";
    setMsg("#mapMsg", `Mapping ${r.mapping_id} saved.${warn}`, warn ? "" : "ok"); toast("Mapping saved", "ok");
    loadConfig();
  } catch (err) { setMsg("#mapMsg", err.message, "err"); }
});

async function loadConfig() {
  if (state.role !== "ADMIN") return;
  try {
    const cfg = await api("/admin/config");
    // populate instance selects
    const opts = cfg.instances.map(i => `<option value="${esc(i.instance_id)}">${esc(i.display_name)} (${esc(i.instance_id)})</option>`).join("");
    $("#ruleInstanceSelect").innerHTML = opts || `<option value="">(register an instance first)</option>`;
    $("#mapInstanceSelect").innerHTML = opts || `<option value="">(register an instance first)</option>`;
    // render config
    $("#configBody").innerHTML = `
      <div class="config-section"><h4>Instances (${cfg.instances.length})</h4>
        ${cfg.instances.map(i => `<div class="kv">${esc(i.display_name)} — ${esc(i.erp_type)} — <code>${esc(i.instance_id)}</code> — ${esc(i.status)}</div>`).join("") || '<div class="hint">none</div>'}</div>
      <div class="config-section"><h4>Routing rules (${cfg.routing_rules.length})</h4>
        ${cfg.routing_rules.map(r => `<div class="kv">#${r.order_index} → <code>${esc(r.target_instance_id)}</code> ${r.enabled ? "" : "(disabled)"}</div>`).join("") || '<div class="hint">none</div>'}</div>
      <div class="config-section"><h4>Mappings (${cfg.mappings.length})</h4>
        ${cfg.mappings.map(m => `<div class="kv"><code>${esc(m.instance_id)}</code> — ${esc(m.data_type)} — ${esc(m.direction)}</div>`).join("") || '<div class="hint">none</div>'}</div>`;
  } catch (err) { toast(err.message, "err"); }
}
$("#refreshConfig").addEventListener("click", loadConfig);

// ---- init ----
(function init() {
  // default order date = today
  const d = new Date().toISOString().slice(0, 10);
  const od = document.querySelector('#orderForm input[name="order_date"]');
  if (od) od.value = d;
  addLine("P1", 5, "EA");
  applyAuthUI();
})();
