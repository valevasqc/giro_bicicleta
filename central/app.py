import secrets
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, render_template, redirect, session, url_for, make_response
from werkzeug.security import check_password_hash

try:
    from .database import get_connection, init_db, log_event
    from .pricing import calculate_duration_minutes, calculate_simulated_cost
    from .config import (
        SECRET_KEY,
        STATION_ID,
        STATION_SERVICE_USERNAME,
        STATION_SERVICE_PASSWORD,
        STATION_OFFLINE_AFTER_SECONDS,
        TRACKER_API_KEY,
        STUB_GPIO,
        LOCK_PIN,
        DOCK_PIN,
        CHARGE_PIN,
        UNLOCK_DURATION_SECONDS,
        STUB_DOCK_OCCUPIED,
        STUB_CHARGE_CONNECTED,
    )
    from .gpio_driver import GPIODriver
except ImportError:
    from database import get_connection, init_db, log_event
    from pricing import calculate_duration_minutes, calculate_simulated_cost
    from config import (
        SECRET_KEY,
        STATION_ID,
        STATION_SERVICE_USERNAME,
        STATION_SERVICE_PASSWORD,
        STATION_OFFLINE_AFTER_SECONDS,
        TRACKER_API_KEY,
        STUB_GPIO,
        LOCK_PIN,
        DOCK_PIN,
        CHARGE_PIN,
        UNLOCK_DURATION_SECONDS,
        STUB_DOCK_OCCUPIED,
        STUB_CHARGE_CONNECTED,
    )
    from gpio_driver import GPIODriver

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

gpio = GPIODriver(
    stub=STUB_GPIO,
    lock_pin=LOCK_PIN,
    dock_pin=DOCK_PIN,
    charge_pin=CHARGE_PIN,
    stub_dock_occupied=STUB_DOCK_OCCUPIED,
    stub_charge_connected=STUB_CHARGE_CONNECTED,
)

STATION_SERVICE_TOKEN_CACHE = {}


@app.template_filter("short_rental_id")
def short_rental_id(value):
    rental_id = (value or "").strip()
    if not rental_id:
        return "-"

    return f"R-{rental_id[:8].upper()}"


@app.route("/")
def station_home():
    return render_template("kiosk/idle.html", station_id=STATION_ID)


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


def get_customer_session():
    customer_auth = session.get("customer_auth")
    if not isinstance(customer_auth, dict):
        return None

    if customer_auth.get("role") != "customer":
        return None

    if not customer_auth.get("token"):
        return None

    return customer_auth


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


def sync_station_active_rental_from_db(customer_auth):
    user_id = customer_auth.get("user_id") if isinstance(customer_auth, dict) else None
    active_rental = get_active_rental_for_user(user_id)

    if active_rental:
        session["active_rental"] = active_rental
    else:
        session.pop("active_rental", None)

    return active_rental


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


def get_station_name():
    return get_station_name_by_id(STATION_ID)


def render_station_error_page(message, back_href):
    return render_template(
        "kiosk/station_error.html",
        station_id=STATION_ID,
        station_name=get_station_name(),
        error_message=message,
        back_href=back_href,
    )


def clear_customer_ride_session_data():
    session.pop("customer_auth", None)
    session.pop("approved_request", None)
    session.pop("active_rental", None)


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

    return render_template(
        "mobile/stations.html",
        customer_name=mobile_auth.get("name") or "Cliente",
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

    return render_template(
        "mobile/station_detail.html",
        station_id=station_id,
        station=station,
        bikes=bikes,
        error_message=error_message,
        active_bike_id=active_bike_id,
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
        return render_template(
            "mobile/payment.html",
            station_id=station_id,
            station_name=station_name,
            bike_id=bike_id,
            error_message=reason_to_human_message(reason),
        )

    return render_template(
        "mobile/payment.html",
        station_id=station_id,
        station_name=station_name,
        bike_id=bike_id,
        error_message=None,
    )


@app.route("/mobile/ride-active", methods=["GET"])
def mobile_ride_active_page():
    mobile_auth = get_mobile_customer_session()
    if not mobile_auth:
        return redirect(url_for("mobile_login_page", notice="session_expired"))

    active_rental = sync_mobile_active_rental_from_db(mobile_auth)
    if not active_rental or not active_rental.get("bike_id"):
        return redirect(url_for("mobile_stations_page"))

    return render_template(
        "mobile/ride_active.html",
        customer_name=mobile_auth.get("name") or "Cliente",
        rental=active_rental,
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
            "currency": payload.get("currency") or "GTQ",
            "payment_status": payload.get("payment_status") or "captured",
        }
        clear_mobile_session_data()
        return render_template(
            "mobile/return_summary.html",
            station_id=target_station_id,
            station_name=target_station_name,
            summary=summary,
        )

    reason = payload.get("reason") or "station_unreachable"
    return render_template(
        "mobile/complete_error.html",
        station_id=target_station_id,
        station_name=target_station_name,
        error_message=reason_to_human_message(reason),
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


@app.route("/station/login", methods=["GET", "POST"])
def station_login():
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
                    error_message = "Solo las cuentas de cliente pueden usar este flujo de estación."
                else:
                    session["customer_auth"] = {
                        "token": payload.get("token"),
                        "user_id": payload.get("user_id"),
                        "name": payload.get("name"),
                        "role": payload.get("role"),
                    }
                    return redirect(url_for("station_rental_request_result"))
            else:
                reason = payload.get("reason") or "invalid_credentials"
                error_message = reason_to_human_message(reason)

    return render_template(
        "kiosk/login.html",
        station_id=STATION_ID,
        error_message=error_message,
        username_value=username_value,
        notice_message=notice_message,
    )


@app.route("/station/rental-request", methods=["GET"])
def station_rental_request_result():
    customer_auth = get_customer_session()
    if not customer_auth:
        return redirect(url_for("station_login", notice="session_expired"))

    existing_active_rental = sync_station_active_rental_from_db(customer_auth)
    if existing_active_rental:
        return redirect(url_for("station_ride_active"))

    token = customer_auth["token"]
    user_name = customer_auth.get("name") or "Cliente"

    try:
        status_code, station_payload = call_internal_api("GET", f"/api/stations/{STATION_ID}/status")
    except Exception:
        status_code, station_payload = 500, {"ok": False, "reason": "station_unreachable"}

    if status_code != 200 or not station_payload.get("ok"):
        reason = station_payload.get("reason") or "station_unreachable"
        return render_template(
            "kiosk/request_result.html",
            station_id=STATION_ID,
            user_name=user_name,
            approved=False,
            bike_id=None,
            reason=reason,
            reason_message=reason_to_human_message(reason),
        )

    available_bikes = station_payload.get("available_bikes") or []
    if not available_bikes:
        reason = "no_bikes_available"
        return render_template(
            "kiosk/request_result.html",
            station_id=STATION_ID,
            user_name=user_name,
            approved=False,
            bike_id=None,
            reason=reason,
            reason_message=reason_to_human_message(reason),
        )

    bike_id = available_bikes[0].get("bike_id")
    if not bike_id:
        reason = "bike_not_available"
        return render_template(
            "kiosk/request_result.html",
            station_id=STATION_ID,
            user_name=user_name,
            approved=False,
            bike_id=None,
            reason=reason,
            reason_message=reason_to_human_message(reason),
        )

    try:
        status_code, request_payload = call_internal_api(
            "POST",
            "/api/rentals/request",
            payload={"station_id": STATION_ID, "bike_id": bike_id},
            token=token,
        )
    except Exception:
        status_code, request_payload = 500, {"ok": False, "reason": "station_unreachable"}

    if status_code == 401:
        session.clear()
        return redirect(url_for("station_login", notice="session_expired"))

    approved = bool(request_payload.get("ok") and request_payload.get("approved"))
    reason = request_payload.get("reason")

    if approved:
        session["approved_request"] = {"bike_id": bike_id}
    else:
        session.pop("approved_request", None)

    return render_template(
        "kiosk/request_result.html",
        station_id=STATION_ID,
        user_name=user_name,
        approved=approved,
        bike_id=bike_id if approved else None,
        reason=reason,
        reason_message=reason_to_human_message(reason) if reason else "",
    )


@app.route("/station/payment", methods=["GET", "POST"])
def station_payment():
    customer_auth = get_customer_session()
    if not customer_auth:
        return redirect(url_for("station_login", notice="session_expired"))

    approved_request = session.get("approved_request")
    bike_id = approved_request.get("bike_id") if isinstance(approved_request, dict) else None
    if not bike_id:
        return redirect(url_for("station_rental_request_result"))

    station_name = get_station_name()
    user_name = customer_auth.get("name") or "Cliente"

    if request.method == "POST":
        try:
            status_code, payload = call_internal_api(
                "POST",
                "/api/rentals/start",
                payload={
                    "station_id": STATION_ID,
                    "bike_id": bike_id,
                    "payment_method": "station_card",
                },
                token=customer_auth["token"],
            )
        except Exception:
            status_code, payload = 500, {"ok": False, "reason": "station_unreachable"}

        if status_code == 401:
            session.clear()
            return redirect(url_for("station_login", notice="session_expired"))

        if status_code in (200, 201) and payload.get("ok"):
            session["active_rental"] = {
                "rental_id": payload.get("rental_id"),
                "bike_id": payload.get("bike_id"),
                "start_time": payload.get("start_time"),
                "payment_method": payload.get("payment_method"),
                "payment_status": payload.get("payment_status"),
            }
            session.pop("approved_request", None)
            return redirect(url_for("station_unlocking"))

        reason = payload.get("reason") or "station_unreachable"
        return render_station_error_page(
            reason_to_human_message(reason),
            back_href=url_for("station_payment"),
        )

    return render_template(
        "kiosk/payment.html",
        station_id=STATION_ID,
        station_name=station_name,
        user_name=user_name,
        bike_id=bike_id,
    )


@app.route("/station/unlocking", methods=["GET"])
def station_unlocking():
    customer_auth = get_customer_session()
    if not customer_auth:
        return redirect(url_for("station_login", notice="session_expired"))

    active_rental = sync_station_active_rental_from_db(customer_auth)
    if not active_rental or not active_rental.get("bike_id"):
        return redirect(url_for("station_home"))

    return render_template(
        "kiosk/unlocking.html",
        station_id=STATION_ID,
        station_name=get_station_name(),
        bike_id=active_rental.get("bike_id"),
    )


@app.route("/station/ride-active", methods=["GET"])
def station_ride_active():
    customer_auth = get_customer_session()
    if not customer_auth:
        return redirect(url_for("station_login", notice="session_expired"))

    active_rental = sync_station_active_rental_from_db(customer_auth)
    if not active_rental or not active_rental.get("bike_id"):
        return redirect(url_for("station_home"))

    return render_template(
        "kiosk/ride_active.html",
        station_id=STATION_ID,
        station_name=get_station_name(),
        bike_id=active_rental.get("bike_id"),
        payment_status=active_rental.get("payment_status") or "authorized",
    )


@app.route("/station/complete-return", methods=["POST"])
def station_complete_return():
    customer_auth = get_customer_session()
    if not customer_auth:
        return redirect(url_for("station_login", notice="session_expired"))

    active_rental = sync_station_active_rental_from_db(customer_auth)
    bike_id = active_rental.get("bike_id") if active_rental else None
    if not bike_id:
        return redirect(url_for("station_home"))

    try:
        status_code, payload = complete_with_station_service_retry(
            bike_id,
            power_connected=gpio.read_charge_connected(),
            lock_confirmed=gpio.read_lock_confirmed(),
        )
    except Exception:
        status_code, payload = 500, {"ok": False, "reason": "station_unreachable"}

    if status_code in (200, 201) and payload.get("ok") and payload.get("completed"):
        summary = {
            "bike_id": bike_id,
            "user_name": payload.get("user_name") or "Cliente",
            "duration_minutes": payload.get("duration_minutes"),
            "simulated_cost": payload.get("simulated_cost"),
            "currency": payload.get("currency") or "GTQ",
            "payment_status": payload.get("payment_status") or "captured",
        }
        clear_customer_ride_session_data()
        return render_template(
            "kiosk/return_summary.html",
            station_id=STATION_ID,
            station_name=get_station_name(),
            summary=summary,
        )

    reason = payload.get("reason") or "station_unreachable"
    return render_template(
        "kiosk/complete_error.html",
        station_id=STATION_ID,
        station_name=get_station_name(),
        error_message=reason_to_human_message(reason),
    )


@app.route("/station/logout", methods=["POST"])
def station_logout():
    customer_auth = session.get("customer_auth")
    token = customer_auth.get("token") if isinstance(customer_auth, dict) else None

    if token:
        try:
            call_internal_api("POST", "/api/auth/logout", token=token)
        except Exception:
            pass

    clear_customer_ride_session_data()
    return redirect(url_for("station_home"))


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

    gpio.unlock_for_seconds(UNLOCK_DURATION_SECONDS)

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

    # Hardware return checks (reed-switch signals from station).
    # Both must be True to confirm a valid return.
    power_connected = bool(data.get("power_connected", False))
    lock_confirmed = bool(data.get("lock_confirmed", False))

    if not power_connected:
        safe_log_event(
            source=station_id,
            event_type="RETURN_FAILED",
            payload={"bike_id": bike_id, "reason": "power_not_connected"},
        )
        return jsonify({
            "ok": False,
            "completed": False,
            "reason": "power_not_connected",
        }), 200

    if not lock_confirmed:
        safe_log_event(
            source=station_id,
            event_type="RETURN_FAILED",
            payload={"bike_id": bike_id, "reason": "lock_not_confirmed"},
        )
        return jsonify({
            "ok": False,
            "completed": False,
            "reason": "lock_not_confirmed",
        }), 200

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
        simulated_cost = calculate_simulated_cost(duration_minutes)

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
                SELECT rental_id, user_id, bike_id, start_station_id, start_time, status, payment_method, payment_status, payment_authorized_at
                FROM rentals
                WHERE status = 'active'
                ORDER BY start_time DESC
                """
            ).fetchall()
        ]

        completed_rentals = [
            dict(row) for row in conn.execute(
                """
                SELECT rental_id, user_id, bike_id, start_station_id, end_station_id, start_time, end_time, duration_minutes, simulated_cost, status, payment_method, payment_status, payment_authorized_at, payment_captured_at
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


@app.route("/api/tracker/gps", methods=["POST"])
def tracker_gps_update():
    tracker_key = (request.headers.get("X-Tracker-Key") or "").strip()
    if not tracker_key or tracker_key != TRACKER_API_KEY:
        return jsonify({
            "ok": False,
            "reason": "invalid_tracker_key"
        }), 401

    data = request.get_json(silent=True) or {}
    bike_id = (data.get("bike_id") or "").strip()
    lat_raw = data.get("lat")
    lon_raw = data.get("lon")
    gps_time_raw = data.get("gps_time")

    if not bike_id or lat_raw is None or lon_raw is None:
        return jsonify({
            "ok": False,
            "reason": "missing_fields"
        }), 400

    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "reason": "invalid_coordinates"
        }), 400

    if lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return jsonify({
            "ok": False,
            "reason": "invalid_coordinates"
        }), 400

    if gps_time_raw is None:
        gps_time = utc_iso(utc_now())
    else:
        gps_time = (gps_time_raw or "").strip()
        if not parse_utc_iso(gps_time):
            return jsonify({
                "ok": False,
                "reason": "invalid_gps_time"
            }), 400

    with get_connection() as conn:
        bike = conn.execute(
            """
            SELECT bike_id
            FROM bikes
            WHERE bike_id = ?
            """,
            (bike_id,),
        ).fetchone()

        if not bike:
            return jsonify({
                "ok": False,
                "reason": "bike_not_found"
            }), 404

        conn.execute(
            """
            UPDATE bikes
            SET last_lat = ?,
                last_lon = ?,
                last_gps_time = ?
            WHERE bike_id = ?
            """,
            (lat, lon, gps_time, bike_id),
        )

        # Look up the active rental so we can attach the ping to it.
        active_rental = conn.execute(
            """
            SELECT rental_id
            FROM rentals
            WHERE bike_id = ? AND status = 'active'
            LIMIT 1
            """,
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

    safe_log_event(
        source=bike_id,
        event_type="GPS_UPDATE",
        payload={
            "lat": lat,
            "lon": lon,
            "gps_time": gps_time,
        },
    )

    return jsonify({
        "ok": True,
        "bike_id": bike_id,
        "last_lat": lat,
        "last_lon": lon,
        "last_gps_time": gps_time,
    })

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)