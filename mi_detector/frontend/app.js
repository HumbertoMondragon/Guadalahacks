const API_BASE = window.location.origin;

function formatTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-MX", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return iso;
  }
}

function statusLabel(status) {
  const labels = {
    pending: "Pendiente",
    confirmed_real: "Confirmada",
    false_alarm: "Falso",
  };
  return labels[status] || status;
}

function setServerStatus(online) {
  const el = document.getElementById("server-status");
  if (!el) return;
  if (online) {
    el.textContent = "Servidor en línea";
    el.className = "status-badge online";
  } else {
    el.textContent = "SERVIDOR OFFLINE";
    el.className = "status-badge offline";
  }
}

async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts?limit=50`);
    if (!res.ok) throw new Error("alerts failed");
    setServerStatus(true);
    const alerts = await res.json();
    const tbody = document.getElementById("alerts-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (!alerts.length) {
      const tr = document.createElement("tr");
      tr.className = "empty-row";
      tr.innerHTML = '<td colspan="5">Sin alertas en las últimas 24h</td>';
      tbody.appendChild(tr);
      return;
    }

    alerts.forEach((alert) => {
      const tr = document.createElement("tr");
      tr.id = `alert-${alert.id}`;
      tr.className = `status-${alert.status}`;
      const conf = (alert.confidence * 100).toFixed(0);
      tr.innerHTML = `
        <td>${formatTime(alert.timestamp)}</td>
        <td>${alert.threat_type}</td>
        <td>${conf}%</td>
        <td>${statusLabel(alert.status)}</td>
        <td>
          <button type="button" onclick="confirmAlert('${alert.id}', 'confirmed_real')">Confirmar</button>
          <button type="button" class="btn-false" onclick="confirmAlert('${alert.id}', 'false_alarm')">Marcar falso</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("fetchAlerts:", err);
    setServerStatus(false);
  }
}

async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics`);
    if (!res.ok) return;
    const m = await res.json();
    const fps = document.getElementById("metric-fps");
    const latency = document.getElementById("metric-latency");
    const falses = document.getElementById("metric-false");
    const total = document.getElementById("metric-total");
    if (fps) fps.textContent = m.fps ?? "—";
    if (latency) latency.textContent = m.avg_latency_ms ?? "—";
    if (falses) falses.textContent = m.false_positives ?? "—";
    if (total) total.textContent = m.alerts_today ?? "—";
  } catch (err) {
    console.error("fetchMetrics:", err);
  }
}

async function confirmAlert(alertId, status) {
  try {
    const res = await fetch(`${API_BASE}/api/alert/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_id: alertId, status }),
    });
    if (!res.ok) throw new Error("confirm failed");
    await fetchAlerts();
    await fetchMetrics();
  } catch (err) {
    console.error("confirmAlert:", err);
    alert("No se pudo actualizar la alerta");
  }
}

window.confirmAlert = confirmAlert;

window.onload = () => {
  fetchAlerts();
  fetchMetrics();
  setInterval(fetchAlerts, 3000);
  setInterval(fetchMetrics, 5000);
};
