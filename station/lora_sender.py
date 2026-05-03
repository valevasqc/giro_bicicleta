"""Outbound LoRa: station -> central.

Thin wrapper around lora_io.send().  All serial/stub state is owned by
lora_io; this class exists so call-sites holding a LoRaSender reference
continue to work unchanged.  Call lora_io.init() before using this.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from . import lora_io
except ImportError:
    import lora_io


class LoRaSender:
    def send(self, message: str) -> bool:
        """Send one pre-formatted LoRa message.  Returns True on success."""
        return lora_io.send(message)

    @property
    def connected(self) -> bool:
        return lora_io.connected()
