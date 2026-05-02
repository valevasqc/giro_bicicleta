"""In-memory kiosk state for the station Flask process.

The Pi has no SQLite; it is a stateless UI around central. This module is
just a pair of module-level dicts, guarded by a single lock. Anything that
survives a process restart must live on central.

Two things live here:

1. INBOX: the most recent central->station message per type. The LoRa
   receiver thread writes, Flask request handlers read. A single slot per
   type is enough because the kiosk flow is strictly one-at-a-time —
   only one user is ever interacting with a given kiosk.

2. PENDING: what the kiosk is currently waiting on. Set by the route that
   fires a LoRa send (e.g. RENTAL_REQUEST); cleared when the matching
   reply arrives (or times out). Routes use this to decide whether to
   show a "waiting" screen vs. the next step.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()

# {msg_type: {"fields": [...], "received_at": float}}
INBOX = {}

# {"kind": "login" | "rental" | "return", "started_at": float, "context": {...}}
PENDING = {}

# {"occupied": bool} when software knows the bike's dock state; {} means unknown → fall back to GPIO.
_DOCK_STATE: dict = {}


def record_inbound(msg_type: str, fields) -> None:
    """Called by the LoRa receiver thread when a message arrives from central."""
    with _lock:
        INBOX[msg_type] = {
            "fields": list(fields),
            "received_at": time.time(),
        }


def take_inbound(msg_type: str):
    """Pop the latest message of this type (returns None if nothing pending)."""
    with _lock:
        return INBOX.pop(msg_type, None)


def peek_inbound(msg_type: str):
    """Look at the latest message of this type without consuming it."""
    with _lock:
        entry = INBOX.get(msg_type)
        if entry is None:
            return None
        return dict(entry)


def set_pending(kind: str, context: dict | None = None) -> None:
    with _lock:
        PENDING.clear()
        PENDING.update({
            "kind": kind,
            "started_at": time.time(),
            "context": dict(context or {}),
        })


def get_pending():
    with _lock:
        if not PENDING:
            return None
        return dict(PENDING)


def clear_pending() -> None:
    with _lock:
        PENDING.clear()


def set_dock_occupied(val: bool | None) -> None:
    """Update the software dock state. None clears the override, restoring GPIO fallback."""
    with _lock:
        if val is None:
            _DOCK_STATE.clear()
        else:
            _DOCK_STATE["occupied"] = bool(val)


def get_dock_occupied() -> bool | None:
    """Return the software dock state, or None if unknown (caller should use GPIO)."""
    with _lock:
        return _DOCK_STATE.get("occupied", None)


def reset_all() -> None:
    """Useful for tests and for /station/reset diagnostic endpoints."""
    with _lock:
        INBOX.clear()
        PENDING.clear()
        # Intentionally does NOT clear _DOCK_STATE: dock presence persists
        # across logout so the idle screen reflects the correct bike count.
