const API_BASE = window.location.origin;

/* ── UTILITIES ─────────────────────────────────────────── */
function formatTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-MX", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      day: "2-digit", month: "2-digit",
    });
  } catch { return iso; }
}

function statusLabel(s) {
  return { pending: "Pendiente", confirmed_real: "Confirmada", false_alarm: "Falso" }[s] || s;
}

function threatPill(type) {
  const t = (type || "").toLowerCase();
  const cls = t === "violence" ? "pill-violence"
            : t === "fight"    ? "pill-fight"
            : t === "person"   ? "pill-person"
            : "pill-default";
  return `<span class="threat-type-pill ${cls}">${(type || "?").toUpperCase()}</span>`;
}

/* ── SERVER STATUS ─────────────────────────────────────── */
function setServerStatus(online) {
  const el = document.getElementById("server-status");
  if (!el) return;
  if (online) {
    el.textContent = "● SERVIDOR EN LÍNEA";
    el.className = "status-chip online";
  } else {
    el.textContent = "● SERVIDOR OFFLINE";
    el.className = "status-chip offline";
  }
}

/* ── LIVE CLOCK ────────────────────────────────────────── */
function updateClock() {
  const el = document.getElementById("live-clock");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString("es-MX", { hour12: false });

  const ts = now.toLocaleTimeString("es-MX", { hour12: false });
  document.querySelectorAll(".cam-ts-1, .cam-ts-3, .cam-ts-4").forEach(e => {
    e.textContent = ts;
  });
}

setInterval(updateClock, 1000);
updateClock();

/* ── FAKE RESOURCE BARS ────────────────────────────────── */
const RESOURCES = [
  { bar: "bar-cpu",  val: "val-cpu",  base: 32, range: 18, color: "bar-cyan" },
  { bar: "bar-ram",  val: "val-ram",  base: 57, range: 8,  color: "bar-cyan" },
  { bar: "bar-gpu",  val: "val-gpu",  base: 68, range: 20, color: "bar-green" },
  { bar: "bar-disk", val: "val-disk", base: 22, range: 4,  color: "bar-dim" },
];

function animateResources() {
  RESOURCES.forEach(r => {
    const v = Math.min(99, Math.max(5, Math.round(r.base + (Math.random() - 0.5) * r.range)));
    const bar = document.getElementById(r.bar);
    const val = document.getElementById(r.val);
    if (bar) {
      bar.style.width = v + "%";
      bar.className = "resource-bar " + (v > 90 ? "bar-red" : r.color);
    }
    if (val) val.textContent = v + "%";
  });
}

setInterval(animateResources, 2500);
animateResources();

/* ── SYSTEM LOG ────────────────────────────────────────── */
const LOG_POOL = [
  ["log-info", "[INFO] Frame analizado en 17ms"],
  ["log-ok",   "[OK] Inferencia YOLO completada"],
  ["log-info", "[INFO] Umbral de confianza: 85%"],
  ["log-info", "[INFO] MediaPipe Pose: activo"],
  ["log-info", "[INFO] Analizando CAM-03"],
  ["log-ok",   "[OK] Heartbeat del modelo OK"],
  ["log-info", "[INFO] Buffer de frames: 2/10"],
  ["log-ok",   "[OK] Base de datos respondiendo"],
  ["log-info", "[INFO] GPU temp: 61°C — normal"],
  ["log-info", "[INFO] Zona Centro — sin actividad"],
  ["log-info", "[INFO] Zona Sur — monitoreando"],
  ["log-ok",   "[OK] NMS procesado en <1ms"],
];

function addLogEntry(cls, msg) {
  const log = document.getElementById("system-log");
  if (!log) return;
  const div = document.createElement("div");
  div.className = "log-line " + (cls || "log-info");
  div.textContent = msg || LOG_POOL[Math.floor(Math.random() * LOG_POOL.length)][1];
  if (!cls) {
    const pick = LOG_POOL[Math.floor(Math.random() * LOG_POOL.length)];
    div.className = "log-line " + pick[0];
    div.textContent = pick[1];
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  while (log.children.length > 15) log.removeChild(log.firstChild);
}

setInterval(addLogEntry, 3500);

/* ── FETCH METRICS ─────────────────────────────────────── */
async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics`);
    if (!res.ok) return;
    const m = await res.json();
    const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v ?? "—"; };
    set("metric-fps", m.fps);
    set("metric-latency", m.avg_latency_ms);
    set("metric-false", m.false_positives);
    set("metric-total", m.alerts_today);
  } catch { /* silent */ }
}

/* ── FETCH ALERTS ──────────────────────────────────────── */
async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts?limit=50`);
    if (!res.ok) throw new Error("alerts failed");
    setServerStatus(true);
    const alerts = await res.json();

    renderAlertsTable(alerts);
    updateThreatFeed(alerts);
    updateThreatChart(alerts);

    const badge = document.getElementById("alert-count-badge");
    if (badge) badge.textContent = alerts.length + " alertas";
  } catch {
    setServerStatus(false);
  }
}

/* ── ALERTS TABLE ──────────────────────────────────────── */
function renderAlertsTable(alerts) {
  const tbody = document.getElementById("alerts-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!alerts.length) {
    const tr = document.createElement("tr");
    tr.className = "empty-row";
    tr.innerHTML = '<td colspan="6">Sin alertas en las últimas 24h</td>';
    tbody.appendChild(tr);
    return;
  }

  alerts.forEach(alert => {
    const tr = document.createElement("tr");
    tr.id = `alert-${alert.id}`;
    tr.className = `status-${alert.status}`;
    const conf = (alert.confidence * 100).toFixed(0);
    tr.innerHTML = `
      <td>${formatTime(alert.timestamp)}</td>
      <td>${threatPill(alert.threat_type)}</td>
      <td>
        <div class="conf-bar-wrap">
          <div class="conf-mini"><div class="conf-mini-fill" style="width:${conf}%"></div></div>
          <span>${conf}%</span>
        </div>
      </td>
      <td>${alert.camera_name || "—"}</td>
      <td>${statusLabel(alert.status)}</td>
      <td>
        <button class="btn-confirm" onclick="confirmAlert('${alert.id}','confirmed_real')">Confirmar</button>
        <button class="btn-false" onclick="confirmAlert('${alert.id}','false_alarm')">Falso</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/* ── THREAT FEED ───────────────────────────────────────── */
function updateThreatFeed(alerts) {
  const feed = document.getElementById("threat-feed");
  if (!feed) return;

  const recent = alerts.slice(0, 6);
  if (!recent.length) {
    feed.innerHTML = '<div class="threat-empty">Sin amenazas activas</div>';
    return;
  }

  feed.innerHTML = recent.map(a => {
    const conf = (a.confidence * 100).toFixed(0);
    return `
      <div class="threat-item threat-${a.status}">
        <div class="threat-item-top">
          <span class="threat-item-type">${(a.threat_type || "?").toUpperCase()}</span>
          <span class="threat-item-conf">${conf}%</span>
        </div>
        <div class="threat-item-meta">
          <span>${a.camera_name || "Cámara"}</span>
          <span>${formatTime(a.timestamp)}</span>
        </div>
        <div class="threat-conf-bar">
          <div class="threat-conf-fill" style="width:${conf}%"></div>
        </div>
      </div>`;
  }).join("");
}

/* ── THREAT CHART ──────────────────────────────────────── */
function updateThreatChart(alerts) {
  const counts = { violence: 0, fight: 0, person: 0, other: 0 };
  alerts.forEach(a => {
    const t = (a.threat_type || "").toLowerCase();
    if (t === "violence") counts.violence++;
    else if (t === "fight") counts.fight++;
    else if (t === "person") counts.person++;
    else counts.other++;
  });

  const total = Math.max(1, alerts.length);
  ["violence", "fight", "person", "other"].forEach(type => {
    const pct = Math.round((counts[type] / total) * 100);
    const bar = document.getElementById("tb-" + type);
    const val = document.getElementById("tv-" + type);
    if (bar) bar.style.width = pct + "%";
    if (val) val.textContent = counts[type];
  });
}

/* ── CONFIRM ALERT ─────────────────────────────────────── */
async function confirmAlert(alertId, status) {
  try {
    const res = await fetch(`${API_BASE}/api/alert/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_id: alertId, status }),
    });
    if (!res.ok) throw new Error("confirm failed");
    addLogEntry("log-ok", `[OK] Alerta ${alertId.slice(0,8)}... → ${status}`);
    await fetchAlerts();
    await fetchMetrics();
  } catch {
    alert("No se pudo actualizar la alerta");
  }
}

window.confirmAlert = confirmAlert;

/* ── CAMERA DETECTION ──────────────────────────────────── */
const SEND_W = 320;

function drawDetections(ctx, threats, frameW, frameH) {
  const cw = ctx.canvas.width;
  const ch = ctx.canvas.height;
  const sx = cw / frameW;
  const sy = ch / frameH;

  ctx.lineWidth = 2;
  ctx.font = "bold 11px 'JetBrains Mono', monospace";

  for (const t of threats) {
    const bbox = t.bbox;
    if (!bbox || bbox.length !== 4) continue;
    const [rx1, ry1, rx2, ry2] = bbox;
    if ([rx1, ry1, rx2, ry2].some(v => typeof v !== "number" || isNaN(v))) continue;

    const x1 = Math.max(0, Math.min(rx1 * sx, cw));
    const y1 = Math.max(0, Math.min(ry1 * sy, ch));
    const x2 = Math.max(0, Math.min(rx2 * sx, cw));
    const y2 = Math.max(0, Math.min(ry2 * sy, ch));
    if (x2 - x1 < 2 || y2 - y1 < 2) continue;

    const type = (t.type || "").toLowerCase();
    const color = type === "violence" ? "#ff3550"
                : type === "fight"    ? "#ffb700"
                : "#00d4ff";

    ctx.strokeStyle = color;
    ctx.fillStyle   = color;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Fondo semitransparente para la etiqueta
    const label = `${t.type?.toUpperCase()} ${(t.confidence * 100).toFixed(0)}%`;
    const textW = ctx.measureText(label).width + 8;
    const textY = y1 > 18 ? y1 - 14 : y2 + 2;
    ctx.fillStyle = color + "cc";
    ctx.fillRect(x1, textY, textW, 14);
    ctx.fillStyle = "#000";
    ctx.fillText(label, x1 + 4, textY + 11);
  }
}

async function detectCamFrame(videoId, canvasId, camName) {
  const video  = document.getElementById(videoId);
  const canvas = document.getElementById(canvasId);
  if (!video || !canvas || video.readyState < 2 || video.paused) return;

  // Ajusta resolución del canvas a su tamaño en pantalla
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0) return;
  canvas.width  = rect.width;
  canvas.height = rect.height;

  const frameH = Math.round((video.videoHeight / video.videoWidth) * SEND_W) || 240;
  const tmp = document.createElement("canvas");
  tmp.width  = SEND_W;
  tmp.height = frameH;
  tmp.getContext("2d").drawImage(video, 0, 0, SEND_W, frameH);

  tmp.toBlob(async (blob) => {
    if (!blob) return;
    const form = new FormData();
    form.append("frame", blob, "frame.jpg");
    form.append("camera_name", camName);
    try {
      const res = await fetch(`${API_BASE}/api/detect`, { method: "POST", body: form });
      if (!res.ok) return;
      const data = await res.json();
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (data.threats && data.threats.length > 0) {
        drawDetections(ctx, data.threats, SEND_W, frameH);
        addLogEntry("log-warn", `[DETECT] ${camName}: ${data.threats.map(t => t.type).join(", ")}`);
      }
    } catch { /* silent */ }
  }, "image/jpeg", 0.8);
}

const CAM_SOURCES = [
  { vid: "cam-video-1", cvs: "cam-canvas-1", name: "CAM 01 · Entrada Principal" },
  { vid: "cam-video-2", cvs: "cam-canvas-2", name: "CAM 02 · Parque Central"   },
  { vid: "cam-video-3", cvs: "cam-canvas-3", name: "CAM 03 · Av. Revolución"   },
];

function startCamDetection() {
  CAM_SOURCES.forEach((cam, i) => {
    // Escalonado: cada cámara empieza 600ms después para no saturar el servidor
    setTimeout(() => {
      setInterval(() => detectCamFrame(cam.vid, cam.cvs, cam.name), 1800);
    }, i * 600);
  });
}

/* ── INIT ──────────────────────────────────────────────── */
window.onload = () => {
  fetchAlerts();
  fetchMetrics();
  setInterval(fetchAlerts, 3000);
  setInterval(fetchMetrics, 5000);
  startCamDetection();
};
