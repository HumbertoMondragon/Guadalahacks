#!/usr/bin/env python3
"""
Fine-tuning de YOLOv8 para clases de amenaza comunitaria.

Requisito para detectar PELEAS REALES:
  - Dataset con imagenes + labels YOLO en data/dataset/
  - Clases: weapon, fight, crowd, fallen, vandalism

Estructura esperada:
  data/dataset/images/train/   data/dataset/labels/train/
  data/dataset/images/val/     data/dataset/labels/val/

COCO128 (scripts/download_dataset.sh) sirve solo para probar el pipeline;
sus etiquetas NO son peleas hasta que re-anotes los frames.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATASET_ROOT = PROJECT_ROOT / "data" / "dataset"
YAML_PATH = PROJECT_ROOT / "data" / "dataset.yaml"
DEST_MODEL = MODELS_DIR / "best.pt"

CLASS_NAMES = ["weapon", "fight", "crowd", "fallen", "vandalism"]


def find_labeled_dataset() -> Path | None:
    """Busca carpeta con split train/val de YOLO."""
    candidates = [
        DATASET_ROOT,
        DATASET_ROOT / "coco128",
        PROJECT_ROOT / "data" / "ucf_crime",
    ]
    for root in candidates:
        if (root / "images" / "train").is_dir() and (root / "labels" / "train").is_dir():
            return root.resolve()
    return None


def count_labels(root: Path) -> int:
    return len(list((root / "labels" / "train").glob("*.txt")))


def write_dataset_yaml(root: Path) -> Path:
    """Genera data/dataset.yaml con rutas absolutas."""
    config = {
        "path": str(root),
        "train": "images/train",
        "val": "images/val",
        "nc": len(CLASS_NAMES),
        "names": CLASS_NAMES,
    }
    YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    return YAML_PATH


def pick_device(requested: str) -> str | int:
    if requested == "cpu":
        return "cpu"
    if requested == "cuda" or requested == "0":
        return 0 if torch.cuda.is_available() else "cpu"
    if torch.cuda.is_available():
        return 0
    return "cpu"


def copy_best_weights(run_name: str) -> bool:
    best = PROJECT_ROOT / "runs" / "detect" / run_name / "weights" / "best.pt"
    if not best.is_file():
        print(f"Error: no se encontro {best}")
        return False
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, DEST_MODEL)
    print(f"Modelo copiado a {DEST_MODEL}")
    return True


def train_custom(args: argparse.Namespace) -> int:
    root = find_labeled_dataset()
    if root is None:
        print("Error: no hay dataset en data/dataset/ con images/train y labels/train.")
        print("  1) bash scripts/download_dataset.sh   (solo prueba pipeline)")
        print("  2) Anota peleas en Roboflow/CVAT y exporta formato YOLO")
        print("  3) Coloca train/val en data/dataset/")
        return 1

    n_labels = count_labels(root)
    if n_labels == 0:
        print(f"Error: {root}/labels/train esta vacio. Necesitas anotaciones YOLO.")
        return 1

    yaml_path = write_dataset_yaml(root)
    device = pick_device(args.device)

    print(f"Dataset:  {root}")
    print(f"Labels train: {n_labels}")
    print(f"YAML:     {yaml_path}")
    print(f"Device:   {device}")
    print(f"Clases:   {CLASS_NAMES}")
    print("")

    if args.coco128_only:
        print(
            "AVISO: Si usas COCO128 sin re-anotar, el modelo NO aprendera 'fight'.\n"
            "       Solo valida que el entrenamiento corre.\n"
        )

    model = YOLO(args.base_weights)
    model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        patience=args.patience,
        save=True,
        project=str(PROJECT_ROOT / "runs" / "detect"),
        name=args.run_name,
        exist_ok=True,
    )

    if not copy_best_weights(args.run_name):
        return 1

    print("\nListo. Reinicia el backend para cargar el nuevo best.pt:")
    print("  cd backend && python main.py")
    return 0


def train_coco128_demo(args: argparse.Namespace) -> int:
    """Entrenamiento rapido con coco128.yaml (NO detecta peleas)."""
    device = pick_device(args.device)
    print("Modo demo: entrenando con coco128.yaml (clases COCO, no fight).\n")
    model = YOLO(args.base_weights)
    model.train(
        data="coco128.yaml",
        epochs=min(args.epochs, 10),
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        patience=args.patience,
        project=str(PROJECT_ROOT / "runs" / "detect"),
        name="train_coco128_demo",
        exist_ok=True,
    )
    copy_best_weights("train_coco128_demo")
    print("\nDemo terminado. Para peleas reales usa dataset anotado con clase 'fight'.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrena YOLOv8 para amenazas comunitarias")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--device", default="auto", help="auto | cpu | cuda | 0")
    parser.add_argument("--base-weights", default="yolov8m.pt")
    parser.add_argument("--run-name", default="train_custom")
    parser.add_argument(
        "--coco128-demo",
        action="store_true",
        help="Entrena con coco128.yaml solo para verificar pipeline",
    )
    parser.add_argument(
        "--coco128-only",
        action="store_true",
        help="Usa dataset local coco128 (misma advertencia)",
    )
    args = parser.parse_args()

    if args.coco128_demo:
        return train_coco128_demo(args)
    return train_custom(args)


if __name__ == "__main__":
    sys.exit(main())
