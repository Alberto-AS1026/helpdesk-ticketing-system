"use strict";

requireLogin();

const FLOW = ["Abierto", "En progreso", "Pendiente", "Resuelto", "Cerrado"];

const TRANSITIONS = {
  "Abierto": ["En progreso"],
  "En progreso": ["Pendiente", "Resuelto"],
  "Pendiente": ["En progreso"],
  "Resuelto": ["Cerrado", "En progreso"],
  "Cerrado": [],
};

/** Texto del botón para cada transición (origen -> destino). */
function actionLabel(from, to) {
  if (to === "En progreso") {
    if (from === "Pendiente") return "Reanudar";
    if (from === "Resuelto") return "Reabrir";
    return "Iniciar trabajo";
  }
  return { "Pendiente": "Poner en espera", "Resuelto": "Resolver", "Cerrado": "Cerrar" }[to] || to;
}

const FIELD_LABELS = {
  creado: "Creación",
  status: "Estado",
  assigned_to: "Asignado a",
  diagnosis: "Diagnóstico",
  solution: "Solución",
};

const ticketId = Number(new URLSearchParams(window.location.search).get("id"));
const $ = (id) => document.getElementById(id);

let me = null;
let ticket = null;
let isStaff = false;
const techNames = {};
const computerNames = {};

function setMessage(error, ok = "") {
  $("message").textContent = error;
  $("action-ok").textContent = ok;
}

// ----- Pintado -----

function renderHeader() {
  const number = ticketNumber(ticket.id);
  $("t-number").textContent = number;
  document.title = number + " | Help Desk";

  // Acciones de estado (solo personal)
  const box = $("status-actions");
  box.replaceChildren();
  if (isStaff) {
    for (const to of TRANSITIONS[ticket.status] || []) {
      const btn = el("button", actionLabel(ticket.status, to), "btn " + (to === "Resuelto" ? "btn-success" : "btn-secondary"));
      btn.type = "button";
      btn.addEventListener("click", () => changeStatus(to));
      box.appendChild(btn);
    }
  }
  $("update-btn").hidden = !isStaff || ticket.status === "Cerrado";
  renderChatLink();
}

/** Usuario: chat con su técnico. Personal: chat con quien abrió el ticket. */
function renderChatLink() {
  let target = null;
  let label = "";
  if (me.role === "user" && ticket.technician_user_id) {
    target = ticket.technician_user_id;
    label = "Chatear con " + ticket.technician_name;
  } else if (me.role !== "user" && ticket.created_by !== me.id) {
    target = ticket.created_by;
    label = "Chatear con " + ticket.creator_name;
  }
  const link = $("chat-link");
  link.hidden = target === null;
  if (target !== null) {
    link.textContent = label;
    link.href = "/chat.html?user=" + Number(target) + "&ticket=" + Number(ticket.id);
  }
}

function renderFlow() {
  const ol = $("process-flow");
  ol.replaceChildren();
  const current = FLOW.indexOf(ticket.status);
  FLOW.forEach((name, i) => {
    const li = el("li", name, "step");
    if (i < current) li.classList.add("done");
    if (i === current) {
      li.classList.add("current");
      li.setAttribute("aria-current", "step");
    }
    ol.appendChild(li);
  });
}

function setValue(id, value) {
  const node = $(id);
  node.replaceChildren();
  if (value instanceof Node) node.appendChild(value);
  else node.textContent = value === null || value === undefined || value === "" ? "(vacío)" : value;
  node.classList.toggle("empty", value === null || value === undefined || value === "");
}

function renderFields() {
  setValue("f-number", ticketNumber(ticket.id));
  setValue("f-caller", ticket.creator_name);
  setValue("f-category", ticket.category_name);
  setValue("f-computer", ticket.computer_id ? computerNames[ticket.computer_id] || "Equipo " + ticket.computer_id : null);
  setValue("f-created", formatDate(ticket.created_at));
  setValue("f-status", statusBadge(ticket.status));
  setValue("f-priority", priorityTag(ticket.priority_name));
  setValue("f-assigned-ro", ticket.technician_name);
  setValue("f-title", ticket.title);
  setValue("f-description", ticket.description);

  // El personal reasigna desde el propio campo, salvo si ya está resuelto o cerrado
  const canAssign = isStaff && !["Resuelto", "Cerrado"].includes(ticket.status);
  $("f-assigned").hidden = !canAssign;
  $("f-assigned-ro").hidden = canAssign;
  if (canAssign) $("f-assigned").value = ticket.assigned_to ? String(ticket.assigned_to) : "";

  $("row-resolved").hidden = !ticket.resolved_at;
  $("row-time").hidden = !ticket.resolved_at;
  if (ticket.resolved_at) {
    setValue("f-resolved", formatDate(ticket.resolved_at));
    setValue("f-time", formatMinutes(ticket.resolution_minutes));
  }

  const editable = isStaff && ticket.status !== "Cerrado";
  for (const id of ["diagnosis", "solution"]) {
    $(id).value = ticket[id] || "";
    $(id).readOnly = !editable;
  }
  $("resolution-hint").hidden = !editable;

  $("comment-form").hidden = ticket.status === "Cerrado";
  $("detail-card").hidden = false;
  $("tabs-card").hidden = false;
}

function formatMinutes(minutes) {
  if (minutes === null || minutes === undefined) return null;
  const d = Math.floor(minutes / 1440);
  const h = Math.floor((minutes % 1440) / 60);
  const m = minutes % 60;
  const parts = [];
  if (d) parts.push(d + " d");
  if (h) parts.push(h + " h");
  parts.push(m + " min");
  return parts.join(" ");
}

function techName(id) {
  if (id === null || id === undefined || id === "") return "(vacío)";
  if (techNames[id]) return techNames[id];
  if (Number(id) === ticket.assigned_to && ticket.technician_name) return ticket.technician_name;
  return "Técnico " + id;
}

function historyValue(field, value) {
  if (field === "assigned_to") return techName(value);
  return value === null ? "(vacío)" : value;
}

/** Comentarios e historial en un único flujo de actividad, del más reciente al más antiguo. */
function renderActivity(comments, history) {
  const entries = [];
  for (const c of comments) {
    entries.push({ kind: "comment", who: c.author_name, at: c.created_at, text: c.comment });
  }
  // Los cambios hechos a la vez por la misma persona se agrupan en una tarjeta
  for (const h of history) {
    const last = entries[entries.length - 1];
    const sameMoment = last && last.kind === "change" && last.who === h.user_name
      && Math.abs(new Date(last.at) - new Date(h.changed_at)) < 2000;
    const line = [FIELD_LABELS[h.field_name] || h.field_name, h.old_value === null && h.field_name !== "assigned_to"
      ? historyValue(h.field_name, h.new_value)
      : historyValue(h.field_name, h.old_value) + " → " + historyValue(h.field_name, h.new_value)];
    if (sameMoment) last.lines.push(line);
    else entries.push({ kind: "change", who: h.user_name, at: h.changed_at, lines: [line] });
  }
  entries.sort((a, b) => new Date(b.at) - new Date(a.at));

  const ul = $("activity");
  ul.replaceChildren();
  if (entries.length === 0) {
    ul.appendChild(el("li", "Sin actividad", "muted"));
    return;
  }
  for (const e of entries) {
    const li = el("li", null, "act act-" + e.kind);
    li.appendChild(el("span", initials(e.who), "avatar-sm"));
    const card = el("div", null, "act-card");
    const head = el("div", null, "act-head");
    head.appendChild(el("strong", e.who));
    head.appendChild(el("span", e.kind === "comment" ? "Comentarios adicionales" : "Cambio de campos", "act-kind"));
    head.appendChild(el("span", formatDate(e.at), "act-time"));
    card.appendChild(head);
    if (e.kind === "comment") {
      card.appendChild(el("div", e.text, "act-text"));
    } else {
      const dl = el("dl", null, "act-changes");
      for (const [label, value] of e.lines) {
        dl.appendChild(el("dt", label));
        dl.appendChild(el("dd", value));
      }
      card.appendChild(dl);
    }
    li.appendChild(card);
    ul.appendChild(li);
  }
}

async function loadTicket() {
  ticket = await apiFetch("/tickets/" + ticketId);
  const [comments, history] = await Promise.all([
    apiFetch("/tickets/" + ticketId + "/comments"),
    apiFetch("/tickets/" + ticketId + "/history"),
  ]);
  renderHeader();
  renderFlow();
  renderFields();
  renderActivity(comments, history);
}

async function loadTechnicians() {
  const [techs, users] = await Promise.all([apiFetch("/technicians"), apiFetch("/users")]);
  const names = Object.fromEntries(users.map((u) => [u.id, u.full_name]));
  const select = $("f-assigned");
  select.replaceChildren();
  const empty = el("option", "-- Sin asignar --");
  empty.value = "";
  empty.disabled = true;
  select.appendChild(empty);
  for (const t of techs) {
    techNames[t.id] = names[t.user_id] || "Técnico " + t.id;
    if (!t.is_active) continue;
    const o = el("option", techNames[t.id] + " (" + t.level + ")");
    o.value = t.id;
    select.appendChild(o);
  }
}

async function loadComputers() {
  try {
    for (const c of await apiFetch("/computers")) computerNames[c.id] = c.hostname;
  } catch (err) {
    // No es imprescindible: se muestra el id del equipo
  }
}

// ----- Acciones -----

function resolutionChanges() {
  const changes = {};
  for (const field of ["diagnosis", "solution"]) {
    const value = $(field).value.trim();
    if (value && value !== (ticket[field] || "")) changes[field] = value;
  }
  return changes;
}

function showResolutionTab() {
  selectTab("resolution");
}

async function changeStatus(to) {
  setMessage("");
  const body = { status: to, ...resolutionChanges() };
  if (to === "Resuelto" && !($("diagnosis").value.trim() && $("solution").value.trim())) {
    showResolutionTab();
    setMessage("Para resolver, rellena el diagnóstico y la solución en «Información de resolución».");
    $($("diagnosis").value.trim() ? "solution" : "diagnosis").focus();
    return;
  }
  try {
    // Si se ha cambiado el técnico en el formulario, se guarda antes
    await saveAssignment();
    await apiFetch("/tickets/" + ticketId + "/status", { method: "PATCH", json: body });
    await loadTicket();
    setMessage("", "Incidente actualizado: " + to);
  } catch (err) {
    setMessage(err.message);
  }
}

async function saveAssignment() {
  const select = $("f-assigned");
  if (select.hidden || !select.value || Number(select.value) === ticket.assigned_to) return false;
  await apiFetch("/tickets/" + ticketId + "/assign", {
    method: "PATCH",
    json: { technician_id: Number(select.value) },
  });
  return true;
}

$("update-btn").addEventListener("click", async () => {
  setMessage("");
  try {
    const assigned = await saveAssignment();
    const changes = resolutionChanges();
    if (Object.keys(changes).length) {
      await apiFetch("/tickets/" + ticketId + "/resolution", { method: "PATCH", json: changes });
    }
    if (!assigned && !Object.keys(changes).length) {
      setMessage("", "No hay cambios que guardar");
      return;
    }
    await loadTicket();
    setMessage("", "Incidente actualizado");
  } catch (err) {
    setMessage(err.message);
  }
});

$("comment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("comment-error").textContent = "";
  const text = $("comment-text").value.trim();
  if (text.length < 2) {
    $("comment-error").textContent = "Escribe al menos 2 caracteres";
    return;
  }
  try {
    await apiFetch("/tickets/" + ticketId + "/comments", { method: "POST", json: { comment: text } });
    $("comment-text").value = "";
    await loadTicket();
  } catch (err) {
    $("comment-error").textContent = err.message;
  }
});

function selectTab(name) {
  for (const tab of ["notes", "resolution"]) {
    const active = tab === name;
    $("tab-" + tab).classList.toggle("active", active);
    $("tab-" + tab).setAttribute("aria-selected", String(active));
    $("panel-" + tab).hidden = !active;
  }
}
$("tab-notes").addEventListener("click", () => selectTab("notes"));
$("tab-resolution").addEventListener("click", () => selectTab("resolution"));

// Volver a la lista de la que se vino (si era del propio help desk)
if (document.referrer.startsWith(window.location.origin + "/?") || document.referrer === window.location.origin + "/") {
  $("back-link").href = document.referrer;
}

async function init() {
  if (!Number.isInteger(ticketId) || ticketId < 1) {
    setMessage("Incidente no válido");
    return;
  }
  try {
    me = await loadCurrentUser();
    isStaff = me.role !== "user";
    $("caller-visible").hidden = !isStaff;
    await Promise.all([isStaff ? loadTechnicians() : null, loadComputers()]);
    await loadTicket();
  } catch (err) {
    $("t-number").textContent = "Incidente";
    setMessage(err.message);
  }
}

init();
