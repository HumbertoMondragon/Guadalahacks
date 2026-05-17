const API_BASE = window.location.origin;
const CAPTURE_INTERVAL_MS = 200;

let stream = null;
let captureTimer = null;
let capturing = true;

const video = document.getElementById("video-element");
const canvas = document.getElementById("canvas");
const statusText = document.getElementById("status-text");
const overlay = document.getElementById("threat-overlay");
const threatLabel = document.getElementById("threat-label");
const alertSound = document.getElementById("alert-sound");

function setStatus(text, ok) {
  if (!statusText) return;
  statusText.textContent = text;
  statusText.className = ok ? "ok" : "err";
}

function showThreat(threatType, confidence) {
  if (!overlay || !threatLabel) return;
  overlay.style.display = "block";
  threatLabel.textContent = `${String(threatType).toUpperCase()} — ${(confidence * 100).toFixed(0)}%`;
  try {
    alertSound?.play();
  } catch {
    /* autoplay puede estar bloqueado */
  }
  setTimeout(() => {
    overlay.style.display = "none";
  }, 2000);
}

async function sendFrame(blob) {
  const form = new FormData();
  form.append("frame", blob, "frame.jpg");
  form.append("camera_name", "Móvil");

  const res = await fetch(`${API_BASE}/api/detect`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function captureLoop() {
  if (!capturing || !video || !canvas) return;
  if (video.readyState < 2) return;

  const w = 320;
  const h = Math.round((video.videoHeight / video.videoWidth) * w) || 240;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, w, h);

  canvas.toBlob(async (blob) => {
    if (!blob || !capturing) return;
    try {
      const data = await sendFrame(blob);
      setStatus("En vivo — enviando frames", true);
      if (data.detected && data.alert_sent) {
        showThreat(data.threat_type, data.confidence);
      }
    } catch (err) {
      console.error("sendFrame:", err);
      setStatus("Desconectado — no se alcanza el servidor", false);
    }
  }, "image/jpeg", 0.75);
}

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    setStatus("En vivo", true);
    captureTimer = setInterval(captureLoop, CAPTURE_INTERVAL_MS);
  } catch (err) {
    console.error("camera:", err);
    setStatus("Permiso de cámara denegado o no disponible", false);
  }
}

function stopCapture() {
  capturing = false;
  if (captureTimer) clearInterval(captureTimer);
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  setStatus("Captura detenida", false);
}

document.getElementById("btn-stop")?.addEventListener("click", stopCapture);
document.getElementById("btn-reload")?.addEventListener("click", () => window.location.reload());

startCamera();
