"use strict";

requireLogin();

const TRANSITIONS = {
  "Abierto": ["En progreso"],
  "En progreso": ["Pendiente", "Resuelto"],
  "Pendiente": ["En progreso"],
  "Resuelto": ["Cerrado", "En progreso"],
  "Cerrado": [],
};

const FIELD_LABELS = {
  creado: "Creación",
  status: "Estado",
  assigned_to: "Técnico (id)",
  diagnosis: "Diagnóstico",
  solution: "Solución",
};

const ticketId = Number(new URLSearchParams(window.location.search).get("id"));
const $ = (id) => document.getElementById(id);

let me = null;
let ticket = null;

function showError(box, message) {
  $(box).textContent = message;
}

function renderDetail() {
  $("t-title").textContent = "#" + ticket.id + " " + ticket.title;
  const dl = $("t-details");
  dl.replaceChildren();
  const rows = [
    ["Estado", statusBadge(ticket.status)],
    ["Prioridad", ticket.priority_name],
    ["Categoría", ticket.category_name],
    ["Creado por", ticket.creator_name],
    ["Técnico", ticket.technician_name || "Sin asignar"],
    ["Creado", formatDate(ticket.created_at)],
    ["Descripción", ticket.description],
    ["Diagnóstico", ticket.diagnosis || "-"],
    ["Solución", ticket.solution || "-"],
  ];
  if (ticket.resolved_at) {
    rows.push(["Resuelto", formatDate(ticket.resolved_at)]);
    rows.push(["Tiempo", ticket.resolution_minutes + " min"]);
  }
  for (const [label, value] of rows) {
    dl.appendChild(el("dt", label));
    const dd = el("dd");
    if (value instanceof Node) dd.appendChild(value);
    else dd.textContent = value;
    dl.appendChild(dd);
  }
  $("detail-card").hidden = false;
}

function renderThread(listId, entries, build) {
  const ul = $(listId);
  ul.replaceChildren();
  if (entries.length === 0) {
    ul.appendChild(el("li", "Sin registros", "muted"));
    return;
  }
  for (const entry of entries) {
    const li = document.createElement("li");
    const [meta, text] = build(entry);
    li.appendChild(el("div", meta, "meta"));
    li.appendChild(el("div", text, "text"));
    ul.appendChild(li);
  }
}

function renderStatusOptions() {
  const select = $("new-status");
  select.replaceChildren();
  const options = TRANSITIONS[ticket.status] || [];
  for (const s of options) {
    const o = el("option", s);
    o.value = s;
    select.appendChild(o);
  }
  const disabled = options.length === 0;
  select.disabled = disabled;
  $("status-form").querySelector("button").disabled = disabled;
  $("diagnosis").value = ticket.diagnosis || "";
  $("solution").value = ticket.solution || "";
}

async function loadTicket() {
  ticket = await apiFetch("/tickets/" + ticketId);
  renderDetail();
  renderStatusOptions();
  const [comments, history] = await Promise.all([
    apiFetch("/tickets/" + ticketId + "/comments"),
    apiFetch("/tickets/" + ticketId + "/history"),
  ]);
  renderThread("comments", comments, (c) => [
    c.author_name + " - " + formatDate(c.created_at),
    c.comment,
  ]);
  renderThread("history", history, (h) => {
    const label = FIELD_LABELS[h.field_name] || h.field_name;
    const change = h.old_value === null ? h.new_value : h.old_value + " → " + h.new_value;
    return [h.user_name + " - " + formatDate(h.changed_at), label + ": " + change];
  });
  $("comments-card").hidden = false;
  $("history-card").hidden = false;
  $("comment-form").hidden = ticket.status === "Cerrado";
}

async function loadTechnicians() {
  const techs = await apiFetch("/technicians");
  const users = await apiFetch("/users");
  const names = Object.fromEntries(users.map((u) => [u.id, u.full_name]));
  const select = $("technician");
  select.replaceChildren();
  for (const t of techs.filter((t) => t.is_active)) {
    const o = el("option", (names[t.user_id] || "Técnico") + " (" + t.level + ")");
    o.value = t.id;
    select.appendChild(o);
  }
}

$("comment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("comment-error", "");
  const text = $("comment-text").value.trim();
  if (text.length < 2) {
    showError("comment-error", "Escribe al menos 2 caracteres");
    return;
  }
  try {
    await apiFetch("/tickets/" + ticketId + "/comments", {
      method: "POST",
      json: { comment: text },
    });
    $("comment-text").value = "";
    await loadTicket();
  } catch (err) {
    showError("comment-error", err.message);
  }
});

$("assign-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("action-error", "");
  $("action-ok").textContent = "";
  try {
    await apiFetch("/tickets/" + ticketId + "/assign", {
      method: "PATCH",
      json: { technician_id: Number($("technician").value) },
    });
    $("action-ok").textContent = "Técnico asignado";
    await loadTicket();
  } catch (err) {
    showError("action-error", err.message);
  }
});

$("status-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("action-error", "");
  $("action-ok").textContent = "";
  const body = { status: $("new-status").value };
  const diagnosis = $("diagnosis").value.trim();
  const solution = $("solution").value.trim();
  if (diagnosis && diagnosis !== (ticket.diagnosis || "")) body.diagnosis = diagnosis;
  if (solution && solution !== (ticket.solution || "")) body.solution = solution;
  try {
    await apiFetch("/tickets/" + ticketId + "/status", { method: "PATCH", json: body });
    $("action-ok").textContent = "Estado actualizado";
    await loadTicket();
  } catch (err) {
    showError("action-error", err.message);
  }
});

async function init() {
  if (!Number.isInteger(ticketId) || ticketId < 1) {
    showError("message", "Ticket no válido");
    return;
  }
  try {
    me = await loadCurrentUser();
    if (me.role !== "user") {
      $("staff-panel").hidden = false;
      await loadTechnicians();
    }
    await loadTicket();
  } catch (err) {
    showError("message", err.message);
  }
}

init();
