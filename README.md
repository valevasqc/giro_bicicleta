# Giro Bicicleta

Smart bike rental system for a university demo. One e-bike (B1), two station kiosks (S1, S2), one central backend. Stations communicate with central via LoRa radio.

## What's built

### Central backend (`central/`)
Flask app that is the source of truth for all system state.

- **Rental lifecycle** — request, approve/deny, start, complete
- **Mobile web flow** — login, browse stations, request bike, mock payment, ride-active screen, return summary, ride history, balance top-up
- **Admin dashboard** — live system state (bikes, stations, rentals), GPS track viewer, top-up code generator
- **REST API** — auth, rental request/start/complete, heartbeat, station status, admin state
- **LoRa integration** — background receiver thread + sender; stub mode routes messages through flat files for single-laptop dev
- **Pricing** — hourly rate with minimum charge, all values from config
- **CSV export** — rentals and GPS track exports
- **SQLite persistence** — no ORM, raw sqlite3

### Station kiosk (`station/`)
Separate Flask app that runs on each Raspberry Pi touchscreen.

- Login, rental request, dock state display
- GPIO driver for dock/lock sensors (stubbed for dev)
- Heartbeat sender, LoRa receiver/sender

### Firmware
- `tracker.ino` — GPS tracker sketch (Arduino/ESP)
- `lora_bridge.ino` — LoRa relay sketch

## Tech stack

Python 3.11, Flask, SQLite (sqlite3), werkzeug.security, pyserial

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install Flask Werkzeug pyserial

# Init database
python3 central/seed.py

# Run central (stub LoRa on by default for dev)
cd central && STUB_LORA=true flask run --port 8000

# Run station kiosk (separate terminal)
cd station && STATION_ID=S1 STUB_GPIO=true STUB_LORA=true flask run --port 5001
```

Or use the provided scripts: `run_dev.sh`, `run_s1_dev.sh`, `run_s1.sh`, `run_s2.sh`.

## Key routes

| App | Route | Purpose |
|---|---|---|
| Central | `/mobile` | Mobile web home |
| Central | `/mobile/login` | Customer login |
| Central | `/admin/login` | Admin dashboard login |
| Central | `/admin/dashboard` | Live system state |
| Central | `/health` | Health check |
| Station | `/` | Kiosk home |

## Demo credentials (from seed)

| Role | Username | Password |
|---|---|---|
| Customer | valeria | demo123 |
| Admin | admin | admin123 |
| Station S1 | station_s1 | station123 |
| Station S2 | station_s2 | station123 |

## Config

All environment-specific values (serial port, baud rate, GPIO pins, stub flags) live in `central/config.py` and `station/config.py`. Never hardcoded.

`STUB_LORA=true` routes LoRa I/O through two append-only files (`to_central.log` / `to_station.log`) so the full flow can be tested on one laptop without hardware.
