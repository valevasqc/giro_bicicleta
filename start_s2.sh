#!/usr/bin/env bash
# start_s2.sh — Station S2: stub LoRa, real GPIO (solenoid + switches).
# Run from the project root on the S2 Raspberry Pi.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
STUB_DIR="$REPO/.lora_stub"

mkdir -p "$STUB_DIR"
> "$STUB_DIR/to_central.log"
> "$STUB_DIR/to_station.log"
echo "[S2] stub channel cleared at $STUB_DIR"

python3 "$REPO/stub_responder.py" --station-id S2 --stub-dir "$STUB_DIR" &
RESP_PID=$!
echo "[S2] responder PID=$RESP_PID"

STUB_LORA=true \
STUB_LORA_DIR="$STUB_DIR" \
STUB_LOCK=false \
STUB_SENSORS=false \
STATION_ID=S2 \
STATION_HTTP_PORT=8002 \
    python3 "$REPO/station/app.py" &
APP_PID=$!
echo "[S2] station app PID=$APP_PID  →  http://localhost:8002"

trap 'echo "[S2] shutting down"; kill $RESP_PID $APP_PID 2>/dev/null; wait' EXIT INT TERM
wait
