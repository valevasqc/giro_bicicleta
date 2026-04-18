"""Shared LoRa protocol helpers used by central and station.

Provides compatibility exports expected by existing receiver/sender code:
message type constants, format_message, parse_message, and parse_lora_message.
"""

from __future__ import annotations

FIELD_SEP = "|"

# Station -> Central
HEARTBEAT = "HEARTBEAT"
RENTAL_REQUEST = "RENTAL_REQUEST"
BIKE_RELEASED = "BIKE_RELEASED"
BIKE_DOCKED = "BIKE_DOCKED"
GPS = "GPS"

# Central -> Station
LOGIN_OK = "LOGIN_OK"
LOGIN_FAIL = "LOGIN_FAIL"
RENTAL_APPROVED = "RENTAL_APPROVED"
RENTAL_DENIED = "RENTAL_DENIED"
RETURN_COMPLETE = "RETURN_COMPLETE"

STATION_TO_CENTRAL = {HEARTBEAT, RENTAL_REQUEST, BIKE_RELEASED, BIKE_DOCKED, GPS}
CENTRAL_TO_STATION = {LOGIN_OK, LOGIN_FAIL, RENTAL_APPROVED, RENTAL_DENIED, RETURN_COMPLETE}
ALL_TYPES = STATION_TO_CENTRAL | CENTRAL_TO_STATION


def format_message(msg_type: str, *fields) -> str:
    """Build a pipe-delimited message line."""
    parts = [str(msg_type)]
    for field in fields:
        parts.append("" if field is None else str(field))
    return FIELD_SEP.join(parts)


def parse_message(line: str):
    """Parse a raw line into (msg_type, [fields]) or None."""
    if not line:
        return None

    cleaned = line.strip()
    if not cleaned:
        return None

    parts = cleaned.split(FIELD_SEP)
    msg_type = parts[0]
    if msg_type not in ALL_TYPES:
        return None

    return msg_type, parts[1:]


def parse_lora_message(raw: str) -> dict | None:
    """Parse one raw LoRa line into a normalized dict.

    Returns None for empty, malformed, or unsupported lines.
    """
    parts = raw.strip().split("|")
    if not parts or not parts[0]:
        return None
    t = parts[0]
    try:
        if t == "HEARTBEAT" and len(parts) == 5:
            return {"type": t, "station_id": parts[1], "dock_occupied": parts[2],
                    "charging_connected": parts[3], "ts": parts[4]}
        if t == "RENTAL_REQUEST" and len(parts) == 6:
            return {"type": t, "station_id": parts[1], "bike_id": parts[2],
                    "username": parts[3], "password": parts[4], "ts": parts[5]}
        if t == "BIKE_RELEASED" and len(parts) == 5:
            return {"type": t, "station_id": parts[1], "bike_id": parts[2],
                    "user_id": parts[3], "ts": parts[4]}
        if t == "BIKE_DOCKED" and len(parts) == 4:
            return {"type": t, "station_id": parts[1], "bike_id": parts[2], "ts": parts[3]}
        if t == "GPS" and len(parts) == 5:
            return {"type": t, "bike_id": parts[1], "ts": parts[2],
                    "lat": float(parts[3]), "lon": float(parts[4])}
        # Central->Station messages (received at station side)
        if t in ("LOGIN_OK", "LOGIN_FAIL", "RENTAL_APPROVED", "RENTAL_DENIED", "RETURN_COMPLETE"):
            return {"type": t, "parts": parts[1:]}
    except (ValueError, IndexError):
        return None
    return None
