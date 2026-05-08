"""Station Pi Flask entrypoint.

Run with: `python -m station.app` from the project root.

Owns the kiosk touchscreen UI (served to local Chromium) and a LoRa
receiver thread. No database, no HTTP to central — everything goes over
the LoRa sender attached at startup.
"""

import logging
import sys
from pathlib import Path

# Allow `python station/app.py` as well as `python -m station.app`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask

from station.config import (
    CHARGE_PIN,
    DOCK_PIN,
    HEARTBEAT_INTERVAL_SECONDS,
    LOCK_PIN,
    LOCK_UNLOCKS_WHEN_HIGH,
    LORA_BAUD_RATE,
    LORA_SERIAL_PORT,
    SECRET_KEY,
    STATION_HTTP_HOST,
    STATION_HTTP_PORT,
    STATION_ID,
    STUB_CHARGE_CONNECTED,
    STUB_DOCK_OCCUPIED,
    STUB_LOCK,
    STUB_SENSORS,
    STUB_LORA,
    STUB_LORA_INBOUND,
    STUB_LORA_OUTBOUND,
)
from station import lora_io
from station.gpio_driver import GPIODriver
from station.heartbeat import HeartbeatSender
from station.lora_receiver import LoRaReceiver
from station.lora_sender import LoRaSender
from station.logging_config import setup_logging
from station.routes.kiosk import bp as kiosk_bp

setup_logging()
logger = logging.getLogger(__name__)

# TODO add mock QR log in
def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = SECRET_KEY

    gpio = GPIODriver(
        stub_lock=STUB_LOCK,
        stub_sensors=STUB_SENSORS,
        lock_pin=LOCK_PIN,
        dock_pin=DOCK_PIN,
        charge_pin=CHARGE_PIN,
        lock_unlocks_when_high=LOCK_UNLOCKS_WHEN_HIGH,
        stub_dock_occupied=STUB_DOCK_OCCUPIED,
        stub_charge_connected=STUB_CHARGE_CONNECTED,
    )
    app.extensions["gpio"] = gpio

    # lora_io owns the single serial.Serial for this process.  Init first so
    # neither LoRaSender nor LoRaReceiver ever open the port themselves.
    lora_io.init(
        LORA_SERIAL_PORT,
        LORA_BAUD_RATE,
        stub=STUB_LORA,
        stub_in=STUB_LORA_INBOUND if STUB_LORA else None,
        stub_out=STUB_LORA_OUTBOUND if STUB_LORA else None,
    )

    sender = LoRaSender()
    app.extensions["lora_sender"] = sender

    receiver = LoRaReceiver(gpio=gpio, sender=sender)
    receiver.start()
    app.extensions["lora_receiver"] = receiver

    app.register_blueprint(kiosk_bp)

    heartbeat = HeartbeatSender(
        gpio=gpio,
        sender=sender,
        station_id=STATION_ID,
        interval_seconds=HEARTBEAT_INTERVAL_SECONDS,
    )
    heartbeat.start()
    app.extensions["heartbeat"] = heartbeat

    logger.info(
        "[STATION %s] Flask ready on http://%s:%s  (LoRa stub=%s, lock stub=%s, sensors stub=%s)",
        STATION_ID, STATION_HTTP_HOST, STATION_HTTP_PORT, STUB_LORA, STUB_LOCK, STUB_SENSORS,
    )

    return app


app = create_app()


if __name__ == "__main__":
    # use_reloader=False so the LoRa receiver thread isn't duplicated.
    app.run(
        host=STATION_HTTP_HOST,
        port=STATION_HTTP_PORT,
        debug=True,
        use_reloader=False,
    )
