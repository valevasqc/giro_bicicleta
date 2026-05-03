#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S2
export STATION_NAME="Estación 2"
export STATION_HTTP_PORT=8002
export FLASK_APP=app.py
export STUB_SENSORS=false
export LOCK_UNLOCKS_WHEN_HIGH=false

python3 -m flask run --host=127.0.0.1 --port=8002