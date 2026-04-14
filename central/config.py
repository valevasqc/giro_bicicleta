import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "giro_bicicleta.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# Station frontend configuration
STATION_ID = os.getenv("STATION_ID", "S1").strip() or "S1"

# Station service credentials used by kiosk return/complete flow.
# Defaults match seeded users: station_s1 / station123, station_s2 / station123.
_default_service_username = f"station_{STATION_ID.lower()}"
STATION_SERVICE_USERNAME = os.getenv("STATION_SERVICE_USERNAME", _default_service_username).strip()
STATION_SERVICE_PASSWORD = os.getenv("STATION_SERVICE_PASSWORD", "station123")

# Session cookie signing key for Flask templates/routes.
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-change-this-in-production")

# Station heartbeat timeout: if too old, station is considered offline.
STATION_OFFLINE_AFTER_SECONDS = int(os.getenv("STATION_OFFLINE_AFTER_SECONDS", "30"))

# Shared secret used by tracker/receiver process for GPS ingestion endpoint.
TRACKER_API_KEY = os.getenv("TRACKER_API_KEY", "dev-tracker-key")

# Tracker bridge defaults (receiver laptop/base computer).
TRACKER_BACKEND_BASE_URL = os.getenv("TRACKER_BACKEND_BASE_URL", "http://127.0.0.1:8000")
TRACKER_SERIAL_PORT = os.getenv("TRACKER_SERIAL_PORT", "/dev/ttyUSB0")
TRACKER_BAUD_RATE = int(os.getenv("TRACKER_BAUD_RATE", "9600"))

# GPIO hardware configuration (Raspberry Pi kiosk).
# Set STUB_GPIO=False and supply BCM pin numbers in production.
STUB_GPIO = os.getenv("STUB_GPIO", "true").lower() not in ("0", "false", "no")
LOCK_PIN = int(os.getenv("LOCK_PIN")) if os.getenv("LOCK_PIN") else None
DOCK_PIN = int(os.getenv("DOCK_PIN")) if os.getenv("DOCK_PIN") else None
CHARGE_PIN = int(os.getenv("CHARGE_PIN")) if os.getenv("CHARGE_PIN") else None
UNLOCK_DURATION_SECONDS = float(os.getenv("UNLOCK_DURATION_SECONDS", "5"))

# Stub reed-switch defaults (laptop demo mode).
# DOCK = bike returned/present in dock, CHARGE = plug connected.
STUB_DOCK_OCCUPIED = os.getenv("STUB_DOCK_OCCUPIED", "true").lower() in ("1", "true", "yes")
STUB_CHARGE_CONNECTED = os.getenv("STUB_CHARGE_CONNECTED", "true").lower() in ("1", "true", "yes")