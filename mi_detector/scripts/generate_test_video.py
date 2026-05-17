#!/usr/bin/env python3
"""Genera un video sintético de prueba con escenas simuladas."""

import os
import sys

import cv2
import numpy as np

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "test_video.mp4")

WIDTH = 640
HEIGHT = 480
FPS = 30
DURATION_SEC = 30


def frame_gray() -> np.ndarray:
    return np.full((HEIGHT, WIDTH, 3), 180, dtype=np.uint8)


def draw_fight(frame: np.ndarray, t: float) -> None:
    x1 = int(120 + 40 * np.sin(t * 8))
    x2 = int(360 + 40 * np.sin(t * 8 + 1))
    cv2.rectangle(frame, (x1, 200), (x1 + 80, 320), (80, 80, 220), -1)
    cv2.rectangle(frame, (x2, 200), (x2 + 80, 320), (220, 80, 80), -1)


def draw_weapon(frame: np.ndarray, t: float) -> None:
    x = int(280 + 30 * np.sin(t * 6))
    cv2.rectangle(frame, (x, 220), (x + 100, 260), (40, 40, 200), -1)


def main() -> int:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    writer = cv2.VideoWriter(
        OUTPUT_PATH,
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        print("Error: no se pudo crear el archivo de video.")
        return 1

    total_frames = FPS * DURATION_SEC
    for i in range(total_frames):
        sec = i / FPS
        frame = frame_gray()

        if 10 <= sec < 15:
            draw_fight(frame, sec)
        elif 15 <= sec < 20:
            draw_weapon(frame, sec)

        writer.write(frame)

    writer.release()
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"Video creado: {OUTPUT_PATH}")
    print(f"  Duracion: {DURATION_SEC}s @ {FPS} fps")
    print(f"  Tamano:   {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
