#!/usr/bin/env python3
"""Simula una cámara enviando frames de un video al API /api/detect."""

import argparse
import os
import subprocess
import sys
import time

import cv2
import requests

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_VIDEO = os.path.join(PROJECT_ROOT, "data", "test_video.mp4")
DEFAULT_API = "http://localhost:8000/api/detect"
FRAME_INTERVAL_SEC = 1 / 30


def create_placeholder_video(path: str) -> None:
    """Crea video minimo si no existe (llama a generate_test_video)."""
    script = os.path.join(os.path.dirname(__file__), "generate_test_video.py")
    print(f"No existe {path}. Generando video de prueba...")
    subprocess.run([sys.executable, script], check=True)


def send_frame(session: requests.Session, api_url: str, frame, index: int) -> None:
    small = cv2.resize(frame, (320, 240))
    ok, buf = cv2.imencode(".jpg", small)
    if not ok:
        print(f"[FRAME {index}] Error al codificar JPEG")
        return

    files = {"frame": ("frame.jpg", buf.tobytes(), "image/jpeg")}
    data = {"camera_name": "Simulador"}
    try:
        t0 = time.perf_counter()
        resp = session.post(api_url, files=files, data=data, timeout=120)
        elapsed = time.perf_counter() - t0
        if resp.status_code != 200:
            print(f"[FRAME {index}] HTTP {resp.status_code}: {resp.text[:120]}")
            return
        body = resp.json()

        print(f"Respuesta JSON completa: {body}")
        print(f"Threats recibidas: {body.get('threats', [])}")

        for threat in body.get("threats", []):
            bbox = threat.get("bbox")
            print(f"  Type: {threat.get('type')}, Confidence: {threat.get('confidence')}, BBox: {bbox}")

            if not bbox or len(bbox) != 4:
                print(f"    BBox invalido, saltando...")
                continue
            x1, y1, x2, y2 = bbox
            confidence = threat.get("confidence", 0)
            threat_type = threat.get("type", "?")
            label = f"{threat_type} {confidence*100:.0f}%"
            h, w = small.shape[:2]
            x1 = max(0, min(int(x1), w))
            y1 = max(0, min(int(y1), h))
            x2 = max(0, min(int(x2), w))
            y2 = max(0, min(int(y2), h))
            cv2.rectangle(small, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(small, label, (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Simulador", small)
        cv2.waitKey(1)

        if body.get("detected"):
            print(
                f"[FRAME {index}] DETECTION! type={body.get('threat_type')} "
                f"conf={body.get('confidence', 0):.2f} "
                f"alert_sent={body.get('alert_sent', False)} "
                f"({elapsed:.2f}s)"
            )
        else:
            print(f"[FRAME {index}] ok ({elapsed:.2f}s)")
    except requests.RequestException as exc:
        print(f"[FRAME {index}] Error de red: {exc}")


def run(video_path: str, api_url: str, once: bool, max_frames: int | None) -> int:
    if not os.path.isfile(video_path):
        create_placeholder_video(video_path)
        if not os.path.isfile(video_path):
            print("Error: no se pudo crear el video de prueba.")
            return 1

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: no se pudo abrir {video_path}")
        return 1

    session = requests.Session()
    frame_index = 0
    window_start = time.perf_counter()
    window_frames = 0

    print(f"Enviando a {api_url}")
    print(f"Video: {video_path} (Ctrl+C para detener)\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if once:
                    break
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame_index += 1
            window_frames += 1
            send_frame(session, api_url, frame, frame_index)

            if max_frames is not None and frame_index >= max_frames:
                break

            if frame_index % 30 == 0:
                elapsed = time.perf_counter() - window_start
                fps = window_frames / elapsed if elapsed > 0 else 0
                print(f"  >> FPS envio ~ {fps:.1f}")
                window_start = time.perf_counter()
                window_frames = 0

            time.sleep(FRAME_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(f"\nTotal frames procesados: {frame_index}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Simula camara IP con video local")
    parser.add_argument("--video", default=DEFAULT_VIDEO, help="Ruta al MP4")
    parser.add_argument("--api", default=DEFAULT_API, help="URL POST /api/detect")
    parser.add_argument("--once", action="store_true", help="Reproducir una sola vez")
    parser.add_argument("--max-frames", type=int, default=None, help="Limite de frames")
    args = parser.parse_args()
    return run(args.video, args.api, args.once, args.max_frames)


if __name__ == "__main__":
    if os.name == 'nt':  # Windows
        import matplotlib
        matplotlib.use('TkAgg')
    sys.exit(main())
