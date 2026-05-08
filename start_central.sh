#!/usr/bin/env bash
# start_central.sh — Central backend: stub LoRa (laptop, no Pi hardware).
# Run from the project root.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
STUB_DIR="$REPO/.lora_stub"

mkdir -p "$STUB_DIR"
> "$STUB_DIR/to_central.log"
> "$STUB_DIR/to_station.log"
echo "[CENTRAL] stub channel cleared at $STUB_DIR"
echo "[CENTRAL] admin dashboard → http://localhost:8000/admin/login"

STUB_LORA=true \
STUB_LORA_DIR="$STUB_DIR" \
    python3 "$REPO/central/app.py"
