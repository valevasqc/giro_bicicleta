#!/usr/bin/env bash
# start_s1.sh — Station S1: stub LoRa, real GPIO (solenoid + switches).
# Run from the project root on the S1 Raspberry Pi.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
STUB_DIR="$REPO/.lora_stub"

mkdir -p "$STUB_DIR"
> "$STUB_DIR/to_central.log"
> "$STUB_DIR/to_station.log"
echo "[S1] stub channel cleared at $STUB_DIR"

# Auto-responder simulates central replies locally (no network needed)
python3 "$REPO/stub_responder.py" --station-id S1 --stub-dir "$STUB_DIR" &
RESP_PID=$!
echo "[S1] responder PID=$RESP_PID"

# Station app — stub LoRa, real solenoid and dock switch
STUB_LORA=true \
STUB_LORA_DIR="$STUB_DIR" \
STUB_LOCK=false \
STUB_SENSORS=false \
STATION_ID=S1 \
STATION_HTTP_PORT=8001 \
    python3 "$REPO/station/app.py" &
APP_PID=$!
echo "[S1] station app PID=$APP_PID  →  http://localhost:8001"

trap 'echo "[S1] shutting down"; kill $RESP_PID $APP_PID 2>/dev/null; wait' EXIT INT TERM
wait
