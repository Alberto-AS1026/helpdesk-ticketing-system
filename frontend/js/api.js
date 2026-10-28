"use strict";

const API = "/api";
const TOKEN_KEY = "helpdesk_token";

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  window.location.href = "/login.html";
}

/** Redirige al login si no hay sesión. Se llama al cargar las pantallas privadas. */
function requireLogin() {
  if (!getToken()) {
    window.location.href = "/login.html";
  }
}

/**
 * Llama a la API con el token. Devuelve el JSON, o lanza un Error con
 * el mensaje que dio el servidor. Un 401 cierra la sesión.
 */
async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }

  let response;
  try {
    response = await fetch(API + path, { ...options, headers });
  } catch (err) {
    throw new Error("No se puede conectar con el servidor");
  }

  if (response.status === 401 && path !== "/auth/login") {
    logout();
    throw new Error("Sesión caducada");
  }

  let data = null;
  if (response.status !== 204) {
    try {
      data = await response.json();
    } catch (err) {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = data && data.detail;
    const message = typeof detail === "string" ? detail : "Error " + response.status;
    throw new Error(message);
  }
  return data;
}


/** Crea un elemento con texto seguro (textContent). */
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function statusBadge(status) {
  return el("span", status, "badge " + status.toLowerCase().replace(/ /g, "-"));
}

function formatDate(iso) {
  return new Date(iso).toLocaleString("es-ES");
}

/** Pinta el nombre del usuario en la barra superior y devuelve sus datos. */
async function loadCurrentUser() {
  document.getElementById("logout-btn").addEventListener("click", logout);
  const me = await apiFetch("/auth/me");
  document.getElementById("user-name").textContent = me.full_name;
  const dashLink = document.getElementById("dash-link");
  if (dashLink && me.role !== "user") dashLink.hidden = false;
  startUnreadBadge();
  return me;
}

/** Contador de mensajes de chat sin leer en la barra superior. */
async function refreshUnreadBadge() {
  const badge = document.getElementById("chat-unread");
  if (!badge) return;
  try {
    const data = await apiFetch("/chat/unread");
    badge.textContent = data.unread > 99 ? "99+" : String(data.unread);
    badge.hidden = data.unread === 0;
  } catch (err) {
    // Un fallo puntual no debe romper la página; se reintenta en el siguiente ciclo
  }
}

/**
 * Conexión WebSocket con la API para los avisos del chat en tiempo real.
 * Se autentica con el primer mensaje (el token nunca va en la URL), hace
 * ping cada 25 s y se reconecta sola con espera creciente. Mientras no hay
 * conexión, las páginas siguen funcionando con el polling de siempre.
 *
 *   realtime.on("message" | "read" | "typing" | "presence" | "open" | "close", fn)
 */
const realtime = (() => {
  const listeners = {};
  let ws = null;
  let connected = false;
  let started = false;
  let stopped = false;
  let retry = 0;
  let retryTimer = null;
  let pingTimer = null;

  function emit(type, data) {
    for (const fn of listeners[type] || []) {
      try {
        fn(data);
      } catch (err) {
        console.error(err);
      }
    }
  }

  function url() {
    return (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host + API + "/chat/ws";
  }

  function scheduleReconnect() {
    if (stopped || retryTimer) return;
    const delay = Math.min(30000, 1000 * 2 ** retry) + Math.random() * 500;
    retry += 1;
    retryTimer = setTimeout(() => {
      retryTimer = null;
      connect();
    }, delay);
  }

  function connect() {
    const token = getToken();
    if (!token || stopped || ws) return;
    try {
      ws = new WebSocket(url());
    } catch (err) {
      ws = null;
      scheduleReconnect();
      return;
    }
    ws.onopen = () => ws.send(JSON.stringify({ type: "auth", token: token }));
    ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (err) {
        return;
      }
      if (msg.type === "ready") {
        connected = true;
        retry = 0;
        pingTimer = setInterval(() => send({ type: "ping" }), 25000);
        emit("open");
      } else if (msg.type !== "pong") {
        emit(msg.type, msg);
      }
    };
    ws.onclose = (event) => {
      const wasConnected = connected;
      connected = false;
      ws = null;
      clearInterval(pingTimer);
      if (wasConnected) emit("close");
      if (event.code === 4401) {
        // Token no válido o caducado: una llamada REST dará 401 y cerrará la sesión
        stopped = true;
        apiFetch("/auth/me").catch(() => {});
        return;
      }
      scheduleReconnect();
    };
  }

  function send(obj) {
    if (!connected || !ws) return false;
    ws.send(JSON.stringify(obj));
    return true;
  }

  // Al recuperar la red o volver a la pestaña, se reintenta sin esperar
  function retryNow() {
    if (!started || connected || ws || stopped) return;
    clearTimeout(retryTimer);
    retryTimer = null;
    retry = 0;
    connect();
  }
  window.addEventListener("online", retryNow);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) retryNow();
  });

  return {
    start() {
      if (started) return;
      started = true;
      connect();
    },
    on(type, fn) {
      (listeners[type] = listeners[type] || []).push(fn);
    },
    send: send,
    get connected() {
      return connected;
    },
  };
})();

let unreadTimer = null;

function startUnreadBadge() {
  if (unreadTimer) return;
  refreshUnreadBadge();
  realtime.start();
  // Con WebSocket, el contador se actualiza al llegar cada aviso
  for (const type of ["open", "message", "read"]) realtime.on(type, refreshUnreadBadge);
  // Sin WebSocket (plan B), se consulta cada 15 s
  unreadTimer = setInterval(() => {
    if (!document.hidden && !realtime.connected) refreshUnreadBadge();
  }, 15000);
}


