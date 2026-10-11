"use strict";

requireLogin();
document.getElementById("logout-btn").addEventListener("click", logout);

const PAGE_SIZE = 20;
const state = { offset: 0, total: 0 };

const els = {
  q: document.getElementById("f-q"),
  status: document.getElementById("f-status"),
  priority: document.getElementById("f-priority"),
  category: document.getElementById("f-category"),
  sort: document.getElementById("f-sort"),
  unassigned: document.getElementById("f-unassigned"),
  unassignedRow: document.getElementById("unassigned-row"),
  body: document.getElementById("tickets-body"),
  message: document.getElementById("message"),
  prev: document.getElementById("prev-btn"),
  next: document.getElementById("next-btn"),
  info: document.getElementById("page-info"),
};

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text === null || text === undefined ? "-" : text;
  if (className) td.className = className;
  return td;
}

function badgeCell(status) {
  const td = document.createElement("td");
  const span = document.createElement("span");
  span.className = "badge " + status.toLowerCase().replace(/ /g, "-");
  span.textContent = status;
  td.appendChild(span);
  return td;
}

function renderRows(items) {
  els.body.replaceChildren();
  if (items.length === 0) {
    const tr = document.createElement("tr");
    const td = cell("No hay tickets con estos filtros");
    td.colSpan = 8;
    td.className = "muted";
    tr.appendChild(td);
    els.body.appendChild(tr);
    return;
  }
  for (const t of items) {
    const tr = document.createElement("tr");
    tr.appendChild(cell(t.id));
    tr.appendChild(cell(t.title));
    tr.appendChild(badgeCell(t.status));
    tr.appendChild(cell(t.priority_name));
    tr.appendChild(cell(t.category_name));
    tr.appendChild(cell(t.creator_name));
    tr.appendChild(cell(t.technician_name));
    tr.appendChild(cell(new Date(t.created_at).toLocaleString("es-ES")));
    els.body.appendChild(tr);
  }
}

function renderPager() {
  const page = Math.floor(state.offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
  els.info.textContent = "Página " + page + " de " + pages + " (" + state.total + " tickets)";
  els.prev.disabled = state.offset === 0;
  els.next.disabled = state.offset + PAGE_SIZE >= state.total;
}

async function loadTickets() {
  els.message.textContent = "";
  const params = new URLSearchParams({ limit: PAGE_SIZE, offset: state.offset });

  const q = els.q.value.trim();
  if (q.length >= 3) params.set("q", q);
  if (els.status.value) params.set("status", els.status.value);
  if (els.priority.value) params.set("priority_id", els.priority.value);
  if (els.category.value) params.set("category_id", els.category.value);
  if (els.unassigned.checked) params.set("unassigned", "true");
  const [sort, order] = els.sort.value.split(":");
  params.set("sort", sort);
  params.set("order", order);

  try {
    const data = await apiFetch("/tickets?" + params.toString());
    state.total = data.total;
    renderRows(data.items);
    renderPager();
  } catch (err) {
    els.message.textContent = err.message;
  }
}

function fillSelect(select, items) {
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    select.appendChild(option);
  }
}

function resetAndLoad() {
  state.offset = 0;
  loadTickets();
}

let debounceTimer;
els.q.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    const len = els.q.value.trim().length;
    if (len === 0 || len >= 3) resetAndLoad();
  }, 400);
});
for (const el of [els.status, els.priority, els.category, els.sort, els.unassigned]) {
  el.addEventListener("change", resetAndLoad);
}
els.prev.addEventListener("click", () => {
  state.offset = Math.max(0, state.offset - PAGE_SIZE);
  loadTickets();
});
els.next.addEventListener("click", () => {
  state.offset += PAGE_SIZE;
  loadTickets();
});

async function init() {
  try {
    const me = await apiFetch("/auth/me");
    document.getElementById("user-name").textContent = me.full_name + " (" + me.role + ")";
    if (me.role !== "user") els.unassignedRow.hidden = false;

    const [priorities, categories] = await Promise.all([
      apiFetch("/priorities"),
      apiFetch("/categories"),
    ]);
    fillSelect(els.priority, priorities);
    fillSelect(els.category, categories);
  } catch (err) {
    els.message.textContent = err.message;
    return;
  }
  loadTickets();
}

init();
