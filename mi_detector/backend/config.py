# Modelo
MODEL_PATH = "models/best.pt"
MODEL_INPUT_SIZE = 320
CONFIDENCE_THRESHOLD = 0.50
CLASSES = {"violence": 0, "fight": 1, "person": 2}

# Servidor
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# Base de datos
DB_PATH = "data/alertas.db"
ALERT_RETENTION_HOURS = 24

# Privacidad
BLUR_FACES = True
SAVE_FRAMES = False
MAX_FRAME_SIZE_MB = 100

# Alertas
ALERT_DEBOUNCE_MS = 5000
ESCALATION_THRESHOLD = 5  # Si 5+ alertas en 30s
