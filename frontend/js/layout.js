"use strict";

// Estructura común de las páginas privadas, al estilo de una consola ITSM:
// cabecera oscura con buscador global y menú lateral de navegación.
// Se ejecuta antes que el script de cada página (que busca estos elementos
// por id) y después de api.js (usa el()).

const SVG_NS = "http://www.w3.org/2000/svg";

const ICONS = {
  menu: ["M3 6h18", "M3 12h18", "M3 18h18"],
  search: ["M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "M21 21l-4.3-4.3"],
  plus: ["M12 5v14", "M5 12h14"],
  list: ["M8 6h13", "M8 12h13", "M8 18h13", "M3 6h.01", "M3 12h.01", "M3 18h.01"],
  inbox: ["M22 12h-6l-2 3h-4l-2-3H2", "M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"],
  user: ["M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
  alert: ["M12 9v4", "M12 17h.01", "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"],
  clock: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M12 6v6l4 2"],
  pause: ["M10 4H6v16h4z", "M18 4h-4v16h4z"],
  check: ["M22 11.08V12a10 10 0 1 1-5.93-9.14", "M22 4 12 14.01l-3-3"],
  chart: ["M18 20V10", "M12 20V4", "M6 20v-6"],
  chat: ["M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"],
  moon: ["M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"],
  sun: ["M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M12 2v2", "M12 20v2", "M4.93 4.93l1.41 1.41", "M17.66 17.66l1.41 1.41", "M2 12h2", "M20 12h2", "M4.93 19.07l1.41-1.41", "M17.66 6.34l1.41-1.41"],
  logout: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "M16 17l5-5-5-5", "M21 12H9"],
};

function icon(name, className) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  if (className) svg.setAttribute("class", className);
  for (const d of ICONS[name]) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  }
  return svg;
}

function iconButton(id, iconNames, label) {
  const btn = el("button", null, "hdr-btn");
  btn.type = "button";
  btn.id = id;
  btn.title = label;
  btn.setAttribute("aria-label", label);
  for (const [name, cls] of iconNames) btn.appendChild(icon(name, cls));
  return btn;
}

/**
 * Menú lateral. "view" coincide con el parámetro ?view= del listado.
 * roles: quién ve la entrada (por defecto, todos).
 */
const NAV_SECTIONS = [
  {
    title: "Autoservicio",
    items: [
      { label: "Crear incidente", href: "/new.html", icon: "plus", page: "/new.html" },
      { label: "Mis incidentes", href: "/?view=mine", icon: "user", view: "mine", roles: ["user"] },
    ],
  },
  {
    title: "Service Desk",
    roles: ["technician", "admin"],
    items: [
      { label: "Asignados a mí", href: "/?view=assigned", icon: "inbox", view: "assigned", roles: ["technician"] },
      { label: "Sin asignar", href: "/?view=unassigned", icon: "alert", view: "unassigned" },
      { label: "Abiertos", href: "/?view=open", icon: "clock", view: "open" },
      { label: "En progreso", href: "/?view=progress", icon: "clock", view: "progress" },
      { label: "Pendientes", href: "/?view=pending", icon: "pause", view: "pending" },
      { label: "Resueltos", href: "/?view=resolved", icon: "check", view: "resolved" },
      { label: "Todos los incidentes", href: "/?view=all", icon: "list", view: "all" },
    ],
  },
  {
    title: "Informes",
    roles: ["technician", "admin"],
    items: [{ label: "Dashboard", href: "/dashboard.html", icon: "chart", page: "/dashboard.html", id: "dash-link" }],
  },
  {
    title: "Comunicación",
    items: [{ label: "Chat", href: "/chat.html", icon: "chat", page: "/chat.html", badge: "chat-unread" }],
  },
];

function currentView() {
  return new URLSearchParams(window.location.search).get("view") || "";
}

function isNavActive(item) {
  const path = window.location.pathname;
  if (item.page) return path === item.page;
  if (path !== "/" && path !== "/index.html") return false;
  const view = currentView();
  // Sin ?view= se ve la lista por defecto: "Mis incidentes" o "Todos" según el rol
  if (!view) return item.view === "mine" || item.view === "all";
  return item.view === view;
}

function buildHeader() {
  const header = el("header", null, "app-header");

  const menuBtn = iconButton("menu-btn", [["menu"]], "Mostrar u ocultar el menú");
  menuBtn.classList.add("menu-btn");
  header.appendChild(menuBtn);

  const brand = el("a", null, "brand");
  brand.href = "/";
  brand.appendChild(el("span", "HD", "brand-mark"));
  brand.appendChild(el("span", "Help Desk", "brand-name"));
  header.appendChild(brand);

  // Buscador global: un número (INC0000012 o 12) abre el incidente; el resto busca texto
  const form = el("form", null, "global-search");
  form.setAttribute("role", "search");
  form.appendChild(icon("search", "search-icon"));
  const input = el("input");
  input.type = "search";
  input.id = "global-search";
  input.maxLength = 100;
  input.placeholder = "Buscar incidente (INC0000001) o texto";
  input.setAttribute("aria-label", "Buscar incidentes");
  form.appendChild(input);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    const number = parseTicketNumber(value);
    if (number) {
      window.location.href = "/ticket.html?id=" + number;
    } else {
      window.location.href = "/?view=all&q=" + encodeURIComponent(value);
    }
  });
  header.appendChild(form);

  const userBox = el("div", null, "hdr-user");
  userBox.appendChild(iconButton("theme-btn", [["moon", "icon-moon"], ["sun", "icon-sun"]], "Cambiar tema"));
  const who = el("div", null, "who");
  who.appendChild(el("span", "", "avatar-sm"));
  who.lastChild.id = "user-avatar";
  const names = el("div", null, "who-text");
  names.appendChild(el("span", "", "who-name"));
  names.lastChild.id = "user-name";
  names.appendChild(el("span", "", "who-role"));
  names.lastChild.id = "user-role";
  who.appendChild(names);
  userBox.appendChild(who);
  userBox.appendChild(iconButton("logout-btn", [["logout"]], "Cerrar sesión"));
  header.appendChild(userBox);

  return header;
}

function buildSidebar() {
  const nav = el("nav", null, "sidebar");
  nav.id = "sidebar";
  nav.setAttribute("aria-label", "Navegación");

  const filter = el("input", null, "nav-filter");
  filter.type = "search";
  filter.placeholder = "Filtrar navegador";
  filter.setAttribute("aria-label", "Filtrar el menú");
  nav.appendChild(filter);

  for (const section of NAV_SECTIONS) {
    const sec = el("div", null, "nav-section");
    if (section.roles) sec.dataset.roles = section.roles.join(" ");
    sec.appendChild(el("div", section.title, "nav-title"));
    const ul = el("ul");
    for (const item of section.items) {
      const li = el("li");
      if (item.roles) li.dataset.roles = item.roles.join(" ");
      const a = el("a", null, "nav-item");
      a.href = item.href;
      if (item.id) a.id = item.id;
      if (isNavActive(item)) {
        a.classList.add("active");
        a.setAttribute("aria-current", "page");
      }
      a.appendChild(icon(item.icon));
      a.appendChild(el("span", item.label, "nav-label"));
      if (item.badge) {
        const badge = el("span", null, "count-badge");
        badge.id = item.badge;
        badge.hidden = true;
        a.appendChild(badge);
      }
      li.appendChild(a);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    nav.appendChild(sec);
  }

  filter.addEventListener("input", () => {
    const text = filter.value.trim().toLowerCase();
    for (const li of nav.querySelectorAll("li")) {
      li.classList.toggle("filtered-out", !li.textContent.toLowerCase().includes(text));
    }
  });
  return nav;
}

/** Oculta las entradas del menú que no corresponden al rol. Lo llama loadCurrentUser(). */
function applyRoleToLayout(me) {
  for (const node of document.querySelectorAll("[data-roles]")) {
    node.hidden = !node.dataset.roles.split(" ").includes(me.role);
  }
  const avatar = document.getElementById("user-avatar");
  if (avatar) avatar.textContent = initials(me.full_name);
  const role = document.getElementById("user-role");
  if (role) role.textContent = ROLE_LABELS[me.role] || me.role;
}

(function mountLayout() {
  const main = document.querySelector("main");
  if (!main) return;
  const shell = el("div", null, "app-shell");
  const content = el("div", null, "app-content");
  main.parentNode.insertBefore(shell, main);
  shell.appendChild(buildSidebar());
  content.appendChild(main);
  shell.appendChild(content);
  document.body.insertBefore(buildHeader(), shell);

  // Hasta saber el rol, no se enseñan las secciones restringidas
  for (const node of document.querySelectorAll(".sidebar [data-roles]")) node.hidden = true;

  const KEY = "helpdesk_nav_collapsed";
  try {
    if (localStorage.getItem(KEY) === "1") document.body.classList.add("nav-collapsed");
  } catch (err) {
    // Sin almacenamiento: el menú empieza abierto
  }
  document.getElementById("menu-btn").addEventListener("click", () => {
    if (window.matchMedia("(max-width: 900px)").matches) {
      document.body.classList.toggle("nav-open");
      return;
    }
    document.body.classList.toggle("nav-collapsed");
    try {
      localStorage.setItem(KEY, document.body.classList.contains("nav-collapsed") ? "1" : "0");
    } catch (err) {
      // Ignorado
    }
  });
})();
