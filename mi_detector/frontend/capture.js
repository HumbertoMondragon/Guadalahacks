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

function drawBoundingBoxes(ctx, threats, frameW, frameH) {
  const cw = ctx.canvas.width;
  const ch = ctx.canvas.height;
  const scaleX = cw / frameW;
  const scaleY = ch / frameH;

  ctx.lineWidth = 3;
  ctx.font = "bold 14px monospace";

  for (const threat of threats) {
    const bbox = threat.bbox;
    console.log("bbox raw:", bbox, "type:", threat.type, "conf:", threat.confidence);

    if (!bbox || bbox.length !== 4) {
      console.warn("bbox invalido:", bbox);
      continue;
    }

    const [rx1, ry1, rx2, ry2] = bbox;
    if ([rx1, ry1, rx2, ry2].some((v) => typeof v !== "number" || isNaN(v))) {
      console.warn("bbox contiene NaN:", bbox);
      continue;
    }

    const x1 = Math.max(0, Math.min(rx1 * scaleX, cw));
    const y1 = Math.max(0, Math.min(ry1 * scaleY, ch));
    const x2 = Math.max(0, Math.min(rx2 * scaleX, cw));
    const y2 = Math.max(0, Math.min(ry2 * scaleY, ch));
    console.log("bbox escalado:", x1, y1, x2, y2, "canvas:", cw, ch);

    if (x2 - x1 < 1 || y2 - y1 < 1) {
      console.warn("bbox degenerado tras escalar:", x1, y1, x2, y2);
      continue;
    }

    ctx.strokeStyle = "#ff3333";
    ctx.fillStyle = "#ff3333";
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    const label = `${threat.type} ${(threat.confidence * 100).toFixed(0)}%`;
    const textY = y1 > 20 ? y1 - 5 : y1 + 16;
    ctx.fillText(label, x1 + 2, textY);
  }
}

async function captureLoop() {
  if (!capturing || !video || !canvas) return;
  if (video.readyState < 2) return;

  const frameW = 320;
  const frameH = Math.round((video.videoHeight / video.videoWidth) * frameW) || 240;

  // Canvas es overlay transparente encima del video — solo dibuja bboxes
  canvas.width = video.videoWidth || frameW;
  canvas.height = video.videoHeight || frameH;
  const ctx = canvas.getContext("2d");

  const sendCanvas = document.createElement("canvas");
  sendCanvas.width = frameW;
  sendCanvas.height = frameH;
  sendCanvas.getContext("2d").drawImage(video, 0, 0, frameW, frameH);

  sendCanvas.toBlob(async (blob) => {
    if (!blob || !capturing) return;
    try {
      const data = await sendFrame(blob);
      setStatus("En vivo — analizando", true);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (data.threats && data.threats.length > 0) {
        drawBoundingBoxes(ctx, data.threats, frameW, frameH);
      }

      if (data.detected && data.alert_sent) {
        showThreat(data.threat_type, data.confidence);
      }
    } catch (err) {
      console.error("sendFrame:", err);
      setStatus("Desconectado — sin servidor", false);
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
