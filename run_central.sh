#!/usr/bin/env bash
# Real central mode: uses the hardware LoRa serial port by default.
set -e
cd "$(dirname "$0")/central"

export FLASK_APP=app.py
export FLASK_RUN_HOST="${FLASK_RUN_HOST:-0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:-8000}"

python3 -m flask run
