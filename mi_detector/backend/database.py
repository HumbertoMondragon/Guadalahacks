import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any


class DatabaseManager:
    """Gestiona la base de datos SQLite local de incidentes."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection | None:
        """Abre conexión a SQLite; retorna None si falla."""
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None

    def init_db(self) -> bool:
        """Crea la tabla incidents si no existe."""
        conn = self._connect()
        if conn is None:
            return False
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    camera_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    confirmed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def create_alert(
        self, threat_type: str, confidence: float, camera_name: str
    ) -> str | None:
        """Registra una nueva alerta y retorna su id."""
        conn = self._connect()
        if conn is None:
            return None
        alert_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        try:
            conn.execute(
                """
                INSERT INTO incidents (
                    id, timestamp, threat_type, confidence,
                    camera_name, status, confirmed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?)
                """,
                (alert_id, now, threat_type, confidence, camera_name, now),
            )
            conn.commit()
            return alert_id
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def confirm_alert(self, alert_id: str, status: str) -> bool:
        """Actualiza el estado de una alerta (confirmed_real o false_alarm)."""
        conn = self._connect()
        if conn is None:
            return False
        now = datetime.utcnow().isoformat() + "Z"
        try:
            cursor = conn.execute(
                """
                UPDATE incidents
                SET status = ?, confirmed_at = ?
                WHERE id = ?
                """,
                (status, now, alert_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna alertas de las últimas N horas, más recientes primero."""
        conn = self._connect()
        if conn is None:
            return []
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        try:
            rows = conn.execute(
                """
                SELECT id, timestamp, threat_type, confidence, camera_name,
                       status, confirmed_at, created_at
                FROM incidents
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()
