import argparse
import json
import sys
from typing import Dict, Iterable, Optional

import requests

try:
    import serial
except ImportError:
    serial = None

try:
    from .config import (
        TRACKER_API_KEY,
        TRACKER_BACKEND_BASE_URL,
        TRACKER_SERIAL_PORT,
        TRACKER_BAUD_RATE,
    )
except ImportError:
    from config import (
        TRACKER_API_KEY,
        TRACKER_BACKEND_BASE_URL,
        TRACKER_SERIAL_PORT,
        TRACKER_BAUD_RATE,
    )


def parse_packet_line(raw_line: str) -> Dict[str, object]:
    line = raw_line.strip()
    if not line:
        raise ValueError("empty line")

    payload: Dict[str, object]

    if line.startswith("{"):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid json: {exc.msg}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("json line must be an object")

        payload = {
            "bike_id": parsed.get("bike_id"),
            "lat": parsed.get("lat"),
            "lon": parsed.get("lon"),
            "gps_time": parsed.get("gps_time"),
        }
    else:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) not in (3, 4):
            raise ValueError("csv line must be bike_id,lat,lon[,gps_time]")

        payload = {
            "bike_id": parts[0],
            "lat": parts[1],
            "lon": parts[2],
        }
        if len(parts) == 4 and parts[3]:
            payload["gps_time"] = parts[3]

    return validate_payload(payload)


def validate_payload(payload: Dict[str, object]) -> Dict[str, object]:
    bike_id = str(payload.get("bike_id") or "").strip()
    if not bike_id:
        raise ValueError("bike_id is required")

    try:
        lat = float(payload.get("lat"))
        lon = float(payload.get("lon"))
    except (TypeError, ValueError) as exc:
        raise ValueError("lat/lon must be numeric") from exc

    if lat < -90 or lat > 90:
        raise ValueError("lat must be between -90 and 90")

    if lon < -180 or lon > 180:
        raise ValueError("lon must be between -180 and 180")

    normalized = {
        "bike_id": bike_id,
        "lat": lat,
        "lon": lon,
    }

    gps_time_raw = payload.get("gps_time")
    if gps_time_raw is not None:
        gps_time = str(gps_time_raw).strip()
        if gps_time:
            normalized["gps_time"] = gps_time

    return normalized


def iter_serial_lines(port: str, baud_rate: int) -> Iterable[str]:
    if serial is None:
        raise RuntimeError(
            "pyserial is not installed. Run: pip install pyserial"
        )

    with serial.Serial(port=port, baudrate=baud_rate, timeout=1) as ser:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            yield raw.decode("utf-8", errors="replace")


def iter_stdin_lines() -> Iterable[str]:
    for line in sys.stdin:
        yield line


def send_packet(session: requests.Session, base_url: str, tracker_key: str, payload: Dict[str, object]) -> None:
    url = base_url.rstrip("/") + "/api/tracker/gps"
    headers = {"X-Tracker-Key": tracker_key}

    try:
        response = session.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException as exc:
        print(f"[ERROR] network error for {payload.get('bike_id')}: {exc}")
        return

    if response.ok:
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        print(
            "[OK] sent",
            f"bike_id={payload.get('bike_id')}",
            f"lat={payload.get('lat')}",
            f"lon={payload.get('lon')}",
            f"gps_time={body.get('last_gps_time', payload.get('gps_time', '-'))}",
        )
        return

    print(
        "[ERROR] backend rejected packet",
        f"status={response.status_code}",
        f"body={response.text.strip()}",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LoRa GPS receiver bridge: reads lines and forwards to /api/tracker/gps"
    )
    parser.add_argument(
        "--backend-url",
        default=TRACKER_BACKEND_BASE_URL,
        help="Backend base URL (default from config)",
    )
    parser.add_argument(
        "--tracker-key",
        default=TRACKER_API_KEY,
        help="Tracker API key for X-Tracker-Key header",
    )
    parser.add_argument(
        "--serial-port",
        default=TRACKER_SERIAL_PORT,
        help="Serial device path (default from config)",
    )
    parser.add_argument(
        "--baud-rate",
        type=int,
        default=TRACKER_BAUD_RATE,
        help="Serial baud rate (default from config)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read packets from stdin instead of serial port",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    source_label = "stdin" if args.stdin else f"serial {args.serial_port}@{args.baud_rate}"
    print(f"[INFO] tracker bridge started ({source_label})")
    print(f"[INFO] backend={args.backend_url.rstrip('/')}/api/tracker/gps")

    session = requests.Session()

    try:
        line_stream = iter_stdin_lines() if args.stdin else iter_serial_lines(args.serial_port, args.baud_rate)

        for line_number, raw_line in enumerate(line_stream, start=1):
            try:
                payload = parse_packet_line(raw_line)
            except ValueError as exc:
                print(f"[WARN] line {line_number}: skipped ({exc})")
                continue

            send_packet(session, args.backend_url, args.tracker_key, payload)

    except KeyboardInterrupt:
        print("\n[INFO] tracker bridge stopped by user")
        return 0
    except Exception as exc:
        print(f"[ERROR] bridge stopped: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
