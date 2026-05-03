"""Inbound LoRa dispatcher: central -> station.

Pure message-routing layer — serial/stub I/O is owned by lora_io.
Call start() once to register this object as the inbound handler;
lora_io launches a daemon thread that calls _handle_line() for every
non-empty, non-comment line arriving from the LoRa module.

Central broadcasts over LoRa; every station hears every packet.  Lines
not addressed to this station's STATION_ID are silently dropped.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from common.lora_protocol import parse_message
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.lora_protocol import parse_message

try:
    from . import lora_io
    from . import state
    from .config import STATION_ID
except ImportError:
    import lora_io
    import state
    from config import STATION_ID


class LoRaReceiver:
    def __init__(self, **_kwargs):
        # Accept and ignore any legacy keyword args (stub, stub_path, etc.)
        # so existing call-sites that pass them do not break.
        pass

    def start(self) -> None:
        """Register _handle_line with lora_io and start the read thread."""
        lora_io.start_read_thread(self._handle_line)

    def stop(self) -> None:
        lora_io.stop()

    # --- dispatch -------------------------------------------------------
    def _handle_line(self, line: str) -> None:
        # line arrives already stripped and non-empty from lora_io._dispatch
        if line.startswith("READY"):
            return
        logger.debug("[LORA RX] handle_line: %r", line)
        parsed = parse_message(line)
        if parsed is None:
            logger.warning("[LORA RX] dropped unparseable line: %r", line)
            return

        msg_type, fields = parsed
        # Drop packets not addressed to this station.
        if not fields or fields[0] != STATION_ID:
            return
        logger.info("[LORA <- central] %s %s", msg_type, fields)
        state.record_inbound(msg_type, fields)
