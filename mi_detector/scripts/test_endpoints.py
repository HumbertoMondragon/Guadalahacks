#!/usr/bin/env python3
"""Verifica que el backend responda en todos los endpoints principales."""

import io
import sys

import requests
from PIL import Image

BASE = "http://localhost:8000"


def ok(label: str) -> None:
    print(f"  OK {label}")


def fail(label: str, detail: str = "") -> None:
    msg = f"  FAIL {label}"
    if detail:
        msg += f" -> {detail}"
    print(msg)


def make_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (320, 240), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def main() -> int:
    print("Probando API en", BASE)
    print("")

    errors = 0

    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        if r.status_code == 200 and r.json().get("status") == "ok":
            ok("GET /health")
        else:
            fail("GET /health", r.text)
            errors += 1
    except requests.RequestException as exc:
        fail("GET /health", str(exc))
        print("\nERROR: Servidor no responde. Ejecuta: cd backend && python main.py")
        return 1

    try:
        r = requests.get(f"{BASE}/api/alerts", timeout=5)
        if r.status_code == 200 and isinstance(r.json(), list):
            ok("GET /api/alerts")
        else:
            fail("GET /api/alerts", r.text)
            errors += 1
    except requests.RequestException as exc:
        fail("GET /api/alerts", str(exc))
        errors += 1

    try:
        r = requests.get(f"{BASE}/api/metrics", timeout=5)
        if r.status_code == 200 and "fps" in r.json():
            ok("GET /api/metrics")
        else:
            fail("GET /api/metrics", r.text)
            errors += 1
    except requests.RequestException as exc:
        fail("GET /api/metrics", str(exc))
        errors += 1

    try:
        files = {"frame": ("test.jpg", make_jpeg_bytes(), "image/jpeg")}
        data = {"camera_name": "test_script"}
        r = requests.post(f"{BASE}/api/detect", files=files, data=data, timeout=120)
        if r.status_code == 200 and "detected" in r.json():
            body = r.json()
            loaded = requests.get(f"{BASE}/health", timeout=5).json().get("model_loaded")
            ok(f"POST /api/detect (model_loaded={loaded})")
            if body.get("detected"):
                print(f"       deteccion: {body.get('threat_type')} {body.get('confidence')}")
        else:
            fail("POST /api/detect", r.text)
            errors += 1
    except requests.RequestException as exc:
        fail("POST /api/detect", str(exc))
        errors += 1

    alert_id = None
    try:
        alerts = requests.get(f"{BASE}/api/alerts?limit=1", timeout=5).json()
        if alerts:
            alert_id = alerts[0]["id"]
    except requests.RequestException:
        pass

    if not alert_id:
        files = {"frame": ("test.jpg", make_jpeg_bytes(), "image/jpeg")}
        requests.post(
            f"{BASE}/api/detect",
            files=files,
            data={"camera_name": "test_confirm"},
            timeout=120,
        )
        alerts = requests.get(f"{BASE}/api/alerts?limit=1", timeout=5).json()
        if alerts:
            alert_id = alerts[0]["id"]

    if alert_id:
        try:
            r = requests.post(
                f"{BASE}/api/alert/confirm",
                json={"alert_id": alert_id, "status": "false_alarm"},
                timeout=5,
            )
            if r.status_code == 200 and r.json().get("success"):
                ok("POST /api/alert/confirm")
            else:
                fail("POST /api/alert/confirm", r.text)
                errors += 1
        except requests.RequestException as exc:
            fail("POST /api/alert/confirm", str(exc))
            errors += 1
    else:
        fail("POST /api/alert/confirm", "sin alertas en BD para probar")

    try:
        r = requests.get(BASE, timeout=5)
        if r.status_code == 200 and "Detector de Violencia" in r.text:
            ok("GET / (dashboard HTML)")
        else:
            fail("GET /", f"status {r.status_code}")
            errors += 1
    except requests.RequestException as exc:
        fail("GET /", str(exc))
        errors += 1

    print("")
    if errors:
        print(f"Resultado: {errors} prueba(s) fallaron.")
        return 1
    print("Resultado: todo OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
