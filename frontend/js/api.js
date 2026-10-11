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
  document.getElementById("user-name").textContent = me.full_name + " (" + me.role + ")";
  return me;
}


