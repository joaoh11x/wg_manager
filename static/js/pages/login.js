import { apiFetch, setToken, toast } from "../app.js";

function setLoading(isLoading) {
  const btn = document.getElementById("btnLogin");
  if (!btn) return;
  btn.disabled = isLoading;
  btn.textContent = isLoading ? "Entrando…" : "Entrar";
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = form.username.value.trim();
    const password = form.password.value;

    if (!username || !password) {
      toast("Usuário e senha são obrigatórios", "warning");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/login", {
        method: "POST",
        json: { username, password },
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data?.error || "Falha no login", "danger");
        return;
      }

      if (!data?.access_token) {
        toast("Login OK, mas sem token", "danger");
        return;
      }

      setToken(data.access_token);
      toast("Login realizado", "success");
      location.href = "/ui/dashboard";
    } finally {
      setLoading(false);
    }
  });
});
