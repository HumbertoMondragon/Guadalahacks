#!/usr/bin/env python3
"""Descarga YOLOv8 medium y lo guarda como models/best.pt para el backend."""

import os
import shutil
import sys
from pathlib import Path

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEST_PATH = MODELS_DIR / "best.pt"
MODEL_NAME = "yolov8m.pt"
# yolov8m.pt ~50 MB; yolov8l/x superan 100 MB
MIN_SIZE_BYTES = 50 * 1024 * 1024


def main() -> int:
    print("Descargando modelo YOLOv8 (medium)...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    cwd_before = Path.cwd()
    try:
        os.chdir(MODELS_DIR)
        model = YOLO(MODEL_NAME)
        source = Path(model.ckpt_path or MODEL_NAME)
        if not source.is_file():
            source = MODELS_DIR / MODEL_NAME
        if not source.is_file():
            source = cwd_before / MODEL_NAME
        if not source.is_file():
            print(f"Error: no se encontro {MODEL_NAME} despues de la descarga.")
            return 1

        shutil.copy2(source, DEST_PATH)
    finally:
        os.chdir(cwd_before)

    if not DEST_PATH.is_file():
        print(f"Error: no se creo {DEST_PATH}")
        return 1

    size_mb = DEST_PATH.stat().st_size / (1024 * 1024)
    if DEST_PATH.stat().st_size < MIN_SIZE_BYTES:
        print(
            f"Advertencia: el archivo pesa {size_mb:.1f} MB "
            f"(esperado >= {MIN_SIZE_BYTES / (1024 * 1024):.0f} MB para yolov8m)."
        )

    print("")
    print("Modelo listo.")
    print(f"  Ruta:   {DEST_PATH}")
    print(f"  Tamano: {size_mb:.1f} MB")
    print(f"  Clases: {len(model.names)} (COCO pre-entrenado)")
    print("")
    print("Uso: cd backend && python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
