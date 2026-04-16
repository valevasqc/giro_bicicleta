"""Inbound LoRa: station -> central.

Runs as a daemon thread. Reads one line at a time from the shared stub
file (or serial port), parses via common.lora_protocol, and dispatches
to a handler that mutates the DB and/or emits a reply via the attached
LoRaSender.

Stub mode tails an append-only file from its current EOF, keeping a
read offset so a restart doesn't re-consume old messages. Serial mode
uses pyserial.readline() with a short timeout.

All handlers are wrapped in try/except at the dispatch boundary — a
bad message logs and is skipped; the thread never dies on bad input.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    import serial
except ImportError:
    serial = None

try:
    from .database import get_connection, log_event
    from .pricing import calculate_duration_minutes, calculate_simulated_cost
    from .config import MINIMUM_BALANCE_TO_RENT
except ImportError:
    from database import get_connection, log_event
    from pricing import calculate_duration_minutes, calculate_simulated_cost
    from config import MINIMUM_BALANCE_TO_RENT

try:
    from common.lora_protocol import (
        BIKE_DOCKED,
        BIKE_RELEASED,
        GPS,
        HEARTBEAT,
        LOGIN_FAIL,
        LOGIN_OK,
        RENTAL_APPROVED,
        RENTAL_DENIED,
        RENTAL_REQUEST,
        RETURN_COMPLETE,
        format_message,
        parse_message,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.lora_protocol import (
        BIKE_DOCKED,
        BIKE_RELEASED,
        GPS,
        HEARTBEAT,
        LOGIN_FAIL,
        LOGIN_OK,
        RENTAL_APPROVED,
        RENTAL_DENIED,
        RENTAL_REQUEST,
        RETURN_COMPLETE,
        format_message,
        parse_message,
    )

from werkzeug.security import check_password_hash


TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def _to_int01(value) -> int:
    """Coerce '1'/'0'/'true'/'false' (case-insensitive) to 1/0."""
    if isinstance(value, bool):
        return 1 if value else 0
    s = str(value).strip().lower()
    if s in ("1", "true", "yes"):
        return 1
    return 0


class LoRaReceiver(threading.Thread):
    def __init__(
        self,
        stub: bool,
        stub_path: Path | None,
        serial_port: str | None,
        baud_rate: int | None,
        sender,
        poll_interval: float = 0.2,
    ):
        super().__init__(daemon=True, name="central-lora-receiver")
        self._stub = stub
        self._stub_path = stub_path
        self._serial_port = serial_port
        self._baud_rate = baud_rate
        self._sender = sender
        self._poll_interval = poll_interval
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

        offset = self._stub_path.stat().st_size
        print(f"[LORA STUB] central receiver tailing {self._stub_path} from offset {offset}")

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

        with serial.Serial(port=self._serial_port, baudrate=self._baud_rate, timeout=1) as ser:
            while not self._stop.is_set():
                try:
                    raw = ser.readline()
                except Exception as exc:
                    print(f"[LORA] serial read error: {exc}")
                    time.sleep(self._poll_interval)
                    continue

                if not raw:
                    continue

                self._handle_line(raw.decode("utf-8", errors="replace"))

    # --- dispatch -------------------------------------------------------
    def _handle_line(self, line: str) -> None:
        parsed = parse_message(line)
        if parsed is None:
            if line.strip():
                print(f"[LORA] dropped unparseable line: {line!r}")
            return

        msg_type, fields = parsed
        print(f"[LORA <- station] {msg_type} {fields}")

        try:
            if msg_type == HEARTBEAT:
                self._handle_heartbeat(fields)
            elif msg_type == RENTAL_REQUEST:
                self._handle_rental_request(fields)
            elif msg_type == BIKE_RELEASED:
                self._handle_bike_released(fields)
            elif msg_type == BIKE_DOCKED:
                self._handle_bike_docked(fields)
            elif msg_type == GPS:
                self._handle_gps(fields)
            else:
                print(f"[LORA] ignoring central-bound or unknown type: {msg_type}")
        except Exception as exc:
            print(f"[LORA] handler {msg_type} crashed: {exc!r} — fields={fields}")

    # --- handlers -------------------------------------------------------
    def _handle_heartbeat(self, fields) -> None:
        # HEARTBEAT|station_id|dock_occupied|charging_connected|ts
        if len(fields) < 4:
            print(f"[LORA] HEARTBEAT: expected 4 fields, got {len(fields)}")
            return

        station_id = fields[0].strip()
        dock_occupied = _to_int01(fields[1])
        power_connected = _to_int01(fields[2])
        heartbeat_time = _utc_iso()

        with get_connection() as conn:
            row = conn.execute(
                "SELECT station_id FROM stations WHERE station_id = ?",
                (station_id,),
            ).fetchone()
            if not row:
                print(f"[LORA] HEARTBEAT: unknown station {station_id!r}")
                return

            conn.execute(
                """
                UPDATE stations
                SET last_heartbeat = ?,
                    dock_occupied = ?,
                    power_connected = ?,
                    lock_confirmed = ?,
                    is_online = 1
                WHERE station_id = ?
                """,
                (heartbeat_time, dock_occupied, power_connected, dock_occupied, station_id),
            )
            conn.commit()

        self._safe_log_event(
            source=station_id,
            event_type="STATION_HEARTBEAT",
            payload={
                "dock_occupied": dock_occupied,
                "power_connected": bool(power_connected),
            },
        )

    def _handle_rental_request(self, fields) -> None:
        # RENTAL_REQUEST|station_id|bike_id|username|password|ts
        if len(fields) < 5:
            print(f"[LORA] RENTAL_REQUEST: expected 5 fields, got {len(fields)}")
            return

        station_id = fields[0].strip()
        bike_id = fields[1].strip()
        username = fields[2].strip()
        password = fields[3]  # do not strip — passwords may be whitespace-sensitive

        def deny(reason: str) -> None:
            self._sender.send(format_message(RENTAL_DENIED, station_id, reason, _utc_iso()))
            self._safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={"username": username, "bike_id": bike_id, "reason": reason},
            )

        def login_fail(reason: str) -> None:
            self._sender.send(format_message(LOGIN_FAIL, station_id, reason, _utc_iso()))
            self._safe_log_event(
                source=station_id,
                event_type="LOGIN_FAIL",
                payload={"username": username, "reason": reason},
            )

        with get_connection() as conn:
            user = conn.execute(
                """
                SELECT user_id, username, name, password_hash, role, is_active, balance
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

            if not user or not check_password_hash(user["password_hash"], password):
                login_fail("invalid_credentials")
                return

            if not user["is_active"]:
                login_fail("account_inactive")
                return

            if user["role"] != "customer":
                # Kiosks are for customers only; station_service / admin must
                # not be able to start rentals from the touchscreen.
                login_fail("invalid_credentials")
                return

            station = conn.execute(
                "SELECT station_id FROM stations WHERE station_id = ?",
                (station_id,),
            ).fetchone()
            if not station:
                deny("invalid_station")
                return

            active_user_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE user_id = ? AND status = 'active'",
                (user["user_id"],),
            ).fetchone()
            if active_user_rental:
                deny("user_has_active_rental")
                return

            bike = conn.execute(
                "SELECT bike_id, status, current_station_id FROM bikes WHERE bike_id = ?",
                (bike_id,),
            ).fetchone()
            if not bike:
                deny("bike_not_available")
                return
            if bike["status"] != "docked":
                deny("bike_not_available")
                return
            if bike["current_station_id"] != station_id:
                deny("bike_not_at_station")
                return

            active_bike_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE bike_id = ? AND status = 'active'",
                (bike_id,),
            ).fetchone()
            if active_bike_rental:
                deny("bike_not_available")
                return

            balance = float(user["balance"] or 0.0)
            if balance < MINIMUM_BALANCE_TO_RENT:
                deny("insufficient_balance")
                return

            # Eligible. Mint a session token (same shape as /api/auth/login)
            # so future HTTP flows can reuse it even though the kiosk itself
            # talks over LoRa.
            import secrets
            from datetime import timedelta
            token = secrets.token_hex(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, expires_at, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (token, user["user_id"], expires_at.strftime(TIMESTAMP_FORMAT)),
            )
            conn.commit()

            user_id = user["user_id"]
            name = user["name"]

        ts = _utc_iso()
        # LOGIN_OK|station_id|user_id|name|token|balance|ts
        self._sender.send(format_message(
            LOGIN_OK, station_id, user_id, name, token, f"{balance:.2f}", ts,
        ))
        # RENTAL_APPROVED|station_id|bike_id|user_id|ts
        self._sender.send(format_message(
            RENTAL_APPROVED, station_id, bike_id, user_id, ts,
        ))
        self._safe_log_event(
            source=station_id,
            event_type="RENTAL_APPROVED",
            payload={"user_id": user_id, "bike_id": bike_id},
        )

    def _handle_bike_released(self, fields) -> None:
        # BIKE_RELEASED|station_id|bike_id|user_id|ts
        if len(fields) < 4:
            print(f"[LORA] BIKE_RELEASED: expected 4 fields, got {len(fields)}")
            return

        station_id = fields[0].strip()
        bike_id = fields[1].strip()
        user_id = fields[2].strip()
        start_time = _utc_iso()

        with get_connection() as conn:
            # Defensive: re-check eligibility. The approve/release pair is
            # not atomic over LoRa, and another kiosk or admin action could
            # have invalidated things in between.
            bike = conn.execute(
                "SELECT bike_id, status, current_station_id FROM bikes WHERE bike_id = ?",
                (bike_id,),
            ).fetchone()
            if not bike or bike["status"] != "docked" or bike["current_station_id"] != station_id:
                print(f"[LORA] BIKE_RELEASED: bike {bike_id} not docked at {station_id}; ignoring")
                return

            user = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            if not user:
                print(f"[LORA] BIKE_RELEASED: unknown/inactive user {user_id!r}; ignoring")
                return

            active_user_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE user_id = ? AND status = 'active'",
                (user_id,),
            ).fetchone()
            if active_user_rental:
                print(f"[LORA] BIKE_RELEASED: user {user_id} already has an active rental; ignoring")
                return

            rental_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO rentals (
                    rental_id, user_id, bike_id, start_station_id, start_time,
                    payment_method, payment_status, payment_authorized_at, status
                )
                VALUES (?, ?, ?, ?, ?, 'station_card', 'authorized', ?, 'active')
                """,
                (rental_id, user_id, bike_id, station_id, start_time, start_time),
            )
            conn.execute(
                "UPDATE bikes SET status = 'rented', current_station_id = NULL WHERE bike_id = ?",
                (bike_id,),
            )
            conn.execute(
                "UPDATE stations SET dock_occupied = 0 WHERE station_id = ?",
                (station_id,),
            )
            conn.commit()

        self._safe_log_event(
            source=station_id,
            event_type="RENTAL_STARTED",
            payload={
                "rental_id": rental_id,
                "user_id": user_id,
                "bike_id": bike_id,
                "start_station_id": station_id,
                "start_time": start_time,
            },
        )

    def _handle_bike_docked(self, fields) -> None:
        # BIKE_DOCKED|station_id|bike_id|ts
        if len(fields) < 3:
            print(f"[LORA] BIKE_DOCKED: expected 3 fields, got {len(fields)}")
            return

        station_id = fields[0].strip()
        bike_id = fields[1].strip()
        end_time = _utc_iso()

        with get_connection() as conn:
            rental = conn.execute(
                """
                SELECT r.rental_id, r.user_id, r.start_time,
                       u.name AS user_name, u.balance AS user_balance
                FROM rentals r
                JOIN users u ON u.user_id = r.user_id
                WHERE r.bike_id = ? AND r.status = 'active'
                """,
                (bike_id,),
            ).fetchone()

            if not rental:
                # Idempotent: the station may re-send BIKE_DOCKED if it lost
                # our reply, or the bike may already be docked for an admin
                # reason. Log and move on — nothing to bill.
                print(f"[LORA] BIKE_DOCKED: no active rental for {bike_id}; ignoring")
                self._safe_log_event(
                    source=station_id,
                    event_type="BIKE_DOCKED_NO_ACTIVE_RENTAL",
                    payload={"bike_id": bike_id},
                )
                # Still sync the physical state (bike is back in the dock)
                # so the admin dashboard reflects reality.
                conn.execute(
                    """
                    UPDATE bikes SET status = 'docked', current_station_id = ?
                    WHERE bike_id = ? AND status != 'unavailable'
                    """,
                    (station_id, bike_id),
                )
                conn.execute(
                    "UPDATE stations SET dock_occupied = 1 WHERE station_id = ?",
                    (station_id,),
                )
                conn.commit()
                return

            duration_minutes = calculate_duration_minutes(rental["start_time"], end_time)
            simulated_cost = calculate_simulated_cost(duration_minutes)

            prior_balance = float(rental["user_balance"] or 0.0)
            balance_remaining = round(max(prior_balance - simulated_cost, 0.0), 2)

            conn.execute(
                """
                UPDATE rentals
                SET end_station_id = ?,
                    end_time = ?,
                    duration_minutes = ?,
                    simulated_cost = ?,
                    payment_status = 'captured',
                    payment_captured_at = ?,
                    status = 'completed'
                WHERE rental_id = ?
                """,
                (station_id, end_time, duration_minutes, simulated_cost, end_time, rental["rental_id"]),
            )
            conn.execute(
                "UPDATE bikes SET status = 'docked', current_station_id = ? WHERE bike_id = ?",
                (station_id, bike_id),
            )
            conn.execute(
                """
                UPDATE stations
                SET dock_occupied = 1, power_connected = 1, lock_confirmed = 1
                WHERE station_id = ?
                """,
                (station_id,),
            )
            conn.execute(
                "UPDATE users SET balance = ? WHERE user_id = ?",
                (balance_remaining, rental["user_id"]),
            )
            conn.commit()

            user_name = rental["user_name"]
            rental_id = rental["rental_id"]

        # RETURN_COMPLETE|station_id|bike_id|name|duration_minutes|cost|balance_remaining|ts
        self._sender.send(format_message(
            RETURN_COMPLETE,
            station_id,
            bike_id,
            user_name,
            f"{duration_minutes:.2f}",
            f"{simulated_cost:.2f}",
            f"{balance_remaining:.2f}",
            _utc_iso(),
        ))
        self._safe_log_event(
            source=station_id,
            event_type="RENTAL_COMPLETED",
            payload={
                "rental_id": rental_id,
                "bike_id": bike_id,
                "end_station_id": station_id,
                "duration_minutes": duration_minutes,
                "simulated_cost": simulated_cost,
                "balance_remaining": balance_remaining,
            },
        )

    def _handle_gps(self, fields) -> None:
        # GPS|bike_id|unix_ts|lat|lon
        if len(fields) < 4:
            print(f"[LORA] GPS: expected 4 fields, got {len(fields)}")
            return

        bike_id = fields[0].strip()
        try:
            unix_ts = float(fields[1])
            lat = float(fields[2])
            lon = float(fields[3])
        except (TypeError, ValueError):
            print(f"[LORA] GPS: non-numeric payload {fields}")
            return

        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            print(f"[LORA] GPS: out-of-range coords lat={lat} lon={lon}")
            return

        gps_time = datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime(TIMESTAMP_FORMAT)

        with get_connection() as conn:
            bike = conn.execute(
                "SELECT bike_id FROM bikes WHERE bike_id = ?",
                (bike_id,),
            ).fetchone()
            if not bike:
                print(f"[LORA] GPS: unknown bike {bike_id!r}")
                return

            conn.execute(
                """
                UPDATE bikes
                SET last_lat = ?, last_lon = ?, last_gps_time = ?
                WHERE bike_id = ?
                """,
                (lat, lon, gps_time, bike_id),
            )

            active_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE bike_id = ? AND status = 'active' LIMIT 1",
                (bike_id,),
            ).fetchone()
            active_rental_id = active_rental["rental_id"] if active_rental else None

            conn.execute(
                """
                INSERT INTO gps_pings (bike_id, rental_id, timestamp, lat, lon)
                VALUES (?, ?, ?, ?, ?)
                """,
                (bike_id, active_rental_id, gps_time, lat, lon),
            )
            conn.commit()

        self._safe_log_event(
            source=bike_id,
            event_type="GPS_UPDATE",
            payload={"lat": lat, "lon": lon, "gps_time": gps_time},
        )

    # --- helpers --------------------------------------------------------
    def _safe_log_event(self, source, event_type, payload=None):
        try:
            log_event(source=source, event_type=event_type, payload=payload)
        except Exception:
            pass
