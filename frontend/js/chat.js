"use strict";

requireLogin();

const $ = (id) => document.getElementById(id);

const ROLE_LABELS = { user: "Usuario", technician: "Técnico", admin: "Administrador" };
// Sin WebSocket (plan B) se consulta a menudo; con WebSocket, los avisos
// llegan al instante y la consulta periódica es solo una red de seguridad
const SYNC_MS = 2500;
const SYNC_SAFETY_MS = 30000;
const LIST_MS = 5000;
const LIST_SAFETY_MS = 60000;
const TYPING_SHOW_MS = 6000;     // "escribiendo…" se apaga si no llegan más avisos
const TYPING_PING_MS = 3000;     // aviso de "escribiendo…" mientras se teclea
const GROUP_GAP_MS = 5 * 60 * 1000;  // mensajes seguidos del mismo autor se agrupan
const EMOJIS = [
  "😀", "😂", "😊", "😉", "😍", "🤔", "😅", "😢", "😡", "😴",
  "👍", "👎", "👌", "👏", "🙏", "💪", "👋", "🤝", "✌️", "🙌",
  "✅", "❌", "⚠️", "❓", "❗", "🔥", "🎉", "💡", "⏰", "📌",
  "💻", "🖥️", "🖨️", "⌨️", "🖱️", "📶", "🔌", "🔒", "📧", "📞",
];

const SVG_NS = "http://www.w3.org/2000/svg";

const state = {
  me: null,
  conversations: [],
  contacts: [],
  active: null,          // conversación abierta
  lastId: 0,             // último mensaje pintado (para pedir solo los nuevos)
  mine: new Map(),       // id -> { node, created } de mis mensajes, para los checks
  lastMsg: null,         // último mensaje pintado (para agrupar y separar por días)
  otherReadId: 0,
  peer: { online: false, lastSeen: null, typing: false },
  typingTimer: null,
  syncing: false,
  lastSyncAt: 0,
  lastListAt: 0,
  lastTypingPing: 0,
  newWhileAway: 0,
};

// ---------- Utilidades de presentación ----------

function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}

function avatar(node, name) {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.codePointAt(0)) >>> 0;
  node.textContent = initials(name);
  node.className = "avatar av-" + (hash % 8);
}

function sameDay(a, b) {
  return a.toDateString() === b.toDateString();
}

function isYesterday(d) {
  const y = new Date();
  y.setDate(y.getDate() - 1);
  return sameDay(d, y);
}

function hhmm(d) {
  return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

/** Hora para la lista de chats: "10:32", "Ayer", "lunes" o "12/10/26". */
function listTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  if (sameDay(d, now)) return hhmm(d);
  if (isYesterday(d)) return "Ayer";
  if (now - d < 6 * 24 * 3600 * 1000) return d.toLocaleDateString("es-ES", { weekday: "long" });
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

/** Separador de día dentro de la conversación. */
function dayLabel(d) {
  if (sameDay(d, new Date())) return "Hoy";
  if (isYesterday(d)) return "Ayer";
  return d.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

function lastSeenText(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (sameDay(d, new Date())) return "últ. vez hoy a las " + hhmm(d);
  if (isYesterday(d)) return "últ. vez ayer a las " + hhmm(d);
  return "últ. vez el " + d.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" }) + " a las " + hhmm(d);
}

function svgIcon(className, paths) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", className);
  svg.setAttribute("aria-hidden", "true");
  for (const d of paths) {
    const p = document.createElementNS(SVG_NS, "path");
    p.setAttribute("d", d);
    svg.appendChild(p);
  }
  return svg;
}

const CHECK_ONE = ["M4 12.5 9 17.5 20 6.5"];
const CHECK_TWO = ["M1.5 12.5 6.5 17.5 17.5 6.5", "M11.5 16.5 12.5 17.5 23.5 6.5"];

/** ✓ enviado · ✓✓ recibido (la otra persona se ha conectado después) · ✓✓ azul leído. */
function ticks(id, created) {
  let status = "sent";
  if (id <= state.otherReadId) status = "read";
  else if (state.peer.online || (state.peer.lastSeen && new Date(state.peer.lastSeen) >= created)) {
    status = "delivered";
  }
  const span = el("span", null, "ticks " + status);
  span.title = { sent: "Enviado", delivered: "Entregado", read: "Leído" }[status];
  span.appendChild(svgIcon("", status === "sent" ? CHECK_ONE : CHECK_TWO));
  return span;
}

/** Texto del mensaje con "#12" convertido en enlace al ticket 12 (sin innerHTML). */
function messageBody(text) {
  const div = el("div", null, "msg-body");
  for (const part of text.split(/(#\d+)/)) {
    if (/^#\d+$/.test(part)) {
      const a = el("a", part, "ticket-ref");
      a.href = "/ticket.html?id=" + Number(part.slice(1));
      div.appendChild(a);
    } else if (part) {
      div.appendChild(document.createTextNode(part));
    }
  }
  return div;
}

// ---------- Lista de chats ----------

function renderConversations() {
  const ul = $("conv-list");
  const filter = $("search").value.trim().toLowerCase();
  ul.replaceChildren();
  const items = state.conversations.filter((c) => c.other.full_name.toLowerCase().includes(filter));
  if (items.length === 0) {
    ul.appendChild(el("li", filter ? "Ningún chat coincide" : "Todavía no tienes chats. Pulsa ✎ para empezar uno.", "list-empty"));
    return;
  }
  for (const c of items) {
    const li = document.createElement("li");
    const btn = el("button", null, "conv-item");
    btn.type = "button";
    const isActive = state.active && state.active.id === c.id;
    if (isActive) btn.classList.add("active");

    const av = el("span");
    avatar(av, c.other.full_name);
    if (c.other_online) av.classList.add("online");
    btn.appendChild(av);

    const info = el("span", null, "conv-info");
    const top = el("span", null, "conv-row");
    top.appendChild(el("span", c.other.full_name, "conv-name"));
    if (c.last_message_at) {
      top.appendChild(el("span", listTime(c.last_message_at), "conv-time" + (c.unread && !isActive ? " has-unread" : "")));
    }
    const bottom = el("span", null, "conv-row");
    const preview = el("span", null, "conv-last");
    if (c.last_message_mine) {
      const t = el("span", null, "ticks " + (c.last_message_read ? "read" : "sent"));
      t.appendChild(svgIcon("", c.last_message_read ? CHECK_TWO : CHECK_ONE));
      preview.appendChild(t);
    }
    preview.appendChild(document.createTextNode(c.last_message || ROLE_LABELS[c.other.role] || c.other.role));
    bottom.appendChild(preview);
    if (c.unread > 0 && !isActive) {
      bottom.appendChild(el("span", String(c.unread), "unread-pill"));
    }
    info.appendChild(top);
    info.appendChild(bottom);
    btn.appendChild(info);
    btn.addEventListener("click", () => openConversation(c));
    li.appendChild(btn);
    ul.appendChild(li);
  }
  const totalUnread = state.conversations.reduce((n, c) => n + c.unread, 0);
  document.title = (totalUnread ? "(" + totalUnread + ") " : "") + "Help Desk - Chat";
}

async function loadConversations() {
  state.lastListAt = Date.now();
  state.conversations = await apiFetch("/chat/conversations");
  renderConversations();
}

// ---------- Contactos (nuevo chat) ----------

function renderContacts() {
  const ul = $("contact-list");
  const filter = $("contact-search").value.trim().toLowerCase();
  ul.replaceChildren();
  const items = state.contacts.filter((c) => c.full_name.toLowerCase().includes(filter));
  if (items.length === 0) {
    ul.appendChild(el("li", "Ningún contacto coincide", "list-empty"));
    return;
  }
  for (const c of items) {
    const li = document.createElement("li");
    const btn = el("button", null, "conv-item");
    btn.type = "button";
    const av = el("span");
    avatar(av, c.full_name);
    btn.appendChild(av);
    const info = el("span", null, "conv-info");
    info.appendChild(el("span", c.full_name, "conv-name"));
    info.appendChild(el("span", ROLE_LABELS[c.role] || c.role, "conv-last"));
    btn.appendChild(info);
    btn.addEventListener("click", async () => {
      toggleContacts(false);
      try {
        await startChatWith(c.id);
      } catch (err) {
        $("message").textContent = err.message;
      }
    });
    li.appendChild(btn);
    ul.appendChild(li);
  }
}

async function toggleContacts(show) {
  $("contacts-panel").hidden = !show;
  if (!show) return;
  $("contact-search").value = "";
  try {
    state.contacts = await apiFetch("/chat/contacts");
  } catch (err) {
    $("message").textContent = err.message;
  }
  renderContacts();
  $("contact-search").focus();
}

/** Abre (o crea) la conversación con un usuario. */
async function startChatWith(userId) {
  const conv = await apiFetch("/chat/conversations", { method: "POST", json: { user_id: userId } });
  await loadConversations();
  await openConversation(state.conversations.find((c) => c.id === conv.id) || conv);
}

// ---------- Conversación ----------

function isNearBottom() {
  const list = $("messages");
  return list.scrollHeight - list.scrollTop - list.clientHeight < 120;
}

function scrollToBottom() {
  const list = $("messages");
  list.scrollTop = list.scrollHeight;
  state.newWhileAway = 0;
  updateScrollButton();
}

function updateScrollButton() {
  $("scroll-down").hidden = isNearBottom();
  $("new-count").hidden = state.newWhileAway === 0;
  $("new-count").textContent = String(state.newWhileAway);
}

function appendMessages(messages) {
  const list = $("messages");
  const stick = isNearBottom();
  let incoming = 0;
  for (const m of messages) {
    if (m.id <= state.lastId) continue;
    state.lastId = m.id;
    const created = new Date(m.created_at);
    const prev = state.lastMsg;

    if (!prev || !sameDay(prev.created, created)) {
      const sep = el("li", null, "day-sep");
      sep.appendChild(el("span", dayLabel(created)));
      list.appendChild(sep);
    }
    const mine = m.sender_id === state.me.id;
    const continued = prev && prev.sender === m.sender_id && sameDay(prev.created, created)
      && created - prev.created < GROUP_GAP_MS;

    const li = el("li", null, "msg " + (mine ? "mine" : "theirs") + (continued ? " cont" : " first"));
    li.appendChild(messageBody(m.body));
    const meta = el("span", null, "msg-meta");
    meta.appendChild(el("span", hhmm(created)));
    if (mine) {
      meta.appendChild(ticks(m.id, created));
      state.mine.set(m.id, { node: meta, created });
    } else {
      incoming += 1;
    }
    li.appendChild(meta);
    list.appendChild(li);
    state.lastMsg = { sender: m.sender_id, created };
  }
  const sentByMe = messages.some((m) => m.sender_id === state.me.id);
  if (stick || sentByMe) {
    scrollToBottom();
  } else {
    state.newWhileAway += incoming;
    updateScrollButton();
  }
}

/** Repinta los checks de mis mensajes cuando cambia lo leído o la presencia. */
function refreshTicks() {
  for (const [id, { node, created }] of state.mine) {
    const old = node.querySelector(".ticks");
    const fresh = ticks(id, created);
    if (old.className !== fresh.className) old.replaceWith(fresh);
  }
}

function renderPeerStatus() {
  if (!state.active) return;
  const status = $("peer-status");
  const peer = state.peer;
  status.classList.toggle("typing", peer.typing);
  if (peer.typing) status.textContent = "escribiendo…";
  else if (peer.online) status.textContent = "en línea";
  else status.textContent = lastSeenText(peer.lastSeen)
    || ROLE_LABELS[state.active.other.role] || state.active.other.role;
}

function setPeerTyping(typing) {
  clearTimeout(state.typingTimer);
  state.peer.typing = typing;
  if (typing) {
    state.typingTimer = setTimeout(() => setPeerTyping(false), TYPING_SHOW_MS);
  }
  renderPeerStatus();
}

function applySync(sync) {
  state.peer.online = sync.other_online;
  state.peer.lastSeen = sync.other_last_seen_at;
  state.otherReadId = Math.max(state.otherReadId, sync.other_last_read_id);
  const hint = $("messages").querySelector(".empty-hint");
  if (hint && sync.messages.length) hint.remove();
  appendMessages(sync.messages);
  refreshTicks();
  setPeerTyping(sync.other_typing);
}

async function markRead() {
  if (!state.active || !state.lastId || document.hidden) return;
  await apiFetch("/chat/conversations/" + state.active.id + "/read", {
    method: "POST",
    json: { last_read_id: state.lastId },
  });
  const c = state.conversations.find((x) => x.id === state.active.id);
  if (c) c.unread = 0;
  refreshUnreadBadge();
}

async function openConversation(conv) {
  state.active = conv;
  state.lastId = 0;
  state.mine.clear();
  state.lastMsg = null;
  state.otherReadId = 0;
  state.peer = { online: false, lastSeen: null, typing: false };
  clearTimeout(state.typingTimer);
  state.newWhileAway = 0;
  $("messages").replaceChildren();
  $("send-error").textContent = "";
  $("chat-empty").hidden = true;
  $("chat-active").hidden = false;
  $("chat-app").classList.add("show-chat");
  avatar($("peer-avatar"), conv.other.full_name);
  $("peer-name").textContent = conv.other.full_name;
  $("peer-status").textContent = "";
  renderConversations();

  state.lastSyncAt = Date.now();
  const sync = await apiFetch("/chat/conversations/" + conv.id + "/sync");
  if (state.active !== conv) return; // se cambió de conversación mientras cargaba
  if (sync.messages.length === 0) {
    $("messages").appendChild(el("li", "Aún no hay mensajes. ¡Escribe el primero!", "empty-hint"));
  }
  applySync(sync);
  scrollToBottom();
  await markRead();
  if (window.matchMedia("(min-width: 801px)").matches) $("msg-text").focus();
}

function closeConversation() {
  state.active = null;
  $("chat-app").classList.remove("show-chat");
  $("chat-active").hidden = true;
  $("chat-empty").hidden = false;
  renderConversations();
}

async function syncActive() {
  if (!state.active || state.syncing || document.hidden) return;
  state.syncing = true;
  state.lastSyncAt = Date.now();
  const conv = state.active;
  try {
    const sync = await apiFetch("/chat/conversations/" + conv.id + "/sync?after_id=" + state.lastId);
    if (state.active !== conv) return;
    const hadNew = sync.messages.some((m) => m.sender_id !== state.me.id);
    const readChanged = sync.other_last_read_id !== state.otherReadId;
    applySync(sync);
    if (hadNew) await markRead();
    // La lista de la izquierda (último mensaje, checks) se pone al día sin esperar a su ciclo
    if (sync.messages.length || readChanged) await loadConversations();
  } catch (err) {
    // Fallo puntual de red: se reintenta en el siguiente ciclo
  } finally {
    state.syncing = false;
  }
}

// ---------- Escribir y enviar ----------

function autosize() {
  const t = $("msg-text");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 140) + "px";
}

function pingTyping() {
  if (!state.active || !$("msg-text").value.trim()) return;
  const now = Date.now();
  if (now - state.lastTypingPing < TYPING_PING_MS) return;
  state.lastTypingPing = now;
  // Por WebSocket si está conectado; si no, por REST
  if (!realtime.send({ type: "typing", conversation_id: state.active.id })) {
    apiFetch("/chat/conversations/" + state.active.id + "/typing", { method: "POST" }).catch(() => {});
  }
}

async function sendMessage() {
  const text = $("msg-text").value.trim();
  $("send-error").textContent = "";
  if (!text || !state.active) return;
  $("send-btn").disabled = true;
  try {
    const msg = await apiFetch("/chat/conversations/" + state.active.id + "/messages", {
      method: "POST",
      json: { body: text },
    });
    $("msg-text").value = "";
    autosize();
    state.lastTypingPing = 0;
    const hint = $("messages").querySelector(".empty-hint");
    if (hint) hint.remove();
    appendMessages([msg]);
    loadConversations().catch(() => {});
  } catch (err) {
    $("send-error").textContent = err.message;
  } finally {
    $("send-btn").disabled = false;
    $("msg-text").focus();
  }
}

function insertAtCursor(text) {
  const t = $("msg-text");
  const start = t.selectionStart;
  const end = t.selectionEnd;
  t.value = t.value.slice(0, start) + text + t.value.slice(end);
  t.selectionStart = t.selectionEnd = start + text.length;
  t.focus();
  autosize();
}

function buildEmojiPanel() {
  const panel = $("emoji-panel");
  for (const e of EMOJIS) {
    const b = el("button", e, "emoji");
    b.type = "button";
    b.addEventListener("click", () => insertAtCursor(e));
    panel.appendChild(b);
  }
}

function toggleEmojis(show) {
  $("emoji-panel").hidden = !show;
  $("emoji-btn").setAttribute("aria-expanded", String(show));
  $("emoji-btn").classList.toggle("active", show);
}

// ---------- Eventos ----------

$("send-form").addEventListener("submit", (event) => {
  event.preventDefault();
  toggleEmojis(false);
  sendMessage();
});

$("msg-text").addEventListener("keydown", (event) => {
  // Intro envía; Mayús+Intro hace salto de línea
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    toggleEmojis(false);
    sendMessage();
  }
});

$("msg-text").addEventListener("input", () => {
  autosize();
  pingTyping();
});

$("emoji-btn").addEventListener("click", () => toggleEmojis($("emoji-panel").hidden));
$("messages").addEventListener("scroll", () => {
  if (isNearBottom()) state.newWhileAway = 0;
  updateScrollButton();
});
$("scroll-down").addEventListener("click", scrollToBottom);
$("back-btn").addEventListener("click", closeConversation);
$("search").addEventListener("input", renderConversations);
$("new-chat-btn").addEventListener("click", () => toggleContacts(true));
$("contacts-back").addEventListener("click", () => toggleContacts(false));
$("contact-search").addEventListener("input", renderContacts);

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!$("emoji-panel").hidden) toggleEmojis(false);
  else if (!$("contacts-panel").hidden) toggleContacts(false);
});

// ---------- Avisos en tiempo real (WebSocket) ----------

function isActive(conversationId) {
  return state.active && state.active.id === conversationId;
}

realtime.on("message", (event) => {
  if (isActive(event.conversation_id)) {
    const hint = $("messages").querySelector(".empty-hint");
    if (hint) hint.remove();
    appendMessages([event.message]);
    if (event.message.sender_id !== state.me.id) {
      setPeerTyping(false);
      markRead().catch(() => {});
    }
  }
  loadConversations().catch(() => {});
});

realtime.on("read", (event) => {
  if (isActive(event.conversation_id) && event.user_id !== state.me.id) {
    state.otherReadId = Math.max(state.otherReadId, event.last_read_id);
    refreshTicks();
  }
  loadConversations().catch(() => {});
});

realtime.on("typing", (event) => {
  if (isActive(event.conversation_id) && event.user_id !== state.me.id) setPeerTyping(true);
});

realtime.on("presence", (event) => {
  for (const c of state.conversations) {
    if (c.other.id === event.user_id) {
      c.other_online = event.online;
      c.other_last_seen_at = event.last_seen_at;
    }
  }
  renderConversations();
  if (state.active && state.active.other.id === event.user_id) {
    state.peer.online = event.online;
    state.peer.lastSeen = event.last_seen_at;
    if (!event.online) state.peer.typing = false;
    refreshTicks();
    renderPeerStatus();
  }
});

// Al (re)conectar se recupera lo que haya llegado mientras tanto
realtime.on("open", () => {
  syncActive().catch(() => {});
  loadConversations().catch(() => {});
});

// Al volver a la pestaña: ponerse al día y marcar como leído
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) syncActive().then(markRead).catch(() => {});
});

async function init() {
  try {
    state.me = await loadCurrentUser();
    avatar($("my-avatar"), state.me.full_name);
    $("my-avatar").title = state.me.full_name;
    buildEmojiPanel();
    await loadConversations();

    // Desde un ticket: chat.html?user=ID&ticket=N
    const params = new URLSearchParams(window.location.search);
    const userId = Number(params.get("user"));
    const ticketId = Number(params.get("ticket"));
    if (Number.isInteger(userId) && userId > 0) {
      await startChatWith(userId);
      if (Number.isInteger(ticketId) && ticketId > 0 && !$("msg-text").value) {
        $("msg-text").value = "Sobre el ticket #" + ticketId + ": ";
        autosize();
      }
    }
  } catch (err) {
    $("message").textContent = err.message;
    return;
  }
  // Consulta periódica: frecuente sin WebSocket, solo de seguridad con él
  setInterval(() => {
    if (document.hidden) return;
    const now = Date.now();
    if (now - state.lastSyncAt >= (realtime.connected ? SYNC_SAFETY_MS : SYNC_MS)) syncActive();
    if (now - state.lastListAt >= (realtime.connected ? LIST_SAFETY_MS : LIST_MS)) {
      loadConversations().catch(() => {});
    }
  }, 1000);
}

init();
