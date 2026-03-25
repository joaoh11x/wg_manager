import {
  apiFetch,
  escapeHtml,
  formatBytes,
  requireAuth,
  toast,
} from "../app.js";

let groupsCache = [];
let currentPeerForConfig = "";

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
    return;
  }

  const data = await res.json().catch(() => ({}));
  groupsCache = Array.isArray(data?.groups) ? data.groups : [];

  fillGroupSelect("selPeerGroup");
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

      return `
        <tr>
          <td class="fw-semibold">${escapeHtml(p.name)}</td>
          <td>${escapeHtml(p.interface || "")}</td>
          <td style="min-width: 190px;">${groupCell}</td>
          <td class="text-end"><span class="wg-badge">${formatBytes(parseNumber(p.rx))}</span></td>
          <td class="text-end"><span class="wg-badge">${formatBytes(parseNumber(p.tx))}</span></td>
          <td class="text-muted small">${escapeHtml(p.last_handshake || "—")}</td>
          <td class="text-end" style="white-space: nowrap;">
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
  renderPeers(peers);

  const meta = document.getElementById("peersMeta");
  if (meta) meta.textContent = `${peers.length} peer(s)`;
}

async function createPeer(form) {
  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    interface: form.interface.value,
  };

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
    await navigator.clipboard.writeText(`username: ${creds.username}\npassword: ${creds.password}`);
    toast("Senha resetada (copiada para a área de transferência)", "success");
  } else {
    toast("Senha resetada", "success");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await loadInterfaces("selPeerInterface");
  await loadInterfaces("selFilterInterface");
  await loadGroups();
  await loadPeers();

  document.getElementById("btnReload")?.addEventListener("click", loadPeers);
  document.getElementById("selFilterInterface")?.addEventListener("change", loadPeers);

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
    if (action === "config") await showConfig(peer);
    if (action === "qr") await showQr(peer);
    if (action === "reset") await resetPassword(peer);
  });

  document.getElementById("tblPeers")?.addEventListener("change", async (e) => {
    const sel = e.target.closest("select[data-action='set-group']");
    if (!sel) return;

    const peer = sel.dataset.peer;
    const groupId = sel.value;
    const ok = await setPeerGroup(peer, groupId);
    if (!ok) await loadPeers();
  });

  document.getElementById("btnCopyConfig")?.addEventListener("click", async () => {
    const txt = document.getElementById("txtConfig").value;
    await navigator.clipboard.writeText(txt);
    toast("Config copiada", "success");
  });

  document.getElementById("btnDownloadConfig")?.addEventListener("click", async () => {
    if (!currentPeerForConfig) return;
    await downloadConfig(currentPeerForConfig);
  });
});
