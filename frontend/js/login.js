"use strict";

// Si ya hay sesión, entra directamente
if (getToken()) {
  window.location.href = "/";
}

const form = document.getElementById("login-form");
const errorBox = document.getElementById("error");
const submitBtn = document.getElementById("submit-btn");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !password) {
    errorBox.textContent = "Escribe tu email y tu contraseña";
    return;
  }

  submitBtn.disabled = true;
  try {
    // El login usa formulario (OAuth2), no JSON
    const body = new URLSearchParams({ username: email, password: password });
    const data = await apiFetch("/auth/login", { method: "POST", body: body });
    setToken(data.access_token);
    window.location.href = "/";
  } catch (err) {
    errorBox.textContent = err.message;
  } finally {
    submitBtn.disabled = false;
  }
});
