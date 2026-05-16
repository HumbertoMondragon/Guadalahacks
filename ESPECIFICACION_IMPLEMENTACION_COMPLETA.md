# Detector de Violencia Comunitaria - Especificación Técnica Completa
## Implementación para Guadalahacks 2026 - DEMO EN LAPTOP LOCAL

---

## 📋 VISIÓN GENERAL

Este documento describe **EXACTAMENTE** qué vas a construir, cómo funciona cada pieza, en qué orden lo armas, y cómo lo demostrarás el domingo en vivo a los jueces.

**Lo fundamental:**
- Una laptop tu (Ubuntu, Windows o Mac) ejecuta TODA la IA
- Tu celular se conecta a la laptop por WiFi local (sin internet)
- El celular captura video/fotos → se envía a la laptop
- La laptop corre YOLOv8 (detección de objetos) localmente
- Si detecta una amenaza → alerta a un teléfono (simulado o real) por WhatsApp/SMS
- Nada sale de la red local. Nada entra a la nube. Total privacidad.

---

## 🏗️ ARQUITECTURA FÍSICA DE LA DEMO

### Hardware que usarás:

```
┌─────────────────────────────────────────────────────────┐
│                   TU LAPTOP (Intel/AMD/Apple)            │
│  Sistema Operativo: Ubuntu 22.04 LTS / Windows 11 / macOS│
│  Especificaciones mínimas:                               │
│  - CPU: 8 cores (para no morir de aburrimiento)         │
│  - RAM: 16GB (YOLOv8 + FastAPI + OpenCV = hambre RAM)   │
│  - GPU: NVIDIA RTX 2060+ (IDEAL para velocidad)         │
│    SIN GPU: CPU funciona pero es 5-10x más lento        │
│  - Almacenamiento: 50GB libres (dataset + modelo)       │
│  - Puerto Ethernet o WiFi 5GHz (para hablar con celular)│
└─────────────────────────────────────────────────────────┘
                           ↑↓
                    RED WiFi LOCAL
                  (192.168.1.0/24)
                           ↑↓
┌─────────────────────────────────────────────────────────┐
│            TU CELULAR (Android o iPhone)                 │
│  Conectado a MISMA red WiFi que laptop                   │
│  Rol: Cámara + visor de alertas                          │
│  App que usarás: navegador web (Chrome/Safari)          │
│  NO necesita acceso a internet (a menos que quieras SMS) │
└─────────────────────────────────────────────────────────┘
```

### Para la DEMO en vivo:

**Escenario 1 (Ideal):** 
- Laptop en mesita de jueces
- Celular al lado capturando video en vivo
- Un video pre-grabado jugando en el celular (simulando incidente)
- YOLOv8 detecta la amenaza → alerta aparece en pantalla

**Escenario 2 (Backup, si WiFi falla):**
- Video pre-grabado de incidente (archivo MP4 guardado localmente)
- Laptop lo procesa → muestras detección en tiempo real
- Alertas aparecen en terminal / dashboard web

---

## 🔧 COMPONENTES DE SOFTWARE QUE VAS A CONSTRUIR

### 1. BACKEND (En la laptop) - El corazón de todo

Este es un **servidor HTTP local** (Python + FastAPI) que:

**Puerto: localhost:8000**

**Responsabilidades:**
- Recibe frames de video (JPEG) desde el celular
- Corre YOLOv8 en cada frame (< 100ms por frame)
- Detecta si hay: arma, pelea, aglomeración, persona caída
- Si confianza > 85%: genera alerta
- Guarda alertas en BD local (SQLite)
- Borra frames después de 24h (privacidad)
- Envía alerta a WhatsApp/SMS (simulado o real)
- Sirve un dashboard web para ver historial de alertas

**Estructura carpetas:**
```
mi_detector/
├── backend/
│   ├── main.py                 # FastAPI app - punto de entrada
│   ├── detector.py             # Clase YOLOv8Detector (carga modelo, infiere)
│   ├── database.py             # Funciones SQLite (guardar/borrar alertas)
│   ├── alerts.py               # Lógica de detección de amenaza
│   ├── whatsapp_service.py     # Envío de alertas (webhook local o simulado)
│   ├── requirements.txt        # Dependencies (fastapi, yolov8, opencv, etc)
│   └── config.py               # Variables de configuración (puertos, rutas, umbrales)
├── models/
│   └── best.pt                 # Modelo YOLOv8 fine-tuned guardado aquí
├── data/
│   ├── alertas.db             # Base de datos SQLite local
│   ├── frames/                # Frames capturados (borrar cada 24h)
│   └── logs/                  # Logs de ejecución
├── frontend/
│   ├── index.html             # Dashboard web (tabla de alertas + mapa)
│   ├── style.css              # Estilos
│   └── app.js                 # JavaScript (WebSocket, refresh en tiempo real)
├── mobile_app/
│   ├── capture.html           # Página que abre en celular para capturar video
│   ├── camera.js              # Acceso a cámara del celular
│   └── stream.js              # Envía frames a FastAPI cada 200ms
├── scripts/
│   ├── download_dataset.sh    # Descarga UCF-Crime dataset
│   ├── train_model.py         # Fine-tuning YOLOv8
│   ├── simulate_camera.py     # Simula video para testing (sin celular)
│   └── generate_test_video.py # Crea video de prueba con amenaza simulada
└── docker-compose.yml         # (Opcional) Para empaquetar todo
```

### 2. BASE DE DATOS (SQLite en laptop)

**Archivo: data/alertas.db**

**Tabla: incidents**
```
{
  id: UUID único
  timestamp: cuándo se detectó (ISO format)
  threat_type: "arma" | "pelea" | "aglomeración" | "persona_caída"
  confidence: 0.0 - 1.0 (confianza del modelo)
  location: {
    latitude: de la cámara
    longitude: de la cámara
    camera_name: "Cámara 1" o lo que sea
  }
  frame_id: referencia a frame capturado (si existe)
  status: "pending" | "confirmed_real" | "false_alarm"
  confirmed_by: nombre del policía que confirmó
  confirmed_at: timestamp de confirmación
  notes: notas adicionales
  created_at: cuándo se creó el registro
  expires_at: cuándo se borra automáticamente (created_at + 24h)
}
```

**Tabla: detections_log** (para métricas)
```
{
  id: UUID
  timestamp: cuándo
  frames_processed: cuántos frames procesados en último minuto
  avg_latency_ms: latencia promedio de inferencia
  false_positives: cuántos falsos positivos en último minuto
  true_positives: cuántos reales
  memory_usage_mb: uso RAM
  gpu_utilization: % GPU (si tienes)
}
```

**Operaciones:**
- INSERT: cuando hay nueva alerta
- UPDATE: cuando policía confirma o rechaza
- DELETE: automáticamente después de 24h (cron job o scheduler)
- SELECT: para dashboard, para analytics

**Importante:** NO guardas rostros. NO guardas video completo. Solo:
- Timestamp
- Tipo de amenaza
- Bounding box (NO el frame)
- Confianza

### 3. MODELO YOLOv8 (Entrenado antes del hackathon)

**Dónde vive: models/best.pt**

**Qué detecta (clases de objeto):**
1. `weapon` - pistola, cuchillo, objeto contundente
2. `fight` - dos personas con movimiento agresivo
3. `crowd_suspicious` - aglomeración >5 personas, movimiento errático
4. `person_fallen` - persona en el piso (posible víctima)
5. `vandalism` - rotura de vidrio, destrucción
6. `person_aggressive` - postura de riesgo (brazo levantado, etc)

**Especificaciones del modelo:**
- Arquitectura: YOLOv8-Medium (buen balance speed/accuracy)
  - Alternativa si es lenta: YOLOv8-Small
  - Alternativa si tienes tiempo: YOLOv8-Large
- Entrada: imágenes 640x640 pixels
- Salida: bounding boxes + clase + confianza
- Formato guardado: .pt (PyTorch format de Ultralytics)
- Umbral mínimo de confianza: 85% (para evitar falsos positivos)

**Cómo se entrena (ANTES del hackathon, viernes noche):**
- Datos: UCF-Crime dataset (abierto, público)
  - 1,900+ videos de vigilancia
  - Pre-anotados con incidentes
  - Convertir a frames .jpg + .txt (YOLO format)
- Fine-tuning: Mistral lleva epochs, hyperparams, augmentation
- Validación: mAP50 ≥ 80% es "bueno"
- Exportar: a TensorFlow Lite para RPi4 (opcional, para hacerlo escalable)

**Durante demo:**
- Cargas el modelo AL INICIO del backend (toma ~5 segundos)
- Lo guardas en memoria
- Cada frame que llega: lo pasas por el modelo (< 100ms)
- Retornas detecciones

### 4. FRONTEND WEB (Dashboard en laptop)

**Acceso: http://localhost:8000/dashboard** (desde el navegador)

**Lo que ves:**
1. **Mapa** (top izquierda)
   - Pin de ubicación de la cámara
   - Historial de alertas como pins coloreados (rojo=amenaza real, gris=falso)
   - Usa Leaflet.js (librería open-source)
   - Coordenadas hardcodeadas (ej: latitud/longitud de Guadalajara centro)

2. **Tabla de alertas** (top derecha)
   - Columnas: Hora | Tipo | Confianza | Estado | Acciones
   - Filas con último incidente arriba
   - Color de fondo según estado (rojo=real, amarillo=pendiente, gris=falso)
   - Botones: "Confirmar real" | "Marcar falso" | "Ver frame"

3. **Métricas en tiempo real** (bottom)
   - FPS procesado
   - Latencia promedio
   - Falsos positivos últimas 8h
   - Sesgo de género (% diferencia en detección M vs H)
   - Sesgo de etnia (% diferencia por tono de piel, si aplica)

4. **WebSocket conectado**
   - Dashboard se actualiza en tiempo real cuando llegan nuevas alertas
   - No necesitas recargar la página

**Stack:**
- Frontend: HTML5 + Vanilla JavaScript (sin React, para mantenerlo simple)
- Gráficos: Chart.js (simple) o Plotly.js (más fancy)
- Mapas: Leaflet.js + OpenStreetMap (ambos open-source)
- Estilos: CSS3 grid + flexbox (responsive design)
- Comunicación: Fetch API para GET/POST + WebSocket para updates en vivo

### 5. MOBILE APP (En tu celular)

**Acceso: http://192.168.1.XXX:8000/capture** (desde Chrome/Safari del celular)

**Lo que hace:**
1. Solicita permiso para acceder a la cámara del celular
2. Abre la cámara trasera
3. Cada 200ms (5 fps):
   - Captura frame actual
   - Convierte a JPEG de 320x240 (bajo ancho de banda)
   - Envía a laptop: `POST http://192.168.1.XXX:8000/api/detect`
   - Recibe respuesta: `{ detected: true/false, threat_type: "...", confidence: 0.92 }`
4. Si `detected: true`:
   - Muestra overlay rojo en pantalla celular
   - Reproduces sonido de alerta (beep)
5. Botones:
   - "Ver alertas" → redirige a dashboard
   - "Parar captura" → detiene video

**Stack:**
- HTML5 `<video>` y `<canvas>` API (captura local)
- getUserMedia() (acceso a cámara)
- Fetch API (envío de frames)
- Service Worker (opcional, para funcionar offline si hace falta)

**Importante:**
- Frames se capturan y SE DESCARTAN después de procesar
- NO se guardan en celular
- NO viajan a internet, solo a laptop local

### 6. LÓGICA DE DETECCIÓN (alerts.py)

**Input:** Resultado de YOLOv8 (lista de detecciones con clase + confianza)

**Lógica:**
```
FOR cada detección en frame:
  IF confianza < 60%:
    → IGNORAR (ruido)
  ELSE IF confianza 60-85%:
    → ALERTA MODERADA (requiere confirmación manual)
  ELSE IF confianza >= 85%:
    → ALERTA ALTA (envía a policía automáticamente)

IF ALERTA ALTA:
  → Anónima frame (blur rostros automático con método simple)
  → Guarda en DB con timestamp
  → Envía WhatsApp/SMS a policía
  → Emite WebSocket a dashboard
  → LOG en archivo

IF 5+ alertas en 30 segundos de MISMA cámara:
  → Posible ataque prolongado
  → URGENTE (buzzer más fuerte, SMS + WhatsApp)
```

**Validaciones:**
- ¿Es realmente un frame válido? (verificar dimensiones)
- ¿No es un duplicado de alerta previa (< 10 segundos)?
- ¿Confianza consistente? (si varía mucho, espera más frames)

### 7. INTEGRACIÓN WhatsApp/SMS (whatsapp_service.py)

**Para la DEMO, tienes 3 opciones:**

**Opción A (REAL, pero requiere setup):**
- Usar Twilio API (cuesta dinero, pero funciona real)
- Setup: token API + número de teléfono
- Envía SMS/WhatsApp verdadero a tu teléfono
- Ventaja: demostración real
- Desventaja: costo, requiere internet (lo cual viola privacidad local)

**Opción B (SIMULADO LOCAL, recomendado para hackathon):**
- NO envía SMS/WhatsApp real
- Cuando hay alerta: escribe en archivo `alerts_queue.txt` o BD
- Muestras el contenido en dashboard como "Alerta enviada a 555-0123"
- Un Log en la terminal: `[ALERT SENT] Threat: fight, Confidence: 0.92, Phone: +1234567890`
- Ventaja: 100% local, privacidad total, fácil de debuggear
- Los jueces lo entienden: es hackathon, simulación es válida

**Opción C (WEBSOCKET LOCAL):**
- Cuando alerta: emites evento WebSocket
- Dashboard lo recibe Y lo muestra como notificación
- Simulas "teléfono policía" como segundo navegador viendo otro dashboard
- Ventaja: visual, interactivo, totalmente local

**Recomendación:** Usa Opción B + Opción C. Simulado es perfecto para demo.

**Estructura del mensaje (si fuera real):**
```
ALERTA DE SEGURIDAD COMUNITARIA

Tipo: Detección de pelea
Confianza: 92%
Ubicación: Centro comunitario San Juan
Hora: 2026-05-16 14:23:45

Acciones recomendadas:
- Ir al lugar inmediatamente
- Solicitar refuerzos si es necesario
- Confirmar si es verdadera alerta

Dashboard: http://192.168.1.100:8000/dashboard
```

### 8. MANEJO DE PRIVACIDAD (privacy.py)

**Qué se GUARDA:**
- Timestamp de alerta
- Tipo de amenaza (texto: "pelea", no imagen)
- Confianza (número: 0.92)
- Bounding box anónimo (solo coordenadas x,y,w,h, NO el contenido)
- Confirmación humana (policía dijo sí/no)

**Qué NO se guarda:**
- Rostros (blur automático o NO guardar frame)
- Video completo
- Audio
- Movimiento de personas individuales
- Características biométricas

**Retención:**
- Alertas: 24 horas (después se borran automáticamente)
- Logs técnicos: 7 días (para debugging)
- Dashboard histórico: 90 días (por ley, pero solo casos confirmados reales)

**Función: anonymize_frame()**
- INPUT: frame JPEG raw
- Detecta rostros con algoritmo simple (MediaPipe Face Detection)
- Dibuja rectángulo BLUR sobre cada rostro
- OUTPUT: frame JPEG con rostros desenfocados
- Este frame es el que SE GUARDA (si lo guardas)

### 9. CONFIGURACIÓN (config.py)

Variables que puedes cambiar sin tocar código:

```
# Modelo
MODEL_PATH = "models/best.pt"
MODEL_INPUT_SIZE = 640
CONFIDENCE_THRESHOLD = 0.85  # 85%

# Servidor
HOST = "0.0.0.0"  # Escucha en todas las IPs locales
PORT = 8000
DEBUG = True  # Para desarrollo

# BD
DB_PATH = "data/alertas.db"
ALERT_RETENTION_HOURS = 24
LOG_RETENTION_DAYS = 7

# Alertas
ALERT_DEBOUNCE_MS = 5000  # No enviar dos alertas en < 5s mismo tipo
ESCALATION_THRESHOLD = 5  # Si 5+ alertas en 30s → URGENTE

# Privacidad
BLUR_FACES = True
SAVE_FRAMES = False  # Si True, guarda frames con rostros blurreados
MAX_FRAME_SIZE_MB = 100

# WhatsApp (simulado)
WHATSAPP_ENABLED = False  # True si integras Twilio
TWILIO_ACCOUNT_SID = "..."
TWILIO_AUTH_TOKEN = "..."
POLICE_PHONE = "+34..."
```

---

## 🎬 FLUJO DE EJECUCIÓN PASO A PASO (DURANTE LA DEMO)

### Antes de la demo (Setup):

1. **Enciendes la laptop**
2. **Terminal 1:** Inicias el backend
   ```bash
   cd mi_detector/backend
   python main.py
   → [INFO] Cargando modelo... (5 segundos)
   → [INFO] FastAPI escuchando en 0.0.0.0:8000
   ```
   Puedes ver en terminal los logs en tiempo real

3. **Terminal 2 (opcional):** Inicia un script que simula la cámara
   ```bash
   python scripts/simulate_camera.py
   → Lee video pre-grabado de incidente
   → Envía frames a FastAPI cada 100ms
   ```

4. **Navegador (laptop):** Abre dashboard
   ```
   http://localhost:8000/dashboard
   → Ves tabla vacía de alertas
   → Ves mapa con pin de la cámara
   ```

5. **Navegador (celular, OPCIONAL):** Abre captura en vivo
   ```
   http://192.168.1.100:8000/capture
   → Se activa cámara del celular
   → Empieza a enviar frames
   ```
   (O simplemente usas simulador en Terminal 2, es más controlado)

### Durante la demo (Jueces mirando):

**Minuto 0-1:**
- "Aquí ven la laptop. El servidor FastAPI está corriendo."
- Muestras terminal: `[INFO] Server ready, listening on 8000`

**Minuto 1-2:**
- "Ahora voy a simular una amenaza. Voy a reproducir un video de una pelea."
- Inicias script `simulate_camera.py`
- Terminal muestra:
  ```
  [FRAME 1] Processing...
  [FRAME 2] Processing...
  [FRAME 50] DETECTION! Type: fight, Confidence: 0.92
  [ALERT SENT] To database and WebSocket
  ```

**Minuto 2-3:**
- Muestras dashboard. Ve nueva alerta roja apareciendo en tabla:
  ```
  14:23:45 | Pelea | 92% | Pendiente | [Confirmar] [Marcar falso]
  ```
- "La IA detectó una pelea con 92% de confianza. Esto se registró en BD."
- Hace clic "Confirmar real"
  - Registro se pone verde
  - Timestamp de confirmación aparece
  - Dashboard muestra métrica actualizada

**Minuto 3-4:**
- Muestras código/arquitectura en presentación
- "Aquí está el modelo YOLOv8. Se ejecuta localmente en la CPU/GPU de la laptop."
- "Ningún dato va a Internet. Ningún rostro se guarda. 100% privado."

**Minuto 4-5:**
- Responde preguntas:
  - "¿Y si falla la IA?"
    → "Policía siempre confirma. Si es falso, marcamos falso y el modelo aprende."
  - "¿Qué pasa con los datos?"
    → "Se borran en 24 horas. Solo registramos el evento, no el video."
  - "¿Es vigilancia?"
    → "No. Es prevención. Solo alertamos de EVENTOS de riesgo, no de personas."

### Después de la demo:

- Dejas la demo corriendo en background (laptop + celular)
- Jueces pueden jugar con dashboard, simulador
- Pueden hacer preguntas técnicas
- Muestras la carpeta de código (GitHub link en presentación)

---

## 📊 MÉTRICAS QUE VAS A MEDIR Y MOSTRAR

### Métricas técnicas (en logs + dashboard):

1. **FPS procesado**
   - Cuántos frames por segundo procesa YOLOv8
   - Métrica: FPS ≥ 25 es "bueno" (para 30fps input)
   - Con GPU: ~30 FPS
   - Sin GPU: ~5-10 FPS (aceptable)

2. **Latencia de inferencia**
   - Cuánto tarda un frame en pasar por el modelo
   - Métrica: < 100ms es "excelente"
   - Con GPU: 30-50ms
   - Sin GPU: 100-200ms

3. **Tasa de falsos positivos**
   - Cuántas alertas que fueron "falso" en últimas 8 horas
   - Métrica: < 5% de las alertas
   - Si > 10%: ajusta umbral de confianza más alto

4. **Tasa de verdaderos positivos**
   - Cuántas alertas reales en últimas 8 horas
   - Métrica: reportadas por policía/experto
   - Para demo: simulas, dices "esperamos 95%+"

5. **Uso de memoria**
   - RAM consumida por FastAPI + YOLOv8
   - Métrica: < 4GB es "eficiente"
   - Normal: 2-3GB

6. **Sesgo de género**
   - ¿Detecta igual amenazas si es hombre vs mujer?
   - Métrica: diferencia < 3% es "sin sesgo"
   - Cómo mides: testea con videos de misma pelea, diferentes géneros

7. **Sesgo de etnia**
   - Similar al anterior
   - Métrica: diferencia < 3%

8. **Disponibilidad del sistema**
   - Durante cuánto tiempo estuvo activo / no tuvo crashes
   - Métrica: 99%+ (casi nunca se cae)
   - En demo: "Lleva 4 horas corriendo sin fallar"

### Métricas de impacto (para presentación):

- **Tiempo de respuesta:** Policía recibe alerta en < 2 segundos de que ocurrió el incidente
- **Cobertura:** 1 laptop + 1-3 cámaras cubre área de ~10,000 m² (una escuela mediana)
- **Costo por instalación:** < $2,000 USD (laptop + cámaras viejas + software libre)
- **Vidas potencialmente salvadas:** 1 por incidente previo (estimado teórico)

---

## 🎯 CONTENIDO ESPECÍFICO DE CADA ENDPOINT HTTP

Estos son los "puertos de entrada" que tu backend expone:

### **POST /api/detect**
- **Input:** JPEG frame (binary)
- **Output:** JSON `{ threat_type, confidence, threat_detected, detection_id }`
- **Latencia:** < 100ms
- **Uso:** Celular envía frame aquí cada 200ms
- **Error handling:** Si frame está corrupto, retorna 400 "Invalid image"

### **POST /api/alert/confirm**
- **Input:** JSON `{ alert_id, status, notes }`
- **Output:** JSON `{ success: true, updated_at }`
- **Uso:** Dashboard cuando policía confirma "esto fue real"
- **DB:** Actualiza tabla incidents, cambia status a "confirmed_real"

### **GET /api/alerts?limit=50&offset=0**
- **Input:** Query params (paginación)
- **Output:** JSON array de alertas últimas 24h
- **Uso:** Dashboard llena tabla
- **Caché:** Puede cachear 30 segundos

### **GET /dashboard**
- **Input:** None
- **Output:** HTML (la página web del dashboard)
- **Uso:** Abres en navegador

### **GET /capture**
- **Input:** None
- **Output:** HTML (página de captura de cámara)
- **Uso:** Abres en celular

### **WS /ws/alerts** (WebSocket)
- **Upgrade:** HTTP → WebSocket
- **Output:** Cada vez que hay nueva alerta, server emite JSON
- **Uso:** Dashboard se actualiza en tiempo real sin refresh
- **Ejemplo mensaje:**
  ```json
  {
    "event": "new_alert",
    "alert_id": "uuid-123",
    "threat_type": "fight",
    "confidence": 0.92,
    "timestamp": "2026-05-16T14:23:45Z"
  }
  ```

### **GET /api/metrics**
- **Input:** None
- **Output:** JSON con todas las métricas (FPS, latencia, falsos positivos, etc)
- **Uso:** Dashboard muestra en cards

### **GET /api/health**
- **Input:** None
- **Output:** JSON `{ status: "ok", uptime_seconds: 3600, model_loaded: true }`
- **Uso:** Verificar que server esté vivo

---

## 🚀 CÓMO VAS A ENTRENAR EL MODELO (Viernes noche)

### Paso 1: Obtener dataset

**Opción A (Recomendada):**
- Descarga UCF-Crime dataset (abierto)
- Link: http://crcv.ucf.edu/datasets/ucf_crime.php
- Tamaño: ~2GB (1,900 videos)
- Ya está anotado (tiene etiquetas)
- Script para descargar: `scripts/download_dataset.sh`

**Opción B (Rápida, si te falta tiempo):**
- Usa COCO dataset preformado
- La mayoría de modelos YOLOv8 vienen pre-entrenados en COCO
- Simplemente haces "fine-tuning rápido" (5-10 epochs)
- Menos customizado pero funciona

### Paso 2: Preparar datos en formato YOLO

- Extraer frames de videos
- Anotar bounding boxes + clases (si no viene anotado)
- Convertir a formato YOLO (`.txt` files con `class x_center y_center width height`)
- Dividir en train/val/test (80/10/10)

Herramientas: Roboflow (web, gratis) o CVAT (local, open-source)

### Paso 3: Fine-tuning

**Script: scripts/train_model.py**

```
Entrada:
  - Ruta a dataset (carpeta con images/ y labels/)
  - Hiperparámetros: epochs=50, batch=16, imgsz=640

Ejecución:
  - Carga YOLOv8-Medium pre-entrenado (en COCO)
  - Congela primeras capas (no las reentrenarás)
  - Descongelá últimas 3 capas (fine-tune)
  - Entrena 50 epochs (si tienes GPU: 2-3 horas; sin GPU: 8-10 horas)
  - Cada epoch: muestra train loss, val loss, mAP50

Salida:
  - Modelo guardado en models/best.pt (el mejor de los 50 epochs)
  - Weights en models/last.pt (el último epoch, en caso falle best)
  - Logs en runs/detect/train/

Validación:
  - Metrics al final: mAP50 ≥ 80% es bueno
  - Si mAP50 < 70%: re-entrena con más epochs o mejor dataset
```

### Paso 4: Exportar (opcional pero útil)

```
Exporta a múltiples formatos:
  - PyTorch (.pt) → para FastAPI en laptop
  - TFLite (.tflite) → para RPi4 (escalabilidad futura)
  - ONNX (.onnx) → para C++/otros lenguajes

Verifica que exporta sin errores
```

---

## 🎪 DEMOSTRACIÓN EN VIVO: GUIÓN EXACTO

### Setup (5 minutos antes):

1. Laptop lista, servidor running
2. Celular en WiFi local
3. Dashboard abierto en navegador (laptop)
4. Simulador de cámara listo (video pre-grabado)
5. Presentación PowerPoint en otra pestaña
6. Terminal visible (muestra logs)

### Guión para jueces (5 minutos exactos):

**[0:00-0:30]**
- "Buenos días. Esto es un Detector de Violencia Comunitaria."
- Señalas la laptop: "Toda la IA corre aquí, localmente."
- "¿Ven el dashboard? Vamos a simular una amenaza ahora."

**[0:30-1:00]**
- Inicias el simulador: `python simulate_camera.py`
- Ves en terminal: `[FRAME 1] Processing... [FRAME 2]...`
- "La cámara está capturando 30 frames por segundo."

**[1:00-2:00]**
- Video reproduciéndose (pelea simulada)
- De repente: `[FRAME 50] DETECTION! Type: fight, Confidence: 0.92`
- En dashboard: nueva fila roja en tabla
- "¡Detectó una pelea con 92% de confianza!"
- "Esto se registró en la BD local. Cero datos en internet."

**[2:00-3:00]**
- Haces clic en "Confirmar real"
- Registro se pone verde
- "Policía confirmó. El sistema aprendió que eso fue real."
- Muestras código en presentación: "YOLOv8, framework abierto, sin APIs externas."

**[3:00-4:00]**
- "Las diferencias claves: "
  - "✓ Privacidad: sin rostros grabados, solo eventos"
  - "✓ Local: funciona sin internet"
  - "✓ Humano en el loop: policía siempre decide"
  - "✓ Rápido: alerta en < 2 segundos"

**[4:00-5:00]**
- Responde 1-2 preguntas de jueces
- Muestra GitHub con código (si tienes)
- "Preguntas?"

---

## 📁 ÁRBOL DE CARPETAS FINAL (Lo que entregarás)

```
guadalahacks_2026_detector/
│
├── README.md                          # Cómo instalar, ejecutar, arquitectura
├── ETHICAL_GUIDELINES.md              # Principios de privacidad y no-vigilancia
├── TECHNICAL_SPEC.md                  # Este documento
│
├── backend/
│   ├── main.py                        # FastAPI app (punto de entrada)
│   ├── detector.py                    # Clase YOLOv8Detector
│   ├── database.py                    # SQLite operations
│   ├── alerts.py                      # Alert logic
│   ├── privacy.py                     # Face blur, frame anonymization
│   ├── whatsapp_service.py           # Alert dispatch (simulado)
│   ├── config.py                      # Configuration variables
│   ├── requirements.txt               # Dependencies list
│   └── utils.py                       # Helpers
│
├── frontend/
│   ├── index.html                     # Dashboard
│   ├── capture.html                   # Mobile camera capture page
│   ├── style.css                      # Styles
│   └── app.js                         # JavaScript (WebSocket, updates)
│
├── models/
│   ├── best.pt                        # YOLOv8 trained model (75MB)
│   └── model_info.txt                 # Model metrics, training info
│
├── data/
│   ├── alertas.db                     # SQLite DB (created at runtime)
│   ├── frames/                        # Temporary frames (auto-deleted)
│   └── logs/                          # Log files
│
├── scripts/
│   ├── download_dataset.sh            # Get UCF-Crime
│   ├── train_model.py                 # Fine-tune YOLOv8
│   ├── simulate_camera.py             # Simulate video for testing
│   ├── test_endpoints.py              # Test all API endpoints
│   └── generate_test_video.py         # Create fake incident video
│
├── presentation/
│   ├── slides.pptx                    # Presentación para jueces
│   ├── demo_notes.txt                 # Guión de presentación
│   └── architecture_diagram.png       # Imagen de arquitectura
│
├── docker-compose.yml                 # (Opcional) Para empaquetar
└── .gitignore                         # Exclude models/, data/, venv/
```

---

## ✅ CHECKLIST ANTES DE PRESENTAR

**Viernes noche (después de entrenar):**
- [ ] Modelo guardado en `models/best.pt`
- [ ] mAP50 ≥ 80% en validation set
- [ ] Archivo con métricas guardado

**Sábado mañana:**
- [ ] Backend inicia sin errores: `python main.py`
- [ ] Dashboard abre en localhost:8000/dashboard
- [ ] Simulador de cámara funciona: `python simulate_camera.py`
- [ ] Se generan alertas correctamente
- [ ] BD se crea y guarda datos

**Sábado tarde:**
- [ ] WebSocket actualiza dashboard en tiempo real
- [ ] Confirmar/rechazar alertas funciona
- [ ] Logs no tienen errores
- [ ] Memoria no crece indefinidamente (memory leak?)
- [ ] Latencia promedio < 150ms

**Domingo mañana (2h antes de presentar):**
- [ ] Laptop encendida, servidor corriendo
- [ ] Celular conectado a WiFi local
- [ ] Video de prueba listo (incidente simulado)
- [ ] Navegador con dashboard abierto
- [ ] Terminal visible (muestra logs)
- [ ] Presentación PowerPoint lista
- [ ] Respuestas a preguntas éticas memorizadas

**Durante presentación:**
- [ ] Demo corre sin crashes
- [ ] Se ven alertas aparecer en tiempo real
- [ ] Jueces entienden la arquitectura
- [ ] Respuestas sobre privacidad están claras

---

## 🎓 QUÉ APRENDES HACIENDO ESTO

- **Machine Learning en producción:** No solo entrenar, sino servir
- **Backend API:** FastAPI, WebSocket, BD local
- **Frontend:** HTML/JS/WebSocket (no necesitas React)
- **Infraestructura local:** Redes WiFi, comunicación dispositivos
- **Privacidad/Ética en IA:** Realmente importante
- **Demo técnico:** Presentar sin que explote todo

---

## 🔥 VENTAJAS COMPETITIVAS (por qué ganas)

1. **Impacto real:** Otros hacen chatbots bonitos. Tú haces algo que salva vidas.
2. **Ética explícita:** No esquivas el debate sobre vigilancia; lo enfrentas.
3. **Técnicamente sofisticado:** YOLOv8 fine-tuning es difícil. Muestras que sabes.
4. **Offline:** Regla del hackathon cumplida. Funciona sin internet (ventaja en zonas de riesgo).
5. **Demo funcional:** No prometes, ejecutas.

---

## 🎬 AHORA QUÉ?

**LISTO.** Tienes la especificación completa. Ahora:

1. **Lee esto de nuevo** (5 minutos). Entiende cada sección.
2. **Haz un cronograma realista** (cuándo escribes qué código).
3. **Reúne tu equipo** (si tienes). Asigna roles.
4. **Viernes 17:00:** Empieza el setup.
5. **Domingo 10:00:** Presentas.

**Preguntas antes de empezar a codear:**
- ¿Tienes GPU? (NVIDIA cuda, AMD rocm, o Apple Metal)
- ¿Tienes acceso a un policía comunitario para validar?
- ¿Tienes una escuela/centro para instalar (idea futura)?
- ¿Tu laptop tiene 16GB RAM mín?
- ¿WiFi 5GHz en tu casa? (para demo)

Si respondés sí a 3+, estás listo.

**Buena suerte. Esto va a ser increíble.**

---

*Documento generado para Guadalahacks 2026 | Detector de Violencia Comunitaria | Edge AI + Privacidad*
