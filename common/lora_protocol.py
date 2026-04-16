"""Pipe-delimited LoRa message protocol shared by station and central.

Messages are plain-ASCII strings with fields separated by FIELD_SEP ("|").
One message per serial line, terminated by "\n". No JSON, no framing —
the LoRa radio already gives us packetization, and strings are easier to
eyeball during debugging.

Grammar (| = separator):

Station -> Central:
    HEARTBEAT|<station_id>|<dock_occupied:0|1>|<charging_connected:0|1>|<ts>
    RENTAL_REQUEST|<station_id>|<bike_id>|<username>|<password>|<ts>
    BIKE_RELEASED|<station_id>|<bike_id>|<user_id>|<ts>
    BIKE_DOCKED|<station_id>|<bike_id>|<ts>
    GPS|<bike_id>|<unix_ts>|<lat>|<lon>

Central -> Station:
    LOGIN_OK|<station_id>|<user_id>|<name>|<token>|<balance>|<ts>
    LOGIN_FAIL|<station_id>|<reason>|<ts>
    RENTAL_APPROVED|<station_id>|<bike_id>|<user_id>|<ts>
    RENTAL_DENIED|<station_id>|<reason>|<ts>
    RETURN_COMPLETE|<station_id>|<bike_id>|<name>|<duration_minutes>|<cost>|<balance_remaining>|<ts>
"""

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
    """Join a message type and its fields with FIELD_SEP.

    All fields are str()-coerced. Fields must not contain FIELD_SEP or newlines;
    the caller is responsible for keeping payloads clean (usernames, names, etc.).
    """
    parts = [str(msg_type)]
    for field in fields:
        parts.append("" if field is None else str(field))
    return FIELD_SEP.join(parts)


def parse_message(line: str):
    """Parse a raw LoRa line into (msg_type, [fields]).

    Returns None for empty / unrecognized lines so callers can skip them
    without try/except noise in the hot path.
    """
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
