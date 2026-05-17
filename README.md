# SENTINELA AI — Detector de Violencia Comunitaria

Sistema de vigilancia inteligente con inferencia **100% local**. Ningún frame sale del dispositivo: sin nube, sin identificación facial, sin transmisión de datos. Diseñado para comunidades de Guadalajara.

---

## Cómo funciona

Cada cámara captura frames que se comprimen a 320px y se envían al detector híbrido:

1. **YOLOv8 (custom)** — modelo entrenado sobre UCF-Crime que detecta `violence`, `fight` y `person` a nivel de bounding box.
2. **MediaPipe Pose** — extrae 33 landmarks del esqueleto humano. Detecta `fight` (muñecas por encima de hombros → posición de impacto) y `fallen` (nariz al nivel de caderas → persona caída).
3. **Fusión** — si ambos modelos coinciden en el mismo tipo de amenaza, la confianza aumenta +10 pp (cap 1.0) y la fuente se marca como `hybrid`.

Las alertas con confianza ≥ 85% se persisten en SQLite con debounce de 5 segundos por cámara. A partir de 5 detecciones de alta confianza en 30 segundos se activa modo de **escalación**.

---

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI 0.104 · Uvicorn 0.24 |
| Inferencia | YOLOv8 (Ultralytics 8.0) · MediaPipe Pose 0.10 |
| Deep learning | PyTorch 2.1 · OpenCV 4.8 |
| Base de datos | SQLite (aiofiles, sin ORM) |
| Frontend | HTML/CSS/JS vanilla — sin frameworks |
| Modelo base | UCF-Crime dataset · pesos en `models/best.pt` |

---

## Estructura del proyecto

```
mi_detector/
├── backend/
│   ├── main.py          # FastAPI app, endpoints, lógica de inferencia
│   ├── detector.py      # HybridDetector: YOLOv8 + MediaPipe Pose
│   ├── alerts.py        # AlertLogic: debounce, escalación
│   ├── database.py      # DatabaseManager: SQLite
│   ├── config.py        # Parámetros globales
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Dashboard de monitoreo
│   ├── capture.html     # Vista de cámara móvil
│   ├── app.js           # Lógica del dashboard y detección por cámara
│   └── style.css        # Design system SENTINELA
├── models/
│   └── best.pt          # Pesos YOLOv8 custom
├── data/
│   ├── alertas.db       # Base de datos SQLite
│   └── logs/app.log     # Log del servidor
└── scripts/
    ├── download_model.py
    ├── train_model.py
    ├── generate_test_video.py
    └── simulate_camera.py
```

---

## Instalación

```powershell
cd mi_detector
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python scripts\download_model.py   # descarga best.pt si no existe
```

---

## Uso

### Iniciar el servidor

```powershell
cd backend
python main.py
```

- Dashboard: `http://localhost:8000`
- Cámara móvil: `http://localhost:8000/capture`
- Desde otra computadora en la misma red: `http://<IP-LOCAL>:8000`

### Simular cámara (opcional)

```powershell
python scripts\simulate_camera.py --once
```

### Tests de endpoints

```powershell
python scripts\test_endpoints.py
```

---

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servidor y modelo |
| `POST` | `/api/detect` | Frame JPEG → detección + alerta |
| `GET` | `/api/alerts` | Lista de alertas (últimas 24h) |
| `POST` | `/api/alert/confirm` | Confirmar alerta o marcar como falso positivo |
| `GET` | `/api/metrics` | FPS, latencia, conteo de alertas |

### Ejemplo: enviar un frame

```bash
curl -X POST http://localhost:8000/api/detect \
  -F "frame=@frame.jpg" \
  -F "camera_name=CAM 01"
```

### Respuesta

```json
{
  "detected": true,
  "threat_type": "fight",
  "confidence": 0.91,
  "alert_id": "uuid...",
  "alert_sent": true,
  "inference_time_ms": 17.4,
  "threats": [
    { "type": "fight", "confidence": 0.91, "bbox": [120, 80, 400, 360], "source": "hybrid" }
  ]
}
```

---

## Configuración (`backend/config.py`)

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `CONFIDENCE_THRESHOLD` | `0.50` | Umbral mínimo para reportar detección |
| `MODEL_INPUT_SIZE` | `320` | Resolución de entrada a YOLO (px) |
| `ALERT_DEBOUNCE_MS` | `5000` | Tiempo mínimo entre alertas de la misma cámara |
| `ESCALATION_THRESHOLD` | `5` | Detecciones en 30s para activar escalación |
| `BLUR_FACES` | `True` | Anonimización de rostros |
| `SAVE_FRAMES` | `False` | No persistir frames en disco |

---

## Entrenamiento personalizado

```powershell
# Con GPU NVIDIA (recomendado, ~2-4 h)
python scripts\train_model.py --epochs 30 --device cuda

# Solo CPU
python scripts\train_model.py --epochs 30 --device cpu
```

El mejor peso se copia automáticamente a `models/best.pt`. Reinicia el servidor para aplicar.

**Datasets recomendados:** UCF-Crime, RWF-2000, CCTV-Fights.  
**Herramientas de anotación:** Roboflow, CVAT.

---

## Privacidad por diseño

- Inferencia completamente on-device — ningún frame abandona el equipo
- Sin almacenamiento de rostros (`BLUR_FACES = True` por defecto)
- Sin frames guardados en disco (`SAVE_FRAMES = False` por defecto)
- Base de datos local SQLite, sin conexión a servicios externos
- El operador humano confirma o descarta cada alerta — la IA nunca actúa sola

---

## Licencia

MIT — Guadalahacks 2026
