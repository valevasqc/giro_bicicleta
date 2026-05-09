# Giro Bicicleta

Smart bike rental system. One e-bike (B1), two station kiosks (S1, S2), one central backend laptop. Stations communicate with central via LoRa radio — no WiFi or HTTP between nodes.

## Hardware topology

```
[Laptop — central backend]
        |
   USB serial
        |
  [LoRa bridge]  <~~~915MHz~~~>  [LoRa bridge]  <-- USB serial --> [Raspberry Pi — S1 kiosk]
                                 [LoRa bridge]  <-- USB serial --> [Raspberry Pi — S2 kiosk]

[GPS tracker on bike]  ~~~915MHz~~~>  (received by central's bridge)
```

## What's built

### Central backend (`central/`)
Flask app, source of truth for all system state. Port **8000**.

- **Rental lifecycle** — request, approve/deny, start, complete (idempotent)
- **Mobile web flow** — register, login, browse stations, request bike, mock payment, ride-active screen, return summary, ride history, balance top-up, account management
- **Admin dashboard** — live system state (bikes, stations, rentals), GPS track viewer, top-up code generator
- **REST API** — auth, rental request/start/complete, heartbeat, station status, admin state
- **LoRa integration** — background receiver thread + sender; stub mode for dev without hardware
- **Pricing** — hourly rate with minimum charge, all values from config
- **CSV export** — rentals and GPS track
- **SQLite persistence** — no ORM, raw sqlite3

### Station kiosk (`station/`)
Separate Flask app on each Raspberry Pi touchscreen. S1 on port **8001**, S2 on port **8002**.

- Login, rental request, dock state display
- Lock/sensor driver (GPIO or stub)
- Heartbeat sender, LoRa receiver/sender

### Firmware

All firmware uses [RadioLib](https://github.com/jgromes/RadioLib). All radios share the same config: **915 MHz, BW 125 kHz, SF9, CR4/7, sync 0x12**.

| File | Board | Radio | Notes |
|---|---|---|---|
| `lora_bridge_V4.ino` | Heltec WiFi LoRa 32 **V4** | SX1262 + GC1109 FEM | OLED, 22 dBm, TCXO 1.8V, DCDC |
| `lora_bridge_v2.ino` | Heltec WiFi LoRa 32 **V2** | SX1276 | OLED, 20 dBm PA_BOOST |
| `lora_bridge_ESP32.ino` | Generic ESP32 + SX1276 module | SX1276 | No OLED, 20 dBm PA_BOOST |
| `tracker.ino` | Heltec Wireless Tracker | SX1262 + GPS | ST7735 screen, sends GPS every 30 s |

Each bridge acts as a USB serial ↔ LoRa relay. The Pi/laptop reads and writes raw pipe-delimited lines; the bridge transmits/receives them over the air.

## Project structure

```
giro_bicicleta/
├── central/
│   ├── app.py              # All routes (mobile, admin, API)
│   ├── config.py
│   ├── database.py
│   ├── schema.sql
│   ├── seed.py
│   ├── pricing.py
│   ├── lora_io.py
│   ├── lora_receiver.py    # Background thread
│   ├── lora_sender.py
│   ├── export_csv.py
│   ├── services/topup_service.py
│   └── templates/
│       ├── admin/
│       └── mobile/
├── station/
│   ├── app.py
│   ├── config.py
│   ├── gpio_driver.py
│   ├── heartbeat.py
│   ├── lora_receiver.py
│   ├── lora_sender.py
│   └── routes/kiosk.py
├── common/
│   ├── constants.py
│   └── lora_protocol.py
├── run_dev.sh              # Central, stub LoRa, port 8000
├── run_s1.sh               # Station S1, real hardware, port 8001
├── run_s1_dev.sh           # Station S1, stub LoRa/lock, port 8001
├── run_s2.sh               # Station S2, real hardware, port 8002
├── tracker.ino
├── lora_bridge_V4.ino
├── lora_bridge_v2.ino
└── lora_bridge_ESP32.ino
```

## Running on hardware (Raspberry Pi)

Each Pi has the repo cloned and a LoRa bridge (ESP32) connected via USB.

**One-time setup on each Pi:**
```bash
cd giro_bicicleta
python3 -m venv .venv
source .venv/bin/activate
pip install Flask Werkzeug pyserial
```

**Central laptop** — init the database once, then start the backend:
```bash
python3 central/seed.py   # first run only
./run_dev.sh              # stub LoRa (no bridge attached)
# or: LORA_PORT=/dev/ttyUSB0 python3 -m flask run ... for real hardware
```

**Station S1 Pi:**
```bash
./run_s1.sh
```

**Station S2 Pi:**
```bash
./run_s2.sh
```

Both station scripts expect the LoRa bridge on `/dev/ttyUSB0` at 115200 baud. Change `LORA_PORT` in the script if your device shows up differently (e.g. `/dev/ttyACM0`).

## Key routes

| App | Route | Purpose |
|---|---|---|
| Central | `/mobile` | Mobile web home |
| Central | `/mobile/register` | Customer registration |
| Central | `/mobile/login` | Customer login |
| Central | `/mobile/stations` | Browse stations |
| Central | `/mobile/ride-active` | Active ride screen |
| Central | `/mobile/rides` | Ride history |
| Central | `/mobile/topup` | Balance top-up |
| Central | `/mobile/account` | Account settings |
| Central | `/admin/login` | Admin login |
| Central | `/admin/dashboard` | Live system state |
| Central | `/admin/topup-codes/generate` | Generate top-up codes |
| Central | `/api/rentals/request` | Rental request (from station) |
| Central | `/api/rentals/start` | Mark bike released |
| Central | `/api/rentals/complete` | Complete return |
| Central | `/api/stations/heartbeat` | Station heartbeat |
| Central | `/health` | Health check |
| Station | `/` | Kiosk home |

## Demo credentials (from seed)

| Role | Username | Password |
|---|---|---|
| Customer | valeria | demo123 |
| Admin | admin | admin123 |
| Station S1 | station_s1 | station123 |
| Station S2 | station_s2 | station123 |

## LoRa protocol

Messages are pipe-delimited strings over serial (115200 baud). Key inbound messages (station → central):

```
HEARTBEAT|S1|dock_occupied|charging_connected|ts
RENTAL_REQUEST|S1|B1|username|password|ts
BIKE_RELEASED|S1|B1|user_id|ts
BIKE_DOCKED|S2|B1|ts
GPS|B1|unix_ts|lat|lon
```

Key outbound messages (central → station):

```
LOGIN_OK|S1|user_id|name|token|balance|ts
LOGIN_FAIL|S1|reason|ts
RENTAL_APPROVED|S1|B1|user_id|ts
RENTAL_DENIED|S1|reason|ts
RETURN_COMPLETE|S2|B1|name|duration_minutes|cost|balance_remaining|ts
```

## Dev mode (no hardware)

`STUB_LORA=true` (set in `run_dev.sh` and `run_s1_dev.sh`) routes LoRa I/O through append-only files (`.lora_stub/to_central.log` / `.lora_stub/to_station.log`) so the full flow can be tested on one laptop without any bridge attached.
