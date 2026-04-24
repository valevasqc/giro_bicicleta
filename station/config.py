import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Station identity (one value per Pi: "S1", "S2", ...).
STATION_ID = os.getenv("STATION_ID", "S1").strip() or "S1"

# Human-readable name shown on kiosk screens. Falls back to the ID so the
# Pi never has to query central just to render its own header.
STATION_NAME = os.getenv("STATION_NAME", STATION_ID)

# MVP: one bike per station, ID set by convention. Replace with live state
# once the station tracks docked bikes via GPIO + LoRa acknowledgements.
STATION_BIKE_ID = os.getenv("STATION_BIKE_ID", "B1")

# Flask session cookie signing key.
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-change-this-in-production")

# HTTP server exposed to the local Chromium kiosk browser only.
STATION_HTTP_HOST = os.getenv("STATION_HTTP_HOST", "127.0.0.1")
STATION_HTTP_PORT = int(os.getenv("STATION_HTTP_PORT", "8001"))

# --- GPIO ---------------------------------------------------------------
# STUB_GPIO=true runs on a laptop without RPi.GPIO installed.
STUB_GPIO = os.getenv("STUB_GPIO", "true").lower() not in ("0", "false", "no")
LOCK_PIN = int(os.getenv("LOCK_PIN")) if os.getenv("LOCK_PIN") else None
DOCK_PIN = int(os.getenv("DOCK_PIN")) if os.getenv("DOCK_PIN") else None
CHARGE_PIN = int(os.getenv("CHARGE_PIN")) if os.getenv("CHARGE_PIN") else None
LOCK_UNLOCKS_WHEN_HIGH = os.getenv("LOCK_UNLOCKS_WHEN_HIGH", "true").lower() in ("1", "true", "yes")
UNLOCK_DURATION_SECONDS = float(os.getenv("UNLOCK_DURATION_SECONDS", "5"))

# Reed-switch defaults used only by the GPIO stub.
STUB_DOCK_OCCUPIED = os.getenv("STUB_DOCK_OCCUPIED", "true").lower() in ("1", "true", "yes")
STUB_CHARGE_CONNECTED = os.getenv("STUB_CHARGE_CONNECTED", "true").lower() in ("1", "true", "yes")

# --- LoRa ---------------------------------------------------------------
# STUB_LORA=true replaces pyserial with two append-only files so central
# and station can round-trip messages on the same laptop during dev.
STUB_LORA = False

# Shared stub files. Central writes to OUTBOUND (station -> central side:
# it reads), and reads from INBOUND (central writes). Station does the
# mirror-image. Naming below is from the station's point of view.
_default_stub_dir = PROJECT_ROOT / ".lora_stub"
STUB_LORA_DIR = Path(os.getenv("STUB_LORA_DIR", str(_default_stub_dir)))
# station -> central (station writes, central reads)
STUB_LORA_OUTBOUND = STUB_LORA_DIR / "to_central.log"
# central -> station (central writes, station reads)
STUB_LORA_INBOUND = STUB_LORA_DIR / "to_station.log"

# Real pyserial settings (ignored when STUB_LORA is true).
LORA_PORT = "/dev/cu.usbmodem1101"
LORA_SERIAL_PORT = LORA_PORT
LORA_BAUD_RATE = int(os.getenv("LORA_BAUD_RATE", "9600"))

# --- Kiosk timing -------------------------------------------------------
# How long the kiosk UI waits for a LoRa reply before giving up and
# showing an error screen. Keeps "please wait" pages from spinning forever.
LORA_REPLY_TIMEOUT_SECONDS = float(os.getenv("LORA_REPLY_TIMEOUT_SECONDS", "20"))

# How often the station emits HEARTBEAT to central.
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "5"))

# Minimum balance (GTQ) required to start a rental — must match central/config.py.
MINIMUM_BALANCE_TO_RENT = float(os.getenv("MINIMUM_BALANCE_TO_RENT", "50.00"))
