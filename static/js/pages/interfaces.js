import { apiFetch, escapeHtml, requireAuth, toast } from "../app.js";

let interfacesCache = [];

function normalizeInterface(itf) {
  const name = itf?.name || "";
  const listenPort = itf?.["listen-port"] ?? itf?.listen_port ?? "";
  const disabled = String(itf?.disabled ?? "false") === "true" || String(itf?.disabled ?? "no") === "yes";
  return { raw: itf, name, listenPort, disabled };
}

function renderInterfaces(items) {
  const tbody = document.getElementById("tblInterfaces");
  if (!tbody) return;

  tbody.innerHTML = items
    .map((itf) => {
      const statusBadge = itf.disabled
        ? '<span class="badge text-bg-secondary">Desabilitada</span>'
        : '<span class="badge text-bg-success">Ativa</span>';

      const toggleAction = itf.disabled ? "enable" : "disable";
      const toggleLabel = itf.disabled ? "Habilitar" : "Desabilitar";

      return `
        <tr>
          <td class="fw-semibold">${escapeHtml(itf.name)}</td>
          <td>${escapeHtml(String(itf.listenPort || "—"))}</td>
          <td>${statusBadge}</td>
          <td class="text-end" style="white-space: nowrap;">
            <button class="btn btn-outline-secondary btn-sm" data-action="stats" data-name="${escapeHtml(itf.name)}">Stats</button>
            <button class="btn btn-outline-secondary btn-sm" data-action="edit" data-name="${escapeHtml(itf.name)}">Editar</button>
            <button class="btn btn-outline-secondary btn-sm" data-action="${toggleAction}" data-name="${escapeHtml(itf.name)}">${toggleLabel}</button>
            <button class="btn btn-outline-danger btn-sm" data-action="delete" data-name="${escapeHtml(itf.name)}">Excluir</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadInterfaces() {
  const res = await apiFetch("/interfaces", { method: "GET" });
  if (res.status === 403) {
    toast("Acesso negado: interfaces requer admin", "warning");
    return;
  }

  const data = await res.json().catch(() => []);
  if (!res.ok) {
    toast(data?.error || "Falha ao carregar interfaces", "danger");
    return;
  }

  const list = Array.isArray(data) ? data : [];
  interfacesCache = list.map(normalizeInterface);
  renderInterfaces(interfacesCache);
}

async function createInterface(form) {
  const payload = {
    name: form.name.value.trim(),
    listen_port: Number(form.listen_port.value),
  };

  const res = await apiFetch("/interfaces", { method: "POST", json: payload });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao criar interface", "danger");
    return;
  }

  toast("Interface criada", "success");
  form.reset();
  await loadInterfaces();
}

function openEditModal(name) {
  const itf = interfacesCache.find((x) => x.name === name);
  if (!itf) return;

  const form = document.getElementById("formEditInterface");
  form.old_name.value = itf.name;
  form.name.value = itf.name;
  form.listen_port.value = itf.listenPort || "";

  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditInterface")).show();
}

async function saveEdit() {
  const form = document.getElementById("formEditInterface");
  const oldName = form.old_name.value;

  const payload = {
    name: form.name.value.trim(),
    listen_port: Number(form.listen_port.value),
  };

  const res = await apiFetch(`/interfaces/${encodeURIComponent(oldName)}`, {
    method: "PUT",
    json: payload,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao salvar", "danger");
    return;
  }

  toast("Interface atualizada", "success");
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditInterface")).hide();
  await loadInterfaces();
}

async function toggleInterface(name, action) {
  const res = await apiFetch(`/interfaces/${encodeURIComponent(name)}/${action}`, { method: "POST", json: {} });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao alterar status", "danger");
    return;
  }
  toast("Status atualizado", "success");
  await loadInterfaces();
}

async function deleteInterface(name) {
  const ok = confirm(`Excluir interface ${name}?`);
  if (!ok) return;

  const res = await apiFetch(`/interfaces/${encodeURIComponent(name)}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao excluir", "danger");
    return;
  }
  toast("Interface removida", "success");
  await loadInterfaces();
}

async function showStats(name) {
  const res = await apiFetch(`/interfaces/${encodeURIComponent(name)}/stats`, { method: "GET" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao obter stats", "danger");
    return;
  }

  document.getElementById("modalStatsTitle").textContent = `Stats: ${name}`;
  document.getElementById("preStats").textContent = JSON.stringify(data, null, 2);
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalStats")).show();
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await loadInterfaces();

  document.getElementById("btnReload")?.addEventListener("click", loadInterfaces);

  const formCreate = document.getElementById("formCreateInterface");
  formCreate?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await createInterface(formCreate);
  });

  document.getElementById("btnSaveInterface")?.addEventListener("click", saveEdit);

  document.getElementById("tblInterfaces")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const action = btn.dataset.action;
    const name = btn.dataset.name;
    if (!action || !name) return;

    if (action === "edit") openEditModal(name);
    if (action === "enable") await toggleInterface(name, "enable");
    if (action === "disable") await toggleInterface(name, "disable");
    if (action === "delete") await deleteInterface(name);
    if (action === "stats") await showStats(name);
  });
});
