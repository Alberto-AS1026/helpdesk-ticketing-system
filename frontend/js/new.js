"use strict";

requireLogin();

const $ = (id) => document.getElementById(id);

function fill(select, items) {
  for (const item of items) {
    const o = el("option", item.name);
    o.value = item.id;
    select.appendChild(o);
  }
}

async function init() {
  try {
    await loadCurrentUser();
    const [priorities, categories] = await Promise.all([
      apiFetch("/priorities"),
      apiFetch("/categories"),
    ]);
    fill($("priority"), priorities);
    fill($("category"), categories);
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
    $("error").textContent = "El título necesita al menos 3 caracteres";
    return;
  }
  if (description.length < 5) {
    $("error").textContent = "La descripción necesita al menos 5 caracteres";
    return;
  }
  try {
    const created = await apiFetch("/tickets", {
      method: "POST",
      json: {
        title: title,
        description: description,
        priority_id: Number($("priority").value),
        category_id: Number($("category").value),
      },
    });
    window.location.href = "/ticket.html?id=" + Number(created.id);
  } catch (err) {
    $("error").textContent = err.message;
  }
});

init();
