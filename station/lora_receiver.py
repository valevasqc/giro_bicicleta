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
    from common.lora_protocol import parse_message, RENTAL_APPROVED
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.lora_protocol import parse_message, RENTAL_APPROVED

try:
    from . import lora_io
    from . import state
    from .config import STATION_ID, UNLOCK_DURATION_SECONDS
except ImportError:
    import lora_io
    import state
    from config import STATION_ID, UNLOCK_DURATION_SECONDS


class LoRaReceiver:
    def __init__(self, gpio=None, sender=None, **_kwargs):
        self._gpio = gpio
        self._sender = sender

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

        if msg_type == RENTAL_APPROVED:
            self._handle_rental_approved(fields)
        else:
            state.record_inbound(msg_type, fields)

    def _handle_rental_approved(self, fields) -> None:
        state.record_inbound(RENTAL_APPROVED, fields)

        pending = state.get_pending()
        if pending and pending.get("kind") == "login":
            # Kiosk flow: kiosk UI is waiting for this, it will handle the unlock.
            logger.info("[LORA] RENTAL_APPROVED → kiosk flow, deferring unlock to kiosk UI")
            return

        # Mobile flow: no kiosk session waiting — auto-unlock the dock now.
        logger.info("[LORA] RENTAL_APPROVED → mobile flow, auto-unlocking dock")
        if self._gpio is not None:
            self._gpio.unlock_for_seconds(UNLOCK_DURATION_SECONDS)
        state.set_dock_occupied(False)
