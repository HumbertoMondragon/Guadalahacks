#!/usr/bin/env bash
# Descarga dataset para entrenamiento (opcional).
# UCF-Crime requiere registro manual; este script usa COCO128 como alternativa rápida.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/data/dataset"
COCO_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip"
ZIP="${DEST}/coco128.zip"

echo "=============================================="
echo " Detector de Violencia - Descarga de dataset"
echo "=============================================="
echo ""
echo "UCF-Crime (recomendado para entrenamiento real):"
echo "  http://crcv.ucf.edu/datasets/ucf_crime.php"
echo "  Requiere formulario de registro. Coloca los videos en:"
echo "  ${DEST}/ucf_crime/"
echo ""
echo "Alternativa automatica: COCO128 (pruebas rapidas YOLOv8)..."
echo ""

mkdir -p "${DEST}"

if command -v curl >/dev/null 2>&1; then
  curl -L --progress-bar -o "${ZIP}" "${COCO_URL}"
elif command -v wget >/dev/null 2>&1; then
  wget -O "${ZIP}" "${COCO_URL}"
else
  echo "Error: instala curl o wget."
  exit 1
fi

if command -v unzip >/dev/null 2>&1; then
  unzip -q -o "${ZIP}" -d "${DEST}"
else
  echo "Error: instala unzip (Git Bash en Windows lo incluye)."
  exit 1
fi

rm -f "${ZIP}"

DATA_DIR="${DEST}/coco128"
if [[ ! -d "${DATA_DIR}" ]]; then
  DATA_DIR="${DEST}"
fi

IMAGE_COUNT="$(find "${DATA_DIR}" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) 2>/dev/null | wc -l | tr -d ' ')"
LABEL_COUNT="$(find "${DATA_DIR}" -type f -name '*.txt' 2>/dev/null | wc -l | tr -d ' ')"

echo ""
echo "Descarga completada."
echo "  Ubicacion: ${DATA_DIR}"
echo "  Imagenes:  ${IMAGE_COUNT}"
echo "  Labels:    ${LABEL_COUNT}"
echo "  Frames estimados (videos UCF): N/A (usa COCO128 = imagenes estaticas)"
echo ""
echo "Para entrenar: python scripts/train_model.py (Fase 7, opcional)"
