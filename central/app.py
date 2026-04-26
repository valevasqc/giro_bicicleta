import json
import logging
import secrets
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, render_template, redirect, session, url_for, make_response
from werkzeug.security import check_password_hash

try:
    from .database import get_connection, init_db, log_event
    from .pricing import calculate_duration_minutes, calculate_cost
    from .lora_receiver import LoRaReceiver
    from .lora_sender import LoRaSender
    from .config import (
        SECRET_KEY,
        STATION_ID,
        STATION_SERVICE_USERNAME,
        STATION_SERVICE_PASSWORD,
        STATION_OFFLINE_AFTER_SECONDS,
        STUB_LORA,
        STUB_LORA_INBOUND,
        STUB_LORA_OUTBOUND,
        LORA_SERIAL_PORT,
        LORA_BAUD_RATE,
        PRICING_RATE_PER_MINUTE,
        MINIMUM_CHARGE,
        GEOFENCE_CENTER_LAT,
        GEOFENCE_CENTER_LON,
        GEOFENCE_RADIUS_M,
    )
    from .services import topup_service
    from .logging_config import setup_logging
except ImportError:
    from database import get_connection, init_db, log_event
    from pricing import calculate_duration_minutes, calculate_cost
    from lora_receiver import LoRaReceiver
    from lora_sender import LoRaSender
    from config import (
        SECRET_KEY,
        STATION_ID,
        STATION_SERVICE_USERNAME,
        STATION_SERVICE_PASSWORD,
        STATION_OFFLINE_AFTER_SECONDS,
        STUB_LORA,
        STUB_LORA_INBOUND,
        STUB_LORA_OUTBOUND,
        LORA_SERIAL_PORT,
        LORA_BAUD_RATE,
        PRICING_RATE_PER_MINUTE,
        MINIMUM_CHARGE,
        GEOFENCE_CENTER_LAT,
        GEOFENCE_CENTER_LON,
        GEOFENCE_RADIUS_M,
    )
    import services.topup_service as topup_service
    from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# Make sure the DB schema (and any migrations) are in place before the LoRa
# receiver thread starts hitting it.
init_db()

# LoRa I/O for station <-> central messages. The receiver runs on a daemon
# thread that tails the stub file (or serial port) and mutates the DB.
lora_sender = LoRaSender(
    stub=STUB_LORA,
    stub_path=STUB_LORA_OUTBOUND if STUB_LORA else None,
    serial_port=None if STUB_LORA else LORA_SERIAL_PORT,
    baud_rate=None if STUB_LORA else LORA_BAUD_RATE,
)
app.extensions["lora_sender"] = lora_sender

lora_receiver = LoRaReceiver(
    stub=STUB_LORA,
    stub_path=STUB_LORA_INBOUND if STUB_LORA else None,
    serial_port=None if STUB_LORA else LORA_SERIAL_PORT,
    baud_rate=None if STUB_LORA else LORA_BAUD_RATE,
    sender=lora_sender,
)
lora_receiver.start()
app.extensions["lora_receiver"] = lora_receiver

logger.info("LoRa ready (stub=%s)", STUB_LORA)

STATION_SERVICE_TOKEN_CACHE = {}


@app.template_filter("short_rental_id")
def short_rental_id(value):
    rental_id = (value or "").strip()
    if not rental_id:
        return "-"

    return f"R-{rental_id[:8].upper()}"


def call_internal_api(method, path, payload=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with app.test_client() as client:
        response = client.open(path, method=method, json=payload, headers=headers)

    return response.status_code, response.get_json(silent=True) or {}


def reason_to_human_message(reason):
    mapping = {
        "missing_credentials": "Ingresa usuario y contraseña para continuar.",
        "missing_fields": "Faltan datos requeridos para continuar.",
        "invalid_credentials": "Usuario o contraseña incorrectos.",
        "account_inactive": "Esta cuenta está inactiva. Contacta a soporte.",
        "forbidden": "No tienes permiso para esta operación.",
        "invalid_session": "Tu sesión expiró. Inicia sesión de nuevo.",
        "missing_token": "No se encontró una sesión activa.",
        "invalid_payment_method": "El método de pago no es válido para esta estación.",
        "user_has_active_rental": "Ya tienes un viaje activo.",
        "bike_not_available": "La bicicleta ya no está disponible.",
        "bike_not_at_station": "La bicicleta seleccionada ya no está en esta estación.",
        "invalid_station": "La estación configurada no es válida.",
        "wrong_station_token": "El token de servicio no corresponde a esta estación.",
        "no_active_rental": "No hay un viaje activo para completar en esta bicicleta.",
        "power_not_connected": "La bicicleta no está conectada a la fuente de carga. Conecta el cable e intenta de nuevo.",
        "lock_not_confirmed": "El candado no está cerrado correctamente. Asegúralo e intenta de nuevo.",
        "return_checks_failed": "No se pudo verificar el retorno. Asegúrate de que el cable esté conectado y el candado cerrado.",
        "station_unreachable": "No se pudo consultar el estado de la estación.",
        "no_bikes_available": "No hay bicicletas disponibles en este momento.",
        "admin_state_unavailable": "No se pudo cargar el estado del sistema en este momento.",
    }
    return mapping.get(reason, "Ocurrió un error inesperado. Intenta de nuevo.")


def get_notice_message():
    notice = (request.args.get("notice") or "").strip()
    notice_mapping = {
        "session_expired": "Tu sesión expiró o no estaba activa. Inicia sesión nuevamente.",
    }
    return notice_mapping.get(notice)


def get_admin_session():
    admin_auth = session.get("admin_auth")
    if not isinstance(admin_auth, dict):
        return None

    if admin_auth.get("role") != "admin":
        return None

    if not admin_auth.get("token"):
        return None

    return admin_auth


def clear_admin_session_data():
    session.pop("admin_auth", None)


def no_store_html_response(html):
    response = make_response(html)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def get_mobile_customer_session():
    mobile_auth = session.get("mobile_customer_auth")
    if not isinstance(mobile_auth, dict):
        return None

    if mobile_auth.get("role") != "customer":
        return None

    if not mobile_auth.get("token"):
        return None

    return mobile_auth


def clear_mobile_session_data():
    session.pop("mobile_customer_auth", None)
    session.pop("mobile_pending_request", None)
    session.pop("mobile_active_rental", None)


def clear_mobile_ride_state():
    session.pop("mobile_pending_request", None)
    session.pop("mobile_active_rental", None)


def get_active_rental_for_user(user_id):
    if not user_id:
        return None

    with get_connection() as conn:
        rental = conn.execute(
            """
            SELECT rental_id,
                   bike_id,
                   start_station_id,
                   start_time,
                   payment_method,
                   payment_status
            FROM rentals
            WHERE user_id = ?
              AND status = 'active'
            ORDER BY start_time DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    return dict(rental) if rental else None


def sync_mobile_active_rental_from_db(mobile_auth):
    user_id = mobile_auth.get("user_id") if isinstance(mobile_auth, dict) else None
    active_rental = get_active_rental_for_user(user_id)

    if active_rental:
        session["mobile_active_rental"] = active_rental
    else:
        session.pop("mobile_active_rental", None)

    return active_rental


def get_mobile_user_balance(user_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return float(row["balance"] or 0.0) if row else 0.0


def get_station_name_by_id(station_id):
    with get_connection() as conn:
        station = conn.execute(
            """
            SELECT name
            FROM stations
            WHERE station_id = ?
            """,
            (station_id,),
        ).fetchone()

    return station["name"] if station else station_id


def get_station_service_credentials_for_station(station_id):
    if station_id == STATION_ID:
        return STATION_SERVICE_USERNAME, STATION_SERVICE_PASSWORD

    derived_username = f"station_{station_id.lower()}"
    return derived_username, STATION_SERVICE_PASSWORD


def get_station_service_token(force_refresh=False, station_id=None):
    target_station_id = station_id or STATION_ID

    if not force_refresh and STATION_SERVICE_TOKEN_CACHE.get(target_station_id):
        return STATION_SERVICE_TOKEN_CACHE[target_station_id], None

    username, password = get_station_service_credentials_for_station(target_station_id)

    status_code, payload = call_internal_api(
        "POST",
        "/api/auth/login",
        payload={
            "username": username,
            "password": password,
        },
    )

    if status_code != 200 or not payload.get("ok"):
        STATION_SERVICE_TOKEN_CACHE[target_station_id] = None
        return None, payload.get("reason") or "invalid_credentials"

    if payload.get("role") != "station_service":
        STATION_SERVICE_TOKEN_CACHE[target_station_id] = None
        return None, "forbidden"

    if payload.get("bound_station_id") != target_station_id:
        STATION_SERVICE_TOKEN_CACHE[target_station_id] = None
        return None, "wrong_station_token"

    token = payload.get("token")
    if not token:
        STATION_SERVICE_TOKEN_CACHE[target_station_id] = None
        return None, "missing_token"

    STATION_SERVICE_TOKEN_CACHE[target_station_id] = token
    return token, None


def complete_with_station_service_retry(bike_id, station_id=None, power_connected=True, lock_confirmed=True):
    """Call /api/rentals/complete with automatic token refresh on 401.

    power_connected and lock_confirmed come from GPIO reed-switch reads on the Pi.
    Both default to True so the laptop demo works without real hardware attached.
    Replace these defaults with actual GPIO stub reads once the Pi driver is wired up.
    """
    target_station_id = station_id or STATION_ID

    token, token_error = get_station_service_token(force_refresh=False, station_id=target_station_id)
    if not token:
        return 401, {"ok": False, "reason": token_error or "missing_token"}

    complete_payload = {
        "station_id": target_station_id,
        "bike_id": bike_id,
        "power_connected": power_connected,   # TODO: read from GPIO stub / LoRa
        "lock_confirmed": lock_confirmed,     # TODO: read from GPIO stub / LoRa
    }

    status_code, payload = call_internal_api(
        "POST",
        "/api/rentals/complete",
        payload=complete_payload,
        token=token,
    )

    should_retry = status_code == 401 and (payload.get("reason") in ("invalid_session", "missing_token"))
    if not should_retry:
        return status_code, payload

    refreshed_token, token_error = get_station_service_token(force_refresh=True, station_id=target_station_id)
    if not refreshed_token:
        return 401, {"ok": False, "reason": token_error or "invalid_session"}

    return call_internal_api(
        "POST",
        "/api/rentals/complete",
        payload=complete_payload,
        token=refreshed_token,
    )


@app.route("/mobile")
def mobile_home_page():
    # TODO: Mobile flow should eventually use phone GPS (or user-entered location) to suggest nearby stations.
    mobile_auth = get_mobile_customer_session()
    if mobile_auth:
        return redirect(url_for("mobile_stations_page"))
    return render_template("mobile/home.html")


@app.route("/mobile/login", methods=["GET", "POST"])
def mobile_login_page():
    error_message = None
    username_value = ""
    notice_message = get_notice_message()

    if request.method == "POST":
        username_value = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username_value or not password:
            error_message = reason_to_human_message("missing_credentials")
        else:
            try:
                status_code, payload = call_internal_api(
                    "POST",
                    "/api/auth/login",
                    payload={"username": username_value, "password": password},
                )
            except Exception:
                status_code, payload = 500, {"ok": False, "reason": "invalid_credentials"}

            if status_code == 200 and payload.get("ok"):
                if payload.get("role") != "customer":
                    token = payload.get("token")
                    if token:
                        call_internal_api("POST", "/api/auth/logout", token=token)
                    error_message = "Solo las cuentas de cliente pueden usar el flujo móvil."
                else:
                    session["mobile_customer_auth"] = {
                        "token": payload.get("token"),
                        "user_id": payload.get("user_id"),
                        "name": payload.get("name"),
                        "role": payload.get("role"),
                    }
                    return redirect(url_for("mobile_stations_page"))
            else:
                reason = payload.get("reason") or "invalid_credentials"
                error_message = reason_to_human_message(reason)

    return render_template(
        "mobile/login.html",
        error_message=error_message,
        username_value=username_value,
        notice_message=notice_message,
    )


@app.route("/mobile/logout", methods=["POST"])
def mobile_logout_page():
    mobile_auth = session.get("mobile_customer_auth")
    token = mobile_auth.get("token") if isinstance(mobile_auth, dict) else None

    if token:
        try:
            call_internal_api("POST", "/api/auth/logout", token=token)
        except Exception:
            pass

    clear_mobile_session_data()
    return redirect(url_for("mobile_home_page"))


@app.route("/mobile/stations", methods=["GET"])
def mobile_stations_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    active_rental = sync_mobile_active_rental_from_db(mobile_auth)
    active_bike_id = active_rental.get("bike_id") if active_rental else None

    with get_connection() as conn:
        stations = [
            dict(row) for row in conn.execute(
                """
                SELECT station_id, name, is_online, dock_occupied,
                       power_connected, lock_confirmed, last_heartbeat
                FROM stations
                ORDER BY station_id
                """
            ).fetchall()
        ]

    balance = get_mobile_user_balance(mobile_auth["user_id"])

    return render_template(
        "mobile/stations.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        balance=balance,
        active_tab="stations",
        stations=stations,
        active_bike_id=active_bike_id,
    )


def load_mobile_station_detail(station_id):
    status_code, payload = call_internal_api("GET", f"/api/stations/{station_id}/status")

    if status_code != 200 or not payload.get("ok"):
        reason = payload.get("reason") or "station_unreachable"
        return None, None, reason

    station = payload.get("station") or {}
    bikes = payload.get("available_bikes") or []
    return station, bikes, None


@app.route("/mobile/stations/<station_id>", methods=["GET"])
def mobile_station_detail_page(station_id):
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    active_rental = sync_mobile_active_rental_from_db(mobile_auth)
    active_bike_id = active_rental.get("bike_id") if active_rental else None

    station, bikes, reason = load_mobile_station_detail(station_id)
    error_message = reason_to_human_message(reason) if reason else None

    balance = get_mobile_user_balance(mobile_auth["user_id"])

    return render_template(
        "mobile/station_detail.html",
        station_id=station_id,
        station=station,
        bikes=bikes,
        error_message=error_message,
        active_bike_id=active_bike_id,
        customer_name=mobile_auth.get("name") or "Cliente",
        balance=balance,
        active_tab="stations",
    )


@app.route("/mobile/request", methods=["POST"])
def mobile_request_rental_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    station_id = (request.form.get("station_id") or "").strip()
    bike_id = (request.form.get("bike_id") or "").strip()

    if not station_id or not bike_id:
        return redirect(url_for("mobile_stations_page"))

    try:
        status_code, payload = call_internal_api(
            "POST",
            "/api/rentals/request",
            payload={"station_id": station_id, "bike_id": bike_id},
            token=mobile_auth["token"],
        )
    except Exception:
        status_code, payload = 500, {"ok": False, "reason": "station_unreachable"}

    if status_code == 401:
        clear_mobile_session_data()
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    approved = bool(payload.get("ok") and payload.get("approved"))
    if approved:
        session["mobile_pending_request"] = {
            "station_id": station_id,
            "bike_id": bike_id,
        }
        return redirect(url_for("mobile_payment_page"))

    station, bikes, reason = load_mobile_station_detail(station_id)
    reason = payload.get("reason") or reason or "station_unreachable"

    return render_template(
        "mobile/station_detail.html",
        station_id=station_id,
        station=station,
        bikes=bikes,
        error_message=reason_to_human_message(reason),
    )


@app.route("/mobile/payment", methods=["GET", "POST"])
def mobile_payment_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    pending_request = session.get("mobile_pending_request")
    if not isinstance(pending_request, dict):
        return redirect(url_for("mobile_stations_page"))

    station_id = pending_request.get("station_id")
    bike_id = pending_request.get("bike_id")
    if not station_id or not bike_id:
        return redirect(url_for("mobile_stations_page"))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM stations WHERE station_id = ?",
            (station_id,),
        ).fetchone()
    station_name = row["name"] if row else station_id

    if request.method == "POST":
        try:
            status_code, payload = call_internal_api(
                "POST",
                "/api/rentals/start",
                payload={
                    "station_id": station_id,
                    "bike_id": bike_id,
                    "payment_method": "mobile_web",
                },
                token=mobile_auth["token"],
            )
        except Exception:
            status_code, payload = 500, {"ok": False, "reason": "station_unreachable"}

        if status_code == 401:
            clear_mobile_session_data()
            return redirect(url_for("mobile_login_page", notice="session_expired"))

        if status_code in (200, 201) and payload.get("ok"):
            session["mobile_active_rental"] = {
                "rental_id": payload.get("rental_id"),
                "bike_id": payload.get("bike_id"),
                "start_station_id": payload.get("start_station_id"),
                "start_time": payload.get("start_time"),
                "payment_status": payload.get("payment_status"),
                "payment_method": payload.get("payment_method"),
            }
            session.pop("mobile_pending_request", None)
            return redirect(url_for("mobile_ride_active_page"))

        reason = payload.get("reason") or "station_unreachable"
        balance = get_mobile_user_balance(mobile_auth["user_id"])
        return render_template(
            "mobile/payment.html",
            station_id=station_id,
            station_name=station_name,
            bike_id=bike_id,
            error_message=reason_to_human_message(reason),
            customer_name=mobile_auth.get("name") or "Cliente",
            balance=balance,
            active_tab="stations",
        )

    balance = get_mobile_user_balance(mobile_auth["user_id"])
    return render_template(
        "mobile/payment.html",
        station_id=station_id,
        station_name=station_name,
        bike_id=bike_id,
        error_message=None,
        customer_name=mobile_auth.get("name") or "Cliente",
        balance=balance,
        active_tab="stations",
    )


@app.route("/mobile/ride-active", methods=["GET"])
def mobile_ride_active_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    active_rental = sync_mobile_active_rental_from_db(mobile_auth)
    if not active_rental or not active_rental.get("bike_id"):
        return redirect(url_for("mobile_stations_page"))

    balance = get_mobile_user_balance(mobile_auth["user_id"])
    return render_template(
        "mobile/ride_active.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        rental=active_rental,
        balance=balance,
        active_tab="rides",
    )


@app.route("/mobile/complete-return", methods=["POST"])
def mobile_complete_return_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    active_rental = sync_mobile_active_rental_from_db(mobile_auth)
    bike_id = active_rental.get("bike_id") if active_rental else None
    if not bike_id:
        return redirect(url_for("mobile_stations_page"))

    target_station_id = (request.form.get("station_id") or "").strip() or STATION_ID
    target_station_name = get_station_name_by_id(target_station_id)

    try:
        status_code, payload = complete_with_station_service_retry(bike_id, station_id=target_station_id)
    except Exception:
        status_code, payload = 500, {"ok": False, "reason": "station_unreachable"}

    if status_code in (200, 201) and payload.get("ok") and payload.get("completed"):
        summary = {
            "bike_id": bike_id,
            "user_name": payload.get("user_name") or "Cliente",
            "duration_minutes": payload.get("duration_minutes"),
            "simulated_cost": payload.get("simulated_cost"),
            "balance_remaining": payload.get("balance_remaining"),
            "currency": payload.get("currency") or "GTQ",
            "payment_status": payload.get("payment_status") or "captured",
        }
        clear_mobile_session_data()
        balance_after = float(payload.get("balance_remaining") or 0.0)
        return render_template(
            "mobile/return_summary.html",
            station_id=target_station_id,
            station_name=target_station_name,
            summary=summary,
            customer_name=summary["user_name"],
            balance=balance_after,
            active_tab="rides",
        )

    reason = payload.get("reason") or "station_unreachable"
    balance = get_mobile_user_balance(mobile_auth["user_id"])
    return render_template(
        "mobile/complete_error.html",
        station_id=target_station_id,
        station_name=target_station_name,
        error_message=reason_to_human_message(reason),
        customer_name=mobile_auth.get("name") or "Cliente",
        balance=balance,
        active_tab="stations",
    )


@app.route("/mobile/reset", methods=["POST"])
def mobile_reset_after_error_page():
    clear_mobile_ride_state()
    return redirect(url_for("mobile_stations_page"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login_page():
    error_message = None
    username_value = ""
    notice_message = get_notice_message()

    if request.method == "POST":
        username_value = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username_value or not password:
            error_message = reason_to_human_message("missing_credentials")
        else:
            try:
                status_code, payload = call_internal_api(
                    "POST",
                    "/api/auth/login",
                    payload={"username": username_value, "password": password},
                )
            except Exception:
                status_code, payload = 500, {"ok": False, "reason": "invalid_credentials"}

            if status_code == 200 and payload.get("ok"):
                if payload.get("role") != "admin":
                    token = payload.get("token")
                    if token:
                        call_internal_api("POST", "/api/auth/logout", token=token)
                    error_message = "Solo las cuentas admin pueden entrar al dashboard."
                else:
                    session["admin_auth"] = {
                        "token": payload.get("token"),
                        "user_id": payload.get("user_id"),
                        "name": payload.get("name"),
                        "role": payload.get("role"),
                    }
                    return redirect(url_for("admin_dashboard_page"))
            else:
                reason = payload.get("reason") or "invalid_credentials"
                error_message = reason_to_human_message(reason)

    return render_template(
        "admin/admin_login.html",
        error_message=error_message,
        username_value=username_value,
        notice_message=notice_message,
    )


@app.route("/admin/logout", methods=["POST"])
def admin_logout_page():
    admin_auth = session.get("admin_auth")
    token = admin_auth.get("token") if isinstance(admin_auth, dict) else None

    if token:
        try:
            call_internal_api("POST", "/api/auth/logout", token=token)
        except Exception:
            pass

    clear_admin_session_data()
    return redirect(url_for("admin_login_page"))


@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard_page():
    admin_auth = get_admin_session()
    if not admin_auth:
        return redirect(url_for("admin_login_page", notice="session_expired"))

    try:
        status_code, payload = call_internal_api(
            "GET",
            "/api/admin/state",
            token=admin_auth["token"],
        )
    except Exception:
        status_code, payload = 500, {"ok": False, "reason": "admin_state_unavailable"}

    if status_code == 401:
        clear_admin_session_data()
        return redirect(url_for("admin_login_page", notice="session_expired"))

    if status_code != 200 or not payload.get("ok"):
        return no_store_html_response(
            render_template(
                "admin/admin_dashboard.html",
                admin_name=admin_auth.get("name") or "Admin",
                refresh_seconds=7,
                error_message=reason_to_human_message(payload.get("reason") or "admin_state_unavailable"),
                summary={
                    "online_stations": 0,
                    "total_stations": 0,
                    "available_bikes": 0,
                    "active_rentals": 0,
                    "completed_recent": 0,
                },
                stations=[],
                bikes=[],
                active_rentals=[],
                completed_rentals=[],
            )
        )

    stations = payload.get("stations") or []
    bikes = payload.get("bikes") or []
    active_rentals = payload.get("active_rentals") or []
    completed_rentals = payload.get("completed_rentals") or []

    summary = {
        "online_stations": sum(1 for row in stations if row.get("is_online")),
        "total_stations": len(stations),
        "available_bikes": sum(1 for row in bikes if row.get("status") == "docked"),
        "active_rentals": len(active_rentals),
        "completed_recent": len(completed_rentals),
    }

    return no_store_html_response(
        render_template(
            "admin/admin_dashboard.html",
            admin_name=admin_auth.get("name") or "Admin",
            refresh_seconds=7,
            error_message=None,
            summary=summary,
            stations=stations,
            bikes=bikes,
            active_rentals=active_rentals,
            completed_rentals=completed_rentals,
        )
    )



def utc_now():
    return datetime.now(timezone.utc)


def utc_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc_iso(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def is_station_online(last_heartbeat):
    last_heartbeat_dt = parse_utc_iso(last_heartbeat)
    if not last_heartbeat_dt:
        return False

    elapsed_seconds = (utc_now() - last_heartbeat_dt).total_seconds()
    return elapsed_seconds <= STATION_OFFLINE_AFTER_SECONDS


def safe_log_event(source, event_type, payload=None):
    try:
        log_event(source=source, event_type=event_type, payload=payload)
    except Exception:
        # Event logging should never break core request behavior.
        pass


def get_bearer_token():
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    return auth_header[7:].strip()


def validate_token(required_role=None):
    token = get_bearer_token()

    if not token:
        return None, None, (jsonify({
            "ok": False,
            "reason": "missing_token"
        }), 401)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT s.token, s.user_id, u.username, u.name, u.role, u.bound_station_id
            FROM sessions s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.token = ?
              AND s.is_active = 1
              AND u.is_active = 1
              AND s.expires_at > ?
            """,
            (token, utc_iso(utc_now())),
        ).fetchone()

    if not row:
        return token, None, (jsonify({
            "ok": False,
            "reason": "invalid_session"
        }), 401)

    if required_role and row["role"] != required_role:
        return token, None, (jsonify({
            "ok": False,
            "reason": "forbidden"
        }), 403)

    return token, row, None


@app.route("/")
def index():
    return redirect(url_for("admin_login_page"))


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "message": "central backend is running"
    })


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({
            "ok": False,
            "reason": "missing_credentials"
        }), 400

    with get_connection() as conn:
        user = conn.execute(
            """
            SELECT user_id, username, name, password_hash, role, bound_station_id, is_active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not user:
            return jsonify({
                "ok": False,
                "reason": "invalid_credentials"
            }), 401

        if not user["is_active"]:
            return jsonify({
                "ok": False,
                "reason": "account_inactive"
            }), 403

        if not check_password_hash(user["password_hash"], password):
            return jsonify({
                "ok": False,
                "reason": "invalid_credentials"
            }), 401

        duration_hours = 24 if user["role"] == "station_service" else 2
        token = secrets.token_hex(32)
        expires_at = utc_now() + timedelta(hours=duration_hours)

        conn.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (token, user["user_id"], utc_iso(expires_at)),
        )
        conn.commit()

    return jsonify({
        "ok": True,
        "token": token,
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "bound_station_id": user["bound_station_id"]
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    token, session_user, error = validate_token()

    if error:
        return error

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET is_active = 0
            WHERE token = ?
            """,
            (token,),
        )
        conn.commit()

    return jsonify({
        "ok": True,
        "message": "logged_out"
    })


@app.route("/api/rentals/request", methods=["POST"])
def request_rental():
    _, session_user, error = validate_token(required_role="customer")

    if error:
        return error

    data = request.get_json(silent=True) or {}
    station_id = (data.get("station_id") or "").strip()
    bike_id = (data.get("bike_id") or "").strip()

    if not station_id or not bike_id:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    with get_connection() as conn:
        station = conn.execute(
            """
            SELECT station_id
            FROM stations
            WHERE station_id = ?
            """,
            (station_id,),
        ).fetchone()

        if not station:
            return jsonify({
                "ok": False,
                "reason": "invalid_station"
            }), 400

        # Keep it simple for now:
        # we will add station_offline checks later when heartbeat exists.

        active_user_rental = conn.execute(
            """
            SELECT rental_id
            FROM rentals
            WHERE user_id = ? AND status = 'active'
            """,
            (session_user["user_id"],),
        ).fetchone()

        if active_user_rental:
            safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={
                    "user_id": session_user["user_id"],
                    "bike_id": bike_id,
                    "reason": "user_has_active_rental",
                },
            )
            return jsonify({
                "ok": True,
                "approved": False,
                "reason": "user_has_active_rental"
            })

        bike = conn.execute(
            """
            SELECT bike_id, status, current_station_id
            FROM bikes
            WHERE bike_id = ?
            """,
            (bike_id,),
        ).fetchone()

        if not bike:
            safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={
                    "user_id": session_user["user_id"],
                    "bike_id": bike_id,
                    "reason": "bike_not_available",
                },
            )
            return jsonify({
                "ok": True,
                "approved": False,
                "reason": "bike_not_available"
            })

        if bike["status"] != "docked":
            safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={
                    "user_id": session_user["user_id"],
                    "bike_id": bike_id,
                    "reason": "bike_not_available",
                },
            )
            return jsonify({
                "ok": True,
                "approved": False,
                "reason": "bike_not_available"
            })

        if bike["current_station_id"] != station_id:
            safe_log_event(
                source=station_id,
                event_type="RENTAL_REQUEST_DENIED",
                payload={
                    "user_id": session_user["user_id"],
                    "bike_id": bike_id,
                    "reason": "bike_not_at_station",
                },
            )
            return jsonify({
                "ok": True,
                "approved": False,
                "reason": "bike_not_at_station"
            })

    safe_log_event(
        source=station_id,
        event_type="RENTAL_APPROVED",
        payload={
            "user_id": session_user["user_id"],
            "bike_id": bike_id,
        },
    )

    return jsonify({
        "ok": True,
        "approved": True
    })

@app.route("/api/rentals/start", methods=["POST"])
def start_rental():
    _, session_user, error = validate_token(required_role="customer")

    if error:
        return error

    data = request.get_json(silent=True) or {}
    station_id = (data.get("station_id") or "").strip()
    bike_id = (data.get("bike_id") or "").strip()
    payment_method = (data.get("payment_method") or "").strip()

    if not station_id or not bike_id or not payment_method:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    if payment_method not in ("station_card", "mobile_web"):
        return jsonify({
            "ok": False,
            "reason": "invalid_payment_method"
        }), 400

    with get_connection() as conn:
        active_user_rental = conn.execute(
            """
            SELECT rental_id
            FROM rentals
            WHERE user_id = ? AND status = 'active'
            """,
            (session_user["user_id"],),
        ).fetchone()

        if active_user_rental:
            return jsonify({
                "ok": False,
                "reason": "user_has_active_rental"
            }), 409

        bike = conn.execute(
            """
            SELECT bike_id, status, current_station_id
            FROM bikes
            WHERE bike_id = ?
            """,
            (bike_id,),
        ).fetchone()

        if not bike or bike["status"] != "docked":
            return jsonify({
                "ok": False,
                "reason": "bike_not_available"
            }), 409

        if bike["current_station_id"] != station_id:
            return jsonify({
                "ok": False,
                "reason": "bike_not_at_station"
            }), 409

        rental_id = str(uuid4())
        authorized_at = utc_iso(utc_now())
        start_time = authorized_at

        conn.execute(
            """
            INSERT INTO rentals (
                rental_id,
                user_id,
                bike_id,
                start_station_id,
                start_time,
                payment_method,
                payment_status,
                payment_authorized_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'authorized', ?, 'active')
            """,
            (
                rental_id,
                session_user["user_id"],
                bike_id,
                station_id,
                start_time,
                payment_method,
                authorized_at,
            ),
        )

        conn.execute(
            """
            UPDATE bikes
            SET status = 'rented',
                current_station_id = NULL
            WHERE bike_id = ?
            """,
            (bike_id,),
        )

        conn.execute(
            """
            UPDATE stations
            SET dock_occupied = 0
            WHERE station_id = ?
            """,
            (station_id,),
        )

        conn.commit()

    # Hardware unlock now happens on the station Pi when it receives
    # RENTAL_APPROVED over LoRa. Mobile-web rentals rely on the user
    # walking up to the kiosk; the unlock fires there, not here.

    safe_log_event(
        source=station_id,
        event_type="PAYMENT_AUTHORIZED",
        payload={
            "rental_id": rental_id,
            "user_id": session_user["user_id"],
            "bike_id": bike_id,
            "payment_method": payment_method,
        },
    )

    safe_log_event(
        source=station_id,
        event_type="RENTAL_STARTED",
        payload={
            "rental_id": rental_id,
            "user_id": session_user["user_id"],
            "bike_id": bike_id,
            "start_station_id": station_id,
            "start_time": start_time,
        },
    )

    return jsonify({
        "ok": True,
        "rental_id": rental_id,
        "user_id": session_user["user_id"],
        "bike_id": bike_id,
        "start_station_id": station_id,
        "start_time": start_time,
        "status": "active",
        "payment_method": payment_method,
        "payment_status": "authorized"
    }), 201

@app.route("/api/rentals/complete", methods=["POST"])
def complete_rental():
    _, session_user, error = validate_token(required_role="station_service")

    if error:
        return error

    data = request.get_json(silent=True) or {}
    station_id = (data.get("station_id") or "").strip()
    bike_id = (data.get("bike_id") or "").strip()

    if not station_id or not bike_id:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    if session_user["bound_station_id"] != station_id:
        return jsonify({
            "ok": False,
            "reason": "wrong_station_token"
        }), 403

    # Reed switches are not installed yet; bypass hardware return checks.
    power_connected = True
    lock_confirmed = True

    with get_connection() as conn:
        rental = conn.execute(
            """
            SELECT r.rental_id, r.user_id, r.start_time, r.payment_method, r.payment_status,
                   u.name AS user_name
            FROM rentals r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.bike_id = ? AND r.status = 'active'
            """,
            (bike_id,),
        ).fetchone()

        if not rental:
            return jsonify({
                "ok": True,
                "completed": False,
                "reason": "no_active_rental"
            })

        end_time = utc_iso(utc_now())
        duration_minutes = calculate_duration_minutes(rental["start_time"], end_time)
        simulated_cost = calculate_cost(duration_minutes, PRICING_RATE_PER_MINUTE, MINIMUM_CHARGE)

        user_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?", (rental["user_id"],)
        ).fetchone()
        prior_balance = float(user_row["balance"] or 0.0) if user_row else 0.0
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
            (
                station_id,
                end_time,
                duration_minutes,
                simulated_cost,
                end_time,
                rental["rental_id"],
            ),
        )

        conn.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (balance_remaining, rental["user_id"]),
        )

        conn.execute(
            """
            UPDATE bikes
            SET status = 'docked',
                current_station_id = ?
            WHERE bike_id = ?
            """,
            (station_id, bike_id),
        )

        conn.execute(
            """
            UPDATE stations
            SET dock_occupied = 1,
                power_connected = 1,
                lock_confirmed = 1
            WHERE station_id = ?
            """,
            (station_id,),
        )

        conn.commit()

    safe_log_event(
        source=station_id,
        event_type="PAYMENT_CAPTURED",
        payload={
            "rental_id": rental["rental_id"],
            "bike_id": bike_id,
            "payment_method": rental["payment_method"],
            "simulated_cost": simulated_cost,
        },
    )

    safe_log_event(
        source=station_id,
        event_type="RENTAL_COMPLETED",
        payload={
            "rental_id": rental["rental_id"],
            "bike_id": bike_id,
            "end_station_id": station_id,
            "duration_minutes": duration_minutes,
            "simulated_cost": simulated_cost,
            "power_connected": True,
            "lock_confirmed": True,
        },
    )

    return jsonify({
        "ok": True,
        "completed": True,
        "rental_id": rental["rental_id"],
        "user_name": rental["user_name"],
        "duration_minutes": duration_minutes,
        "simulated_cost": simulated_cost,
        "balance_remaining": balance_remaining,
        "currency": "GTQ",
        "payment_method": rental["payment_method"],
        "payment_status": "captured"
    })

@app.route("/api/admin/state", methods=["GET"])
def admin_state():
    _, session_user, error = validate_token(required_role="admin")

    if error:
        return error

    with get_connection() as conn:
        stations = [
            dict(row) for row in conn.execute(
                """
                SELECT station_id, name, is_online, dock_occupied,
                       power_connected, lock_confirmed, last_heartbeat
                FROM stations
                ORDER BY station_id
                """
            ).fetchall()
        ]

        for station in stations:
            computed_is_online = 1 if is_station_online(station.get("last_heartbeat")) else 0
            if int(station.get("is_online") or 0) != computed_is_online:
                conn.execute(
                    """
                    UPDATE stations
                    SET is_online = ?
                    WHERE station_id = ?
                    """,
                    (computed_is_online, station["station_id"]),
                )
                station["is_online"] = computed_is_online

        conn.commit()

        bikes = [
            dict(row) for row in conn.execute(
                """
                SELECT bike_id, status, current_station_id, last_lat, last_lon, last_gps_time
                FROM bikes
                ORDER BY bike_id
                """
            ).fetchall()
        ]

        active_rentals = [
            dict(row) for row in conn.execute(
                """
                SELECT rental_id, user_id, bike_id, start_station_id, start_time, status,
                       payment_method, payment_status, payment_authorized_at, geofence_breached
                FROM rentals
                WHERE status = 'active'
                ORDER BY start_time DESC
                """
            ).fetchall()
        ]

        completed_rentals = [
            dict(row) for row in conn.execute(
                """
                SELECT rental_id, user_id, bike_id, start_station_id, end_station_id,
                       start_time, end_time, duration_minutes, simulated_cost, status,
                       payment_method, payment_status, payment_authorized_at, payment_captured_at,
                       geofence_breached
                FROM rentals
                WHERE status = 'completed'
                ORDER BY end_time DESC
                LIMIT 10
                """
            ).fetchall()
        ]

        recent_events = [
            dict(row) for row in conn.execute(
                """
                SELECT event_id, timestamp, source, event_type, payload
                FROM events
                WHERE event_type != 'STATION_HEARTBEAT'
                ORDER BY timestamp DESC, event_id DESC
                LIMIT 20
                """
            ).fetchall()
        ]

    return jsonify({
        "ok": True,
        "stations": stations,
        "bikes": bikes,
        "active_rentals": active_rentals,
        "completed_rentals": completed_rentals,
        "recent_events": recent_events
    })

@app.route("/api/admin/bike/<bike_id>/track", methods=["GET"])
def admin_bike_track_api(bike_id):
    if not get_admin_session():
        return jsonify({"ok": False, "reason": "unauthorized"}), 401

    with get_connection() as conn:
        bike = conn.execute(
            "SELECT bike_id, status, last_lat, last_lon, last_gps_time FROM bikes WHERE bike_id = ?",
            (bike_id,),
        ).fetchone()

        if not bike:
            return jsonify({"ok": False, "reason": "bike_not_found"}), 404

        bike = dict(bike)

        active_rental = conn.execute(
            "SELECT rental_id FROM rentals WHERE bike_id = ? AND status = 'active' LIMIT 1",
            (bike_id,),
        ).fetchone()

        if active_rental:
            pings = conn.execute(
                """
                SELECT lat, lon, timestamp
                FROM gps_pings
                WHERE rental_id = ?
                ORDER BY timestamp ASC
                """,
                (active_rental["rental_id"],),
            ).fetchall()
            active_rental_id = active_rental["rental_id"]
        else:
            pings = conn.execute(
                """
                SELECT lat, lon, timestamp
                FROM gps_pings
                WHERE bike_id = ?
                ORDER BY ping_id DESC
                LIMIT 30
                """,
                (bike_id,),
            ).fetchall()
            pings = list(reversed(pings))
            active_rental_id = None

    return jsonify({
        "ok": True,
        "bike": bike,
        "pings": [dict(p) for p in pings],
        "active_rental_id": active_rental_id,
        "geofence": {
            "center_lat": GEOFENCE_CENTER_LAT,
            "center_lon": GEOFENCE_CENTER_LON,
            "radius_m": GEOFENCE_RADIUS_M,
        },
    })


@app.route("/admin/rentals/<rental_id>/track", methods=["GET"])
def admin_rental_track_page(rental_id):
    admin_auth = get_admin_session()
    if not admin_auth:
        return redirect(url_for("admin_login_page", notice="session_expired"))

    with get_connection() as conn:
        rental = conn.execute(
            """
            SELECT r.rental_id, r.user_id, r.bike_id, r.start_station_id, r.end_station_id,
                   r.start_time, r.end_time, r.duration_minutes, r.simulated_cost, r.status,
                   r.geofence_breached, r.first_breach_at,
                   u.name AS user_name
            FROM rentals r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.rental_id = ?
            """,
            (rental_id,),
        ).fetchone()

        if not rental:
            return redirect(url_for("admin_dashboard_page"))

        rental = dict(rental)

        pings = conn.execute(
            """
            SELECT lat, lon, timestamp
            FROM gps_pings
            WHERE rental_id = ?
            ORDER BY timestamp ASC
            """,
            (rental_id,),
        ).fetchall()

    return no_store_html_response(render_template(
        "admin/rental_track.html",
        admin_name=admin_auth.get("name") or "Admin",
        rental=rental,
        pings_json=json.dumps([dict(p) for p in pings]),
        geofence_json=json.dumps({
            "center_lat": GEOFENCE_CENTER_LAT,
            "center_lon": GEOFENCE_CENTER_LON,
            "radius_m": GEOFENCE_RADIUS_M,
        }),
    ))


# --- GPS track export stub (columns TBD) ------------------------------------
# @app.route("/admin/export/gps_track/<rental_id>.csv", methods=["GET"])
# def export_gps_track(rental_id): ...


@app.route("/api/stations/<station_id>/status", methods=["GET"])
def station_status(station_id):
    with get_connection() as conn:
        station = conn.execute(
            """
            SELECT station_id, name, is_online, dock_occupied,
                   power_connected, lock_confirmed, last_heartbeat
            FROM stations
            WHERE station_id = ?
            """,
            (station_id,),
        ).fetchone()

        if not station:
            return jsonify({
                "ok": False,
                "reason": "invalid_station"
            }), 404

        station = dict(station)
        computed_is_online = 1 if is_station_online(station.get("last_heartbeat")) else 0
        if int(station.get("is_online") or 0) != computed_is_online:
            conn.execute(
                """
                UPDATE stations
                SET is_online = ?
                WHERE station_id = ?
                """,
                (computed_is_online, station_id),
            )
            conn.commit()
            station["is_online"] = computed_is_online

        available_bikes = [
            dict(row) for row in conn.execute(
                """
                SELECT bike_id, status, current_station_id
                FROM bikes
                WHERE current_station_id = ?
                  AND status = 'docked'
                ORDER BY bike_id
                """,
                (station_id,),
            ).fetchall()
        ]

    return jsonify({
        "ok": True,
        "station": station,
        "available_bikes": available_bikes,
        "available_count": len(available_bikes)
    })


@app.route("/api/stations/heartbeat", methods=["POST"])
def station_heartbeat():
    _, session_user, error = validate_token(required_role="station_service")

    if error:
        return error

    data = request.get_json(silent=True) or {}
    station_id = (data.get("station_id") or "").strip()
    dock_occupied_raw = data.get("dock_occupied")

    if not station_id or dock_occupied_raw is None:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    if session_user["bound_station_id"] != station_id:
        return jsonify({
            "ok": False,
            "reason": "wrong_station_token"
        }), 403

    if isinstance(dock_occupied_raw, bool):
        dock_occupied = 1 if dock_occupied_raw else 0
    elif isinstance(dock_occupied_raw, int):
        if dock_occupied_raw not in (0, 1):
            return jsonify({
                "ok": False,
                "reason": "missing_fields"
            }), 400
        dock_occupied = dock_occupied_raw
    elif isinstance(dock_occupied_raw, str):
        normalized = dock_occupied_raw.strip().lower()
        if normalized in ("1", "true"):
            dock_occupied = 1
        elif normalized in ("0", "false"):
            dock_occupied = 0
        else:
            return jsonify({
                "ok": False,
                "reason": "missing_fields"
            }), 400
    else:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    # Optional hardware state from reed-switch signals (LoRa packet from station).
    # If not sent (e.g. old station firmware), keep the current DB value.
    def _parse_bool_field(raw) -> int | None:
        """Return 1, 0, or None if the field was not provided."""
        if raw is None:
            return None
        if isinstance(raw, bool):
            return 1 if raw else 0
        if isinstance(raw, int):
            return 1 if raw else 0
        if isinstance(raw, str):
            return 1 if raw.strip().lower() in ("1", "true") else 0
        return None

    power_connected_val = _parse_bool_field(data.get("power_connected"))
    lock_confirmed_val = _parse_bool_field(data.get("lock_confirmed"))

    heartbeat_time = utc_iso(utc_now())

    with get_connection() as conn:
        station = conn.execute(
            """
            SELECT station_id, power_connected, lock_confirmed
            FROM stations
            WHERE station_id = ?
            """,
            (station_id,),
        ).fetchone()

        if not station:
            return jsonify({
                "ok": False,
                "reason": "invalid_station"
            }), 400

        # Fall back to current DB value if the field was not included in the heartbeat.
        power_connected = power_connected_val if power_connected_val is not None else station["power_connected"]
        lock_confirmed = lock_confirmed_val if lock_confirmed_val is not None else station["lock_confirmed"]

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
            (heartbeat_time, dock_occupied, power_connected, lock_confirmed, station_id),
        )
        conn.commit()

    safe_log_event(
        source=station_id,
        event_type="STATION_HEARTBEAT",
        payload={
            "dock_occupied": dock_occupied,
            "power_connected": bool(power_connected),
            "lock_confirmed": bool(lock_confirmed),
        },
    )

    return jsonify({
        "ok": True,
        "station_id": station_id,
        "last_heartbeat": heartbeat_time,
        "dock_occupied": dock_occupied,
        "power_connected": bool(power_connected),
        "lock_confirmed": bool(lock_confirmed),
        "is_online": 1,
    })


@app.route("/admin/topup-codes/generate", methods=["GET", "POST"])
def admin_topup_codes_generate():
    admin_auth = get_admin_session()
    if not admin_auth:
        return redirect(url_for("admin_login_page", notice="session_expired"))

    generated = []
    error_message = None

    if request.method == "POST":
        try:
            count = int(request.form.get("count") or 0)
            amount = float(request.form.get("amount") or 0)
        except (TypeError, ValueError):
            error_message = "Ingresa un número de códigos y un monto válidos."
            count, amount = 0, 0

        if not error_message:
            if count < 1 or count > 200:
                error_message = "El número de códigos debe ser entre 1 y 200."
            elif amount <= 0:
                error_message = "El monto debe ser mayor a 0."
            else:
                with get_connection() as conn:
                    generated = topup_service.generate_codes(conn, count, amount)

    return render_template(
        "admin/topup_codes.html",
        admin_name=admin_auth.get("name") or "Admin",
        generated=generated,
        error_message=error_message,
    )


@app.route("/mobile/topup", methods=["GET", "POST"])
def mobile_topup_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    success_message = None
    error_message = None

    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        if not code:
            error_message = "Ingresa un código de recarga."
        else:
            with get_connection() as conn:
                result = topup_service.redeem_code(conn, mobile_auth["user_id"], code)
            if result["success"]:
                success_message = f"¡Recarga exitosa! Se acreditaron Q{result['amount']:.2f} a tu cuenta."
            else:
                reason = result["error"] or "invalid_code"
                msgs = {
                    "invalid_code": "Código no válido. Revisa el código e intenta de nuevo.",
                    "already_redeemed": "Este código ya fue utilizado.",
                }
                error_message = msgs.get(reason, "No se pudo procesar la recarga.")

    balance = get_mobile_user_balance(mobile_auth["user_id"])

    return render_template(
        "mobile/topup.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        current_balance=balance,
        balance=balance,
        active_tab="account",
        success_message=success_message,
        error_message=error_message,
    )


@app.route("/mobile/account", methods=["GET"])
def mobile_account_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    user_id = mobile_auth["user_id"]
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username, balance, created_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    balance = float(row["balance"] or 0.0) if row else 0.0
    username = row["username"] if row else ""
    member_since = (row["created_at"] or "")[:10] if row else ""

    return render_template(
        "mobile/account.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        username=username,
        balance=balance,
        member_since=member_since,
        active_tab="account",
    )


@app.route("/mobile/rides", methods=["GET"])
def mobile_rides_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    user_id = mobile_auth["user_id"]
    active_rental = sync_mobile_active_rental_from_db(mobile_auth)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.rental_id, r.bike_id,
                   r.start_station_id, r.end_station_id,
                   r.start_time, r.duration_minutes, r.simulated_cost,
                   s1.name AS start_station_name, s2.name AS end_station_name
            FROM rentals r
            LEFT JOIN stations s1 ON s1.station_id = r.start_station_id
            LEFT JOIN stations s2 ON s2.station_id = r.end_station_id
            WHERE r.user_id = ?
              AND r.status = 'completed'
            ORDER BY r.start_time DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()

    rides = []
    for row in rows:
        ride = dict(row)
        raw_ts = ride.get("start_time") or ""
        ride["start_time_fmt"] = raw_ts[:16].replace("T", " ") if raw_ts else "—"
        rides.append(ride)

    balance = get_mobile_user_balance(user_id)

    return render_template(
        "mobile/rides.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        balance=balance,
        active_tab="rides",
        rides=rides,
        active_rental=active_rental,
    )


if __name__ == "__main__":
    # init_db + LoRa startup already happened at import time above so the
    # receiver thread is alive and listening by the time Flask binds the port.
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)