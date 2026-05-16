# Prompts para Claude Code - Detector de Violencia Comunitaria
## Guadalahacks 2026 | Úsalos de uno en uno, en este orden

---

## 📍 CÓMO USAR ESTOS PROMPTS

Cada prompt está diseñado para **1 tarea clara**. 

**Flujo:**
1. Abre Claude Code en tu terminal: `claude code`
2. Copia UN PROMPT de abajo
3. Pégalo en Claude Code
4. Espera a que termine
5. Verifica que funcione
6. Ve al SIGUIENTE prompt

**Importante:** Si algo no funciona en un prompt, NO SIGAS. Fija primero.

---

## FASE 1: SETUP INICIAL (15 minutos)

### PROMPT 1.1: Estructura de carpetas y requirements.txt

```
Crea la estructura de carpetas para el proyecto "Detector de Violencia Comunitaria".

Necesito:
1. Carpeta raíz: mi_detector/
2. Subcarpetas: backend/, frontend/, models/, data/, scripts/
3. Archivo requirements.txt en backend/ con estas dependencias (exactamente):
   - fastapi==0.104.1
   - uvicorn==0.24.0
   - python-multipart==0.0.6
   - opencv-python==4.8.1.78
   - ultralytics==8.0.215
   - torch==2.1.0
   - numpy==1.24.3
   - pillow==10.0.1
   - pydantic==2.4.2
   - sqlalchemy==2.0.23

4. Archivo .gitignore con:
   - models/*.pt
   - data/
   - __pycache__/
   - .env
   - venv/

Crea TODO (directorios y archivos). No ejecutes nada aún.
```

### PROMPT 1.2: Instalar dependencias

```
Instala las dependencias del proyecto.

Necesito que:
1. Crees un ambiente virtual en mi_detector/: python -m venv venv
2. Lo actives
3. Instales desde mi_detector/backend/requirements.txt: pip install -r requirements.txt

Si hay errores con torch (es pesado), dime qué error exacto.
```

---

## FASE 2: BACKEND CORE (2 horas)

### PROMPT 2.1: config.py - Variables de configuración

```
Crea el archivo mi_detector/backend/config.py

Este archivo SOLO contiene constantes y configuración. Nada de lógica.

Incluye:
1. MODELO:
   - MODEL_PATH = "models/best.pt"
   - MODEL_INPUT_SIZE = 640
   - CONFIDENCE_THRESHOLD = 0.85
   - CLASSES = {"weapon": 0, "fight": 1, "crowd": 2, "fallen": 3, "vandalism": 4}

2. SERVIDOR:
   - HOST = "0.0.0.0"
   - PORT = 8000
   - DEBUG = True

3. BASE DE DATOS:
   - DB_PATH = "data/alertas.db"
   - ALERT_RETENTION_HOURS = 24

4. PRIVACIDAD:
   - BLUR_FACES = True
   - SAVE_FRAMES = False
   - MAX_FRAME_SIZE_MB = 100

5. ALERTAS:
   - ALERT_DEBOUNCE_MS = 5000
   - ESCALATION_THRESHOLD = 5  # Si 5+ alertas en 30s

Formato: Python estándar, sin clases. Solo variables.
```

### PROMPT 2.2: database.py - SQLite básico

```
Crea mi_detector/backend/database.py

Necesito:
1. Una clase DatabaseManager que:
   - Constructor: __init__(db_path: str)
   - Método: init_db() → crea tabla "incidents" si no existe
   - Método: create_alert(threat_type: str, confidence: float, camera_name: str) → retorna alert_id
   - Método: confirm_alert(alert_id: str, status: str) → actualiza en BD
   - Método: get_recent_alerts(hours: int = 24, limit: int = 50) → retorna lista de alertas

2. Tabla "incidents" con columnas:
   - id (TEXT PRIMARY KEY)
   - timestamp (TEXT ISO format)
   - threat_type (TEXT)
   - confidence (FLOAT 0.0-1.0)
   - camera_name (TEXT)
   - status (TEXT: pending, confirmed_real, false_alarm)
   - confirmed_at (TEXT, nullable)
   - created_at (TEXT)

Usa sqlite3 (built-in). No uses ORM. SQL directo.

El código debe:
- Crear BD en data/alertas.db si no existe
- No tirar excepciones, manejar errors silenciosamente
- Tener docstrings (qué hace cada función)
```

### PROMPT 2.3: detector.py - Wrapper YOLOv8

```
Crea mi_detector/backend/detector.py

Necesito una clase YOLOv8Detector que:

1. Constructor: __init__(model_path: str, input_size: int = 640, conf_threshold: float = 0.85)
   - Intenta cargar el modelo desde model_path
   - Si NO existe: usa modelo pequeño pre-entrenado en COCO como fallback
   - Si falla: lanza excepción con mensaje claro

2. Método: detect(frame: numpy.ndarray) → dict
   - Input: frame en RGB (numpy array)
   - Output: {
       "detected": bool,
       "threats": [
         {"type": "weapon", "confidence": 0.92, "bbox": [x1, y1, x2, y2]},
         ...
       ],
       "inference_time_ms": 45.2
     }
   - Si confianza < conf_threshold: ignora

3. Método: _format_bbox(coords) → [x1, y1, x2, y2]
   - Convierte formato YOLO a formato normal

4. Atributo: self.model_loaded (bool)
   - True si modelo cargó correctamente

Código debe:
- Usar ultralytics.YOLO
- Medir tiempo de inferencia
- NO guardar frames
- Tener try/except para errores
```

### PROMPT 2.4: alerts.py - Lógica de amenaza

```
Crea mi_detector/backend/alerts.py

Necesito una clase AlertLogic que:

1. Constructor: __init__(debounce_ms: int = 5000, escalation_threshold: int = 5)
   - Guarda últimas detecciones (en memoria, dict)

2. Método: should_alert(threat_type: str, confidence: float, camera_name: str) → bool
   - Lógica:
     * Si confidence < 0.60: retorna False (ignorar)
     * Si 0.60 <= confidence < 0.85: retorna False pero log (alerta pendiente)
     * Si confidence >= 0.85: retorna True (ENVIAR ALERTA)
   - Verifica debounce: no alertar de MISMO tipo en < 5 segundos
   - Si 5+ alertas en 30s de misma cámara: marca como ESCALATION (urgente)

3. Método: get_alert_message(threat_type: str, confidence: float) → str
   - Retorna mensaje para WhatsApp:
     "ALERTA: {threat_type.upper()} detectada
      Confianza: {confidence*100:.0f}%
      Hora: {timestamp}"

4. Atributo: self.recent_detections (dict)
   - Guarda últimas 10 detecciones en memoria
   - Cada una con {timestamp, threat_type, camera_name}

Código debe:
- Ser stateful (guarda estado entre llamadas)
- Manejar timestamps en ISO format
- Tener logs (print o logging module)
```

### PROMPT 2.5: main.py - FastAPI server

```
Crea mi_detector/backend/main.py

Necesito un servidor FastAPI que:

1. Imports de los archivos anteriores:
   - from config import *
   - from database import DatabaseManager
   - from detector import YOLOv8Detector
   - from alerts import AlertLogic

2. Inicialización al startup:
   - app = FastAPI()
   - db = DatabaseManager(DB_PATH)
   - db.init_db()
   - model = YOLOv8Detector(MODEL_PATH, MODEL_INPUT_SIZE, CONFIDENCE_THRESHOLD)
   - alert_logic = AlertLogic(ALERT_DEBOUNCE_MS, ESCALATION_THRESHOLD)

3. Endpoint: POST /api/detect
   - Input: form data con "frame" (archivo JPEG)
   - Convierte JPEG a numpy array con OpenCV
   - Pasa a model.detect()
   - Si should_alert() es True:
     * Crea alerta en BD
     * Retorna {"detected": True, "threat_type": "...", "confidence": 0.92, "alert_id": "..."}
   - Si False:
     * Retorna {"detected": False}
   - Maneja errores: si frame está corrupto, retorna 400

4. Endpoint: GET /api/alerts
   - Query params: ?limit=50&offset=0
   - Retorna JSON array de alertas últimas 24h

5. Endpoint: POST /api/alert/confirm
   - Input: {"alert_id": "...", "status": "confirmed_real" | "false_alarm"}
   - Actualiza BD
   - Retorna {"success": True}

6. Endpoint: GET /health
   - Retorna {"status": "ok", "model_loaded": model.model_loaded, "uptime_seconds": ...}

7. Main:
   - if __name__ == "__main__":
       uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)

Código debe:
- Tener try/except en cada endpoint
- Loguear (timestamp + qué pasó)
- Retornar JSON válido siempre
- Sin WebSocket aún (lo hacemos después)
```

---

## FASE 3: DATOS & BD (30 minutos)

### PROMPT 3.1: Script para descargar dataset

```
Crea mi_detector/scripts/download_dataset.sh

Script que:
1. Descarga UCF-Crime dataset (abierto):
   - URL base: http://crcv.ucf.edu/datasets/ucf_crime.php
   - Los usuarios deben completar un form para descargar
   - ALTERNATIVA si quieres evitar eso:
     * Descarga COCO128.yaml (dataset pequeño de ejemplo)
     * Sirve para pruebas rápidas de YOLOv8

2. Extrae a: mi_detector/data/dataset/
3. Verifica que descargó correctamente
4. Muestra información:
   - Cuántos videos
   - Cuántos frames (estimado)
   - Dónde guardó

Script en bash. Usa curl o wget.

Nota: El usuario puede correrlo opcionalmente si quiere entrenar. Para DEMO, usaremos un modelo pre-entrenado.
```

### PROMPT 3.2: Script para obtener modelo pre-entrenado

```
Crea mi_detector/scripts/download_model.py

Script Python que:
1. Descarga un modelo YOLOv8 pre-entrenado:
   - Usa ultralytics.YOLO
   - Descarga yolov8m.pt (medium) desde Ultralytics hub
   - Esto es 100% público y libre
   
2. Lo guarda en: models/best.pt (así detector.py lo encuentra)

3. Verifica:
   - Archivo existe
   - Tamaño > 100MB (modelo válido)
   - Muestra información del modelo

Cómo usarlo:
- python scripts/download_model.py
- Toma 2-3 minutos (descarga ~175MB)
- Después el modelo está listo para usar

Esto es lo que harás viernes para tener un modelo rápido.
```

---

## FASE 4: FRONTEND (1 hora)

### PROMPT 4.1: HTML estático - Dashboard

```
Crea mi_detector/frontend/index.html

Página web que muestra:

1. Header (arriba):
   - Título: "Detector de Violencia Comunitaria"
   - Subtítulo: "Sistema local de prevención"
   - Estado del servidor (online/offline)

2. Main layout: 2 columnas
   - Izquierda (60%): Tabla de alertas
   - Derecha (40%): Métricas en vivo

3. Tabla de alertas:
   - Columnas: Hora | Tipo | Confianza | Estado | Acciones
   - Filas: las últimas alertas
   - Colores: rojo (real), gris (falso), amarillo (pendiente)
   - Botones por fila: "Confirmar real" | "Marcar falso"

4. Métricas (lado derecho):
   - Cards con:
     * FPS procesado
     * Latencia promedio (ms)
     * Falsos positivos (últimas 8h)
     * Total alertas hoy

5. Footer:
   - Nota: "Sistema 100% local. Sin internet. Sin rostros grabados."

HTML puro. Estructura básica. No CSS aún.
Incluye IDs claros en elementos que JavaScript va a tocar (table, cards, etc).

Ejemplo estructura:
<div id="alerts-table">
  <table>
    <tr id="alert-row-123">...</tr>
  </table>
</div>
<div id="metrics">
  <div id="metric-fps">...</div>
  ...
</div>
```

### PROMPT 4.2: CSS para dashboard

```
Crea mi_detector/frontend/style.css

Estilos para el dashboard:

1. General:
   - Font: Arial, sans-serif
   - Colores: gris claro fondo (#f5f5f5), texto oscuro (#333)
   - Márgenes/padding: generoso (12px mín)

2. Header:
   - Fondo: azul oscuro (#1e3a5f)
   - Texto: blanco
   - Padding: 20px
   - Font-size: title 24px, subtitle 14px

3. Main layout:
   - display: grid / flex (2 columnas)
   - 60% izquierda, 40% derecha
   - Gap: 16px

4. Tabla:
   - Borde: 1px gris claro
   - Header: fondo gris (#e0e0e0)
   - Filas: alternadas (blanco, gris muy claro)
   - Hover: fondo amarillo claro
   - Colores por status:
     * "confirmed_real": fondo verde claro
     * "false_alarm": fondo gris claro
     * "pending": fondo rojo claro

5. Métricas (cards):
   - Borde: 1px gris
   - Fondo: blanco
   - Border-radius: 8px
   - Padding: 16px
   - Font grande para número (24px, bold)
   - Font pequeña para etiqueta (12px)
   - Sombra suave (box-shadow)

6. Botones:
   - Padding: 8px 16px
   - Font-size: 13px
   - Verde oscuro (#2d7a3e)
   - Hover: verde más claro
   - Cursor: pointer
   - Border-radius: 4px

7. Responsive:
   - En mobile (< 768px): 1 columna
   - Stack vertical

No uses frameworks (Bootstrap, Tailwind). CSS puro.
```

### PROMPT 4.3: JavaScript para dashboard

```
Crea mi_detector/frontend/app.js

Script que:

1. Al cargar la página (window.onload):
   - Llama a fetchAlerts() cada 3 segundos
   - Llama a fetchMetrics() cada 5 segundos

2. Función: fetchAlerts()
   - Hace GET /api/alerts?limit=50
   - Recibe JSON array
   - Actualiza tabla HTML
   - Nuevo alerta arriba (sin recargar página)
   - Ejemplo:
     ```javascript
     const alerts = await fetch('/api/alerts').then(r => r.json());
     const tbody = document.getElementById('alerts-table-body');
     tbody.innerHTML = '';
     alerts.forEach(alert => {
       const tr = document.createElement('tr');
       tr.id = 'alert-' + alert.id;
       tr.innerHTML = `
         <td>${alert.timestamp}</td>
         <td>${alert.threat_type}</td>
         <td>${(alert.confidence*100).toFixed(0)}%</td>
         <td>${alert.status}</td>
         <td>
           <button onclick="confirmAlert('${alert.id}', 'confirmed_real')">Confirmar</button>
           <button onclick="confirmAlert('${alert.id}', 'false_alarm')">Marcar falso</button>
         </td>
       `;
       tbody.appendChild(tr);
     });
     ```

3. Función: fetchMetrics()
   - Hace GET /api/metrics
   - Actualiza cards: fps, latencia, falsos positivos, etc
   - Usa document.getElementById para actualizar valores

4. Función: confirmAlert(alert_id, status)
   - Hace POST /api/alert/confirm con {alert_id, status}
   - Actualiza tabla inmediatamente
   - Cambia color de fila según status

5. Error handling:
   - Si servidor está offline: muestra "SERVER OFFLINE" en rojo
   - Si fetch falla: log en consola, no crashea

Código simple. Sin librerías (jQuery, React, etc).
```

### PROMPT 4.4: HTML para móvil - Captura

```
Crea mi_detector/frontend/capture.html

Página que abre en el celular. Muestra:

1. Header:
   - Título: "Captura de cámara"
   - Botón: "Ir al dashboard"

2. Main:
   - Video element (<video>): muestra cámara en vivo
   - Canvas element (<canvas>): oculto (para procesar frames)
   - Status: "Conectando..." → "En vivo" (verde) o "Desconectado" (rojo)

3. Overlay (encima del video):
   - Si se detecta amenaza: borde ROJO parpadeante
   - Muestra tipo: "PELEA DETECTADA - 92%"
   - Sonido: beep (audio element)

4. Botones abajo:
   - "Detener captura"
   - "Recarga"

5. Footer:
   - "Sistema local. Cero internet. Cero privacidad."

HTML puro. No CSS aún.
Incluye <video>, <canvas>, <audio> elements.
IDs para JavaScript: video-element, canvas, status-text, threat-overlay, etc.
```

### PROMPT 4.5: JavaScript para captura móvil

```
Crea mi_detector/frontend/capture.js

Script para el celular que:

1. Al cargar:
   - Solicita permisos de cámara: navigator.mediaDevices.getUserMedia()
   - Si acepta: abre cámara trasera (facingMode: 'environment')
   - Si rechaza: muestra error

2. Bucle de captura (each 200ms ~ 5 fps):
   - Toma frame del <video>
   - Lo dibuja en <canvas>
   - Lo convierte a JPEG: canvas.toBlob(blob)
   - Envía a laptop: POST http://192.168.1.XXX:8000/api/detect

3. Respuesta del servidor:
   - Si {"detected": true}:
     * Overlay rojo en pantalla
     * Muestra: threat_type + confidence
     * Reproduce sonido (beep)
     * Dura 2 segundos después desaparece
   - Si {"detected": false}:
     * Nada (silencio, sin visual)

4. Botones:
   - "Detener captura": para el loop, cierra cámara
   - "Recarga": recarga la página

5. Status:
   - Actualiza elemento #status-text
   - Conexión a servidor: verde (ok), rojo (error)

Código simple. Sin librerías.
```

---

## FASE 5: UTILITIES & TESTING (45 minutos)

### PROMPT 5.1: Script para simular cámara (video estático)

```
Crea mi_detector/scripts/simulate_camera.py

Script que simula una cámara enviando frames de un video local.

Qué hace:
1. Lee un video MP4 desde: data/test_video.mp4
   - Si no existe: crea uno FAKE con OpenCV (frames de colores, abiertos al principio)
   
2. Extrae frames del video (cada 33ms ~ 30 fps)

3. Por cada frame:
   - Lo redimensiona a 320x240 (menos ancho de banda)
   - Lo convierte a JPEG
   - Lo envía como POST a http://localhost:8000/api/detect
   - Imprime en terminal: [FRAME N] DETECTION: {type} {confidence}

4. Cuando termina el video:
   - Repite desde el principio (loop infinito)
   - O cierra si pasás --once

Uso:
  python scripts/simulate_camera.py                    # Infinito
  python scripts/simulate_camera.py --once             # Una sola vez
  python scripts/simulate_camera.py --video my_vid.mp4 # Video custom

Útil para:
- Testing sin celular
- Demo reproducible
- Testing durante desarrollo

Código debe:
- Tener try/except para errores de red
- Mostrar FPS actual
- Contar cuántos frames procesó
```

### PROMPT 5.2: Script para crear video de prueba

```
Crea mi_detector/scripts/generate_test_video.py

Script que genera un video FAKE (test) con amenazas simuladas.

Qué hace:
1. Crea un video MP4 de 30 segundos con OpenCV

2. Estructura:
   - 0-10s: fondo gris (nada, baseline)
   - 10-15s: dos rectángulos moviéndose rápido (simula "pelea")
   - 15-20s: otro rectángulo con color rojo (simula "arma")
   - 20-30s: vuelve a gris (fin)

3. Guarda en: data/test_video.mp4

4. Propiedades:
   - Resolución: 640x480
   - FPS: 30
   - Duración: 30 segundos
   - Tamaño: ~2MB

Uso:
  python scripts/generate_test_video.py
  → Crea data/test_video.mp4
  → Listo para usar con simulate_camera.py

Ventaja: No necesitas video real, es 100% sintético y reproducible.
```

### PROMPT 5.3: Script para testear endpoints

```
Crea mi_detector/scripts/test_endpoints.py

Script que verifica que todos los endpoints funcionen.

Qué hace:
1. Verifica que servidor esté en http://localhost:8000
   - GET /health
   - Si no responde: "ERROR: Server not running"

2. Testea cada endpoint:
   - GET /api/alerts → debe retornar array (incluso si vacío)
   - GET /api/metrics → debe retornar números
   - POST /api/detect con frame dummy (JPEG)
     * Si no existe modelo: debe decir "Model not loaded"
     * Si existe: retorna {"detected": true/false}
   - POST /api/alert/confirm → debe retornar {"success": true}

3. Imprime reporte:
   - ✓ GET /health → OK
   - ✓ GET /api/alerts → OK
   - ✓ POST /api/detect → OK (model loaded)
   - ✓ POST /api/alert/confirm → OK
   - ✓ GET /api/metrics → OK
   
   O:
   - ✗ POST /api/detect → FAIL (error: Connection refused)

Uso:
  python scripts/test_endpoints.py
  → Toma 5 segundos
  → Te dice si todo está bien

Útil para verificar que el backend está vivo antes de demo.
```

---

## FASE 6: INTEGRACIÓN & PULIDO (30 minutos)

### PROMPT 6.1: Servir frontend desde FastAPI

```
Modifica mi_detector/backend/main.py para servir HTML/CSS/JS estáticos.

Necesito:
1. Importar: from fastapi.staticfiles import StaticFiles
2. En main.py, después de crear app:
   app.mount("/static", StaticFiles(directory="../frontend"), name="static")

3. Agregar endpoint:
   - GET / 
   - Retorna el archivo ../frontend/index.html
   - Usa: from fastapi.responses import FileResponse

4. Agregar endpoint:
   - GET /capture
   - Retorna ../frontend/capture.html

Así cuando abras:
- http://localhost:8000 → ves dashboard
- http://localhost:8000/capture → ves captura móvil
- http://localhost:8000/static/app.js → ves JS
- http://localhost:8000/static/style.css → ves CSS

Todo servido desde el mismo servidor (0 dependencias externas).
```

### PROMPT 6.2: Logging simple

```
Modifica mi_detector/backend/main.py para agregar logging básico.

Necesito:
1. Al inicio:
   ```python
   import logging
   from datetime import datetime
   
   logging.basicConfig(
       level=logging.INFO,
       format='[%(asctime)s] %(levelname)s: %(message)s',
       handlers=[
           logging.FileHandler('data/logs/app.log'),
           logging.StreamHandler()  # también a terminal
       ]
   )
   logger = logging.getLogger(__name__)
   ```

2. Agregar logs en cada endpoint:
   - POST /api/detect:
     * logger.info(f"[DETECT] Frame received. Processing...")
     * logger.info(f"[DETECT] Threat detected: {threat_type} ({confidence:.2f})")
     * logger.info(f"[DETECT] False alarm (confidence too low)")
   
   - POST /api/alert/confirm:
     * logger.info(f"[CONFIRM] Alert {alert_id} → {status}")

3. Crea carpeta data/logs/ si no existe

Esto te muestra en tiempo real qué está pasando:
$ python main.py
[2026-05-16 14:23:45] INFO: Server started
[2026-05-16 14:23:50] INFO: [DETECT] Frame received...
[2026-05-16 14:23:50] INFO: [DETECT] Threat: fight (0.92)
...
```

### PROMPT 6.3: README.md

```
Crea mi_detector/README.md

Contenido:

# Detector de Violencia Comunitaria

## Instalación

1. Clone el repo
2. python -m venv venv && source venv/bin/activate
3. cd backend && pip install -r requirements.txt
4. cd .. && python scripts/download_model.py

## Uso

### Terminal 1 - Backend:
python backend/main.py
→ Accede a http://localhost:8000

### Terminal 2 (Optional) - Simulador de cámara:
python scripts/simulate_camera.py

### Navegador - Dashboard:
http://localhost:8000 (laptop)

### Navegador - Captura móvil:
http://192.168.1.XXX:8000/capture (celular en WiFi)

## Arquitectura

- Backend: FastAPI + YOLOv8
- BD: SQLite local
- Frontend: HTML/JS vanilla
- Privacidad: 100% local, sin caras guardadas

## Testing

python scripts/test_endpoints.py

## Ethical Guidelines

Ver ETHICAL_GUIDELINES.md

## License

MIT (abierto)
```

---

## FASE 7: ENTRENAMIENTO DEL MODELO (Viernes noche - OPCIONAL)

### PROMPT 7.1: Script para entrenar YOLOv8 (fine-tuning)

```
Crea mi_detector/scripts/train_model.py

Script para entrenar/fine-tunear YOLOv8 en UCF-Crime dataset.

IMPORTANTE: Este script es OPCIONAL. Para la DEMO usarás el modelo pre-entrenado descargado con download_model.py.

Pero si tienes tiempo viernes y quieres customizar:

Qué hace:
1. Asume que el dataset está en: data/dataset/
   - Structure: data/dataset/images/ y data/dataset/labels/

2. Crea archivo YAML: data/dataset.yaml
   ```yaml
   path: /ruta/absoluta/a/data/dataset
   train: images/train
   val: images/val
   nc: 6  # number of classes
   names: ['weapon', 'fight', 'crowd', 'fallen', 'vandalism', 'background']
   ```

3. Fine-tunea:
   ```python
   from ultralytics import YOLO
   model = YOLO('yolov8m.pt')  # Load pre-trained
   results = model.train(
       data='data/dataset.yaml',
       epochs=30,
       imgsz=640,
       batch=16,
       device=0,  # GPU
       patience=5,
       save=True,
       project='runs/detect',
       name='train_custom'
   )
   ```

4. Copia el mejor modelo:
   cp runs/detect/train_custom/weights/best.pt models/best.pt

Uso:
  python scripts/train_model.py
  → Toma 2-3 horas en GPU
  → Guarda modelo en models/best.pt

NOTA: Si no haces esto, usas el modelo pre-entrenado. Es suficiente para demo.
```

---

## 📋 RESUMEN DEL FLUJO COMPLETO

```
VIERNES:
├─ Descarga modelo: python scripts/download_model.py (2 min)
├─ Setup backend (PROMPT 1.1, 1.2): estructura + deps (10 min)
├─ Backend (PROMPTS 2.1-2.5): FastAPI + BD + YOLOv8 (1 hora)
├─ Testing básico: python scripts/test_endpoints.py (5 min)
└─ Verificar que http://localhost:8000/health retorna OK

SÁBADO MAÑANA:
├─ Frontend (PROMPTS 4.1-4.3): dashboard + CSS + JS (1 hora)
├─ Integración (PROMPT 6.1): servir HTML desde FastAPI (5 min)
├─ Testing simulador (PROMPT 5.1): simulate_camera.py (10 min)
└─ Verificar que dashboard se actualiza con alertas

SÁBADO TARDE:
├─ Mobile (PROMPTS 4.4-4.5): capture.html + capture.js (45 min)
├─ Logging (PROMPT 6.2): logs en consola (5 min)
├─ Testing full: scripts/test_endpoints.py (5 min)
├─ Limpieza: README + .gitignore (PROMPT 6.3) (10 min)
└─ Demo seco: simula incidente, verifica que alerta aparece

DOMINGO:
├─ Verificar que servidor inicia sin errores (2 min)
├─ Abrir dashboard (http://localhost:8000) (1 min)
├─ Iniciar simulador o usar celular (simulate_camera.py) (1 min)
└─ PRESENTAR
```

---

## 🎯 CÓMO USAR ESTOS PROMPTS

1. **Copia UN PROMPT** (ej: PROMPT 1.1)
2. **Abre Claude Code:**
   ```bash
   cd tu_carpeta
   claude code
   ```
3. **Pega el prompt** en Claude Code
4. **Espera a que termine**
5. **Verifica que el código se creó** (abre el archivo)
6. **Prueba si funciona** (si es backend: `python main.py`)
7. **Si hay error: dile a Claude qué salió mal**
8. **Cuando funcione: ve al SIGUIENTE prompt**

---

## ⚠️ ORDEN IMPORTANTE

**NO SALTES PASOS.** Los prompts están ordenados por dependencias:

- config.py debe existir antes de que otros lo importen
- database.py antes de main.py
- detector.py antes de main.py
- main.py antes de test_endpoints.py
- etc

Si haces prompt 2.5 (main.py) sin haber hecho 2.1-2.4, te dará errores de imports.

---

## 💬 SI ALGO FALLA

**Ejemplo:**
- Hiciste PROMPT 2.1 (config.py)
- Hiciste PROMPT 2.2 (database.py)
- Hiciste PROMPT 2.5 (main.py)
- Al correr `python main.py` te da error: `ModuleNotFoundError: No module named 'detector'`

**Solución:**
- Dijiste que hiciste 2.3 (detector.py) pero no lo hiciste
- Vuelve a hacer PROMPT 2.3
- Después intenta main.py de nuevo

---

## 📚 CHEAT SHEET: Qué hace cada fase

| Fase | Qué | Cuándo |
|------|-----|--------|
| 1 | Setup inicial (carpetas, deps) | Viernes 17:00 |
| 2 | Backend core (FastAPI, BD, IA) | Viernes 18:00-19:30 |
| 3 | Datos (descargas, dataset) | Sábado 09:00 |
| 4 | Frontend (HTML, CSS, JS) | Sábado 10:00-12:00 |
| 5 | Testing (simulador, tests) | Sábado 13:00 |
| 6 | Integración (servir HTML, logs) | Sábado 14:00 |
| 7 | Training (OPCIONAL, si tienes tiempo) | Viernes 20:00+ |

---

## 🔥 LISTO PARA EMPEZAR

Copia el **PROMPT 1.1**, abre Claude Code, y dale.

**¿Preguntas antes de empezar?**

---

*Generado para Guadalahacks 2026 | Cada prompt es pequeño, enfocado, y completamente funcional*
