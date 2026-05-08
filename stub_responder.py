#!/usr/bin/env python3
"""
Local LoRa stub auto-responder for isolated station demo (no network).

Tails the station's outbound file (to_central.log) and writes correct
central-style replies into the station's inbound file (to_station.log).
The station app never knows central isn't there.

All RENTAL_REQUESTs are approved, all REGISTER_REQUESTs succeed,
all TOPUP_REQUESTs credit 200.00 GTQ.

Usage (from project root):
    python3 stub_responder.py --station-id S1
    python3 stub_responder.py --station-id S2 --stub-dir /custom/path
"""

import argparse
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from common.lora_protocol import (
    BIKE_DOCKED,
    BIKE_RELEASED,
    GPS,
    HEARTBEAT,
    LOGIN_OK,
    REGISTER_OK,
    REGISTER_REQUEST,
    RENTAL_APPROVED,
    RENTAL_REQUEST,
    RETURN_COMPLETE,
    TOPUP_OK,
    TOPUP_REQUEST,
    format_message,
    parse_message,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [STUB %(station_id)s] %(message)s",
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reply(stub_in: Path, msg: str, log) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    with stub_in.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
    log.info("→ %s", msg)


def _handle(line: str, station_id: str, stub_in: Path, log) -> None:
    parsed = parse_message(line)
    if parsed is None:
        return

    msg_type, fields = parsed
    log.info("← %s %s", msg_type, fields)

    if not fields or fields[0] != station_id:
        return

    ts = _utc_iso()

    if msg_type == RENTAL_REQUEST:
        # RENTAL_REQUEST|S1|B1|username|password|ts
        bike_id  = fields[1] if len(fields) > 1 else "B1"
        username = fields[2] if len(fields) > 2 else "usuario"
        fake_uid   = str(uuid.uuid4())[:8]
        fake_token = str(uuid.uuid4()).replace("-", "")[:32]
        _reply(stub_in, format_message(LOGIN_OK,       station_id, fake_uid, username, fake_token, "100.00", ts), log)
        _reply(stub_in, format_message(RENTAL_APPROVED, station_id, bike_id, fake_uid, ts), log)

    elif msg_type == BIKE_DOCKED:
        # BIKE_DOCKED|S1|B1|ts
        bike_id = fields[1] if len(fields) > 1 else "B1"
        _reply(stub_in, format_message(RETURN_COMPLETE, station_id, bike_id, "Usuario", "5", "5.00", "95.00", ts), log)

    elif msg_type == REGISTER_REQUEST:
        # REGISTER_REQUEST|S1|name|username|email|password|ts
        _reply(stub_in, format_message(REGISTER_OK, station_id, ts), log)

    elif msg_type == TOPUP_REQUEST:
        # TOPUP_REQUEST|S1|token|code|ts
        _reply(stub_in, format_message(TOPUP_OK, station_id, "200.00", ts), log)

    # HEARTBEAT, BIKE_RELEASED, GPS — no reply needed


def run(station_id: str, stub_dir: Path) -> None:
    log = logging.getLogger(station_id)
    log = logging.LoggerAdapter(log, {"station_id": station_id})

    stub_out = stub_dir / "to_central.log"
    stub_in  = stub_dir / "to_station.log"

    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_out.touch(exist_ok=True)
    stub_in.touch(exist_ok=True)

    offset = stub_out.stat().st_size
    log.info("watching %s from byte %d", stub_out, offset)

    buf = ""
    while True:
        try:
            with stub_out.open("r", encoding="utf-8") as fh:
                fh.seek(offset)
                chunk = fh.read()
                offset = fh.tell()
        except FileNotFoundError:
            time.sleep(0.2)
            continue

        if not chunk:
            time.sleep(0.2)
            continue

        buf += chunk
        while "\n" in buf:
            raw, buf = buf.split("\n", 1)
            line = raw.strip()
            if line and not line.startswith("#"):
                _handle(line, station_id, stub_in, log)


def main() -> None:
    ap = argparse.ArgumentParser(description="LoRa stub auto-responder — no central needed")
    ap.add_argument("--station-id", default="S1", help="Station ID to serve (S1 or S2)")
    ap.add_argument("--stub-dir",   default=None,  help="Path to .lora_stub dir (default: <repo>/.lora_stub)")
    args = ap.parse_args()

    stub_dir = Path(args.stub_dir) if args.stub_dir else REPO / ".lora_stub"
    run(args.station_id, stub_dir)


if __name__ == "__main__":
    main()
