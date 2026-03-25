import { apiFetch, formatBytes, requireAuth, toast } from "../app.js";

let timer = null;
let polling = true;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setBar(id, percent) {
  const el = document.getElementById(id);
  if (!el) return;
  const p = Math.max(0, Math.min(100, Number(percent) || 0));
  el.style.width = `${p}%`;
  el.setAttribute("aria-valuenow", String(p));
}

async function refresh() {
  const res = await apiFetch("/system/resources", { method: "GET" });
  if (res.status === 403) {
    toast("Acesso negado: hardware requer admin", "warning");
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data?.error || "Falha ao carregar recursos", "danger");
    return;
  }

  const cpuLoad = Number(data.cpu_load ?? 0);
  const totalMem = Number(data.total_memory ?? 0);
  const freeMem = Number(data.free_memory ?? 0);
  const usedMem = Math.max(0, totalMem - freeMem);

  setText("cpuLoad", `${cpuLoad}%`);
  setText("cpuMeta", `${data.cpu_count || "—"} cores • ${data.cpu_frequency || "—"} MHz`);
  setBar("cpuBar", cpuLoad);

  const memPct = totalMem ? (usedMem / totalMem) * 100 : 0;
  setText("memUsed", `${formatBytes(usedMem)}`);
  setText("memMeta", `${formatBytes(totalMem)} total`);
  setBar("memBar", memPct);

  setText("board", data.board_name || "—");
  setText("version", data.version || "—");
  setText("uptime", data.uptime || "—");
  setText("arch", data.architecture_name || "—");

  setText("lastUpdate", `Atualizado em ${new Date().toLocaleString()}`);
}

function startPolling() {
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    if (polling) refresh();
  }, 2000);
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  await refresh();
  startPolling();

  document.getElementById("btnRefresh")?.addEventListener("click", refresh);
  document.getElementById("btnTogglePoll")?.addEventListener("click", () => {
    polling = !polling;
    document.getElementById("btnTogglePoll").textContent = polling ? "Pausar" : "Continuar";
  });
});
