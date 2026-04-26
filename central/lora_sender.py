"""Outbound LoRa: central -> station.

Mirror of station/lora_sender.py — same two modes:

- STUB_LORA=true: append each line to the shared stub file (STUB_LORA_OUTBOUND
  from central's POV == to_station.log). Station's receiver tails it.
- STUB_LORA=false: open a pyserial port and write to it.

Every message terminates with "\n" so the receiver can read line-by-line.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import serial
except ImportError:
    serial = None


class LoRaSender:
    def __init__(
        self,
        stub: bool,
        stub_path: Path | None,
        serial_port: str | None,
        baud_rate: int | None,
    ):
        self._stub = stub
        self._lock = threading.Lock()
        self._serial = None

        if stub:
            if stub_path is None:
                raise ValueError("stub_path is required when stub=True")
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.touch(exist_ok=True)
            self._stub_path = stub_path
        else:
            if serial is None:
                raise RuntimeError("pyserial is not installed. Run: pip install pyserial")
            self._stub_path = None
            self._serial_port = serial_port
            self._baud_rate = baud_rate
            t = threading.Thread(target=self._connect_loop, daemon=True, name="lora-connect")
            t.start()

    def _connect_loop(self) -> None:
        while True:
            with self._lock:
                already_open = self._serial is not None and self._serial.is_open
            if already_open:
                time.sleep(1)
                continue
            try:
                ser = serial.Serial(
                    port=self._serial_port, baudrate=self._baud_rate, timeout=1
                )
                with self._lock:
                    self._serial = ser
                logger.info("[LORA] connected to %s", self._serial_port)
            except Exception as exc:
                logger.warning("[LORA] serial unavailable: %s — retrying in 5s", exc)
                time.sleep(5)

    @property
    def connected(self) -> bool:
        if self._stub:
            return True
        with self._lock:
            return self._serial is not None and self._serial.is_open

    @property
    def serial(self):
        """Expose the current Serial object so the receiver can share it."""
        return self._serial

    def send(self, message: str) -> None:
        """Send one pre-formatted LoRa message (no trailing newline required)."""
        line = message.rstrip("\n") + "\n"

        with self._lock:
            if self._stub:
                with self._stub_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                logger.debug("[LORA STUB -> station] %s", line.rstrip())
                return
            if self._serial is None or not self._serial.is_open:
                logger.warning("[LORA] no connection — dropping: %s", line.rstrip())
                return
            try:
                self._serial.write(line.encode("utf-8"))
                self._serial.flush()
            except Exception as exc:
                logger.warning("[LORA] send error: %s — will reconnect", exc)
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
