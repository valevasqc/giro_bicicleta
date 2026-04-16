"""Kiosk routes — Flask blueprint served by the station Pi.

These were previously /station/* routes on central/app.py. They now live
on the Pi and talk to central strictly over LoRa.

Flow shape for any route that needs a central reply:

1. The POST handler fires a LoRa message via the sender attached to the
   Flask app (current_app.extensions["lora_sender"]) and records a
   "pending" marker in station.state.
2. It redirects the browser to the corresponding result route
   (e.g. /station/rental-request). That result route renders either:
   - the final template, if INBOX already has the matching reply, or
   - kiosk/waiting.html, which polls /station/status every second and
     redirects itself once the reply lands.
3. The LoRa receiver thread drops replies into state.INBOX out of band.

Until central's LoRa receiver is wired up, the waiting page will spin
until LORA_REPLY_TIMEOUT_SECONDS elapses — no crashes, just a visible
timeout. That's the explicit next step.
"""

from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

try:
    from common.lora_protocol import (
        BIKE_DOCKED,
        BIKE_RELEASED,
        LOGIN_FAIL,
        LOGIN_OK,
        RENTAL_APPROVED,
        RENTAL_DENIED,
        RENTAL_REQUEST,
        RETURN_COMPLETE,
        format_message,
    )
except ImportError:  # fallback if someone runs station directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from common.lora_protocol import (
        BIKE_DOCKED,
        BIKE_RELEASED,
        LOGIN_FAIL,
        LOGIN_OK,
        RENTAL_APPROVED,
        RENTAL_DENIED,
        RENTAL_REQUEST,
        RETURN_COMPLETE,
        format_message,
    )

from .. import state
from ..config import (
    LORA_REPLY_TIMEOUT_SECONDS,
    STATION_BIKE_ID,
    STATION_ID,
    STATION_NAME,
)

bp = Blueprint("kiosk", __name__)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lora_send(message: str) -> None:
    current_app.extensions["lora_sender"].send(message)


def _reason_to_human(reason: str) -> str:
    mapping = {
        "missing_credentials": "Ingresa usuario y contraseña para continuar.",
        "invalid_credentials": "Usuario o contraseña incorrectos.",
        "account_inactive": "Esta cuenta está inactiva. Contacta a soporte.",
        "user_has_active_rental": "Ya tienes un viaje activo.",
        "bike_not_available": "La bicicleta ya no está disponible.",
        "bike_not_at_station": "La bicicleta seleccionada ya no está en esta estación.",
        "no_bikes_available": "No hay bicicletas disponibles en este momento.",
        "power_not_connected": "La bicicleta no está conectada a la fuente de carga.",
        "lock_not_confirmed": "El candado no está cerrado correctamente.",
        "timeout": "La estación no recibió respuesta de la central. Intenta de nuevo.",
        "station_unreachable": "No se pudo consultar el estado de la estación.",
    }
    return mapping.get(reason, "Ocurrió un error inesperado. Intenta de nuevo.")


def _consume_response_pair(ok_type: str, fail_type: str):
    """Take whichever of ok/fail arrived first (if any).

    Returns (msg_type, fields) or (None, None) if nothing is in the inbox.
    """
    ok = state.peek_inbound(ok_type)
    fail = state.peek_inbound(fail_type)
    if ok and (not fail or ok["received_at"] <= fail["received_at"]):
        state.take_inbound(ok_type)
        return ok_type, ok["fields"]
    if fail:
        state.take_inbound(fail_type)
        return fail_type, fail["fields"]
    return None, None


def _render_waiting(kind: str, result_url: str):
    return render_template(
        "kiosk/waiting.html",
        station_id=STATION_ID,
        station_name=STATION_NAME,
        pending_kind=kind,
        poll_url=url_for("kiosk.station_status"),
        result_url=result_url,
        timeout_seconds=int(LORA_REPLY_TIMEOUT_SECONDS),
    )


# ---------------------------------------------------------------------
# Idle / login
# ---------------------------------------------------------------------

@bp.route("/", endpoint="station_home")
def station_home():
    return render_template("kiosk/idle.html", station_id=STATION_ID)


@bp.route("/station/login", methods=["GET", "POST"], endpoint="station_login")
def station_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template(
                "kiosk/login.html",
                station_id=STATION_ID,
                error_message=_reason_to_human("missing_credentials"),
                username_value=username,
                notice_message=None,
            )

        # Clear any stale replies from a previous attempt so we don't
        # act on outdated INBOX entries.
        for mt in (LOGIN_OK, LOGIN_FAIL, RENTAL_APPROVED, RENTAL_DENIED):
            state.take_inbound(mt)

        state.set_pending("login", {"username": username, "bike_id": STATION_BIKE_ID})

        _lora_send(format_message(
            RENTAL_REQUEST,
            STATION_ID,
            STATION_BIKE_ID,
            username,
            password,
            _utc_iso(),
        ))

        return redirect(url_for("kiosk.station_rental_request_result"))

    notice = request.args.get("notice") or ""
    notice_message = None
    if notice == "session_expired":
        notice_message = "Tu sesión expiró. Inicia sesión nuevamente."

    return render_template(
        "kiosk/login.html",
        station_id=STATION_ID,
        error_message=None,
        username_value="",
        notice_message=notice_message,
    )


# ---------------------------------------------------------------------
# Rental request result
# ---------------------------------------------------------------------

@bp.route("/station/rental-request", methods=["GET"], endpoint="station_rental_request_result")
def station_rental_request_result():
    # LOGIN_FAIL and RENTAL_DENIED are terminal failures.
    fail = state.peek_inbound(LOGIN_FAIL) or state.peek_inbound(RENTAL_DENIED)
    if fail:
        fail_type = LOGIN_FAIL if state.peek_inbound(LOGIN_FAIL) else RENTAL_DENIED
        state.take_inbound(fail_type)
        state.take_inbound(LOGIN_OK)
        state.take_inbound(RENTAL_APPROVED)
        state.clear_pending()
        fields = fail["fields"]
        reason = fields[1] if len(fields) > 1 else "invalid_credentials"
        return render_template(
            "kiosk/request_result.html",
            station_id=STATION_ID,
            user_name="Cliente",
            approved=False,
            bike_id=None,
            reason=reason,
            reason_message=_reason_to_human(reason),
        )

    login_ok = state.peek_inbound(LOGIN_OK)
    rental_approved = state.peek_inbound(RENTAL_APPROVED)

    if login_ok and rental_approved:
        state.take_inbound(LOGIN_OK)
        state.take_inbound(RENTAL_APPROVED)

        ok_fields = login_ok["fields"]
        # LOGIN_OK|station_id|user_id|name|token|balance|ts
        session["customer_auth"] = {
            "user_id": ok_fields[1] if len(ok_fields) > 1 else None,
            "name": ok_fields[2] if len(ok_fields) > 2 else "Cliente",
            "token": ok_fields[3] if len(ok_fields) > 3 else None,
            "balance": ok_fields[4] if len(ok_fields) > 4 else None,
        }
        session["approved_request"] = {"bike_id": STATION_BIKE_ID}
        state.clear_pending()

        return render_template(
            "kiosk/request_result.html",
            station_id=STATION_ID,
            user_name=session["customer_auth"].get("name") or "Cliente",
            approved=True,
            bike_id=STATION_BIKE_ID,
            reason=None,
            reason_message="",
        )

    # Still waiting on central.
    return _render_waiting(
        kind="login",
        result_url=url_for("kiosk.station_rental_request_result"),
    )


# ---------------------------------------------------------------------
# Payment (authorization only — no money moves in MVP)
# ---------------------------------------------------------------------

@bp.route("/station/payment", methods=["GET", "POST"], endpoint="station_payment")
def station_payment():
    customer_auth = session.get("customer_auth") or {}
    approved_request = session.get("approved_request") or {}
    bike_id = approved_request.get("bike_id")

    if not customer_auth.get("user_id"):
        return redirect(url_for("kiosk.station_login", notice="session_expired"))
    if not bike_id:
        return redirect(url_for("kiosk.station_rental_request_result"))

    if request.method == "POST":
        # Unlock the dock physically, then tell central the bike has left.
        gpio = current_app.extensions.get("gpio")
        if gpio is not None:
            from ..config import UNLOCK_DURATION_SECONDS
            gpio.unlock_for_seconds(UNLOCK_DURATION_SECONDS)

        _lora_send(format_message(
            BIKE_RELEASED,
            STATION_ID,
            bike_id,
            customer_auth.get("user_id") or "",
            _utc_iso(),
        ))

        session["active_rental"] = {
            "bike_id": bike_id,
            "payment_status": "authorized",
        }
        session.pop("approved_request", None)
        return redirect(url_for("kiosk.station_unlocking"))

    return render_template(
        "kiosk/payment.html",
        station_id=STATION_ID,
        station_name=STATION_NAME,
        user_name=customer_auth.get("name") or "Cliente",
        bike_id=bike_id,
    )


# ---------------------------------------------------------------------
# Unlock / ride / return
# ---------------------------------------------------------------------

@bp.route("/station/unlocking", methods=["GET"], endpoint="station_unlocking")
def station_unlocking():
    active_rental = session.get("active_rental") or {}
    if not active_rental.get("bike_id"):
        return redirect(url_for("kiosk.station_home"))

    return render_template(
        "kiosk/unlocking.html",
        station_id=STATION_ID,
        station_name=STATION_NAME,
        bike_id=active_rental["bike_id"],
    )


@bp.route("/station/ride-active", methods=["GET"], endpoint="station_ride_active")
def station_ride_active():
    active_rental = session.get("active_rental") or {}
    if not active_rental.get("bike_id"):
        return redirect(url_for("kiosk.station_home"))

    return render_template(
        "kiosk/ride_active.html",
        station_id=STATION_ID,
        station_name=STATION_NAME,
        bike_id=active_rental["bike_id"],
        payment_status=active_rental.get("payment_status") or "authorized",
    )


@bp.route("/station/complete-return", methods=["POST"], endpoint="station_complete_return")
def station_complete_return():
    active_rental = session.get("active_rental") or {}
    bike_id = active_rental.get("bike_id")
    if not bike_id:
        return redirect(url_for("kiosk.station_home"))

    state.take_inbound(RETURN_COMPLETE)
    state.set_pending("return", {"bike_id": bike_id})

    _lora_send(format_message(
        BIKE_DOCKED,
        STATION_ID,
        bike_id,
        _utc_iso(),
    ))

    # Render a waiting page that will redirect to this same endpoint (GET)
    # once central replies. GET handler below consumes RETURN_COMPLETE.
    return _render_waiting(
        kind="return",
        result_url=url_for("kiosk.station_return_result"),
    )


@bp.route("/station/return-result", methods=["GET"], endpoint="station_return_result")
def station_return_result():
    reply = state.peek_inbound(RETURN_COMPLETE)
    if reply:
        state.take_inbound(RETURN_COMPLETE)
        state.clear_pending()
        # RETURN_COMPLETE|station_id|bike_id|name|duration_minutes|cost|balance_remaining|ts
        f = reply["fields"]
        summary = {
            "bike_id": f[1] if len(f) > 1 else "",
            "user_name": f[2] if len(f) > 2 else "Cliente",
            "duration_minutes": f[3] if len(f) > 3 else None,
            "simulated_cost": f[4] if len(f) > 4 else None,
            "balance_remaining": f[5] if len(f) > 5 else None,
            "currency": "GTQ",
            "payment_status": "captured",
        }
        # Clear ride state so the kiosk goes back to idle after the user
        # taps "Finalizar".
        session.pop("active_rental", None)
        session.pop("customer_auth", None)
        return render_template(
            "kiosk/return_summary.html",
            station_id=STATION_ID,
            station_name=STATION_NAME,
            summary=summary,
        )

    pending = state.get_pending()
    if pending is None:
        # User probably hit refresh after state expired.
        return redirect(url_for("kiosk.station_home"))

    return _render_waiting(
        kind="return",
        result_url=url_for("kiosk.station_return_result"),
    )


# ---------------------------------------------------------------------
# Logout / status / error
# ---------------------------------------------------------------------

@bp.route("/station/logout", methods=["POST"], endpoint="station_logout")
def station_logout():
    session.pop("customer_auth", None)
    session.pop("approved_request", None)
    session.pop("active_rental", None)
    state.reset_all()
    return redirect(url_for("kiosk.station_home"))


@bp.route("/api/stations/<station_id>/status", methods=["GET"], endpoint="station_api_status")
def station_api_status(station_id):
    """Local status endpoint polled by idle.js. Derived from GPIO, not central."""
    if station_id != STATION_ID:
        return jsonify({"ok": False, "reason": "unknown_station"}), 404

    gpio = current_app.extensions.get("gpio")
    dock_occupied = bool(gpio.read_dock_occupied()) if gpio else False
    charge_connected = bool(gpio.read_charge_connected()) if gpio else False
    available = dock_occupied and charge_connected

    available_bikes = [{"bike_id": STATION_BIKE_ID}] if available else []
    return jsonify({
        "ok": True,
        "station": {"station_id": STATION_ID, "name": STATION_NAME},
        "available_count": len(available_bikes),
        "available_bikes": available_bikes,
        "dock_occupied": dock_occupied,
        "charge_connected": charge_connected,
    })


@bp.route("/station/status", methods=["GET"], endpoint="station_status")
def station_status():
    """JSON endpoint polled by waiting.html to decide when to redirect."""
    import time

    pending = state.get_pending()
    if pending is None:
        return jsonify({"pending": False, "outcome": "idle"})

    kind = pending["kind"]
    age = time.time() - pending["started_at"]

    def _has(mt):
        return state.peek_inbound(mt) is not None

    if kind == "login":
        if _has(LOGIN_FAIL) or _has(RENTAL_DENIED):
            return jsonify({"pending": False, "outcome": "denied"})
        if _has(LOGIN_OK) and _has(RENTAL_APPROVED):
            return jsonify({"pending": False, "outcome": "approved"})
    elif kind == "return":
        if _has(RETURN_COMPLETE):
            return jsonify({"pending": False, "outcome": "complete"})

    if age > LORA_REPLY_TIMEOUT_SECONDS:
        state.clear_pending()
        return jsonify({"pending": False, "outcome": "timeout"})

    return jsonify({"pending": True, "kind": kind, "age": age})
