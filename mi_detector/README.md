# Detector de Violencia Comunitaria

Sistema local de detección de incidentes (Edge AI + FastAPI). Sin nube, sin identificación facial.

## Instalación

```powershell
cd mi_detector
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python scripts\download_model.py
```

## Uso rápido

### Terminal 1 — Backend

```powershell
cd backend
python main.py
```

→ http://localhost:8000 (dashboard)  
→ http://localhost:8000/capture (cámara móvil)

### Terminal 2 — Simulador (opcional)

```powershell
python scripts\generate_test_video.py
python scripts\simulate_camera.py --once
```

### Tests

```powershell
python scripts\test_endpoints.py
```

## Arquitectura

- **Backend:** FastAPI + YOLOv8 + SQLite (`backend/`)
- **Frontend:** HTML/CSS/JS vanilla (`frontend/`)
- **Modelo:** `models/best.pt` (generado con `download_model.py` o `train_model.py`)
- **Logs:** `data/logs/app.log`
- **Privacidad:** procesamiento local; frames no se guardan por defecto

## Detectar peleas reales (entrenamiento)

El modelo por defecto es **YOLOv8 preentrenado en COCO** (personas, autos, etc.).  
Para alertas tipo `fight` / `weapon` necesitas **fine-tuning** con dataset anotado.

### 1. Obtener datos

- **UCF-Crime** (recomendado): http://crcv.ucf.edu/datasets/ucf_crime.php  
- **Prueba de pipeline:** `bash scripts/download_dataset.sh` (COCO128)

### 2. Anotar en formato YOLO

Herramientas: [Roboflow](https://roboflow.com) o [CVAT](https://www.cvat.ai).

Clases del proyecto:

`weapon`, `fight`, `crowd`, `fallen`, `vandalism`

Estructura:

```
data/dataset/
  images/train/   labels/train/
  images/val/     labels/val/
```

### 3. Entrenar

```powershell
# Con GPU NVIDIA (recomendado, 2-4 h)
python scripts\train_model.py --epochs 30 --device cuda

# Solo CPU (mucho más lento)
python scripts\train_model.py --epochs 30 --device cpu

# Probar que el pipeline corre (NO aprende peleas)
python scripts\train_model.py --coco128-demo --epochs 5
```

El mejor peso se copia a `models/best.pt`. Reinicia `python main.py`.

### 4. Validar

- `python scripts\simulate_camera.py --once` con video real de incidente  
- Ajustar `CONFIDENCE_THRESHOLD` en `backend/config.py` si hay muchos falsos positivos

## Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servidor |
| POST | `/api/detect` | Frame JPEG → detección |
| GET | `/api/alerts` | Lista de alertas |
| POST | `/api/alert/confirm` | Confirmar / falso positivo |
| GET | `/api/metrics` | Métricas del dashboard |

## Licencia

MIT
