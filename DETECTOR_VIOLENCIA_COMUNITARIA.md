# Detector de Violencia Comunitaria - Edge AI
## Arquitectura Técnica + Marco Ético
### Guadalahacks 2026 | Guadalajara

---

## ⚠️ PRINCIPIO FUNDAMENTAL: PREVENCIÓN ≠ VIGILANCIA

### La Diferencia Crítica

| Aspecto | **VIGILANCIA** (❌ Evitar) | **PREVENCIÓN** (✅ Propósito) |
|--------|---|---|
| **Objetivo** | Monitoreo continuo de personas | Detección de incidentes de riesgo en tiempo real |
| **Almacenamiento** | Guarda toda la información por meses/años | Sin grabación permanente; solo alertas |
| **Privacidad** | Datos suben a servidores/nube | 100% local, datos nunca salen del dispositivo |
| **Control** | Una autoridad decide qué ver | Comunidad define qué se alerta (configuración local) |
| **Transparencia** | Secreto, usuarios no saben | Claro y consentido: "Esta cámara detecta amenazas" |
| **Acceso** | Pocas personas acceden a datos | Solo policía comunitaria + centro recibe alertas |
| **Ejemplo real** | China: reconocimiento facial de disidentes | Escuela: alerta local si detecta arma o agresión |

**Tu proyecto = PREVENCIÓN COMUNITARIA**, no vigilancia estatal. La clave es: **sin historial, sin registro de caras, solo alertas de incidentes.**

---

## 🏗️ ARQUITECTURA TÉCNICA

### 1. HARDWARE & INFRAESTRUCTURA

```
┌─────────────────────────────────────────────┐
│ CÁMARA IP / CELULAR                         │
│ (Hikvision, Dahua, o celular viejo usado)   │
│ → MJPEG stream a red local                   │
└─────────────┬───────────────────────────────┘
              │
              │ WiFi / Ethernet local
              │ (SIN internet externo)
              ↓
┌─────────────────────────────────────────────┐
│ LAPTOP / RASPBERRY PI 4+ (8GB RAM mín)      │
│ - YOLOv8 (TensorFlow Lite o ONNX)           │
│ - OpenCV para procesamiento de video        │
│ - Redis para caché local de alertas         │
│ - Base de datos local (SQLite o MongoDB)    │
└─────────────┬───────────────────────────────┘
              │
         ┌────┴────┐
         ↓         ↓
    ALERTA    REPORTE
    LOCAL     LOCAL
    WiFi      (PDF/JSON)
      │
      ↓
┌─────────────────────────────────────────────┐
│ TELÉFONO POLICÍA COMUNITARIA                │
│ (WhatsApp Business / API local)             │
│ Coordenadas GPS, foto capturada, timestamp  │
└─────────────────────────────────────────────┘
```

### 2. STACK TÉCNICO

```yaml
Backend (Laptop):
  - OS: Ubuntu 22.04 LTS
  - Runtime: Python 3.10+
  - Servidor: FastAPI (async, bajo latency)
  - Visión: YOLOv8 (ultralytics) + TensorFlow Lite
  - Video: OpenCV 4.8+
  - BD Local: SQLite (sin servidor)
  - Cola de tareas: Celery + Redis (alertas en tiempo real)
  - Logging: Prometheus + Grafana (opcional, para métricas)

Frontend (Celular + Dashboard):
  - App mobile: React Native / Flutter
  - Dashboard: React + Vite (para policía comunitaria)
  - Comunicación: WebSocket local + REST API

Infraestructura:
  - Red: WiFi 5GHz dedicada (sin acceso a internet público)
  - Almacenamiento: SSD local (1TB mín para búfer temporal)
  - Energía: UPS (batería 4+ horas post-apagón)
```

### 3. FLUJO DE DATOS (SIN NUBE)

```
[Cámara] 
   → MJPEG stream @ 30fps
   → [Laptop] YOLOv8 inference
   ┌─ Detección de objeto/comportamiento
   │  (toma <50ms por frame en RTX 3060)
   │
   ├─ SI confianza > umbral (85%+)
      └─ Genera alerta local
         ├─ Guarda frame capturado (temporal, 24h)
         ├─ Extrae bounding box (SIN cara identificable)
         ├─ Obtiene timestamp + coordenadas GPS
         ├─ Envía a policía por WhatsApp Business API local
         ├─ Registra en BD local (log de incidente)
         └─ Borra frame original después de 24h
   
   ├─ SI confianza 60-85%
      └─ Alerta de "riesgo moderado" (requiere confirmación manual)
   
   └─ SI confianza < 60%
      └─ Descarta (no genera alerta)
```

### 4. MODELO YOLOv8 - QUÉ DETECTAR

**Objetos:**
- Armas (pistola, cuchillo, objeto contundente)
- Personas en posición de riesgo (caída, inmóvil)
- Aglomeración sospechosa (>5 personas, movimientos agresivos)

**Eventos (usando pose estimation + motion):
- Pelea (dos personas, brazos elevados, contacto)
- Persecución (una persona corriendo, otra detrás)
- Ataque (persona sobre otra, movimientos rápidos)
- Acto vandálico (objeto lanzado, rotura de vidrio)

**NO detectar:**
- ❌ Rostros (anonimato)
- ❌ Patrones de movimiento de individuos específicos
- ❌ Característica de persona (ropa, tatuajes)

---

## 🎓 CÓMO ENTRENAR ÉTICAMENTE

### Paso 1: Obtener Dataset

**OPCIONES (todas públicas/éticas):**

1. **UCF-Crime Dataset** (Universidad de Florida)
   - 1,900+ videos de vigilancia reales
   - Anotado: peleas, robo, vandalismo, etc.
   - Licencia: investigación académica
   - Link: `http://crcv.ucf.edu/datasets/ucf_crime.php`

2. **Street View Imagery + Synthetic Data**
   - Descarga videos de YouTube (de incidentes públicos/noticias)
   - Usa SOLO si el canal permite reutilización educativa
   - Sintetiza videos con Blender (personas 3D, colisiones simuladas)

3. **Alcanza a policía comunitaria de tu delegación**
   - Pide 50-100 frames de cámaras municipales (datos anonymizados)
   - Asegúrate: solo objetos/eventos, NO caras
   - Acuerdo por escrito sobre uso educativo

4. **Contacta a Secretaría de Seguridad Jalisco**
   - Podrían facilitar footage histórico (abierto)
   - Para hackathon, mejor pedir dataset sintético

### Paso 2: Anotación Responsable

**Herramienta:** Roboflow o CVAT (open-source)

**QUÉ anotar:**
```
Frame 001:
  - Bounding box: "arma" (solo el objeto, NO la cara de quién la sostiene)
  - Label: "pistola | cuchillo | arma_contundente"
  - Confianza: 1.0 (si es claro) o 0.7 (si ambiguo)

Frame 015:
  - Bounding box: "pelea" (dos personas, sin rostro visible)
  - Label: "pelea" (dos BBOXes para dos personas)
  - Motion: "aggressive"

Frame 042:
  - Bounding box: "persona_caída"
  - Label: "posible_víctima" (requiere ayuda)
```

**NO anotar:**
```
❌ Identidad de personas
❌ Características faciales
❌ Ropa/tatuajes para identificación
❌ Comportamientos "normales" (caminar, hablar)
```

### Paso 3: Fine-tuning de YOLOv8

```python
# Pseudocódigo
from ultralytics import YOLO

# Carga modelo base (pre-entrenado en COCO)
model = YOLO('yolov8m.pt')  # 'medium' para balance speed/accuracy

# Fine-tune con tu dataset anotado
results = model.train(
    data='dataset.yaml',  # Ruta a dataset anotado
    epochs=50,
    imgsz=640,
    batch=16,  # Ajustar según GPU disponible
    device=0,  # GPU index
    patience=10,  # Early stopping
    conf=0.85,  # Umbral mínimo de confianza
    iou=0.6,
    augment=True,
)

# Validar
metrics = model.val()
print(f"mAP50: {metrics.box.map50}")

# Exportar a TensorFlow Lite (para Raspberry Pi)
model.export(format='tflite')
```

### Paso 4: Validación Ética (CRÍTICA)

**Haz esto DURANTE el hackathon:**

1. **Prueba con cámara real**
   - Monta la cámara en una escuela/centro comunitario
   - 100 frames grabados durante recreo/movimiento normal
   - **Resultado esperado:** <2% falsos positivos

2. **Test de sesgo**
   - ¿La IA detecta la misma "pelea" si los que pelean son diferentes etnias?
   - ¿Detecta objetos de riesgo igual en diferentes condiciones de luz?
   - Documenta los resultados

3. **Consulta con policía comunitaria**
   - Muéstrales 10 casos detectados
   - Pregunta: "¿Esto es una amenaza real o falsa alarma?"
   - Ajusta umbral de confianza si hay muchos falsos positivos

---

## 🔗 INTEGRACIÓN CON POLICÍA

### Modelo 1: WhatsApp Business API Local (RECOMENDADO)

```python
# FastAPI endpoint que detecta incidente
@app.post("/detect")
async def detect_incident(frame: Image):
    results = yolo_model(frame)
    
    if results.conf > 0.85 and is_threat(results):
        incident = {
            'timestamp': datetime.now().isoformat(),
            'threat_type': results.label,  # 'arma', 'pelea', 'aglomeración'
            'confidence': float(results.conf),
            'location': get_gps(),  # Coordenadas de la cámara
            'frame_anonymized': save_anonymized_frame(frame)  # Sin caras
        }
        
        # Envía a policía comunitaria vía WhatsApp Business
        send_whatsapp_alert(incident)
        
        # Guarda en BD local (para historial)
        db.incidents.insert_one(incident)
        
        return {"status": "alert_sent", "id": incident._id}
```

**Ventajas:**
- Policía ya usa WhatsApp (no necesita nueva app)
- Mensajes incluyen foto + timestamp + ubicación
- Confirmación de lectura automática
- Sin servidor externo

**Setup:**
```bash
# 1. Registra Business Account en WhatsApp
# 2. Obtén API key local
# 3. Configura número de policía

WHATSAPP_PHONE = "+34917123456"
WHATSAPP_TOKEN = "tu_token_local"
```

### Modelo 2: Dashboard Web Local (OPCIONAL)

Para que policía comunitaria vea mapa en tiempo real:

```html
<!-- Dashboard simple -->
<div id="map" style="height: 600px;"></div>
<div id="alerts">
  <h3>Alertas últimas 24h</h3>
  <table id="alert-table">
    <tr>
      <th>Hora</th>
      <th>Tipo</th>
      <th>Ubicación</th>
      <th>Foto</th>
      <th>Acción</th>
    </tr>
  </table>
</div>

<script>
// Conecta a WebSocket local
const ws = new WebSocket('ws://localhost:8000/alerts');
ws.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  // Añade pin al mapa, actualiza tabla
  addAlertToMap(alert);
};
</script>
```

### Modelo 3: Confirmación Manual (ESSENTIAL para evitar falsos positivos)

```python
@app.post("/confirm_alert/{alert_id}")
async def confirm_alert(alert_id: str, action: str):
    """
    action: 'confirmed' | 'false_alarm' | 'needs_backup'
    """
    alert = db.incidents.find_one({"_id": ObjectId(alert_id)})
    alert['human_confirmed'] = action
    alert['confirmed_by'] = request.user  # Policía que confirma
    alert['confirmed_at'] = datetime.now()
    db.incidents.update_one({"_id": alert._id}, {"$set": alert})
    
    if action == 'needs_backup':
        # Envía llamada de emergencia adicional
        send_emergency_call(alert['location'])
    
    return {"status": "recorded"}
```

---

## 🛡️ PRIVACIDAD & SEGURIDAD

### ✅ LO QUE GUARDAMOS (y por cuánto)

```yaml
Almacenamiento Local:
  - Frame capturado (baja resolución):
    - Duración: 24 horas
    - Propósito: Verificación de alerta
    - Procesamiento: Blur automático de rostros
  
  - Log de alerta (JSON):
    - Duración: 90 días (por requerimiento legal)
    - Campos: timestamp, tipo, ubicación, confianza, confirmación humana
    - Acceso: Solo policía comunitaria + administrador del sistema
  
  - Métricas de rendimiento:
    - Duración: 30 días
    - Campos: FPS, latencia, falsos positivos
```

### ❌ LO QUE NO GUARDAMOS

```
❌ Rostros o características faciales
❌ Identidad de personas
❌ Video continuo (solo frames de alertas)
❌ Datos en servidores externos
❌ Historial de movimientos individuales
```

### 🔐 PROTECCIONES TÉCNICAS

1. **Cifrado en reposo**
   ```bash
   # Cifra BD local
   sudo ecryptfs-setup-swap
   sudo mount -t ecryptfs /mnt/data /mnt/data
   ```

2. **Acceso restringido**
   ```yaml
   # Solo policía comunitaria puede ver alertas
   API:
     /alerts: [requiere JWT token]
     /confirm: [requiere policía]
     /admin: [requiere admin del sistema]
   ```

3. **Auditoría de acceso**
   ```python
   # Registra quién vio qué y cuándo
   @app.middleware("http")
   async def log_access(request: Request, call_next):
       user = request.user
       timestamp = datetime.now()
       response = await call_next(request)
       db.access_log.insert_one({
           'user': user,
           'endpoint': request.url,
           'timestamp': timestamp
       })
       return response
   ```

---

## 📋 PLAN DE IMPLEMENTACIÓN (48 HORAS)

### Viernes (Kick-off + Setup)

| Hora | Tarea |
|------|-------|
| 17:00 | Configurar laptop, instalar Docker, clonar repo YOLOv8 |
| 18:00 | Descargar dataset pre-anotado (UCF-Crime) |
| 19:00 | Empezar fine-tuning básico en GPU (dejar corriendo toda la noche) |
| 20:00 | Diseñar arquitectura de alertas + diagrama de flujo |
| 21:00 | Setup de cámara IP / simulador de video |

### Sábado (Desarrollo)

| Hora | Tarea |
|------|-------|
| 09:00 | Checkear modelo fine-tuned, evaluar métricas |
| 10:00 | Desarrollar servidor FastAPI (endpoint `/detect`) |
| 12:00 | Integración con WhatsApp Business API (pruebas) |
| 14:00 | Build dashboard web para policía (mapa + tabla alertas) |
| 16:00 | Tests de integración (cámara → modelo → alerta → teléfono) |
| 18:00 | Validación ética + test con policía comunitaria |
| 20:00 | Polish + documentación |

### Domingo (Demo + Presentación)

| Hora | Tarea |
|------|-------|
| 09:00 | Ensayo de demo completo |
| 10:00 | Presentación ante jueces |
| 11:00 | Preguntas + discusión sobre ética |

---

## 💬 RESPUESTAS A PREGUNTAS DE JUECES (PREPARADAS)

### **P: "¿No es esto vigilancia invasiva?"**

**R:** 
> No. Vigilancia es registrar actividad de personas inocentes para seguimiento a largo plazo (China, regímenes autoritarios). Nosotros:
> - **Solo alertamos sobre incidentes** (arma, pelea, emergencia médica)
> - **Sin grabación permanente**: boramos frames después de 24h
> - **Sin identificación de rostros**: solo detectamos el evento, no quién lo hace
> - **Consentimiento**: es instalado en centro comunitario, todos saben que hay cámara
> - **Control local**: solo policía comunitaria accede, no gobierno central
> 
> Es como un guardia de seguridad que camina vigilando, pero 24/7, sin fatiga, y sin prejuicios.

### **P: "¿Y si la IA comete error y acusa a inocentes?"**

**R:**
> Por eso tenemos **confirmación humana obligatoria**. La IA solo genera alerta; policía siempre decide si responder. Si es falso positivo:
> - Se registra en BD ("false_alarm")
> - Usamos eso para re-entrenar y mejorar
> - Responsabilidad sigue siendo humana, no de máquina

### **P: "¿Cómo garantizan que policía no lo abuse?"**

**R:**
> - **Sistema local**: policía no puede ver datos remotamente (necesita estar en la zona)
> - **Auditoría de acceso**: registramos quién vio qué y cuándo
> - **Protocolo claro**: alertas solo de incidentes de riesgo, no comportamientos normales
> - **Comité de supervisión**: idealmente, incluir a ONG de derechos humanos + comunidad
> - **Transparencia**: mostrar públicamente métricas de falsos positivos

### **P: "¿Qué pasa si cámara se daña o falla?"**

**R:**
> Sistema es **graceful degradation**:
> - Si cámara muere → alerta a admin, pero sistema sigue funcionando
> - Si GPU muere → cambia a CPU (más lento pero sigue)
> - Si red local cae → alertas se encolan localmente y se envían cuando red vuelve
> - **UPS en laptop**: 4+ horas de batería para alertas críticas

---

## 📊 MÉTRICAS DE ÉXITO (para demo)

```yaml
Accuracy:
  - True Positive Rate (detecta amenaza real): 85%+
  - False Positive Rate (falsa alarma): <5% por 8h
  - Falso Negativo Rate (se le escapa una amenaza): <2%

Velocidad:
  - Latencia de detección: <100ms desde captura
  - Tiempo de alerta a policía: <2s (WhatsApp enviado)

Ética:
  - Sesgo de género: <3% diferencia en detección
  - Sesgo de etnia: <3% diferencia en detección
  - Falsos positivos revisados por policía: 100%

Escalabilidad:
  - FPS procesado: 30fps @ 640p (en RTX 3060)
  - Múltiples cámaras: 2-3 simultáneas en una laptop
```

---

## 🎯 DIFERENCIADORES PARA JURADOS

### ¿Por qué tu proyecto gana en Guadalahacks?

1. **Impacto real**: Guadalajara sufre violencia actual. Esto es solución hoy.
2. **Ética explícita**: No huyes del debate sobre privacidad; lo enfrentas con diseño.
3. **Técnicamente ambicioso**: YOLOv8 fine-tuning offline es difícil; mostralo.
4. **Offline por diseño**: Cero dependencia de cloud (regla cumplida 100%).
5. **Integración humana**: No es "IA toma decisión"; es "IA alerta, humano decide."
6. **Replicable**: Una laptop, software libre, metodología abierta.

---

## 📚 RECURSOS TÉCNICOS

### Repositorios + Librerías

```bash
# YOLOv8
pip install ultralytics opencv-python

# Dataset anotado (pre-descargado)
wget http://crcv.ucf.edu/datasets/ucf_crime.zip

# FastAPI + async
pip install fastapi uvicorn pydantic

# WhatsApp Business
pip install twilio  # O alternativa local

# Visión local
pip install mediapipe pillow numpy

# BD local
pip install pymongo  # Si usas MongoDB
# O sqlalchemy + sqlite3 (built-in)
```

### Tutoriales

- YOLOv8 Fine-tuning: `https://docs.ultralytics.com/tasks/detect/`
- OpenCV Video Capture: `https://docs.opencv.org/4.8.0/`
- FastAPI Basics: `https://fastapi.tiangolo.com/`
- WhatsApp Business API Local: `https://developers.facebook.com/docs/whatsapp/`

---

## ⚖️ CONSIDERACIONES LEGALES (IMPORTANTE)

### En México (Jalisco)

1. **Ley de Protección de Datos Personales** (LFPDPP)
   - Debes obtener consentimiento para procesar imágenes
   - Cartel claro: "CÁMARA DE SEGURIDAD"
   - Acceso restringido a datos

2. **Responsabilidad civil**
   - Si IA comete error y causa daño, ¿quién es responsable?
   - Solución: contrato claro que policía comunitaria es responsable de actuar sobre alertas
   - Descargo: "Sistema es herramienta de apoyo, no decisión final"

3. **Autorización de policía**
   - Trabaja **con** policía comunitaria, no contra ella
   - Obtén autorización oficial para instalar cámara
   - Contrato de uso entre escuela/centro + policía + desarrolladores

### Texto recomendado en lugar visible:

```
-----------------------------------
AVISO DE VIGILANCIA
-----------------------------------
Esta zona está bajo vigilancia local
mediante sistema de detección de
incidentes de seguridad.

El sistema opera sin conexión a
servidores externos.

Los datos se retienen máximo 24 horas.

Acceso restringido a policía comunitaria
y autoridades locales.

Para información: contactar a [teléfono]
-----------------------------------
```

---

## 🚀 DEMO FINAL (5 MINUTOS)

```
[Juez viendo laptop]

Minuto 0-1:
  - Muestra cámara en vivo (escuela, cancha)
  - "El sistema corre todo localmente"

Minuto 1-2:
  - Simula incidente (video pre-grabado: dos personas peleando)
  - YOLOv8 detecta "pelea" en <100ms
  - "Confianza: 92%"

Minuto 2-3:
  - Alerta llega a teléfono de policía en <2s
  - WhatsApp con foto + ubicación + hora
  - "Policía confirma: SÍ es pelea real"

Minuto 3-4:
  - Dashboard web mostrando historial de alertas
  - Métricas: "Hoy: 3 alertas, 2 confirmadas reales, 1 falso"
  - "Sesgo de género: -0.8% (sin sesgo)"

Minuto 4-5:
  - "Diferencia clave: prevención, no vigilancia"
  - "100% privacidad: sin rostros grabados"
  - "Abierto: policía comunitaria controla, no estado"
```

---

## ✨ CONCLUSIÓN

El **Detector de Violencia Comunitaria** es:

✅ **Técnicamente sofisticado**: YOLOv8 fine-tuning, visión offline, integración tiempo real  
✅ **Éticamente defensible**: Prevención vs. vigilancia está claro en diseño  
✅ **Localmente impactante**: Guadalajara necesita esto; puedes demostrarlo  
✅ **Escalable**: Una laptop, 2-3 cámaras, costo <$2,000 por instalación  
✅ **Replicable**: Código abierto, metodología transferible a otras ciudades  

**El reto**: Ejecutar todo esto en 48h SIN comprometer ética.

**Tu ventaja**: La mayoría de competidores hacen un chatbot bonito. Tú estás salvando vidas.

---

**Hecho en Guadalahacks 2026 | Guadalajara, Jalisco**
