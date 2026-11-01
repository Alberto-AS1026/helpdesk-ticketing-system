"use strict";

requireLogin();

const PAGE_SIZE = 20;
const $ = (id) => document.getElementById(id);

// Vistas del menú lateral (?view=): título y filtros que aplican
const VIEWS = {
  mine: { title: "Mis incidentes" },
  all: { title: "Todos los incidentes" },
  assigned: { title: "Asignados a mí" },
  unassigned: { title: "Incidentes sin asignar", unassigned: true },
  open: { title: "Incidentes abiertos", status: "Abierto" },
  progress: { title: "Incidentes en progreso", status: "En progreso" },
  pending: { title: "Incidentes pendientes", status: "Pendiente" },
  resolved: { title: "Incidentes resueltos", status: "Resuelto" },
};

const state = {
  offset: 0,
  total: 0,
  sort: "created_at",
  order: "desc",
  myTechnicianId: null,
  names: { priority: {}, category: {}, tech: {} },
};

const filters = {
  q: $("f-q"),
  status: $("f-status"),
  priority: $("f-priority"),
  category: $("f-category"),
  tech: $("f-tech"),
  from: $("f-from"),
  to: $("f-to"),
  unassigned: $("f-unassigned"),
};

function cell(content) {
  const td = el("td");
  if (content instanceof Node) td.appendChild(content);
  else td.textContent = content === null || content === undefined || content === "" ? "(vacío)" : content;
  if (content === null || content === undefined) td.classList.add("empty");
  return td;
}

function renderRows(items) {
  const body = $("tickets-body");
  body.replaceChildren();
  if (items.length === 0) {
    const tr = el("tr");
    const td = el("td", "No hay registros que cumplan las condiciones", "no-records");
    td.colSpan = 8;
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }
  for (const t of items) {
    const tr = el("tr");
    const link = el("a", ticketNumber(t.id), "record-link");
    link.href = "/ticket.html?id=" + Number(t.id);
    tr.appendChild(cell(link));
    tr.appendChild(cell(t.title));
    tr.appendChild(cell(t.creator_name));
    tr.appendChild(cell(priorityTag(t.priority_name)));
    tr.appendChild(cell(statusBadge(t.status)));
    tr.appendChild(cell(t.category_name));
    tr.appendChild(cell(t.technician_name));
    tr.appendChild(cell(formatDate(t.created_at)));
    // Toda la fila abre el registro, como en las listas ITSM
    tr.addEventListener("click", (event) => {
      if (event.target.closest("a")) return;
      window.location.href = link.href;
    });
    body.appendChild(tr);
  }
}

function renderPager() {
  const from = state.total === 0 ? 0 : state.offset + 1;
  const to = Math.min(state.offset + PAGE_SIZE, state.total);
  $("page-info").textContent = from + " a " + to + " de " + state.total;
  $("list-count").textContent = state.total + (state.total === 1 ? " registro" : " registros");
  const atStart = state.offset === 0;
  const atEnd = state.offset + PAGE_SIZE >= state.total;
  $("first-btn").disabled = atStart;
  $("prev-btn").disabled = atStart;
  $("next-btn").disabled = atEnd;
  $("last-btn").disabled = atEnd;
}

function renderSortHeaders() {
  for (const btn of document.querySelectorAll(".sort-btn")) {
    const active = btn.dataset.sort === state.sort;
    btn.classList.toggle("sorted", active);
    btn.dataset.dir = active ? state.order : "";
    btn.closest("th").setAttribute("aria-sort", active ? (state.order === "asc" ? "ascending" : "descending") : "none");
  }
}

/** Migas de filtro: cada condición activa, con una × para quitarla. */
function renderBreadcrumbs() {
  const box = $("breadcrumbs");
  box.replaceChildren();
  const conditions = [];
  const q = filters.q.value.trim();
  if (q.length >= 3) conditions.push(["Texto contiene «" + q + "»", () => { filters.q.value = ""; }]);
  if (filters.status.value) conditions.push(["Estado = " + filters.status.value, () => { filters.status.value = ""; }]);
  if (filters.priority.value) {
    conditions.push(["Prioridad = " + priorityLabel(state.names.priority[filters.priority.value]), () => { filters.priority.value = ""; }]);
  }
  if (filters.category.value) {
    conditions.push(["Categoría = " + state.names.category[filters.category.value], () => { filters.category.value = ""; }]);
  }
  if (filters.tech.value) {
    conditions.push(["Asignado a = " + (state.names.tech[filters.tech.value] || "técnico"), () => { filters.tech.value = ""; }]);
  }
  if (filters.unassigned.checked) conditions.push(["Asignado a está vacío", () => { filters.unassigned.checked = false; }]);
  if (filters.from.value) conditions.push(["Creado ≥ " + filters.from.value, () => { filters.from.value = ""; }]);
  if (filters.to.value) conditions.push(["Creado ≤ " + filters.to.value, () => { filters.to.value = ""; }]);

  const root = el("button", "Todos", "crumb crumb-root");
  root.type = "button";
  root.title = "Quitar todas las condiciones";
  root.addEventListener("click", () => {
    clearFilters();
    resetAndLoad();
  });
  box.appendChild(root);

  for (const [label, remove] of conditions) {
    box.appendChild(el("span", ">", "crumb-sep"));
    const chip = el("span", null, "crumb");
    chip.appendChild(el("span", label));
    const x = el("button", "×", "crumb-x");
    x.type = "button";
    x.setAttribute("aria-label", "Quitar condición: " + label);
    x.addEventListener("click", () => {
      remove();
      resetAndLoad();
    });
    chip.appendChild(x);
    box.appendChild(chip);
  }
}

async function loadTickets() {
  $("message").textContent = "";
  const params = new URLSearchParams({ limit: PAGE_SIZE, offset: state.offset, sort: state.sort, order: state.order });
  const q = filters.q.value.trim();
  if (q.length >= 3) params.set("q", q);
  if (filters.status.value) params.set("status", filters.status.value);
  if (filters.priority.value) params.set("priority_id", filters.priority.value);
  if (filters.category.value) params.set("category_id", filters.category.value);
  if (filters.tech.value) params.set("technician_id", filters.tech.value);
  if (filters.unassigned.checked) params.set("unassigned", "true");
  if (filters.from.value) params.set("created_from", filters.from.value);
  if (filters.to.value) params.set("created_to", filters.to.value);

  renderBreadcrumbs();
  renderSortHeaders();
  try {
    const data = await apiFetch("/tickets?" + params.toString());
    state.total = data.total;
    renderRows(data.items);
    renderPager();
  } catch (err) {
    $("message").textContent = err.message;
  }
}

function clearFilters() {
  for (const key of ["q", "status", "priority", "category", "tech", "from", "to"]) filters[key].value = "";
  filters.unassigned.checked = false;
}

function resetAndLoad() {
  state.offset = 0;
  loadTickets();
}

function fillSelect(select, items, nameMap, label = (i) => i.name) {
  for (const item of items) {
    const option = el("option", label(item));
    option.value = item.id;
    nameMap[item.id] = item.name;
    select.appendChild(option);
  }
}

// ----- Eventos -----

let debounceTimer;
filters.q.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    const len = filters.q.value.trim().length;
    if (len === 0 || len >= 3) resetAndLoad();
  }, 400);
});
for (const key of ["status", "priority", "category", "tech", "from", "to", "unassigned"]) {
  filters[key].addEventListener("change", resetAndLoad);
}

$("filter-btn").addEventListener("click", () => {
  const panel = $("filter-panel");
  panel.hidden = !panel.hidden;
  $("filter-btn").setAttribute("aria-expanded", String(!panel.hidden));
});
$("clear-btn").addEventListener("click", () => {
  clearFilters();
  resetAndLoad();
});

for (const btn of document.querySelectorAll(".sort-btn")) {
  btn.addEventListener("click", () => {
    if (state.sort === btn.dataset.sort) {
      state.order = state.order === "asc" ? "desc" : "asc";
    } else {
      state.sort = btn.dataset.sort;
      state.order = btn.dataset.sort === "status" ? "asc" : "desc";
    }
    resetAndLoad();
  });
}

$("first-btn").addEventListener("click", () => { state.offset = 0; loadTickets(); });
$("prev-btn").addEventListener("click", () => { state.offset = Math.max(0, state.offset - PAGE_SIZE); loadTickets(); });
$("next-btn").addEventListener("click", () => { state.offset += PAGE_SIZE; loadTickets(); });
$("last-btn").addEventListener("click", () => {
  state.offset = Math.max(0, Math.floor((state.total - 1) / PAGE_SIZE) * PAGE_SIZE);
  loadTickets();
});

// ----- Arranque -----

async function init() {
  const params = new URLSearchParams(window.location.search);
  let me;
  try {
    me = await loadCurrentUser();
    const staff = me.role !== "user";
    for (const node of document.querySelectorAll("[data-staff]")) node.hidden = !staff;

    const [priorities, categories] = await Promise.all([apiFetch("/priorities"), apiFetch("/categories")]);
    // De más a menos grave, como en las herramientas ITSM
    priorities.sort((a, b) => (PRIORITY_RANK[a.name] || 9) - (PRIORITY_RANK[b.name] || 9));
    fillSelect(filters.priority, priorities, state.names.priority, (p) => priorityLabel(p.name));
    fillSelect(filters.category, categories, state.names.category);

    if (staff) {
      const [techs, users] = await Promise.all([apiFetch("/technicians"), apiFetch("/users")]);
      const names = Object.fromEntries(users.map((u) => [u.id, u.full_name]));
      fillSelect(filters.tech, techs.map((t) => ({ id: t.id, name: names[t.user_id] || "Técnico " + t.id })), state.names.tech);
      const mine = techs.find((t) => t.user_id === me.id);
      state.myTechnicianId = mine ? mine.id : null;
    }
  } catch (err) {
    $("message").textContent = err.message;
    return;
  }

  // Vista inicial según el menú lateral
  let viewName = params.get("view") || (me.role === "user" ? "mine" : "all");
  if (!VIEWS[viewName]) viewName = "all";
  const view = VIEWS[viewName];
  let title = view.title;
  if (me.role === "user" && viewName === "all") title = VIEWS.mine.title;
  $("list-title").textContent = title;
  document.title = title + " | Help Desk";

  if (view.status) filters.status.value = view.status;
  if (view.unassigned) filters.unassigned.checked = true;
  if (viewName === "assigned") {
    if (state.myTechnicianId) filters.tech.value = String(state.myTechnicianId);
    else $("message").textContent = "Tu usuario no tiene perfil de técnico.";
  }
  if (params.get("q")) filters.q.value = params.get("q").slice(0, 100);

  loadTickets();
}

init();
