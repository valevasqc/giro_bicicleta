#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S1
export STATION_NAME="Estación 1"
export STATION_HTTP_PORT=8001

flask run --port 8001
