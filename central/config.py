import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "giro_bicicleta.db"
DATABASE_PATH = DB_PATH
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

# GPIO hardware configuration (Raspberry Pi kiosk).
# Set STUB_GPIO=False and supply BCM pin numbers in production.
STUB_GPIO = os.getenv("STUB_GPIO", "true").lower() not in ("0", "false", "no")
LOCK_PIN = int(os.getenv("LOCK_PIN")) if os.getenv("LOCK_PIN") else None
DOCK_PIN = int(os.getenv("DOCK_PIN")) if os.getenv("DOCK_PIN") else None
CHARGE_PIN = int(os.getenv("CHARGE_PIN")) if os.getenv("CHARGE_PIN") else None
# When True, GPIO HIGH energizes solenoid and unlocks the dock.
LOCK_UNLOCKS_WHEN_HIGH = os.getenv("LOCK_UNLOCKS_WHEN_HIGH", "true").lower() in ("1", "true", "yes")
UNLOCK_DURATION_SECONDS = float(os.getenv("UNLOCK_DURATION_SECONDS", "5"))

# Stub reed-switch defaults (laptop demo mode).
# DOCK = bike returned/present in dock, CHARGE = plug connected.
STUB_DOCK_OCCUPIED = os.getenv("STUB_DOCK_OCCUPIED", "true").lower() in ("1", "true", "yes")
STUB_CHARGE_CONNECTED = os.getenv("STUB_CHARGE_CONNECTED", "true").lower() in ("1", "true", "yes")

# Minimum wallet balance (GTQ) a customer must have for a RENTAL_REQUEST to
# be approved by the LoRa receiver.
MINIMUM_BALANCE_TO_RENT = float(os.getenv("MINIMUM_BALANCE_TO_RENT", "50.00"))

# Pricing (GTQ). Rate is per minute; unlock fee is charged at ride start.
PRICING_RATE_PER_MINUTE = float(os.getenv("PRICING_RATE_PER_MINUTE", "1.00"))
PRICING_UNLOCK_FEE = float(os.getenv("PRICING_UNLOCK_FEE", "0.00"))
MINIMUM_CHARGE = float(os.getenv("MINIMUM_CHARGE", "1.00"))

# --- LoRa ---------------------------------------------------------------
# STUB_LORA=true routes every LoRa I/O through two append-only files so
# central and station can round-trip messages on one laptop during dev.
# Naming below is from central's point of view — mirror of station/config.py.
STUB_LORA = os.getenv("STUB_LORA", "false").lower() in ("1", "true", "yes")

_default_stub_dir = BASE_DIR.parent / ".lora_stub"
STUB_LORA_DIR = Path(os.getenv("STUB_LORA_DIR", str(_default_stub_dir)))
# station -> central (station writes, central reads)
STUB_LORA_INBOUND = STUB_LORA_DIR / "to_central.log"
# central -> station (central writes, station reads)
STUB_LORA_OUTBOUND = STUB_LORA_DIR / "to_station.log"

# Real pyserial settings (ignored when STUB_LORA is true).
LORA_PORT = "/dev/cu.usbmodem101"
LORA_SERIAL_PORT = LORA_PORT
LORA_BAUD_RATE = int(os.getenv("LORA_BAUD_RATE", "9600"))

# Geofence — UFM main campus. Center of the presentation route, 400 m radius.
GEOFENCE_CENTER_LAT = float(os.getenv("GEOFENCE_CENTER_LAT", "14.6065"))
GEOFENCE_CENTER_LON = float(os.getenv("GEOFENCE_CENTER_LON", "-90.5054"))
GEOFENCE_RADIUS_M   = float(os.getenv("GEOFENCE_RADIUS_M", "400"))