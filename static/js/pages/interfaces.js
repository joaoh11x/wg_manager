import { apiFetch, escapeHtml, requireAuth, toast } from "../app.js";

let interfacesCache = [];
let ipsCache = [];

const wizard = {
  step: 1,
  mode: "create", // create | edit
  oldName: "",
  interfaceName: "",
};

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

async function loadIps() {
  const res = await apiFetch("/ips", { method: "GET" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    ipsCache = [];
    return;
  }
  ipsCache = Array.isArray(data?.data) ? data.data : [];
}

function wizardModalEl() {
  return document.getElementById("modalInterfaceWizard");
}

function setWizardStep(step) {
  wizard.step = step;
  const stepLabel = document.getElementById("wizardStepLabel");
  const btnBack = document.getElementById("btnWizardBack");
  const btnNext = document.getElementById("btnWizardNext");

  [1, 2, 3, 4].forEach((n) => {
    const el = document.getElementById(`wizardStep${n}`);
    if (!el) return;
    el.classList.toggle("d-none", n !== step);
  });

  if (stepLabel) {
    const titles = {
      1: "Etapa 1 de 4: Criar interface",
      2: "Etapa 2 de 4: Configurar IP",
      3: "Etapa 3 de 4: Configurar NAT",
      4: "Etapa 4 de 4: Configurar firewall",
    };
    stepLabel.textContent = titles[step] || `Etapa ${step} de 4`;
  }

  if (btnBack) btnBack.disabled = step === 1;
  if (btnNext) btnNext.textContent = step === 4 ? "Concluir" : "Próximo";
}

function fillInterfaceSelect(selectEl, selectedName = "") {
  if (!selectEl) return;
  const options = interfacesCache
    .map((itf) => {
      const sel = itf.name === selectedName ? "selected" : "";
      return `<option value="${escapeHtml(itf.name)}" ${sel}>${escapeHtml(itf.name)}</option>`;
    })
    .join("");
  selectEl.innerHTML = options || '<option value="" disabled selected>Sem interfaces</option>';
}

function fillPortSelect(selectEl, selectedPort = "") {
  if (!selectEl) return;
  const options = interfacesCache
    .map((itf) => {
      const value = String(itf.listenPort || "");
      const label = `${itf.name} (${value || "—"})`;
      const sel = selectedPort && value === String(selectedPort) ? "selected" : "";
      return `<option value="${escapeHtml(value)}" ${sel}>${escapeHtml(label)}</option>`;
    })
    .join("");
  selectEl.innerHTML = options || '<option value="" disabled selected>Sem portas</option>';
}

function fillNetworkSelect(selectEl, interfaceName) {
  if (!selectEl) return;
  const nets = ipsCache
    .filter((ip) => String(ip?.interface || "") === String(interfaceName || ""))
    .map((ip) => String(ip?.address || ""))
    .filter(Boolean);

  const unique = Array.from(new Set(nets));
  const options = unique
    .map((cidr, idx) => {
      const sel = idx === 0 ? "selected" : "";
      return `<option value="${escapeHtml(cidr)}" ${sel}>${escapeHtml(cidr)}</option>`;
    })
    .join("");

  if (!options) {
    selectEl.innerHTML = '<option value="" disabled selected>Nenhum IP configurado</option>';
  } else {
    selectEl.innerHTML = options;
  }
}

function syncWizardDependentSelects() {
  const step2 = document.getElementById("wizardStep2");
  const step4 = document.getElementById("wizardStep4");
  if (!step2 || !step4) return;

  const interfaceName = step2.interface?.value || wizard.interfaceName;
  const itf = interfacesCache.find((x) => x.name === interfaceName);
  const port = itf?.listenPort ? String(itf.listenPort) : "";
  fillPortSelect(step4.port, port);
  fillNetworkSelect(step4.network, interfaceName);
}

async function openWizardCreate() {
  wizard.mode = "create";
  wizard.oldName = "";
  wizard.interfaceName = "";

  document.getElementById("wizardTitle").textContent = "Nova interface";

  const s1 = document.getElementById("wizardStep1");
  s1.mode.value = "create";
  s1.old_name.value = "";
  s1.name.value = "";
  s1.listen_port.value = "";

  await loadInterfaces();
  await loadIps();

  const s2 = document.getElementById("wizardStep2");
  fillInterfaceSelect(s2.interface, "");
  syncWizardDependentSelects();
  setWizardStep(1);
  bootstrap.Modal.getOrCreateInstance(wizardModalEl()).show();
}

async function openWizardEdit(name) {
  const itf = interfacesCache.find((x) => x.name === name);
  if (!itf) return;

  wizard.mode = "edit";
  wizard.oldName = itf.name;
  wizard.interfaceName = itf.name;

  document.getElementById("wizardTitle").textContent = `Editar interface: ${itf.name}`;

  const s1 = document.getElementById("wizardStep1");
  s1.mode.value = "edit";
  s1.old_name.value = itf.name;
  s1.name.value = itf.name;
  s1.listen_port.value = itf.listenPort || "";

  await loadInterfaces();
  await loadIps();

  const s2 = document.getElementById("wizardStep2");
  fillInterfaceSelect(s2.interface, itf.name);
  syncWizardDependentSelects();
  setWizardStep(1);
  bootstrap.Modal.getOrCreateInstance(wizardModalEl()).show();
}

async function runStep1() {
  const s1 = document.getElementById("wizardStep1");
  const mode = s1.mode.value;
  const name = s1.name.value.trim();
  const listenPort = Number(s1.listen_port.value);

  if (!name) {
    toast("Informe o nome da interface", "warning");
    return false;
  }
  if (!Number.isFinite(listenPort) || listenPort < 1 || listenPort > 65535) {
    toast("Porta de escuta inválida", "warning");
    return false;
  }

  if (mode === "create") {
    const res = await apiFetch("/interfaces", { method: "POST", json: { name, listen_port: listenPort } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      toast(data?.error || "Falha ao criar interface", "danger");
      return false;
    }
    toast("Interface criada", "success");
  } else {
    const oldName = s1.old_name.value;
    const res = await apiFetch(`/interfaces/${encodeURIComponent(oldName)}`,
      { method: "PUT", json: { name, listen_port: listenPort } }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      toast(data?.error || "Falha ao salvar interface", "danger");
      return false;
    }
    toast("Interface atualizada", "success");
  }

  wizard.interfaceName = name;
  wizard.oldName = name;
  await loadInterfaces();

  const s2 = document.getElementById("wizardStep2");
  fillInterfaceSelect(s2.interface, name);
  syncWizardDependentSelects();
  return true;
}

async function runStep2() {
  const s2 = document.getElementById("wizardStep2");
  const ip = s2.ip.value.trim();
  const mask = Number(s2.mask.value);
  const iface = s2.interface.value;
  const comment = s2.comment.value.trim();

  if (!ip) {
    toast("Informe o IP", "warning");
    return false;
  }
  if (!Number.isFinite(mask) || mask < 0 || mask > 32) {
    toast("Máscara inválida", "warning");
    return false;
  }
  if (!iface) {
    toast("Selecione a interface", "warning");
    return false;
  }

  const address = `${ip}/${mask}`;
  const res = await apiFetch("/ips", {
    method: "POST",
    json: { address, interface: iface, comment },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    toast(data?.error || "Falha ao configurar IP", "danger");
    return false;
  }

  toast("IP configurado", "success");
  wizard.interfaceName = iface;
  await loadIps();
  syncWizardDependentSelects();
  return true;
}

async function runStep3() {
  const s3 = document.getElementById("wizardStep3");
  const srcNet = s3.src_net.value.trim();
  const mask = Number(s3.mask.value);
  if (!srcNet) {
    toast("Informe a rede de origem", "warning");
    return false;
  }
  if (!Number.isFinite(mask) || mask < 0 || mask > 32) {
    toast("Máscara inválida", "warning");
    return false;
  }

  const src_network = `${srcNet}/${mask}`;
  const res = await apiFetch("/nat/wireguard", { method: "POST", json: { src_network } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.status === "error") {
    toast(data?.message || "Falha ao configurar NAT", "danger");
    return false;
  }

  toast("NAT configurado", "success");
  return true;
}

async function runStep4() {
  const s4 = document.getElementById("wizardStep4");
  const port = s4.port.value;
  const network = s4.network.value;
  if (!port) {
    toast("Selecione a porta", "warning");
    return false;
  }
  if (!network) {
    toast("Selecione a rede WireGuard", "warning");
    return false;
  }

  const res = await apiFetch("/firewall/wireguard", { method: "POST", json: { port, network } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.status === "error") {
    toast(data?.message || "Falha ao configurar firewall", "danger");
    return false;
  }

  toast("Firewall configurado", "success");
  return true;
}

async function wizardNext() {
  const btn = document.getElementById("btnWizardNext");
  if (btn) btn.disabled = true;
  try {
    if (wizard.step === 1) {
      const ok = await runStep1();
      if (ok) setWizardStep(2);
      return;
    }
    if (wizard.step === 2) {
      const ok = await runStep2();
      if (ok) setWizardStep(3);
      return;
    }
    if (wizard.step === 3) {
      const ok = await runStep3();
      if (ok) {
        await loadIps();
        syncWizardDependentSelects();
        setWizardStep(4);
      }
      return;
    }
    if (wizard.step === 4) {
      const ok = await runStep4();
      if (ok) {
        bootstrap.Modal.getOrCreateInstance(wizardModalEl()).hide();
        await loadInterfaces();
      }
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

function wizardBack() {
  if (wizard.step > 1) setWizardStep(wizard.step - 1);
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
  await loadIps();

  document.getElementById("btnReload")?.addEventListener("click", loadInterfaces);

  document.getElementById("btnNewWizard")?.addEventListener("click", openWizardCreate);
  document.getElementById("btnWizardNext")?.addEventListener("click", wizardNext);
  document.getElementById("btnWizardBack")?.addEventListener("click", wizardBack);

  document.getElementById("wizardStep2")?.interface?.addEventListener("change", async () => {
    await loadIps();
    syncWizardDependentSelects();
  });

  document.getElementById("tblInterfaces")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const action = btn.dataset.action;
    const name = btn.dataset.name;
    if (!action || !name) return;

    if (action === "edit") await openWizardEdit(name);
    if (action === "enable") await toggleInterface(name, "enable");
    if (action === "disable") await toggleInterface(name, "disable");
    if (action === "delete") await deleteInterface(name);
    if (action === "stats") await showStats(name);
  });
});
