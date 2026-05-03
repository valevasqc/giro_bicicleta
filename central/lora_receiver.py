"""Inbound LoRa dispatcher: station -> central.

Pure message-routing layer — serial/stub I/O is owned by lora_io.
Call start() once to register this object as the inbound handler;
lora_io launches a daemon thread that calls _handle_line() for every
non-empty, non-comment line arriving from the LoRa module.

All handlers are wrapped in try/except at the dispatch boundary so a
bad message logs and is skipped without killing the read thread.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    from .database import get_connection, log_event
    from .pricing import calculate_duration_minutes, calculate_cost
    from .config import (
        MINIMUM_BALANCE_TO_RENT,
        PRICING_RATE_PER_MINUTE,
        MINIMUM_CHARGE,
        GEOFENCE_CENTER_LAT,
        GEOFENCE_CENTER_LON,
        GEOFENCE_RADIUS_M,
    )
    from .services import topup_service
    from . import lora_io
except ImportError:
    from database import get_connection, log_event
    from pricing import calculate_duration_minutes, calculate_cost
    from config import (
        MINIMUM_BALANCE_TO_RENT,
        PRICING_RATE_PER_MINUTE,
        MINIMUM_CHARGE,
        GEOFENCE_CENTER_LAT,
        GEOFENCE_CENTER_LON,
        GEOFENCE_RADIUS_M,
    )
    import services.topup_service as topup_service
    import lora_io

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
        TOPUP_FAIL,
        TOPUP_OK,
        TOPUP_REQUEST,
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
        TOPUP_FAIL,
        TOPUP_OK,
        TOPUP_REQUEST,
        format_message,
        parse_message,
    )

from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


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


class LoRaReceiver:
    def __init__(self, sender):
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
        if msg_type in (HEARTBEAT, GPS):
            logger.debug("[LORA <- station] %s %s", msg_type, fields)
        else:
            logger.info("[LORA <- station] %s %s", msg_type, fields)

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
            elif msg_type == TOPUP_REQUEST:
                self._handle_topup_request(fields)
            else:
                logger.debug("[LORA] ignoring central-bound or unknown type: %s", msg_type)
        except Exception as exc:
            logger.error("[LORA] handler %s crashed: %r — fields=%s", msg_type, exc, fields)

    # --- handlers -------------------------------------------------------
    def _handle_heartbeat(self, fields) -> None:
        # HEARTBEAT|station_id|dock_occupied|charging_connected|ts
        if len(fields) < 4:
            logger.warning("[LORA] HEARTBEAT: expected 4 fields, got %d", len(fields))
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
                logger.warning("[LORA] HEARTBEAT: unknown station %r", station_id)
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
            logger.warning("[LORA] RENTAL_REQUEST: expected 5 fields, got %d", len(fields))
            return

        station_id = fields[0].strip()
        bike_id = fields[1].strip()
        username = fields[2].strip()
        password = fields[3]  # do not strip — passwords may be whitespace-sensitive
        logger.info("[LORA] RENTAL_REQUEST: station=%s bike=%s user=%r", station_id, bike_id, username)

        def deny(reason: str) -> None:
            logger.info("[LORA] RENTAL_DENIED → %s: %s", station_id, reason)
            msg = format_message(RENTAL_DENIED, station_id, reason, _utc_iso())
            self._sender.send(msg)
            time.sleep(2)
            self._sender.send(msg)
            self._safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={"username": username, "bike_id": bike_id, "reason": reason},
            )

        def login_fail(reason: str) -> None:
            logger.info("[LORA] LOGIN_FAIL → %s: %s", station_id, reason)
            msg = format_message(LOGIN_FAIL, station_id, reason, _utc_iso())
            self._sender.send(msg)
            time.sleep(2)
            self._sender.send(msg)
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

            if not user:
                logger.warning("[LORA] RENTAL_REQUEST: user %r not found", username)
                login_fail("invalid_credentials")
                return
            if not check_password_hash(user["password_hash"], password):
                logger.warning("[LORA] RENTAL_REQUEST: bad password for %r", username)
                login_fail("invalid_credentials")
                return

            if not user["is_active"]:
                login_fail("account_inactive")
                return

            if user["role"] != "customer":
                login_fail("invalid_credentials")
                return

            station = conn.execute(
                "SELECT station_id FROM stations WHERE station_id = ?",
                (station_id,),
            ).fetchone()
            if not station:
                deny("invalid_station")
                return

            balance = float(user["balance"] or 0.0)
            logger.debug("[LORA] RENTAL_REQUEST: balance=%.2f  minimum=%s", balance, MINIMUM_BALANCE_TO_RENT)

            import secrets
            from datetime import timedelta
            token = secrets.token_hex(8)
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
            name = (user["name"] or "")[:16]

            active_user_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE user_id = ? AND status = 'active'",
                (user["user_id"],),
            ).fetchone()
            has_active_rental = bool(active_user_rental)

            if not has_active_rental:
                bike = conn.execute(
                    "SELECT bike_id, status, current_station_id FROM bikes WHERE bike_id = ?",
                    (bike_id,),
                ).fetchone()
                if not bike:
                    logger.warning("[LORA] RENTAL_REQUEST: bike %r not in DB", bike_id)
                    deny("bike_not_available")
                    return
                logger.debug("[LORA] RENTAL_REQUEST: bike status=%s at=%r", bike['status'], bike['current_station_id'])
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

        ts = _utc_iso()
        login_ok_msg = format_message(LOGIN_OK, station_id, user_id, name, token, f"{balance:.2f}", ts)

        def _send_login_ok_denied(reason: str) -> None:
            denied_msg = format_message(RENTAL_DENIED, station_id, reason, ts)
            logger.info("[LORA] LOGIN_OK + RENTAL_DENIED(%s) → %s (attempt 1)", reason, station_id)
            self._sender.send(login_ok_msg)
            self._sender.send(denied_msg)
            time.sleep(3)
            logger.info("[LORA] LOGIN_OK + RENTAL_DENIED(%s) → %s (attempt 2)", reason, station_id)
            self._sender.send(login_ok_msg)
            self._sender.send(denied_msg)
            self._safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={"user_id": user_id, "bike_id": bike_id, "reason": reason},
            )

        if has_active_rental:
            _send_login_ok_denied("user_has_active_rental")
            return

        if balance < MINIMUM_BALANCE_TO_RENT:
            _send_login_ok_denied("insufficient_balance")
            return

        approved_msg = format_message(RENTAL_APPROVED, station_id, bike_id, user_id, ts)
        logger.info("[LORA] LOGIN_OK + RENTAL_APPROVED → %s  bike=%s (attempt 1)", station_id, bike_id)
        self._sender.send(login_ok_msg)
        self._sender.send(approved_msg)
        time.sleep(3)
        logger.info("[LORA] LOGIN_OK + RENTAL_APPROVED → %s  bike=%s (attempt 2)", station_id, bike_id)
        self._sender.send(login_ok_msg)
        self._sender.send(approved_msg)
        self._safe_log_event(
            source=station_id,
            event_type="RENTAL_APPROVED",
            payload={"user_id": user_id, "bike_id": bike_id},
        )

    def _handle_bike_released(self, fields) -> None:
        # BIKE_RELEASED|station_id|bike_id|user_id|ts
        if len(fields) < 4:
            logger.warning("[LORA] BIKE_RELEASED: expected 4 fields, got %d", len(fields))
            return

        station_id = fields[0].strip()
        bike_id = fields[1].strip()
        user_id = fields[2].strip()
        start_time = _utc_iso()

        with get_connection() as conn:
            bike = conn.execute(
                "SELECT bike_id, status, current_station_id FROM bikes WHERE bike_id = ?",
                (bike_id,),
            ).fetchone()
            if not bike or bike["status"] != "docked" or bike["current_station_id"] != station_id:
                logger.warning("[LORA] BIKE_RELEASED: bike %s not docked at %s; ignoring", bike_id, station_id)
                return

            user = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            if not user:
                logger.warning("[LORA] BIKE_RELEASED: unknown/inactive user %r; ignoring", user_id)
                return

            active_user_rental = conn.execute(
                "SELECT rental_id FROM rentals WHERE user_id = ? AND status = 'active'",
                (user_id,),
            ).fetchone()
            if active_user_rental:
                logger.warning("[LORA] BIKE_RELEASED: user %s already has an active rental; ignoring", user_id)
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
            logger.warning("[LORA] BIKE_DOCKED: expected 3 fields, got %d", len(fields))
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
                logger.info("[LORA] BIKE_DOCKED: no active rental for %s; ignoring", bike_id)
                self._safe_log_event(
                    source=station_id,
                    event_type="BIKE_DOCKED_NO_ACTIVE_RENTAL",
                    payload={"bike_id": bike_id},
                )
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
            simulated_cost = calculate_cost(duration_minutes, PRICING_RATE_PER_MINUTE, MINIMUM_CHARGE)

            prior_balance = float(rental["user_balance"] or 0.0)
            balance_remaining = round(prior_balance - simulated_cost, 2)

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

        rc_msg = format_message(
            RETURN_COMPLETE,
            station_id,
            bike_id,
            user_name,
            f"{duration_minutes:.2f}",
            f"{simulated_cost:.2f}",
            f"{balance_remaining:.2f}",
            _utc_iso(),
        )
        logger.info(
            "[LORA] RETURN_COMPLETE → %s  user=%s duration=%.1fmin cost=%s balance=%s",
            station_id, user_name, duration_minutes, simulated_cost, balance_remaining,
        )
        self._sender.send(rc_msg)
        time.sleep(2)
        logger.info("[LORA] RETURN_COMPLETE → %s (attempt 2)", station_id)
        self._sender.send(rc_msg)
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

    def _handle_topup_request(self, fields) -> None:
        # TOPUP_REQUEST|station_id|token|code|ts
        if len(fields) < 3:
            logger.warning("[LORA] TOPUP_REQUEST: expected ≥3 fields, got %d", len(fields))
            return

        station_id = fields[0].strip()
        token = fields[1].strip()
        code = fields[2].strip()
        logger.info("[LORA] TOPUP_REQUEST: station=%s code=%r", station_id, code)

        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT s.user_id
                FROM sessions s
                JOIN users u ON u.user_id = s.user_id
                WHERE s.token = ? AND s.is_active = 1 AND u.is_active = 1
                  AND s.expires_at > ?
                """,
                (token, _utc_iso()),
            ).fetchone()

            if not row:
                logger.warning("[LORA] TOPUP_REQUEST: invalid/expired token")
                self._sender.send(format_message(TOPUP_FAIL, station_id, "invalid_session", _utc_iso()))
                return

            user_id = row["user_id"]
            result = topup_service.redeem_code(conn, user_id, code)

        if result["success"]:
            logger.info("[LORA] TOPUP_OK → %s  amount=%s  new_balance=%s", station_id, result['amount'], result['new_balance'])
            ok_msg = format_message(TOPUP_OK, station_id, f"{result['new_balance']:.2f}", _utc_iso())
            self._sender.send(ok_msg)
            time.sleep(2)
            logger.info("[LORA] TOPUP_OK → %s (attempt 2)", station_id)
            self._sender.send(ok_msg)
        else:
            reason = result["error"] or "invalid_code"
            logger.info("[LORA] TOPUP_FAIL → %s: %s", station_id, reason)
            fail_msg = format_message(TOPUP_FAIL, station_id, reason, _utc_iso())
            self._sender.send(fail_msg)
            time.sleep(2)
            logger.info("[LORA] TOPUP_FAIL → %s (attempt 2)", station_id)
            self._sender.send(fail_msg)

    def _handle_gps(self, fields) -> None:
        # GPS|bike_id|unix_ts|lat|lon
        if len(fields) < 4:
            logger.warning("[LORA] GPS: expected 4 fields, got %d", len(fields))
            return

        bike_id = fields[0].strip()
        try:
            unix_ts = float(fields[1])
            lat = float(fields[2])
            lon = float(fields[3])
        except (TypeError, ValueError):
            logger.warning("[LORA] GPS: non-numeric payload %s", fields)
            return

        if unix_ts == 0 and lat == 0.0 and lon == 0.0:
            logger.debug("[LORA] GPS: no-fix packet from %s, skipping", bike_id)
            return

        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            logger.warning("[LORA] GPS: out-of-range coords lat=%s lon=%s", lat, lon)
            return

        gps_time = datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime(TIMESTAMP_FORMAT)

        with get_connection() as conn:
            bike = conn.execute(
                "SELECT bike_id FROM bikes WHERE bike_id = ?",
                (bike_id,),
            ).fetchone()
            if not bike:
                logger.warning("[LORA] GPS: unknown bike %r", bike_id)
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

            if active_rental_id:
                dist_m = _haversine_m(lat, lon, GEOFENCE_CENTER_LAT, GEOFENCE_CENTER_LON)
                if dist_m > GEOFENCE_RADIUS_M:
                    existing = conn.execute(
                        "SELECT geofence_breached FROM rentals WHERE rental_id = ?",
                        (active_rental_id,),
                    ).fetchone()
                    was_breached = bool(existing and existing["geofence_breached"])
                    conn.execute(
                        """
                        UPDATE rentals
                        SET geofence_breached = 1,
                            first_breach_at = COALESCE(first_breach_at, ?)
                        WHERE rental_id = ?
                        """,
                        (gps_time, active_rental_id),
                    )
                    conn.commit()
                    if not was_breached:
                        logger.warning("[GEOFENCE] BREACH: bike=%s dist=%.0fm rental=%s", bike_id, dist_m, active_rental_id)
                        self._safe_log_event(
                            source=bike_id,
                            event_type="GEOFENCE_BREACH",
                            payload={
                                "lat": lat,
                                "lon": lon,
                                "dist_m": round(dist_m, 1),
                                "rental_id": active_rental_id,
                            },
                        )

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
