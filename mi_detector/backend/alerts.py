import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

MODERATE_CONFIDENCE = 0.60
HIGH_CONFIDENCE = 0.85
ESCALATION_WINDOW_SECONDS = 30
MAX_RECENT_DETECTIONS = 10


class AlertLogic:
    """Lógica stateful para decidir cuándo enviar alertas de amenaza."""

    def __init__(self, debounce_ms: int = 5000, escalation_threshold: int = 5) -> None:
        self.debounce_ms = debounce_ms
        self.escalation_threshold = escalation_threshold
        self.recent_detections: list[dict[str, Any]] = []
        self.escalation_active = False
        self._last_alert_at: dict[tuple[str, str], datetime] = {}

    def should_alert(self, threat_type: str, confidence: float, camera_name: str) -> bool:
        """
        Decide si se debe enviar alerta según confianza, debounce y escalación.

        Retorna True solo si confianza >= 85% y no hay debounce activo.
        """
        now = datetime.utcnow()
        self._record_detection(
            {
                "timestamp": now.isoformat() + "Z",
                "threat_type": threat_type,
                "camera_name": camera_name,
                "confidence": confidence,
            }
        )

        if confidence < MODERATE_CONFIDENCE:
            return False

        if confidence < HIGH_CONFIDENCE:
            logger.info(
                "[ALERT] Riesgo moderado (pendiente): %s %.0f%% @ %s",
                threat_type,
                confidence * 100,
                camera_name,
            )
            return False

        key = (camera_name, threat_type)
        last_alert = self._last_alert_at.get(key)
        if last_alert is not None:
            elapsed_ms = (now - last_alert).total_seconds() * 1000
            if elapsed_ms < self.debounce_ms:
                return False

        recent_count = self._count_high_confidence_recent(camera_name, now)
        if recent_count >= self.escalation_threshold:
            self.escalation_active = True
            logger.warning(
                "[ALERT] ESCALATION: %d+ detecciones en %ds @ %s",
                self.escalation_threshold,
                ESCALATION_WINDOW_SECONDS,
                camera_name,
            )
        else:
            self.escalation_active = False

        self._last_alert_at[key] = now
        return True

    def get_alert_message(self, threat_type: str, confidence: float) -> str:
        """Genera mensaje de alerta para WhatsApp o log simulado."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        prefix = "ALERTA URGENTE" if self.escalation_active else "ALERTA"
        return (
            f"{prefix}: {threat_type.upper()} detectada\n"
            f"Confianza: {confidence * 100:.0f}%\n"
            f"Hora: {timestamp}"
        )

    def _record_detection(self, detection: dict[str, Any]) -> None:
        """Guarda las últimas detecciones en memoria (máximo 10)."""
        self.recent_detections.append(detection)
        if len(self.recent_detections) > MAX_RECENT_DETECTIONS:
            self.recent_detections = self.recent_detections[-MAX_RECENT_DETECTIONS:]

    def _count_high_confidence_recent(self, camera_name: str, now: datetime) -> int:
        """Cuenta detecciones de alta confianza en la ventana de escalación."""
        cutoff = now - timedelta(seconds=ESCALATION_WINDOW_SECONDS)
        count = 0
        for detection in self.recent_detections:
            if detection.get("camera_name") != camera_name:
                continue
            if detection.get("confidence", 0) < HIGH_CONFIDENCE:
                continue
            ts = self._parse_timestamp(detection.get("timestamp", ""))
            if ts is not None and ts >= cutoff:
                count += 1
        return count

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.rstrip("Z"))
        except ValueError:
            return None
