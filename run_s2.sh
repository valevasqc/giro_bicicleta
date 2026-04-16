#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/station"

export STATION_ID=S2
export STATION_NAME="Estación 2"
export STATION_HTTP_PORT=8002

# S2 starts empty: the bike is seeded at S1. Real hardware would read this
# from the reed switch — in stub mode we override the default.
export STUB_DOCK_OCCUPIED=false
export STUB_CHARGE_CONNECTED=false

flask run --port 8002
