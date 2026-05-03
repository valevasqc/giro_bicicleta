"""Single serial.Serial owner for the central process.

Call init() once at startup before any sender/receiver uses send() or
start_read_thread().  Module-level state guarantees exactly one open port
per process.

Stub mode (STUB_LORA=True):
  init()              — creates the stub files, no real serial.
  send()              — appends to stub_out and logs.
  start_read_thread() — tails stub_in for incoming lines.
  inject_line()       — enqueues a fake inbound line (for tests).
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import serial as _serial_mod
except ImportError:
    _serial_mod = None

# ---- module-level state (one per process) ---------------------------------
_stub: bool = False
_stub_in: Path | None = None
_stub_out: Path | None = None
_serial = None
_lock = threading.Lock()
_stop = threading.Event()
_inject: queue.SimpleQueue = queue.SimpleQueue()


def init(
    port: str | None,
    baud: int | None,
    *,
    stub: bool = False,
    stub_in: Path | None = None,
    stub_out: Path | None = None,
) -> None:
    """Open (or stub) the LoRa serial port.  Must be called once before
    start_read_thread() or send()."""
    global _stub, _stub_in, _stub_out
    _stub = stub
    _stub_in = stub_in
    _stub_out = stub_out
    _stop.clear()

    if stub:
        if stub_out is not None:
            stub_out.parent.mkdir(parents=True, exist_ok=True)
            stub_out.touch(exist_ok=True)
        if stub_in is not None:
            stub_in.parent.mkdir(parents=True, exist_ok=True)
            stub_in.touch(exist_ok=True)
        logger.info("[LORA IO] stub mode — in=%s out=%s", stub_in, stub_out)
        return

    if _serial_mod is None:
        raise RuntimeError("pyserial is not installed.  Run: pip install pyserial")

    threading.Thread(
        target=_connect_loop, args=(port, baud), daemon=True, name="lora-io-connect"
    ).start()


def _connect_loop(port: str, baud: int) -> None:
    global _serial
    while not _stop.is_set():
        with _lock:
            already_open = _serial is not None and _serial.is_open
        if already_open:
            time.sleep(1)
            continue
        try:
            ser = _serial_mod.Serial(port=port, baudrate=baud, timeout=1)
            with _lock:
                _serial = ser
            logger.info("[LORA IO] connected to %s", port)
        except Exception as exc:
            logger.warning("[LORA IO] serial unavailable: %s — retrying in 5s", exc)
            time.sleep(5)


def start_read_thread(handler: Callable[[str], None]) -> None:
    """Start a daemon thread that calls handler(line) for each non-empty,
    non-comment inbound line."""
    target = _read_stub if _stub else _read_serial
    threading.Thread(
        target=target, args=(handler,), daemon=True, name="lora-io-read"
    ).start()


def connected() -> bool:
    """Return True if the port is open (always True in stub mode)."""
    if _stub:
        return True
    with _lock:
        return _serial is not None and _serial.is_open


def send(message: str) -> bool:
    """Write one message.  Appends \\n if absent.  Thread-safe.  Returns True on success."""
    global _serial
    line = message if message.endswith("\n") else message + "\n"
    with _lock:
        if _stub:
            if _stub_out is not None:
                with _stub_out.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
            logger.debug("[LORA IO STUB ->] %s", line.rstrip())
            return True
        if _serial is None or not _serial.is_open:
            logger.warning("[LORA IO] no connection — dropping: %s", line.rstrip())
            return False
        try:
            _serial.write(line.encode("utf-8"))
            _serial.flush()
            return True
        except Exception as exc:
            logger.warning("[LORA IO] send error: %s — will reconnect", exc)
            try:
                _serial.close()
            except Exception:
                pass
            _serial = None
            return False


def inject_line(line: str) -> None:
    """Enqueue a fake inbound line; consumed by the read thread (test helper)."""
    _inject.put(line)


def stop() -> None:
    """Signal the read/connect threads to exit and close the port."""
    _stop.set()
    with _lock:
        if _serial is not None:
            try:
                _serial.close()
            except Exception:
                pass


# ---- internal read loops --------------------------------------------------

def _dispatch(raw: str, handler: Callable[[str], None]) -> None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return
    handler(line)


def _drain_inject(handler: Callable[[str], None]) -> None:
    while True:
        try:
            _dispatch(_inject.get_nowait(), handler)
        except queue.Empty:
            break


def _read_stub(handler: Callable[[str], None]) -> None:
    if _stub_in is None:
        logger.warning("[LORA IO] stub read started but no stub_in path configured")
        return
    _stub_in.parent.mkdir(parents=True, exist_ok=True)
    _stub_in.touch(exist_ok=True)
    offset = _stub_in.stat().st_size
    logger.info("[LORA IO] stub tailing %s from byte %d", _stub_in, offset)
    buf = ""
    while not _stop.is_set():
        _drain_inject(handler)
        try:
            with _stub_in.open("r", encoding="utf-8") as fh:
                fh.seek(offset)
                chunk = fh.read()
                offset = fh.tell()
        except FileNotFoundError:
            time.sleep(0.2)
            continue
        if not chunk:
            time.sleep(0.2)
            continue
        buf += chunk
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            _dispatch(line, handler)


def _read_serial(handler: Callable[[str], None]) -> None:
    logger.info("[LORA IO] serial read thread started")
    while not _stop.is_set():
        _drain_inject(handler)
        ser = _serial  # CPython atomic read; stale ref handled by exception
        if ser is None or not ser.is_open:
            time.sleep(0.5)
            continue
        try:
            raw = ser.readline()
        except Exception as exc:
            logger.warning("[LORA IO] read error: %s", exc)
            _reset()
            time.sleep(2)
            continue
        if not raw:
            continue
        _dispatch(raw.decode("utf-8", errors="replace"), handler)


def _reset() -> None:
    global _serial
    with _lock:
        if _serial is not None:
            try:
                _serial.close()
            except Exception:
                pass
            _serial = None
    logger.info("[LORA IO] port reset — reconnect loop will reopen")
