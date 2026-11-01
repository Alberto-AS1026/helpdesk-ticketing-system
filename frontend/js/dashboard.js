"use strict";

requireLogin();

const $ = (id) => document.getElementById(id);
const charts = {};

// Mismo código de color que las etiquetas de estado
const STATUS_COLORS = {
  "Abierto": "#ef4444",
  "En progreso": "#eab308",
  "Pendiente": "#facc15",
  "Resuelto": "#22c55e",
  "Cerrado": "#15803d",
};

let lastData = null;

/** Texto y rejilla de los gráficos según el tema activo. */
function applyChartTheme() {
  const css = getComputedStyle(document.documentElement);
  Chart.defaults.color = css.getPropertyValue("--muted").trim();
  Chart.defaults.borderColor = css.getPropertyValue("--border").trim();
  // Son conteos: sin decimales en los ejes numéricos
  Chart.defaults.scales.linear.ticks.precision = 0;
}

function drawChart(id, type, labels, datasets, options = {}) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), {
    type: type,
    data: { labels: labels, datasets: datasets },
    options: Object.assign({ responsive: true, maintainAspectRatio: false, animation: false }, options),
  });
}

function renderKpis(s) {
  // Cada indicador abre la lista correspondiente, como en las consolas ITSM
  const items = [
    ["Total de incidentes", s.total_tickets, "/?view=all", "kpi-neutral"],
    ["Activos", s.open_tickets, null, "kpi-warn"],
    ["Sin asignar", s.unassigned_tickets, "/?view=unassigned", s.unassigned_tickets > 0 ? "kpi-alert" : "kpi-neutral"],
    ["Resueltos o cerrados", s.resolved_tickets, "/?view=resolved", "kpi-ok"],
    ["Tiempo medio de resolución", s.avg_resolution_minutes === null ? "-" : s.avg_resolution_minutes + " min", null, "kpi-neutral"],
  ];
  const box = $("kpis");
  box.replaceChildren();
  for (const [label, value, href, tone] of items) {
    const tile = el(href ? "a" : "div", null, "kpi " + tone);
    if (href) tile.href = href;
    tile.appendChild(el("div", label, "label"));
    tile.appendChild(el("div", String(value), "value"));
    box.appendChild(tile);
  }
}

function render(data) {
  lastData = data;
  applyChartTheme();
  renderKpis(data.summary);

  drawChart("c-status", "doughnut", data.by_status.map((i) => i.label),
    [{
      data: data.by_status.map((i) => i.count),
      backgroundColor: data.by_status.map((i) => STATUS_COLORS[i.label] || "#6b7280"),
      borderColor: getComputedStyle(document.documentElement).getPropertyValue("--card").trim(),
    }]);

  drawChart("c-priority", "bar", data.by_priority.map((i) => i.label),
    [{ label: "Tickets", data: data.by_priority.map((i) => i.count), backgroundColor: "#1f73d6" }],
    { plugins: { legend: { display: false } } });

  drawChart("c-category", "bar", data.by_category.map((i) => i.label),
    [{ label: "Tickets", data: data.by_category.map((i) => i.count), backgroundColor: "#2f9e8f" }],
    { indexAxis: "y", plugins: { legend: { display: false } } });

  drawChart("c-tech", "bar", data.technician_load.map((t) => t.name),
    [
      { label: "Activos", data: data.technician_load.map((t) => t.open_tickets), backgroundColor: "#f59e0b" },
      { label: "Total", data: data.technician_load.map((t) => t.total_tickets), backgroundColor: "#6b7280" },
    ]);

  drawChart("c-day", "line", data.per_day.map((d) => d.day),
    [{ label: "Creados", data: data.per_day.map((d) => d.count), borderColor: "#1f73d6", backgroundColor: "#1f73d6", tension: 0.2, fill: false }],
    { plugins: { legend: { display: false } } });
}

async function load() {
  $("message").textContent = "";
  try {
    const data = await apiFetch("/stats?days=" + encodeURIComponent($("days").value));
    render(data);
  } catch (err) {
    $("message").textContent = err.message;
  }
}

$("days").addEventListener("change", load);

// Al cambiar de tema se repintan los gráficos con los datos ya cargados
document.addEventListener("themechange", () => {
  if (lastData) render(lastData);
});

async function init() {
  try {
    const me = await loadCurrentUser();
    if (me.role === "user") {
      $("message").textContent = "El dashboard solo está disponible para el personal técnico.";
      return;
    }
  } catch (err) {
    $("message").textContent = err.message;
    return;
  }
  load();
}

init();
