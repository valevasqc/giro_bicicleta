"""Inbound LoRa: central -> station.

Runs as a daemon thread. Reads one line at a time, parses via
common.lora_protocol, and drops the result into station.state.INBOX for
the Flask handlers to pick up on the next /station/status poll.

Two modes mirror LoRaSender:

- STUB_LORA=true: tail an append-only file (STUB_LORA_INBOUND). Keeps a
  read offset so reloads don't re-consume old messages.
- STUB_LORA=false: read from a pyserial port with a short timeout.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

try:
    import serial
except ImportError:
    serial = None

try:
    from common.lora_protocol import parse_message
except ImportError:  # allow `python station/app.py` from inside station/
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.lora_protocol import parse_message

from . import state
from .config import STATION_ID


class LoRaReceiver(threading.Thread):
    def __init__(
        self,
        stub: bool,
        stub_path: Path | None,
        serial_port: str | None,
        baud_rate: int | None,
        poll_interval: float = 0.2,
        serial_obj=None,
    ):
        super().__init__(daemon=True, name="lora-receiver")
        self._stub = stub
        self._stub_path = stub_path
        self._serial_port = serial_port
        self._baud_rate = baud_rate
        self._poll_interval = poll_interval
        self._serial_obj = serial_obj  # pre-opened port shared with LoRaSender
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        if self._stub:
            self._run_stub()
        else:
            self._run_serial()

    # --- stub mode ------------------------------------------------------
    def _run_stub(self) -> None:
        self._stub_path.parent.mkdir(parents=True, exist_ok=True)
        self._stub_path.touch(exist_ok=True)

        # Start at EOF so we don't replay historical messages on restart.
        offset = self._stub_path.stat().st_size
        print(f"[LORA STUB] receiver tailing {self._stub_path} from offset {offset}")

        buffer = ""
        while not self._stop.is_set():
            try:
                with self._stub_path.open("r", encoding="utf-8") as fh:
                    fh.seek(offset)
                    chunk = fh.read()
                    offset = fh.tell()
            except FileNotFoundError:
                time.sleep(self._poll_interval)
                continue

            if not chunk:
                time.sleep(self._poll_interval)
                continue

            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self._handle_line(line)

    # --- serial mode ----------------------------------------------------
    def _run_serial(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install pyserial")

        print(f"[LORA RX] serial mode on {self._serial_port}, waiting for connection…")
        while not self._stop.is_set():
            # Get the sender's current serial each iteration so reconnects are transparent.
            ser = getattr(self._serial_obj, "serial", None) if self._serial_obj is not None else None
            if ser is None or not ser.is_open:
                time.sleep(0.5)
                continue

            try:
                raw = ser.readline()
            except Exception as exc:
                print(f"[LORA RX] serial read error: {exc}")
                time.sleep(self._poll_interval)
                continue

            if not raw:
                continue

            self._handle_line(raw.decode("utf-8", errors="replace"))

    # --- shared ---------------------------------------------------------
    def _handle_line(self, line: str) -> None:
        stripped = line.strip()
        # Silently skip ESP32 diagnostic lines (# debug, READY).
        # Keep TX result: visible — it only appears on TX failure in new firmware.
        if not stripped or stripped.startswith("#") or stripped.startswith("READY"):
            return
        print(f"[LORA RX DEBUG] handle_line: {stripped!r}")
        parsed = parse_message(line)
        if parsed is None:
            print(f"[LORA RX] dropped unparseable line: {line!r}")
            return

        msg_type, fields = parsed
        # Central broadcasts over LoRa; every station hears every packet.
        # Drop anything not addressed to us (first field is station_id).
        if not fields or fields[0] != STATION_ID:
            return
        print(f"[LORA <- central] {msg_type} {fields}")
        state.record_inbound(msg_type, fields)
