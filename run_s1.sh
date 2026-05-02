#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S1
export STATION_NAME="Estación 1"
export STATION_HTTP_PORT=8001
export FLASK_APP=app.py
export STUB_SENSORS=false

python3 -m flask run --host=127.0.0.1 --port=8001
