import {
  apiFetch,
  escapeHtml,
  formatBytes,
  requireAuth,
  toast,
} from "../app.js";

let groupsCache = [];
let currentPeerForConfig = "";
let currentPeerForEdit = "";
let allPeersCache = [];
const PAGE_SIZE = 10;
let currentPage = 1;
let currentTotalPages = 1;

function asEnabled(value) {
  if (value === false) return false;
  if (value === true) return true;
  return true;
}

function parseNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

async function loadInterfaces(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;

  sel.innerHTML = `<option value="">Carregando…</option>`;

  const res = await apiFetch("/interfaces", { method: "GET" });
  if (res.status === 403) {
    sel.innerHTML = `<option value="">(admin necessário)</option>`;
    return;
  }
  const data = await res.json().catch(() => []);

  const interfaces = Array.isArray(data) ? data : [];
  sel.innerHTML = "";

  if (selectId === "selFilterInterface") {
    sel.appendChild(new Option("Todas as interfaces", ""));
  }

  for (const itf of interfaces) {
    const name = itf?.name;
    if (!name) continue;
    sel.appendChild(new Option(name, name));
  }

  if (!sel.options.length) {
    sel.appendChild(new Option("(sem interfaces)", ""));
  }
}

async function loadGroups() {
  const res = await apiFetch("/groups", { method: "GET" });
  if (res.status === 403) {
    groupsCache = [];
    fillGroupSelect("selPeerGroup");
    fillGroupFilterSelect();
    return;
  }

  const data = await res.json().catch(() => ({}));
  groupsCache = Array.isArray(data?.groups) ? data.groups : [];

  fillGroupSelect("selPeerGroup");
  fillGroupFilterSelect();
}

function fillGroupSelect(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;

  sel.innerHTML = "";
  sel.appendChild(new Option("Sem grupo", ""));
  for (const g of groupsCache) {
    sel.appendChild(new Option(g.name, String(g.id)));
  }
}

function fillGroupFilterSelect() {
  const sel = document.getElementById("selFilterGroup");
  if (!sel) return;

  sel.innerHTML = "";
  sel.appendChild(new Option("Todos os grupos", ""));
  sel.appendChild(new Option("Sem grupo", "__none__"));
  for (const g of groupsCache) {
    sel.appendChild(new Option(g.name, String(g.id)));
  }
}

function fillStatusFilterSelect() {
  const sel = document.getElementById("selFilterStatus");
  if (!sel) return;

  sel.innerHTML = "";
  sel.appendChild(new Option("Todos", ""));
  sel.appendChild(new Option("Ativo", "active"));
  sel.appendChild(new Option("Inativo", "inactive"));
}

function getFilteredPeers() {
  const rawName = document.getElementById("txtFilterName")?.value || "";
  const nameNeedle = rawName.trim().toLowerCase();

  const groupValue = document.getElementById("selFilterGroup")?.value ?? "";
  const statusValue = document.getElementById("selFilterStatus")?.value ?? "";

  return allPeersCache.filter((p) => {
    if (nameNeedle) {
      const peerName = String(p?.name || "").toLowerCase();
      if (!peerName.includes(nameNeedle)) return false;
    }

    if (groupValue) {
      const peerGroupId = p?.group?.id;
      if (groupValue === "__none__") {
        if (peerGroupId !== null && peerGroupId !== undefined && String(peerGroupId) !== "") return false;
      } else if (String(peerGroupId ?? "") !== String(groupValue)) {
        return false;
      }
    }

    if (statusValue) {
      const enabled = asEnabled(p?.enabled);
      if (statusValue === "active" && !enabled) return false;
      if (statusValue === "inactive" && enabled) return false;
    }

    return true;
  });
}

function applyFilters() {
  const filtered = getFilteredPeers();
  const total = allPeersCache.length;
  const filteredCount = filtered.length;

  currentTotalPages = Math.max(1, Math.ceil(filteredCount / PAGE_SIZE));
  if (currentPage > currentTotalPages) currentPage = currentTotalPages;
  if (currentPage < 1) currentPage = 1;

  const start = (currentPage - 1) * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, filteredCount);
  const pageItems = filtered.slice(start, end);

  renderPeers(pageItems);

  const meta = document.getElementById("peersMeta");
  if (meta) {
    meta.textContent = filteredCount === total ? `${filteredCount} peer(s)` : `${filteredCount} de ${total} peer(s)`;
  }

  const pageLbl = document.getElementById("peersPage");
  if (pageLbl) {
    pageLbl.textContent = `Página ${currentPage}/${currentTotalPages}`;
  }

  const btnPrev = document.getElementById("btnPrevPage");
  const btnNext = document.getElementById("btnNextPage");
  if (btnPrev) btnPrev.disabled = currentPage <= 1;
  if (btnNext) btnNext.disabled = currentPage >= currentTotalPages;
}

function resetToFirstPageAndApply() {
  currentPage = 1;
  applyFilters();
}

function buildGroupSelectHtml(peerName, currentGroupId) {
  const options = [
    `<option value="">Sem grupo</option>`,
    ...groupsCache.map(
      (g) =>
        `<option value="${g.id}" ${String(g.id) === String(currentGroupId) ? "selected" : ""}>${escapeHtml(g.name)}</option>`
    ),
  ].join("");

  return `<select class="form-select form-select-sm" data-peer="${escapeHtml(peerName)}" data-action="set-group">${options}</select>`;
}

async function setPeerGroup(peerName, groupId) {
  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/group`, {
    method: "PUT",
    json: { group_id: groupId === "" ? null : Number(groupId) },
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao atualizar grupo", "danger");
    return false;
  }

  toast("Grupo atualizado", "success");
  return true;
}

function renderPeers(peers) {
  const tbody = document.getElementById("tblPeers");
  if (!tbody) return;

  tbody.innerHTML = peers
    .map((p) => {
      const groupId = p?.group?.id ?? "";
      const groupName = p?.group?.name || "";
      const groupCell = groupsCache.length
        ? buildGroupSelectHtml(p.name, groupId)
        : (groupName ? escapeHtml(groupName) : "—");

      const enabled = asEnabled(p?.enabled);
      const statusDot = enabled
        ? `<span class="wg-status-dot text-success" title="Ativo">●</span>`
        : `<span class="wg-status-dot text-danger" title="Inativo">●</span>`;

      const toggleBtn = enabled
        ? `<button class="btn btn-outline-secondary btn-sm" data-action="disable" data-peer="${escapeHtml(p.name)}">Desativar</button>`
        : `<button class="btn btn-outline-secondary btn-sm" data-action="enable" data-peer="${escapeHtml(p.name)}">Ativar</button>`;

      return `
        <tr>
          <td class="fw-semibold">${escapeHtml(p.name)}</td>
          <td>${escapeHtml(p.interface || "")}</td>
          <td style="min-width: 190px;">${groupCell}</td>
          <td class="wg-status-cell">${statusDot}</td>
          <td class="text-end"><span class="wg-badge">${formatBytes(parseNumber(p.rx))}</span></td>
          <td class="text-end"><span class="wg-badge">${formatBytes(parseNumber(p.tx))}</span></td>
          <td class="text-muted small">${escapeHtml(p.last_handshake || "—")}</td>
          <td class="text-end" style="white-space: nowrap;">
            ${toggleBtn}
            <button class="btn btn-outline-secondary btn-sm" data-action="edit" data-peer="${escapeHtml(p.name)}">Editar</button>
            <button class="btn btn-outline-secondary btn-sm" data-action="config" data-peer="${escapeHtml(p.name)}">Config</button>
            <button class="btn btn-outline-secondary btn-sm" data-action="qr" data-peer="${escapeHtml(p.name)}">QR</button>
            <button class="btn btn-outline-secondary btn-sm" data-action="reset" data-peer="${escapeHtml(p.name)}">Reset senha</button>
            <button class="btn btn-outline-danger btn-sm" data-action="delete" data-peer="${escapeHtml(p.name)}">Excluir</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function setPeerEnabled(peerName, enabled) {
  const action = enabled ? "enable" : "disable";
  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/${action}`, {
    method: "POST",
    json: {},
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao alterar status", "danger");
    return false;
  }

  allPeersCache = allPeersCache.map((p) => (p?.name === peerName ? { ...p, enabled } : p));
  applyFilters();
  toast(enabled ? "Peer ativado" : "Peer desativado", "success");
  return true;
}

async function loadPeers() {
  const sel = document.getElementById("selFilterInterface");
  const iface = sel?.value || "";
  const url = iface ? `/wireguard/peers?interface=${encodeURIComponent(iface)}` : "/wireguard/peers";

  const res = await apiFetch(url, { method: "GET" });
  if (res.status === 403) {
    toast("Acesso negado: peers requer admin", "warning");
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.success) {
    toast(data?.error || "Falha ao carregar peers", "danger");
    return;
  }

  const peers = Array.isArray(data.peers) ? data.peers : [];
  allPeersCache = peers;
  currentPage = 1;
  applyFilters();
}

async function createPeer(form) {
  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    interface: form.interface.value,
  };

  const cpf = (form.cpf?.value || "").trim();
  if (cpf) payload.cpf = cpf;

  const dns = (form.client_dns.value || "").trim();
  if (dns) payload.client_dns = dns;

  const groupId = (form.group_id.value || "").trim();
  if (groupId) payload.group_id = Number(groupId);

  const res = await apiFetch("/wireguard/peers", {
    method: "POST",
    json: payload,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao criar peer", "danger");
    return;
  }

  toast("Peer criado", "success");
  form.reset();
  await loadPeers();
}

function findPeer(peerName) {
  return allPeersCache.find((p) => p?.name === peerName) || null;
}

async function showEdit(peerName) {
  const peer = findPeer(peerName);
  if (!peer) {
    toast("Peer não encontrado na lista", "warning");
    return;
  }

  currentPeerForEdit = peerName;
  const form = document.getElementById("formEditPeer");
  if (!form) return;

  form.peer_name.value = peerName;
  form.email.value = peer?.email || "";
  form.cpf.value = peer?.cpf || "";

  document.getElementById("modalEditPeerTitle").textContent = `Editar: ${peerName}`;
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditPeer"));
  modal.show();
}

async function updatePeer(peerName, form) {
  const payload = {
    email: form.email.value.trim(),
  };

  const cpf = (form.cpf.value || "").trim();
  if (cpf) payload.cpf = cpf;
  else payload.cpf = "";

  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}`, {
    method: "PUT",
    json: payload,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao atualizar peer", "danger");
    return false;
  }

  const updated = data?.peer;
  if (updated?.name) {
    allPeersCache = allPeersCache.map((p) =>
      p?.name === updated.name
        ? {
            ...p,
            email: updated.email,
            cpf: updated.cpf,
          }
        : p
    );
  } else {
    await loadPeers();
  }

  applyFilters();
  toast("Peer atualizado", "success");
  return true;
}

async function deletePeer(peerName) {
  const ok = confirm(`Remover peer ${peerName}?`);
  if (!ok) return;

  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}`, {
    method: "DELETE",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao remover", "danger");
    return;
  }
  toast("Peer removido", "success");
  await loadPeers();
}

async function showConfig(peerName) {
  currentPeerForConfig = peerName;

  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/config`, {
    method: "GET",
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao obter config", "danger");
    return;
  }

  document.getElementById("modalConfigTitle").textContent = `Config: ${peerName}`;
  document.getElementById("txtConfig").value = data.config || "";

  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("modalConfig"));
  modal.show();
}

async function downloadConfig(peerName) {
  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/config/download`, {
    method: "GET",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    toast(data?.error || "Falha ao baixar", "danger");
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${peerName}.conf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function showQr(peerName) {
  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/qrcode`, {
    method: "GET",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao obter QR", "danger");
    return;
  }

  document.getElementById("modalQrTitle").textContent = `QR Code: ${peerName}`;
  document.getElementById("imgQr").src = data.qr_code || "";
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("modalQr"));
  modal.show();
}

async function copyToClipboard(text) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  // Fallback para contextos onde Clipboard API não está disponível (ex.: HTTP)
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  const ok = document.execCommand("copy");
  ta.remove();
  return ok;
}

async function resetPassword(peerName) {
  const ok = confirm(`Resetar a senha do usuário vinculado ao peer ${peerName}?`);
  if (!ok) return;

  const res = await apiFetch(`/wireguard/peers/${encodeURIComponent(peerName)}/password/reset`, {
    method: "POST",
    json: {},
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao resetar", "danger");
    return;
  }

  const creds = data?.credentials;
  if (creds?.username && creds?.password) {
    const text = `username: ${creds.username}\npassword: ${creds.password}`;
    const copied = await copyToClipboard(text);
    toast(
      copied
        ? "Senha resetada (copiada para a área de transferência)"
        : "Senha resetada (não foi possível copiar automaticamente)",
      copied ? "success" : "warning"
    );
  } else {
    toast("Senha resetada", "success");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await loadInterfaces("selPeerInterface");
  await loadInterfaces("selFilterInterface");
  await loadGroups();
  fillStatusFilterSelect();
  await loadPeers();

  document.getElementById("btnReload")?.addEventListener("click", loadPeers);
  document.getElementById("selFilterInterface")?.addEventListener("change", loadPeers);
  document.getElementById("txtFilterName")?.addEventListener("input", resetToFirstPageAndApply);
  document.getElementById("selFilterGroup")?.addEventListener("change", resetToFirstPageAndApply);
  document.getElementById("selFilterStatus")?.addEventListener("change", resetToFirstPageAndApply);

  document.getElementById("btnPrevPage")?.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage -= 1;
      applyFilters();
    }
  });
  document.getElementById("btnNextPage")?.addEventListener("click", () => {
    if (currentPage < currentTotalPages) {
      currentPage += 1;
      applyFilters();
    }
  });

  const createForm = document.getElementById("formCreatePeer");
  createForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await createPeer(createForm);
  });

  document.getElementById("tblPeers")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const action = btn.dataset.action;
    const peer = btn.dataset.peer;
    if (!action || !peer) return;

    if (action === "delete") await deletePeer(peer);
    if (action === "edit") await showEdit(peer);
    if (action === "config") await showConfig(peer);
    if (action === "qr") await showQr(peer);
    if (action === "reset") await resetPassword(peer);
    if (action === "enable") await setPeerEnabled(peer, true);
    if (action === "disable") await setPeerEnabled(peer, false);
  });

  const editForm = document.getElementById("formEditPeer");
  editForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentPeerForEdit) return;
    const ok = await updatePeer(currentPeerForEdit, editForm);
    if (ok) {
      const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEditPeer"));
      modal.hide();
    }
  });

  document.getElementById("tblPeers")?.addEventListener("change", async (e) => {
    const sel = e.target.closest("select[data-action='set-group']");
    if (!sel) return;

    const peer = sel.dataset.peer;
    const groupId = sel.value;
    const ok = await setPeerGroup(peer, groupId);
    if (!ok) {
      await loadPeers();
      return;
    }

    const newGroupId = groupId === "" ? null : Number(groupId);
    const groupObj = groupsCache.find((g) => String(g.id) === String(newGroupId)) || null;
    allPeersCache = allPeersCache.map((p) =>
      p?.name === peer
        ? {
            ...p,
            group: groupObj ? { id: groupObj.id, name: groupObj.name } : null,
          }
        : p
    );
    applyFilters();
  });

  document.getElementById("btnCopyConfig")?.addEventListener("click", async () => {
    const txt = document.getElementById("txtConfig").value;
    const copied = await copyToClipboard(txt);
    toast(copied ? "Config copiada" : "Não foi possível copiar", copied ? "success" : "warning");
  });

  document.getElementById("btnDownloadConfig")?.addEventListener("click", async () => {
    if (!currentPeerForConfig) return;
    await downloadConfig(currentPeerForConfig);
  });
});
