const TOKEN_KEY = "wg_access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(normalized)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function formatBytes(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = n;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  const digits = idx === 0 ? 0 : value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(digits)} ${units[idx]}`;
}

export function formatIso(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleString();
}

export function toast(message, variant = "dark") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${variant} border-0`;
  el.role = "alert";
  el.ariaLive = "assertive";
  el.ariaAtomic = "true";
  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${escapeHtml(message)}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 3500 });
  t.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

function renderForcePasswordChangeModal() {
  if (document.getElementById("modalForcePasswordChange")) return;

  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <div class="modal fade" id="modalForcePasswordChange" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Trocar senha</h5>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label" for="newPassword">Nova senha</label>
              <input class="form-control" type="password" id="newPassword" autocomplete="new-password" />
            </div>
            <div class="mb-2">
              <label class="form-label" for="confirmPassword">Confirmar nova senha</label>
              <input class="form-control" type="password" id="confirmPassword" autocomplete="new-password" />
            </div>
            <div class="text-muted small">Obrigatório na primeira entrada após reset.</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-dark" id="btnChangePassword" type="button">Salvar</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(wrapper.firstElementChild);
}

async function enforceMustChangePassword() {
  const token = getToken();
  if (!token) return;
  const payload = decodeJwt(token);
  if (!payload?.must_change_password) return;

  renderForcePasswordChangeModal();

  const elModal = document.getElementById("modalForcePasswordChange");
  const elNew = document.getElementById("newPassword");
  const elConfirm = document.getElementById("confirmPassword");
  const btn = document.getElementById("btnChangePassword");

  const modal = new bootstrap.Modal(elModal, {
    backdrop: "static",
    keyboard: false,
    focus: true,
  });

  const submit = async () => {
    const newPassword = elNew?.value || "";
    const confirmPassword = elConfirm?.value || "";
    if (!newPassword || !confirmPassword) {
      toast("Preencha os dois campos", "warning");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast("As senhas não conferem", "warning");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Salvando…";
    try {
      const res = await apiFetch("/me/password/change", {
        method: "POST",
        json: { new_password: newPassword, confirm_password: confirmPassword },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data?.error || "Falha ao trocar senha", "danger");
        return;
      }
      if (data?.access_token) setToken(data.access_token);
      modal.hide();
      location.reload();
    } finally {
      btn.disabled = false;
      btn.textContent = "Salvar";
    }
  };

  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", submit);
  }

  // Enter para submeter
  [elNew, elConfirm].forEach((el) => {
    if (!el || el.dataset.bound) return;
    el.dataset.bound = "1";
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
    });
  });

  modal.show();
  setTimeout(() => elNew?.focus(), 250);
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.json) headers.set("Content-Type", "application/json");

  const res = await fetch(path, {
    ...options,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });

  if (res.status === 401) {
    clearToken();
    if (location.pathname !== "/login") location.href = "/login";
  }

  return res;
}

export function requireAuth() {
  if (!getToken()) {
    location.href = "/login";
    return false;
  }
  return true;
}

export function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setActiveNav() {
  const path = location.pathname || "/";
  document.querySelectorAll(".navbar .nav-link").forEach((a) => {
    const href = a.getAttribute("href") || "";
    a.classList.toggle("active", href === path);
  });
}

function initNavUser() {
  const elUser = document.getElementById("navUser");
  const btnLogout = document.getElementById("btnLogout");

  const token = getToken();
  const payload = token ? decodeJwt(token) : null;
  const username = payload?.username || payload?.sub || "";
  const role = payload?.role ? `(${payload.role})` : "";

  if (elUser) elUser.textContent = username ? `${username} ${role}` : "";
  if (btnLogout) {
    btnLogout.classList.toggle("d-none", !token);
    btnLogout.addEventListener("click", () => {
      clearToken();
      location.href = "/login";
    });
  }

  // Para peers: esconder links da navbar (defesa em profundidade)
  const roleValue = payload?.role || "peer";
  if (roleValue === "peer") {
    const navLinks = document.getElementById("navLinks");
    if (navLinks) navLinks.classList.add("d-none");
  }
}

function enforcePeerSingleScreen() {
  const token = getToken();
  if (!token) return;
  const payload = decodeJwt(token);
  const role = payload?.role || "peer";
  const path = location.pathname || "/";
  if (role === "peer" && path.startsWith("/ui/") && path !== "/ui/me") {
    location.replace("/ui/me");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  enforcePeerSingleScreen();
  setActiveNav();
  initNavUser();
  enforceMustChangePassword();
});
