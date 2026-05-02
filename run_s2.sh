#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S2
export STATION_NAME="Estación 2"
export STATION_HTTP_PORT=8002
export STUB_SENSORS=false

flask run --port 8002
