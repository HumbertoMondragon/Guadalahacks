import os
import time
from typing import Any

import numpy as np
from ultralytics import YOLO

try:
    import mediapipe as mp  # type: ignore[import-untyped]
    from mediapipe.solutions import pose as pose_module  # type: ignore[import-untyped]
    _MEDIAPIPE_AVAILABLE = True
except ImportError:
    _MEDIAPIPE_AVAILABLE = False

from config import CLASSES

ID_TO_CLASS = {class_id: name for name, class_id in CLASSES.items()}

# MediaPipe Pose landmark indices (33-point body model)
_NOSE = 0
_SHOULDER_L, _SHOULDER_R = 11, 12
_WRIST_L, _WRIST_R = 15, 16
_HIP_L, _HIP_R = 23, 24
_ANKLE_L, _ANKLE_R = 27, 28


class HybridDetector:
    """
    Detector híbrido: YOLOv8 (objetos) + MediaPipe Pose (esqueletos).

    YOLOv8  → armas, vandalismo, aglomeraciones.
    Pose    → pelea (brazos levantados), persona caída (posición horizontal).
    Fusión  → si ambos modelos coinciden en el mismo tipo de amenaza,
              se aplica un boost de confianza del +10 pp.
    """

    def __init__(
        self,
        model_path: str,
        input_size: int = 640,
        conf_threshold: float = 0.85,
    ) -> None:
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.model_loaded = False
        self.model: YOLO | None = None

        self._pose = None
        if _MEDIAPIPE_AVAILABLE:
            self._pose = pose_module.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        resolved = self._resolve_model_path(model_path)
        try:
            if os.path.isfile(resolved):
                self.model = YOLO("../models/best.pt")
            else:
                self.model = YOLO("../models/best.pt")
            self.model_loaded = True
        except Exception as exc:
            self.model_loaded = False
            raise RuntimeError(
                f"No se pudo cargar el modelo desde '{model_path}' "
                f"ni el fallback yolov8n.pt: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> dict[str, Any]:
        """
        Ejecuta detección híbrida sobre un frame RGB.

        Retorna:
            detected          – bool
            threats           – lista de dicts {type, confidence, bbox, source}
            inference_time_ms – tiempo total de inferencia en ms
        """
        start = time.perf_counter()

        yolo_threats = self._run_yolo(frame) if self.model_loaded else []
        pose_threats = self._run_pose(frame) if self._pose is not None else []
        threats = self._merge_threats(yolo_threats, pose_threats)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "detected": len(threats) > 0,
            "threats": threats,
            "inference_time_ms": round(elapsed_ms, 2),
        }

    # ------------------------------------------------------------------
    # YOLOv8 branch — objetos y amenazas visuales
    # ------------------------------------------------------------------

    def _run_yolo(self, frame: np.ndarray) -> list[dict[str, Any]]:
        threats: list[dict[str, Any]] = []
        try:
            results = self.model.predict(  # type: ignore[union-attr]
                frame,
                imgsz=self.input_size,
                conf=self.conf_threshold,
                verbose=False,
            )
            for result in results:
                if result.boxes is None:
                    continue
                names = result.names or {}
                for box in result.boxes:
                    conf = float(box.conf[0])
                    if conf < self.conf_threshold:
                        continue
                    cls_id = int(box.cls[0])
                    threat_type = ID_TO_CLASS.get(
                        cls_id, names.get(cls_id, str(cls_id))
                    )
                    threats.append(
                        {
                            "type": threat_type,
                            "confidence": round(conf, 3),
                            "bbox": _format_bbox(box.xyxy[0].tolist()),
                            "source": "yolo",
                        }
                    )
        except Exception:
            pass
        print(f"DEBUG _run_yolo - {len(threats)} threats:")
        for t in threats:
            print(f"  type={t['type']} conf={t['confidence']} source={t['source']} bbox={t['bbox']}")
        return threats

    # ------------------------------------------------------------------
    # MediaPipe Pose branch — comportamientos y posturas
    # ------------------------------------------------------------------

    def _run_pose(self, frame: np.ndarray) -> list[dict[str, Any]]:
        threats: list[dict[str, Any]] = []
        try:
            result = self._pose.process(frame)  # type: ignore[union-attr]
            if result.pose_landmarks is None:
                return threats

            lm = result.pose_landmarks.landmark
            h, w = frame.shape[:2]
            bbox = _landmarks_bbox(lm, w, h)

            fight_conf = _estimate_fight_confidence(lm)
            if fight_conf >= 0.60:
                threats.append(
                    {
                        "type": "fight",
                        "confidence": round(fight_conf, 3),
                        "bbox": bbox,
                        "source": "pose",
                    }
                )

            fallen_conf = _estimate_fallen_confidence(lm)
            if fallen_conf >= 0.60:
                threats.append(
                    {
                        "type": "fallen",
                        "confidence": round(fallen_conf, 3),
                        "bbox": bbox,
                        "source": "pose",
                    }
                )
        except Exception:
            pass
        return threats

    # ------------------------------------------------------------------
    # Fusión de resultados
    # ------------------------------------------------------------------

    def _merge_threats(
        self,
        yolo: list[dict[str, Any]],
        pose: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Fusiona amenazas de ambas ramas.
        Cuando el mismo tipo aparece en las dos ramas se aplica un boost
        del +10 pp sobre la confianza mayor (cap 1.0) y la fuente pasa
        a ser 'hybrid'.
        Solo se devuelven amenazas con confianza >= conf_threshold.
        """
        combined: dict[str, dict[str, Any]] = {}

        for threat in yolo + pose:
            t = threat["type"]
            if t not in combined:
                combined[t] = dict(threat)
            else:
                new_conf = min(
                    1.0,
                    max(combined[t]["confidence"], threat["confidence"]) + 0.10,
                )
                combined[t]["confidence"] = round(new_conf, 3)
                combined[t]["source"] = "hybrid"

        merged = [t for t in combined.values() if t["confidence"] >= self.conf_threshold]
        print(f"DEBUG _merge_threats - {len(merged)} threats tras fusion:")
        for t in merged:
            print(f"  type={t['type']} conf={t['confidence']} source={t['source']} bbox={t.get('bbox')}")
        return merged

    # ------------------------------------------------------------------
    # Resolución de ruta del modelo
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model_path(model_path: str) -> str:
        if os.path.isfile(model_path):
            return model_path
        project_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        candidate = os.path.join(project_root, model_path)
        if os.path.isfile(candidate):
            return candidate
        return model_path


# Alias de compatibilidad para que main.py no necesite cambios
YOLOv8Detector = HybridDetector


# ------------------------------------------------------------------
# Helpers estáticos (funciones puras, no necesitan estado de clase)
# ------------------------------------------------------------------

def _format_bbox(coords: list[float]) -> list[float]:
    return [float(c) for c in coords[:4]]


def _landmarks_bbox(lm: Any, w: int, h: int) -> list[float]:
    xs = [l.x * w for l in lm]
    ys = [l.y * h for l in lm]
    return [min(xs), min(ys), max(xs), max(ys)]


def _estimate_fight_confidence(lm: Any) -> float:
    """
    Heurística de postura agresiva basada en posición de muñecas vs hombros.

    En coordenadas normalizadas de MediaPipe, y=0 es arriba, y=1 abajo.
    Una muñeca por encima de su hombro (y_muñeca < y_hombro) indica brazo
    levantado, señal clásica de golpe o defensa activa.
    """
    try:
        wl, wr = lm[_WRIST_L], lm[_WRIST_R]
        sl, sr = lm[_SHOULDER_L], lm[_SHOULDER_R]

        arm_l_raised = (sl.y - wl.y) > 0.10  # muñeca izquierda sobre hombro
        arm_r_raised = (sr.y - wr.y) > 0.10  # muñeca derecha sobre hombro

        if arm_l_raised and arm_r_raised:
            return 0.88
        if arm_l_raised or arm_r_raised:
            return 0.72
        return 0.0
    except (IndexError, AttributeError):
        return 0.0


def _estimate_fallen_confidence(lm: Any) -> float:
    """
    Heurística de persona caída.

    Si la nariz está al mismo nivel o más abajo que el promedio de las
    caderas, la persona está horizontal (posición de caída o víctima).
    """
    try:
        nose = lm[_NOSE]
        hip_y = (lm[_HIP_L].y + lm[_HIP_R].y) / 2

        diff = nose.y - hip_y  # positivo → nariz más abajo que caderas
        if diff >= 0.05:
            return 0.85
        if diff >= -0.05:
            return 0.70
        return 0.0
    except (IndexError, AttributeError):
        return 0.0
