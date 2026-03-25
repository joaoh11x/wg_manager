import { apiFetch, formatBytes, formatIso, requireAuth, toast } from "../app.js";

let chart;

function parseNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function isActiveHandshake(value) {
  if (!value) return false;
  const s = String(value).toLowerCase();
  return s !== "never" && s !== "0";
}

async function loadInterfaces() {
  const sel = document.getElementById("selInterface");
  if (!sel) return;

  sel.innerHTML = `<option value="">Todas as interfaces</option>`;

  const res = await apiFetch("/interfaces", { method: "GET" });
  if (res.status === 403) {
    toast("Acesso negado: precisa ser admin", "warning");
    return;
  }
  const data = await res.json().catch(() => []);
  if (!Array.isArray(data)) return;

  for (const itf of data) {
    const name = itf?.name || itf?.["name"];
    if (!name) continue;
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  }
}

function updateChart(peers) {
  const ctx = document.getElementById("chartTraffic");
  if (!ctx) return;

  const sorted = [...peers]
    .map((p) => ({
      name: p.name,
      total: parseNumber(p.rx) + parseNumber(p.tx),
      rx: parseNumber(p.rx),
      tx: parseNumber(p.tx),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);

  const labels = sorted.map((p) => p.name);
  const rx = sorted.map((p) => p.rx);
  const tx = sorted.map((p) => p.tx);

  if (!chart) {
    chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "RX", data: rx },
          { label: "TX", data: tx },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${formatBytes(item.raw)}`,
            },
          },
        },
        scales: {
          y: {
            ticks: {
              callback: (v) => formatBytes(v),
            },
          },
        },
      },
    });
  } else {
    chart.data.labels = labels;
    chart.data.datasets[0].data = rx;
    chart.data.datasets[1].data = tx;
    chart.update();
  }

  const hint = document.getElementById("chartHint");
  if (hint) hint.textContent = sorted.length ? `Top ${sorted.length}` : "Sem dados";
}

function updateTable(peers) {
  const tbody = document.getElementById("tblPeers");
  if (!tbody) return;

  const top = [...peers]
    .map((p) => ({
      name: p.name,
      rx: parseNumber(p.rx),
      tx: parseNumber(p.tx),
    }))
    .sort((a, b) => b.rx + b.tx - (a.rx + a.tx))
    .slice(0, 12);

  tbody.innerHTML = top
    .map(
      (p) => `
      <tr>
        <td class="text-truncate" style="max-width: 220px;">${p.name}</td>
        <td class="text-end"><span class="wg-badge">${formatBytes(p.rx)}</span></td>
        <td class="text-end"><span class="wg-badge">${formatBytes(p.tx)}</span></td>
      </tr>
    `
    )
    .join("");
}

async function loadStats() {
  const sel = document.getElementById("selInterface");
  const iface = sel?.value || "";

  const url = iface ? `/wireguard/peers/stats?interface=${encodeURIComponent(iface)}` : "/wireguard/peers/stats";
  const res = await apiFetch(url, { method: "GET" });

  if (res.status === 403) {
    toast("Acesso negado: dashboard requer admin", "warning");
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.success) {
    toast(data?.error || "Falha ao carregar estatísticas", "danger");
    return;
  }

  const peers = Array.isArray(data.stats) ? data.stats : [];
  const rxTotal = peers.reduce((acc, p) => acc + parseNumber(p.rx), 0);
  const txTotal = peers.reduce((acc, p) => acc + parseNumber(p.tx), 0);
  const active = peers.filter((p) => isActiveHandshake(p.last_handshake)).length;

  const kpiPeers = document.getElementById("kpiPeers");
  const kpiActive = document.getElementById("kpiActive");
  const kpiRx = document.getElementById("kpiRx");
  const kpiTx = document.getElementById("kpiTx");
  if (kpiPeers) kpiPeers.textContent = String(peers.length);
  if (kpiActive) kpiActive.textContent = String(active);
  if (kpiRx) kpiRx.textContent = formatBytes(rxTotal);
  if (kpiTx) kpiTx.textContent = formatBytes(txTotal);

  const lastUpdate = document.getElementById("lastUpdate");
  if (lastUpdate) lastUpdate.textContent = `Atualizado em ${formatIso(data.timestamp)}`;

  updateChart(peers);
  updateTable(peers);
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await loadInterfaces();
  await loadStats();

  document.getElementById("btnRefresh")?.addEventListener("click", loadStats);
  document.getElementById("selInterface")?.addEventListener("change", loadStats);
});
