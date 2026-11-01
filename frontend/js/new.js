"use strict";

requireLogin();

const $ = (id) => document.getElementById(id);

function fill(select, items, label = (i) => i.name) {
  for (const item of items) {
    const o = el("option", label(item));
    o.value = item.id;
    select.appendChild(o);
  }
}

async function init() {
  try {
    const me = await loadCurrentUser();
    $("caller").textContent = me.full_name;
    const [priorities, categories, computers] = await Promise.all([
      apiFetch("/priorities"),
      apiFetch("/categories"),
      apiFetch("/computers").catch(() => []),
    ]);
    // De más a menos grave; por defecto, la menos grave
    priorities.sort((a, b) => (PRIORITY_RANK[a.name] || 9) - (PRIORITY_RANK[b.name] || 9));
    fill($("priority"), priorities, (p) => priorityLabel(p.name));
    $("priority").selectedIndex = priorities.length - 1;
    fill($("category"), categories);
    // Primero los equipos asignados al solicitante
    computers.sort((a, b) => (b.assigned_to === me.id) - (a.assigned_to === me.id) || a.hostname.localeCompare(b.hostname));
    fill($("computer"), computers, (c) => c.hostname + (c.assigned_to === me.id ? " (mi equipo)" : ""));
    const mine = computers.find((c) => c.assigned_to === me.id);
    if (mine) $("computer").value = String(mine.id);
  } catch (err) {
    $("error").textContent = err.message;
  }
}

$("new-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("error").textContent = "";
  const title = $("title").value.trim();
  const description = $("description").value.trim();
  if (title.length < 3) {
    $("error").textContent = "La breve descripción necesita al menos 3 caracteres";
    $("title").focus();
    return;
  }
  if (description.length < 5) {
    $("error").textContent = "La descripción necesita al menos 5 caracteres";
    $("description").focus();
    return;
  }
  const body = {
    title: title,
    description: description,
    priority_id: Number($("priority").value),
    category_id: Number($("category").value),
  };
  if ($("computer").value) body.computer_id = Number($("computer").value);
  try {
    const created = await apiFetch("/tickets", { method: "POST", json: body });
    window.location.href = "/ticket.html?id=" + Number(created.id);
  } catch (err) {
    $("error").textContent = err.message;
  }
});

init();
