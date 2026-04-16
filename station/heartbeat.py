"""Periodic HEARTBEAT emitter for the station Pi.

Background daemon thread that every HEARTBEAT_INTERVAL_SECONDS reads
the dock + charge reed switches via the GPIODriver and sends a
HEARTBEAT|<station_id>|<dock_occupied>|<charging_connected>|<ts>
LoRa message to central. Never raises out of .run(); GPIO or send
errors are logged and the loop continues on the next tick.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

try:
    from common.lora_protocol import HEARTBEAT, format_message
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.lora_protocol import HEARTBEAT, format_message


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class HeartbeatSender(threading.Thread):
    def __init__(self, gpio, sender, station_id: str, interval_seconds: float):
        super().__init__(daemon=True, name="station-heartbeat")
        self._gpio = gpio
        self._sender = sender
        self._station_id = station_id
        self._interval = interval_seconds
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        # Emit one immediately so central marks us online right after boot,
        # then settle into the periodic cadence.
        while True:
            self._tick()
            if self._stop.wait(self._interval):
                return

    def _tick(self) -> None:
        try:
            dock_occupied = 1 if self._gpio.read_dock_occupied() else 0
            charge_connected = 1 if self._gpio.read_charge_connected() else 0
            self._sender.send(format_message(
                HEARTBEAT,
                self._station_id,
                dock_occupied,
                charge_connected,
                _utc_iso(),
            ))
        except Exception as exc:
            print(f"[HEARTBEAT] tick failed: {exc!r}")
