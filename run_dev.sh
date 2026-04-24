#!/usr/bin/env bash
# Dev mode: no LoRa hardware needed. LoRa I/O goes to .lora_stub/ files.
set -e

export STUB_LORA=true
export FLASK_APP=central/app.py
export FLASK_ENV=development

cd "$(dirname "$0")"
python3 -m flask run --host=0.0.0.0 --port=8000
