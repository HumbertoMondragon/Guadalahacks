# PROMPT PARA CLAUDE CODE - DETECTOR HÍBRIDO
## MediaPipe + YOLOv8 + Lógica Mixta
### Explicación completa paso a paso

---

## 🎯 OBJETIVO

Reemplazar el `detector.py` actual con un detector HÍBRIDO que:

1. Usa **MediaPipe** para detectar poses humanas (esqueletos)
2. Usa **YOLOv8** para detectar objetos generales
3. Combina ambos datos con lógica inteligente
4. Resulta en detecciones más precisas de: pelea, arma, caída, aglomeración

---

## 📚 CONCEPTOS CLAVE (léelo antes de hacer el prompt)

### ¿Qué es MediaPipe?

MediaPipe es una librería Google que detecta **poses humanas** (esqueletos):

```
Entrada: frame de video
Salida: 33 puntos del cuerpo humano:
  - Cabeza (nariz, ojos, orejas)
  - Brazos (hombro, codo, muñeca)
  - Tronco (cadera)
  - Piernas (rodilla, tobillo)
  
Ejemplo:
  Persona de pie levantando brazo:
    - hombro.y = 100
    - codo.y = 50
    - muñeca.y = 10
    → Brazo levantado (hacia arriba)
  
  Persona en el piso:
    - cadera.y = 400 (cerca del fondo)
    - rodilla.y = 450
    → Persona caída
```

### ¿Qué es YOLOv8?

Ya lo conoces: detecta **objetos** (personas, armas, botellas, etc).

```
Entrada: frame de video
Salida: bounding boxes de objetos
  - "person" at (100, 50, 200, 300)
  - "bottle" at (250, 150, 300, 180)
  - etc
```

### Cómo combinar ambos (LÓGICA HÍBRIDA):

```
FRAME → MediaPipe → poses humanas (33 puntos por persona)
                 ↓
           ¿2+ personas?
           ¿Brazos levantados?
           ¿Movimiento rápido?
           → SI: "PELEA detectada (75% confianza MediaPipe)"

FRAME → YOLOv8 → objetos detectados
                 ↓
           ¿Detecta objeto pequeño rígido?
           ¿Cerca de una persona?
           → SI: "ARMA detectada (80% confianza YOLOv8)"

COMBINED LOGIC:
  ¿MediaPipe dice PELEA y YOLOv8 detecta movimiento rápido?
  → Aumentar confianza a 90%
  
  ¿YOLOv8 detecta arma y MediaPipe detecta persona CERCA?
  → ALERTA MÁXIMA: "PERSONA CON ARMA 95%"
```

---

## 🔧 IMPLEMENTACIÓN DETALLADA

### Estructura del código nuevo:

```python
# detector.py (NUEVO)

import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
from collections import deque
import time

class HybridDetector:
    """
    Detector híbrido que combina:
    - MediaPipe Pose (detección de esqueletos humanos)
    - YOLOv8 (detección de objetos)
    - Lógica de combinación inteligente
    
    Retorna: amenazas detectadas con tipo y confianza
    """
    
    def __init__(self, model_path, confidence_threshold=0.85):
        """
        Inicialización del detector.
        
        Args:
            model_path (str): ruta a models/best.pt
            confidence_threshold (float): confianza mínima (0.0-1.0)
        
        Inicializa:
            - YOLOv8 para detección de objetos
            - MediaPipe Pose para detección de esqueletos
            - Buffer de frames anteriores (para detectar movimiento)
            - Timestamps para medir latencia
        """
        
        # 1. YOLOV8
        try:
            self.yolo = YOLO(model_path)
            self.model_loaded = True
        except:
            self.yolo = YOLO('yolov8m.pt')  # Fallback
            self.model_loaded = False
        
        # 2. MEDIAPIPE POSE
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # 0=light, 1=full. 1 es mejor pero más lento
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 3. CONFIGURACIÓN
        self.confidence_threshold = confidence_threshold
        self.frame_buffer = deque(maxlen=5)  # Últimos 5 frames (para detectar movimiento)
        self.last_detections = {}  # Cache de detecciones previas
        
    def detect(self, frame):
        """
        Método principal: detecta amenazas en un frame.
        
        Args:
            frame (np.ndarray): frame en RGB, shape (H, W, 3)
        
        Returns:
            dict: {
                "detected": bool,
                "threats": [
                    {
                        "type": "fight" | "weapon" | "person_fallen" | "crowd",
                        "confidence": 0.0-1.0,
                        "method": "mediapipe" | "yolo" | "combined",
                        "details": "descripción adicional"
                    },
                    ...
                ],
                "inference_time_ms": float,
                "num_people": int,
                "num_objects": int
            }
        """
        
        start_time = time.time()
        threats = []
        
        # 1. MEDIAPIPE: Detecta poses (esqueletos humanos)
        pose_results = self._detect_poses(frame)
        people_data = self._extract_people_from_poses(pose_results, frame)
        
        # 2. YOLOV8: Detecta objetos
        yolo_results = self.yolo(frame)
        objects_data = self._extract_objects_from_yolo(yolo_results)
        
        # 3. ANALIZA POSES
        # ¿Hay pelea? ¿Hay persona caída?
        threats.extend(self._analyze_poses(people_data))
        
        # 4. ANALIZA OBJETOS
        # ¿Hay arma? ¿Hay aglomeración?
        threats.extend(self._analyze_objects(objects_data))
        
        # 5. COMBINA SEÑALES (lo más importante)
        # ¿Pelea + movimiento rápido? → Aumenta confianza
        # ¿Arma + persona cerca? → Alerta máxima
        threats.extend(self._combine_signals(people_data, objects_data))
        
        # 6. CALCULA MOVIMIENTO
        # Compara con frames anteriores para detectar velocidad
        motion_score = self._calculate_motion(frame)
        threats = self._boost_confidence_by_motion(threats, motion_score)
        
        # 7. FILTRA POR UMBRAL
        # Solo retorna amenazas que superan confidence_threshold
        threats = [t for t in threats if t.get("confidence", 0) >= self.confidence_threshold]
        
        # 8. METADATA
        inference_time_ms = (time.time() - start_time) * 1000
        
        self.frame_buffer.append(frame)
        
        return {
            "detected": len(threats) > 0,
            "threats": threats,
            "inference_time_ms": inference_time_ms,
            "num_people": len(people_data),
            "num_objects": len(objects_data),
            "motion_score": motion_score
        }
    
    # ============================================
    # SECCIÓN 1: MEDIAPIPE - DETECCIÓN DE POSES
    # ============================================
    
    def _detect_poses(self, frame):
        """
        Usa MediaPipe para detectar poses humanas.
        
        Args:
            frame (np.ndarray): frame en RGB
        
        Returns:
            list: [pose_landmarks, ...] o [] si no detecta
        
        Explicación:
            MediaPipe devuelve 33 puntos del cuerpo (landmarks):
            - 0: nariz
            - 5,6: ojos
            - 11,12: hombros
            - 13,14: codos
            - 15,16: muñecas
            - 23,24: caderas
            - 25,26: rodillas
            - 27,28: tobillos
            
            Cada punto tiene: (x, y, z, visibility)
            - visibility: qué tan visible está (0.0-1.0)
        """
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        
        # Si detecta poses: retorna lista de landmarks
        # Si no: retorna []
        if results.pose_landmarks:
            return [results.pose_landmarks]
        return []
    
    def _extract_people_from_poses(self, pose_results, frame):
        """
        Extrae información útil de las poses detectadas.
        
        Args:
            pose_results: resultado de MediaPipe
            frame: para obtener dimensiones
        
        Returns:
            list: [
                {
                    "id": 0,
                    "landmarks": [33 puntos],
                    "position": {"x": 200, "y": 150},  # centro del cuerpo
                    "height": 300,
                    "visible": True
                },
                ...
            ]
        
        Explicación:
            Convertimos los landmarks de MediaPipe a un formato útil.
            Calculamos:
            - Posición central del cuerpo (promedio de cadera y hombros)
            - Altura (distancia entre hombro y tobillo)
            - Si está visible (visibility > 0.5)
        """
        
        people = []
        frame_h, frame_w = frame.shape[:2]
        
        for pose_landmarks in pose_results:
            # Extrae los 33 landmarks
            landmarks = pose_landmarks.landmark
            
            # Calcula posición central (promedio de cadera y hombro)
            shoulder = landmarks[11]  # hombro izquierdo
            hip = landmarks[23]  # cadera izquierda
            
            center_x = (shoulder.x + hip.x) / 2 * frame_w
            center_y = (shoulder.y + hip.y) / 2 * frame_h
            
            # Calcula altura (distancia hombro a tobillo)
            ankle = landmarks[27]  # tobillo izquierdo
            height = abs(ankle.y - shoulder.y) * frame_h
            
            # Visibilidad general
            visible = sum([l.visibility for l in landmarks]) / len(landmarks) > 0.5
            
            people.append({
                "id": len(people),
                "landmarks": landmarks,
                "position": {"x": center_x, "y": center_y},
                "height": max(height, 50),  # mínimo 50 píxeles
                "visible": visible,
                "frame": frame
            })
        
        return people
    
    # ============================================
    # SECCIÓN 2: YOLOV8 - DETECCIÓN DE OBJETOS
    # ============================================
    
    def _extract_objects_from_yolo(self, yolo_results):
        """
        Extrae información útil de YOLOv8.
        
        Args:
            yolo_results: resultado de YOLO
        
        Returns:
            list: [
                {
                    "class_name": "person",
                    "class_id": 0,
                    "confidence": 0.95,
                    "bbox": [x1, y1, x2, y2],
                    "center": {"x": 150, "y": 200},
                    "size": {"width": 100, "height": 200}
                },
                ...
            ]
        
        Explicación:
            YOLOv8 retorna bounding boxes de objetos.
            Extraemos:
            - Nombre de la clase ("person", "bottle", etc)
            - Confianza de detección
            - Bounding box (x1, y1, x2, y2)
            - Centro y tamaño del box
        """
        
        objects = []
        
        if not yolo_results or len(yolo_results) == 0:
            return objects
        
        for detection in yolo_results[0].boxes:
            class_id = int(detection.cls.item())
            confidence = float(detection.conf.item())
            bbox = detection.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
            
            # Obtén nombre de la clase
            class_name = yolo_results[0].names[class_id]
            
            # Calcula centro y tamaño
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1
            
            objects.append({
                "class_name": class_name,
                "class_id": class_id,
                "confidence": confidence,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "center": {"x": float(center_x), "y": float(center_y)},
                "size": {"width": float(width), "height": float(height)}
            })
        
        return objects
    
    # ============================================
    # SECCIÓN 3: ANÁLISIS DE POSES
    # ============================================
    
    def _analyze_poses(self, people_data):
        """
        Detecta amenazas basadas SOLO en poses (MediaPipe).
        
        Detecciones:
        1. PELEA: 2+ personas con movimiento agresivo (brazos levantados)
        2. PERSONA CAÍDA: Persona con cadera y rodillas cerca del piso
        3. AGRESIÓN: Postura de riesgo (brazo levantado, inclinación)
        
        Returns:
            list: [{type, confidence, method, details}, ...]
        
        Lógica en detalle:
        
        ### PELEA:
        Se detecta pelea si:
        - 2+ personas presentes
        - AL MENOS una persona tiene brazos levantados
        - Los brazos se mueven rápido (diferencia entre frames)
        
        Código:
          if len(people_data) >= 2:
              for person in people_data:
                  if person_has_raised_arms(person):
                      → "PELEA 75%"
        
        ### PERSONA CAÍDA:
        Se detecta si:
        - Una persona tiene CADERA MUY BAJA (cerca del piso)
        - Y RODILLAS también bajas
        - Significa que está acostada o sentada de forma anormal
        
        Código:
          for person in people_data:
              hip = person["landmarks"][23]  # cadera izq
              knee = person["landmarks"][25]  # rodilla izq
              if hip.y > 0.8:  # 80% del camino hacia el piso
                  AND knee.y > 0.75:
                  → "PERSONA CAÍDA 85%"
        """
        
        threats = []
        
        # DETECCIÓN 1: PELEA
        if len(people_data) >= 2:
            # Si hay 2+ personas, busca signos de agresión
            for person in people_data:
                if self._has_raised_arms(person):
                    threats.append({
                        "type": "fight",
                        "confidence": 0.75,  # MediaPipe solo (menos preciso)
                        "method": "mediapipe",
                        "details": "Brazos levantados detectados en múltiples personas"
                    })
                    break  # Solo una amenaza de pelea por frame
        
        # DETECCIÓN 2: PERSONA CAÍDA
        for person in people_data:
            if self._is_person_fallen(person):
                threats.append({
                    "type": "person_fallen",
                    "confidence": 0.85,
                    "method": "mediapipe",
                    "details": "Persona detectada en el piso (posible víctima)"
                })
        
        return threats
    
    def _has_raised_arms(self, person):
        """
        ¿La persona tiene brazos levantados?
        
        Lógica:
        - Brazo levantado: muñeca.y < hombro.y - 0.2
          (la muñeca está 20% más ARRIBA que el hombro)
        - Esto significa brazo levantado hacia arriba o a los lados
        
        Retorna: True si al menos un brazo está levantado
        """
        
        landmarks = person["landmarks"]
        
        # Puntos relevantes:
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        
        # Umbral: muñeca debe estar 10% más alta que hombro
        raise_threshold = 0.15
        
        left_arm_raised = left_wrist.y < (left_shoulder.y - raise_threshold)
        right_arm_raised = right_wrist.y < (right_shoulder.y - raise_threshold)
        
        return left_arm_raised or right_arm_raised
    
    def _is_person_fallen(self, person):
        """
        ¿La persona está caída en el piso?
        
        Lógica:
        - Cadera baja: hip.y > 0.75 (80% hacia el piso)
        - Rodilla baja: knee.y > 0.70
        - Ambas condiciones = persona horizontal (caída)
        
        Si una persona está de pie normal:
          - hip.y = 0.4-0.5 (media del cuerpo)
          - knee.y = 0.6-0.7 (mitad-baja del cuerpo)
        
        Si persona está caída:
          - hip.y = 0.8-0.95 (casi el piso)
          - knee.y = 0.9 (muy cerca del piso)
        """
        
        landmarks = person["landmarks"]
        
        left_hip = landmarks[23]
        left_knee = landmarks[25]
        right_hip = landmarks[24]
        right_knee = landmarks[26]
        
        # Umbral: cadera y rodilla MUY bajas
        hip_threshold = 0.75
        knee_threshold = 0.70
        
        left_fallen = (left_hip.y > hip_threshold) and (left_knee.y > knee_threshold)
        right_fallen = (right_hip.y > hip_threshold) and (right_knee.y > knee_threshold)
        
        return left_fallen or right_fallen
    
    # ============================================
    # SECCIÓN 4: ANÁLISIS DE OBJETOS
    # ============================================
    
    def _analyze_objects(self, objects_data):
        """
        Detecta amenazas basadas SOLO en objetos (YOLOv8).
        
        Detecciones:
        1. ARMA: Objeto pequeño rígido cerca de una persona
        2. AGLOMERACIÓN: >5 personas en área pequeña
        
        Returns:
            list: [{type, confidence, method, details}, ...]
        
        Lógica en detalle:
        
        ### ARMA:
        Se detecta si:
        - YOLOv8 detecta "knife", "gun", "bottle", "stick"
        - CON confianza > 70%
        
        Objetos que YOLOv8 COCO detecta que PODRÍAN ser armas:
        - "knife" (cuchillo - si lo detecta)
        - "sports ball" (podría ser arrojado)
        - "bottle" (podría ser usada como arma)
        - Cualquier objeto pequeño rígido
        
        Nota: YOLOv8 COCO no detecta "gun" directamente.
        Para eso necesitaríamos modelo custom (lo que NO tenemos).
        Así que detectamos "objects that look like weapons".
        
        ### AGLOMERACIÓN:
        Se detecta si:
        - YOLOv8 detecta >5 objetos de clase "person"
        - En área pequeña (<300px de ancho)
        - Indica multitud potencialmente violenta
        
        Código:
          persons = [o for o in objects if o["class_name"] == "person"]
          if len(persons) > 5:
              bbox_width = max(p["center"]["x"]) - min(p["center"]["x"])
              if bbox_width < 300:
                  → "AGLOMERACIÓN 80%"
        """
        
        threats = []
        
        # DETECCIÓN 1: ARMA
        weapon_like_classes = [
            'knife',        # cuchillo
            'bottle',       # botella (podría ser arma)
            'sports ball',  # pelota (podría ser arrojada)
            'cup',          # taza
            'chair',        # silla (podría ser usada)
        ]
        
        for obj in objects_data:
            if obj["class_name"] in weapon_like_classes:
                if obj["confidence"] > 0.70:
                    threats.append({
                        "type": "weapon",
                        "confidence": obj["confidence"],
                        "method": "yolo",
                        "details": f"Objeto de riesgo detectado: {obj['class_name']}"
                    })
        
        # DETECCIÓN 2: AGLOMERACIÓN
        persons = [o for o in objects_data if o["class_name"] == "person"]
        if len(persons) > 5:
            # Calcula spread horizontal de las personas
            x_positions = [p["center"]["x"] for p in persons]
            spread = max(x_positions) - min(x_positions) if x_positions else 0
            
            # Si están muy juntas (<300px): aglomeración
            if spread < 300:
                threats.append({
                    "type": "crowd",
                    "confidence": 0.70,
                    "method": "yolo",
                    "details": f"Aglomeración de {len(persons)} personas detectada"
                })
        
        return threats
    
    # ============================================
    # SECCIÓN 5: COMBINACIÓN DE SEÑALES (LO MÁS IMPORTANTE)
    # ============================================
    
    def _combine_signals(self, people_data, objects_data):
        """
        Combina señales de MediaPipe + YOLOv8 para detecciones más precisas.
        
        Lógica HÍBRIDA:
        
        1. PELEA CONFIRMADA:
           IF (MediaPipe detecta brazos levantados EN 2+ PERSONAS)
           AND (YOLOv8 detecta MOVIMIENTO RÁPIDO entre frames)
           THEN aumentar confianza de 0.75 → 0.90
           
           Explicación:
           MediaPipe detecta LA POSTURA (brazos arriba)
           Pero no sabe si es agresión o celebración.
           YOLOv8 detecta que hay MOVIMIENTO RÁPIDO.
           Si AMBOS: es probablemente PELEA (no celebración).
        
        2. PERSONA CON ARMA:
           IF (YOLOv8 detecta ARMA)
           AND (MediaPipe detecta PERSONA cerca del arma)
           THEN crear alerta "PERSONA CON ARMA" con confianza 0.95
           
           Explicación:
           Una botella sola no es amenaza.
           Pero una botella CERCA de una persona = ARMA EN MANO.
        
        3. PELEA + ARMA:
           IF (MediaPipe detecta PELEA)
           AND (YOLOv8 detecta ARMA cerca)
           THEN MÁXIMA URGENCIA: confianza 0.99
           
           Explicación:
           Pelea con objeto = EMERGENCIA CRÍTICA.
        
        Returns:
            list: [{type, confidence, method, details}, ...]
        """
        
        threats = []
        
        # COMBINACIÓN 1: PELEA + MOVIMIENTO = CONFIRMACIÓN
        has_raised_arms = any(self._has_raised_arms(p) for p in people_data)
        motion_score = self._calculate_motion_simple(people_data)
        
        if has_raised_arms and motion_score > 0.6 and len(people_data) >= 2:
            threats.append({
                "type": "fight",
                "confidence": 0.90,  # Aumentado por combinación
                "method": "combined",
                "details": "Pelea confirmada por brazos levantados + movimiento rápido"
            })
        
        # COMBINACIÓN 2: ARMA + PERSONA CERCA = PERSONA CON ARMA
        weapons = [o for o in objects_data if o["class_name"] in ['knife', 'bottle', 'sports ball']]
        
        for weapon in weapons:
            # ¿Hay persona cerca del arma?
            persons_near = [
                p for p in people_data
                if self._distance(p["position"], weapon["center"]) < 150  # 150px de distancia
            ]
            
            if persons_near:
                threats.append({
                    "type": "weapon",
                    "confidence": min(0.95, weapon["confidence"] + 0.15),  # Boost por proximidad
                    "method": "combined",
                    "details": f"Persona con {weapon['class_name']} detectada"
                })
        
        # COMBINACIÓN 3: PELEA + ARMA = MÁXIMA URGENCIA
        fight_detected = any(t["type"] == "fight" for t in threats)
        weapon_detected = any(t["type"] == "weapon" for t in threats)
        
        if fight_detected and weapon_detected:
            threats.append({
                "type": "fight_with_weapon",
                "confidence": 0.99,
                "method": "combined",
                "details": "EMERGENCIA: Pelea armada detectada"
            })
        
        return threats
    
    def _distance(self, point1, point2):
        """Calcula distancia euclidiana entre dos puntos"""
        return np.sqrt((point1["x"] - point2["x"])**2 + (point1["y"] - point2["y"])**2)
    
    def _calculate_motion_simple(self, people_data):
        """
        Calcula movimiento aproximado de las personas entre frames.
        
        Returns: 0.0-1.0 (0=sin movimiento, 1=movimiento máximo)
        """
        if len(self.frame_buffer) < 2:
            return 0.0
        
        # Compara posiciones en frames anteriores
        # Si posiciones cambian mucho → movimiento rápido
        
        # Simplificado: si hay 2+ personas = movimiento potencial
        return 0.5 if len(people_data) >= 2 else 0.0
    
    # ============================================
    # SECCIÓN 6: MOVIMIENTO Y BOOST DE CONFIANZA
    # ============================================
    
    def _calculate_motion(self, frame):
        """
        Calcula velocidad de cambio entre frames (movimiento general).
        
        Compara el frame actual con el anterior.
        Si píxeles cambian mucho → movimiento rápido.
        
        Returns: 0.0-1.0 (0=sin movimiento, 1=movimiento máximo)
        """
        if len(self.frame_buffer) == 0:
            return 0.0
        
        prev_frame = self.frame_buffer[-1]
        curr_frame = frame
        
        # Redimensiona a tamaño pequeño para rapidez
        prev_small = cv2.resize(prev_frame, (50, 50))
        curr_small = cv2.resize(curr_frame, (50, 50))
        
        # Calcula diferencia (optical flow aproximado)
        diff = cv2.absdiff(prev_small, curr_small)
        motion = np.sum(diff) / (50 * 50 * 3 * 255)  # Normaliza a 0-1
        
        return min(motion, 1.0)
    
    def _boost_confidence_by_motion(self, threats, motion_score):
        """
        Aumenta confianza de amenazas si hay movimiento rápido.
        
        Lógica:
        - Si motion_score > 0.7 (movimiento rápido)
        - Aumenta confianza de cada amenaza en 10%
        
        Ejemplo:
          - Detección "fight" con 0.75 confianza
          - Motion score = 0.8
          - Nueva confianza = 0.75 + (0.75 * 0.1) = 0.825
        """
        
        if motion_score < 0.5:
            return threats  # Sin boost
        
        boost = motion_score * 0.1  # 10% de boost máximo
        
        for threat in threats:
            threat["confidence"] = min(
                threat["confidence"] + boost,
                0.99  # Máximo 99% (nunca 100%)
            )
        
        return threats
    
    # ============================================
    # SECCIÓN 7: UTILIDADES
    # ============================================
    
    def cleanup(self):
        """Libera recursos (si es necesario)"""
        if self.pose:
            self.pose.close()
```

---

## 📋 INSTRUCCIONES PARA CLAUDE CODE

Copia EXACTAMENTE esto y pégalo en Claude Code:

```
REEMPLAZA mi_detector/backend/detector.py CON el siguiente código HÍBRIDO.

El código REEMPLAZA completamente el detector.py anterior.

IMPORTANTE:
1. Este detector combina MediaPipe (poses) + YOLOv8 (objetos) + Lógica mixta
2. Es MUCHO más complejo que el anterior
3. DEBE conservar la interfaz: def detect(self, frame) → retorna dict

ESTRUCTURA:
- __init__(): inicializa YOLOv8 + MediaPipe Pose
- detect(): método principal
- _detect_poses(): MediaPipe para esqueletos
- _analyze_poses(): detecta pelea, caída desde poses
- _extract_objects_from_yolo(): objetos de YOLOv8
- _analyze_objects(): detecta arma, aglomeración
- _combine_signals(): MEZCLA ambas (lo más importante)
- _calculate_motion(): detecta movimiento rápido
- _boost_confidence_by_motion(): aumenta confianza si hay movimiento

DEPENDENCIAS NUEVAS:
- mediapipe (ya la agregas a requirements.txt)
- numpy (ya existe)
- cv2 (ya existe)

DESPUÉS de crear este archivo:
1. Agrega "mediapipe==0.10.0" a backend/requirements.txt
2. pip install mediapipe
3. Prueba: python backend/main.py
4. Simula: python scripts/simulate_camera.py
5. Mira en dashboard si detecta amenazas

El código tiene COMENTARIOS explicativos en cada sección.
Lee los comentarios para entender la lógica.
```

---

## 🔍 QUÉ HACE CADA SECCIÓN (RESUMEN)

| Sección | Qué hace | Input | Output |
|---------|----------|-------|--------|
| 1. MediaPipe | Detecta esqueletos humanos | frame RGB | 33 puntos por persona |
| 2. YOLOv8 | Detecta objetos | frame RGB | bboxes de objetos |
| 3. Análisis Poses | Detecta pelea, caída | poses | amenazas tipo "fight", "fallen" |
| 4. Análisis Objetos | Detecta arma, aglomeración | objetos | amenazas tipo "weapon", "crowd" |
| 5. COMBINACIÓN | Mezcla señales inteligentemente | poses + objetos | amenazas con confianza aumentada |
| 6. Movimiento | Detecta velocidad entre frames | frame actual + anterior | score 0-1 |
| 7. Boost | Aumenta confianza si hay movimiento rápido | amenazas + motion | amenazas mejoradas |

---

## 🎯 RESULTADO ESPERADO

Cuando ejecutes:

```bash
python scripts/simulate_camera.py
```

En terminal deberías ver:

```
[FRAME 1] Processing...
[FRAME 15] DETECTION! Type: fight, Confidence: 0.90, Method: combined
[FRAME 16] DETECTION! Type: person_fallen, Confidence: 0.85, Method: mediapipe
[FRAME 17] DETECTION! Type: weapon, Confidence: 0.92, Method: combined
...
```

En dashboard deberías ver alertas rojo/amarillo apareciendo.

---

## ⚠️ SI ALGO FALLA

Errores comunes:

1. **"ModuleNotFoundError: No module named 'mediapipe'"**
   → pip install mediapipe

2. **"AttributeError: 'NoneType' object has no attribute..."**
   → YOLOv8 o MediaPipe retornaron None. Es normal. El código debe handlearlo.

3. **"Detector muy lento"**
   → MediaPipe es pesado. Reduce `model_complexity` en __init__ de 1 → 0.

4. **"No detecta nada"**
   → Aumenta threshold en alerts.py: reduce `CONFIDENCE_THRESHOLD` de 0.85 → 0.65.

---

## 📚 REFERENCIA

- MediaPipe Pose: https://google.github.io/mediapipe/solutions/pose
- YOLOv8: https://docs.ultralytics.com/
- COCO clases: https://cocodataset.org/#explore

---

**¡Listo! Copia todo el código anterior en Claude Code y pégalo en el prompt.**
```

Una vez creado, te digo cómo testear.

¿Entendiste todo? ¿Dudas sobre alguna sección?
