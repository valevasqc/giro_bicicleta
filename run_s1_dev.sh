#!/usr/bin/env bash
# Dev mode: no LoRa hardware needed. LoRa I/O goes to .lora_stub/ files.
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S1
export STATION_NAME="Estación 1"
export STATION_HTTP_PORT=8001
export STUB_LORA=true
export FLASK_APP=app.py
export FLASK_ENV=development

python3 -m flask run --host=127.0.0.1 --port=8001
