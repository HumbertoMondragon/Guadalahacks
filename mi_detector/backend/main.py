import logging
import os
import time
from typing import Any

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alerts import AlertLogic
from config import (
    ALERT_DEBOUNCE_MS,
    ALERT_RETENTION_HOURS,
    CONFIDENCE_THRESHOLD,
    DB_PATH,
    DEBUG,
    ESCALATION_THRESHOLD,
    HOST,
    MODEL_INPUT_SIZE,
    MODEL_PATH,
    PORT,
)
from database import DatabaseManager
from detector import YOLOv8Detector

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
LOG_DIR = os.path.join(PROJECT_ROOT, "data", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger(__name__)

_START_TIME = time.time()

_metrics: dict[str, float] = {
    "frame_count": 0,
    "window_start": time.time(),
    "latency_sum_ms": 0.0,
    "latency_samples": 0.0,
}

app = FastAPI(title="Detector de Violencia Comunitaria")

db = DatabaseManager(os.path.join(PROJECT_ROOT, DB_PATH))
db.init_db()
model = YOLOv8Detector(
    os.path.join(PROJECT_ROOT, MODEL_PATH),
    MODEL_INPUT_SIZE,
    CONFIDENCE_THRESHOLD,
)
alert_logic = AlertLogic(ALERT_DEBOUNCE_MS, ESCALATION_THRESHOLD)

logger.info("Servidor iniciado (model_loaded=%s, log=%s)", model.model_loaded, LOG_FILE)


class ConfirmRequest(BaseModel):
    alert_id: str
    status: str


def _record_inference(latency_ms: float) -> None:
    _metrics["frame_count"] += 1
    _metrics["latency_sum_ms"] += latency_ms
    _metrics["latency_samples"] += 1


def _current_fps() -> float:
    elapsed = time.time() - _metrics["window_start"]
    if elapsed <= 0:
        return 0.0
    if elapsed > 60:
        _metrics["frame_count"] = 1
        _metrics["window_start"] = time.time()
        elapsed = 1
    return round(_metrics["frame_count"] / elapsed, 1)


def _decode_frame(contents: bytes) -> np.ndarray | None:
    """Decodifica JPEG a array RGB."""
    arr = np.frombuffer(contents, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


@app.post("/api/detect")
async def detect(
    frame: UploadFile = File(...),
    camera_name: str = Form("Cámara 1"),
) -> dict[str, Any]:
    """Recibe un frame JPEG, ejecuta detección y opcionalmente crea alerta."""
    try:
        contents = await frame.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Invalid image")

        rgb_frame = _decode_frame(contents)
        if rgb_frame is None:
            logger.warning("[DETECT] Frame corrupto o formato inválido")
            raise HTTPException(status_code=400, detail="Invalid image")

        logger.info("[DETECT] Frame recibido desde %s. Procesando...", camera_name)
        result = model.detect(rgb_frame)
        _record_inference(result.get("inference_time_ms", 0))

        if not result["detected"] or not result["threats"]:
            logger.info("[DETECT] Sin amenazas por encima del umbral")
            return {"detected": False}

        best = max(result["threats"], key=lambda t: t["confidence"])
        threat_type = best["type"]
        confidence = best["confidence"]
        logger.info(
            "[DETECT] Threat detected: %s (%.2f)",
            threat_type,
            confidence,
        )

        if not alert_logic.should_alert(threat_type, confidence, camera_name):
            logger.info("[DETECT] Sin alerta (debounce o confianza insuficiente)")
            return {
                "detected": True,
                "threat_type": threat_type,
                "confidence": confidence,
                "alert_sent": False,
            }

        alert_id = db.create_alert(threat_type, confidence, camera_name)
        message = alert_logic.get_alert_message(threat_type, confidence)
        logger.info(
            "[DETECT] Amenaza: %s (%.2f). Alerta %s. %s",
            threat_type,
            confidence,
            alert_id,
            message.replace("\n", " | "),
        )

        return {
            "detected": True,
            "threat_type": threat_type,
            "confidence": confidence,
            "alert_id": alert_id,
            "alert_sent": alert_id is not None,
            "escalation": alert_logic.escalation_active,
            "inference_time_ms": result["inference_time_ms"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[DETECT] Error: %s", exc)
        return {"detected": False, "error": "processing_failed"}


@app.get("/api/alerts")
async def get_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """Lista alertas de las últimas 24 horas."""
    try:
        alerts = db.get_recent_alerts(hours=ALERT_RETENTION_HOURS, limit=limit + offset)
        return alerts[offset : offset + limit]
    except Exception as exc:
        logger.exception("[ALERTS] Error: %s", exc)
        return []


@app.post("/api/alert/confirm")
async def confirm_alert(body: ConfirmRequest) -> dict[str, Any]:
    """Confirma o rechaza una alerta."""
    try:
        if body.status not in ("confirmed_real", "false_alarm"):
            raise HTTPException(status_code=400, detail="Invalid status")

        success = db.confirm_alert(body.alert_id, body.status)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        logger.info("[CONFIRM] Alerta %s → %s", body.alert_id, body.status)
        return {"success": True, "updated_at": time.time()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[CONFIRM] Error: %s", exc)
        return {"success": False}


@app.get("/api/metrics")
async def get_metrics() -> dict[str, Any]:
    """Métricas para el dashboard."""
    try:
        recent = db.get_recent_alerts(hours=8, limit=500)
        false_positives = sum(
            1 for a in recent if a.get("status") == "false_alarm"
        )
        today_alerts = db.get_recent_alerts(hours=24, limit=500)
        avg_latency = 0.0
        if _metrics["latency_samples"] > 0:
            avg_latency = round(
                _metrics["latency_sum_ms"] / _metrics["latency_samples"], 1
            )
        return {
            "fps": _current_fps(),
            "avg_latency_ms": avg_latency,
            "false_positives": false_positives,
            "alerts_today": len(today_alerts),
        }
    except Exception as exc:
        logger.exception("[METRICS] Error: %s", exc)
        return {
            "fps": 0,
            "avg_latency_ms": 0,
            "false_positives": 0,
            "alerts_today": 0,
        }


@app.get("/")
@app.get("/dashboard")
async def dashboard_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/capture")
async def capture_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "capture.html"))


@app.get("/health")
async def health() -> dict[str, Any]:
    """Estado del servidor y del modelo."""
    return {
        "status": "ok",
        "model_loaded": model.model_loaded,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
