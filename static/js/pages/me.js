import { apiFetch, decodeJwt, formatBytes, formatIso, getToken, requireAuth, toast } from "../app.js";

async function copyToClipboard(text) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }

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

function setBusy(isBusy) {
  const btn = document.getElementById("btnRefresh");
  if (btn) {
    btn.disabled = isBusy;
    btn.textContent = isBusy ? "Atualizando…" : "Atualizar";
  }
}

async function loadConfig() {
  const txt = document.getElementById("txtConfig");
  const btnDownload = document.getElementById("btnDownload");
  if (!txt) return;

  txt.value = "Carregando…";

  const res = await apiFetch("/me/config");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error || "Falha ao carregar config");

  txt.value = data?.config || "";
  if (btnDownload) btnDownload.href = "/me/config/download";
}

async function loadQr() {
  const img = document.getElementById("imgQr");
  const hint = document.getElementById("qrHint");
  if (!img) return;

  const res = await apiFetch("/me/qrcode");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error || "Falha ao carregar QRCode");

  img.src = data?.qr_code || "";
  if (hint) hint.textContent = data?.peer_name ? `Peer: ${data.peer_name}` : "—";
}

async function loadTraffic() {
  const rxEl = document.getElementById("rx");
  const txEl = document.getElementById("tx");
  const hsEl = document.getElementById("handshake");
  const hint = document.getElementById("trafficHint");

  const res = await apiFetch("/me/traffic");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error || "Falha ao carregar consumo");

  if (rxEl) rxEl.textContent = formatBytes(data?.rx);
  if (txEl) txEl.textContent = formatBytes(data?.tx);
  if (hsEl) hsEl.textContent = formatIso(data?.last_handshake);
  if (hint) hint.textContent = data?.peer_name ? `Peer: ${data.peer_name}` : "—";
}

async function refreshAll() {
  setBusy(true);
  try {
    await Promise.all([loadConfig(), loadQr(), loadTraffic()]);
    toast("Atualizado", "success");
  } finally {
    setBusy(false);
  }
}

function initCopy() {
  const btn = document.getElementById("btnCopy");
  const txt = document.getElementById("txtConfig");
  if (!btn || !txt) return;

  btn.addEventListener("click", async () => {
    const value = txt.value || "";
    if (!value.trim()) {
      toast("Nada para copiar", "warning");
      return;
    }
    try {
      const copied = await copyToClipboard(value);
      toast(copied ? "Config copiada" : "Não foi possível copiar", copied ? "success" : "warning");
    } catch {
      // fallback simples
      txt.focus();
      txt.select();
      const ok = document.execCommand("copy");
      toast(ok ? "Config copiada" : "Falha ao copiar", ok ? "success" : "danger");
      txt.setSelectionRange(0, 0);
    }
  });
}

function ensurePeerRole() {
  const token = getToken();
  const payload = token ? decodeJwt(token) : null;
  const role = payload?.role || "peer";
  if (role !== "peer") {
    // Admin não deve ficar nesta tela
    location.replace("/ui/dashboard");
    return false;
  }
  return true;
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;
  if (!ensurePeerRole()) return;

  initCopy();

  const btn = document.getElementById("btnRefresh");
  if (btn) btn.addEventListener("click", () => refreshAll().catch((e) => toast(String(e?.message || e), "danger")));

  refreshAll().catch((e) => toast(String(e?.message || e), "danger"));
});
