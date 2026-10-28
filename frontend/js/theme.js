"use strict";

// Se carga en <head> para aplicar el tema antes de pintar la página
// (sin destello blanco). La preferencia se guarda en localStorage; si no
// hay ninguna, se usa la del sistema operativo.

const THEME_KEY = "helpdesk_theme";

function savedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (err) {
    return null;
  }
}

function currentTheme() {
  return document.documentElement.dataset.theme;
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById("theme-btn");
  if (btn) {
    const label = theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro";
    btn.title = label;
    btn.setAttribute("aria-label", label);
  }
  // Avisa a quien lo necesite (por ejemplo, los gráficos del dashboard)
  document.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
}

applyTheme(
  savedTheme() ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
);

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("theme-btn");
  if (!btn) return;
  applyTheme(currentTheme()); // pone el título del botón
  btn.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (err) {
      // Sin almacenamiento (modo privado): el cambio dura hasta recargar
    }
    applyTheme(next);
  });
});
