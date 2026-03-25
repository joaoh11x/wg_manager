import { apiFetch, escapeHtml, requireAuth, toast } from "../app.js";

let selectedGroupId = null;
let groupsCache = [];

async function loadGroups() {
  const res = await apiFetch("/groups", { method: "GET" });
  if (res.status === 403) {
    toast("Acesso negado: grupos requer admin", "warning");
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.success) {
    toast(data?.error || "Falha ao carregar grupos", "danger");
    return;
  }

  groupsCache = Array.isArray(data.groups) ? data.groups : [];
  renderGroups(groupsCache);

  // se o grupo selecionado não existe mais, limpa
  if (selectedGroupId && !groupsCache.some((g) => String(g.id) === String(selectedGroupId))) {
    selectedGroupId = null;
    renderGroupPeers([]);
  }
}

function renderGroups(groups) {
  const tbody = document.getElementById("tblGroups");
  if (!tbody) return;

  tbody.innerHTML = groups
    .map((g) => {
      const isSelected = String(g.id) === String(selectedGroupId);
      return `
        <tr data-group-id="${g.id}" class="${isSelected ? "table-active" : ""}" style="cursor: pointer;">
          <td class="fw-semibold">${escapeHtml(g.name)}</td>
          <td class="text-muted">${escapeHtml(g.description || "—")}</td>
          <td class="text-end" style="white-space: nowrap;">
            <button class="btn btn-outline-secondary btn-sm" data-action="edit" data-group-id="${g.id}">Editar</button>
            <button class="btn btn-outline-danger btn-sm" data-action="delete" data-group-id="${g.id}">Excluir</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function createGroup(form) {
  const payload = {
    name: form.name.value.trim(),
    description: (form.description.value || "").trim() || null,
  };

  const res = await apiFetch("/groups", { method: "POST", json: payload });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao criar grupo", "danger");
    return;
  }

  toast("Grupo criado", "success");
  form.reset();
  await loadGroups();
}

async function deleteGroup(groupId) {
  const g = groupsCache.find((x) => String(x.id) === String(groupId));
  const ok = confirm(`Excluir grupo ${g?.name || groupId}?`);
  if (!ok) return;

  const res = await apiFetch(`/groups/${encodeURIComponent(groupId)}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao excluir", "danger");
    return;
  }

  toast("Grupo removido", "success");
  await loadGroups();
}

function openEditModal(groupId) {
  const group = groupsCache.find((g) => String(g.id) === String(groupId));
  if (!group) return;

  const form = document.getElementById("formEditGroup");
  form.group_id.value = group.id;
  form.name.value = group.name || "";
  form.description.value = group.description || "";

  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditGroup")).show();
}

async function saveEditGroup() {
  const form = document.getElementById("formEditGroup");
  const groupId = form.group_id.value;
  const payload = {
    name: form.name.value.trim(),
    description: (form.description.value || "").trim() || null,
  };

  const res = await apiFetch(`/groups/${encodeURIComponent(groupId)}`, {
    method: "PUT",
    json: payload,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao salvar", "danger");
    return;
  }

  toast("Grupo atualizado", "success");
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditGroup")).hide();
  await loadGroups();
}

async function loadGroupPeers() {
  if (!selectedGroupId) return;

  const btn = document.getElementById("btnReloadGroupPeers");
  if (btn) btn.disabled = true;

  const res = await apiFetch(`/groups/${encodeURIComponent(selectedGroupId)}/peers`, { method: "GET" });
  const data = await res.json().catch(() => ({}));
  if (btn) btn.disabled = false;

  if (!res.ok) {
    toast(data?.error || "Falha ao carregar peers do grupo", "danger");
    return;
  }

  const peers = Array.isArray(data?.peers) ? data.peers : [];
  renderGroupPeers(peers);
}

function renderGroupPeers(peers) {
  const tbody = document.getElementById("tblGroupPeers");
  if (!tbody) return;

  tbody.innerHTML = peers
    .map(
      (p) => `
      <tr>
        <td class="fw-semibold">${escapeHtml(p.name || "")}</td>
        <td class="text-muted">${escapeHtml(p.email || "—")}</td>
      </tr>
    `
    )
    .join("");

  const meta = document.getElementById("groupPeersMeta");
  if (meta) {
    const g = groupsCache.find((x) => String(x.id) === String(selectedGroupId));
    meta.textContent = g ? `${g.name} • ${peers.length} peer(s)` : `${peers.length} peer(s)`;
  }

  const btn = document.getElementById("btnReloadGroupPeers");
  if (btn) btn.disabled = !selectedGroupId;
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await loadGroups();

  document.getElementById("btnReloadGroups")?.addEventListener("click", loadGroups);

  const formCreate = document.getElementById("formCreateGroup");
  formCreate?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await createGroup(formCreate);
  });

  document.getElementById("btnSaveGroup")?.addEventListener("click", saveEditGroup);

  document.getElementById("btnReloadGroupPeers")?.addEventListener("click", loadGroupPeers);

  document.getElementById("tblGroups")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    const row = e.target.closest("tr[data-group-id]");

    if (btn) {
      const action = btn.dataset.action;
      const groupId = btn.dataset.groupId;
      if (action === "edit") openEditModal(groupId);
      if (action === "delete") await deleteGroup(groupId);
      e.stopPropagation();
      return;
    }

    if (row) {
      selectedGroupId = row.dataset.groupId;
      renderGroups(groupsCache);
      await loadGroupPeers();
    }
  });
});
