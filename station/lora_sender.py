"""Outbound LoRa: station -> central.

Two modes:

- STUB_LORA=true: append each line to a shared file (STUB_LORA_OUTBOUND).
  Central's receiver tails the same file. Lets you run both processes on
  the same laptop and round-trip messages without any radio.

- STUB_LORA=false: open a pyserial port and write to it.

Both modes terminate each message with "\n". The receiver (this process
or central) reads line-by-line.
"""

from __future__ import annotations

import threading
from pathlib import Path

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

        if stub:
            if stub_path is None:
                raise ValueError("stub_path is required when stub=True")
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.touch(exist_ok=True)
            self._stub_path = stub_path
            self._serial = None
        else:
            if serial is None:
                raise RuntimeError("pyserial is not installed. Run: pip install pyserial")
            self._stub_path = None
            self._serial = serial.Serial(port=serial_port, baudrate=baud_rate, timeout=1)

    def send(self, message: str) -> None:
        """Send one pre-formatted LoRa message (no trailing newline required)."""
        line = message.rstrip("\n") + "\n"

        with self._lock:
            if self._stub:
                with self._stub_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                print(f"[LORA STUB -> central] {line.rstrip()}")
            else:
                self._serial.write(line.encode("utf-8"))
                self._serial.flush()

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
