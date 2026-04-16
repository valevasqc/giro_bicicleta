"""Outbound LoRa: central -> station.

Mirror of station/lora_sender.py — same two modes:

- STUB_LORA=true: append each line to the shared stub file (STUB_LORA_OUTBOUND
  from central's POV == to_station.log). Station's receiver tails it.
- STUB_LORA=false: open a pyserial port and write to it.

Every message terminates with "\n" so the receiver can read line-by-line.
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
                print(f"[LORA STUB -> station] {line.rstrip()}")
            else:
                self._serial.write(line.encode("utf-8"))
                self._serial.flush()

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
