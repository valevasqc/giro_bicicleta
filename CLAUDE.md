# CLAUDE.md — Bike Rental MVP (Central Backend)

## What this is
Smart bike rental system. Two stations (Raspberry Pi kiosks), one e-bike with GPS tracker, one central laptop backend. You are building the **central backend** only.

## Tech stack
Python 3.11, Flask, raw sqlite3, werkzeug.security (scrypt). No ORM. No WiFi. No HTTP between station and central.

## Project structure
```
bike-rental/
├── central/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── schema.sql
│   ├── seed.py
│   ├── data/rental.db
│   ├── routes/
│   │   ├── admin.py       # /admin/* pages
│   │   └── internal.py
│   ├── services/
│   │   ├── rental_service.py
│   │   ├── pricing.py
│   │   ├── event_logger.py
│   │   ├── lora_receiver.py  # background thread
│   │   └── lora_sender.py
│   └── templates/admin/
├── common/
│   ├── constants.py
│   └── lora_protocol.py
```

## Communication
All station↔central is LoRa (pyserial). Messages are pipe-delimited strings. `lora_receiver.py` runs as a background thread reading serial. `lora_sender.py` writes to serial.

### Inbound messages (station → central)
```
HEARTBEAT|S1|dock_occupied|charging_connected|ts
RENTAL_REQUEST|S1|B1|username|password|ts
BIKE_RELEASED|S1|B1|user_id|ts
BIKE_DOCKED|S2|B1|ts
GPS|B1|unix_ts|lat|lon
```

### Outbound messages (central → station)
```
LOGIN_OK|S1|user_id|name|token|balance|ts
LOGIN_FAIL|S1|reason|ts
RENTAL_APPROVED|S1|B1|user_id|ts
RENTAL_DENIED|S1|reason|ts
RETURN_COMPLETE|S2|B1|name|duration_minutes|cost|balance_remaining|ts
```

## Database tables
`stations`, `users` (roles: customer/station_service/admin, has balance REAL), `bikes` (status: docked/rented/unavailable), `sessions` (UUID tokens), `rentals` (status: active/completed/cancelled), `gps_pings`, `events`. Full schema in `central/schema.sql`.

## Key business rules
- Rental approved only if: bike docked at that station, user balance ≥ MINIMUM_BALANCE_TO_RENT, no active rental for user or bike, user is_active=1.
- Cost = (duration_minutes / 60) * PRICING_RATE_PER_HOUR, minimum MINIMUM_CHARGE. All rates from config, never hardcoded.
- Cost deducted from user.balance at return (floor at 0).
- Rental completion is idempotent — no crash if no active rental found.
- Timestamps: UTC, format `%Y-%m-%dT%H:%M:%SZ`.

## Auth
werkzeug `generate_password_hash` / `check_password_hash`. Session token = UUID in sessions table. Admin dashboard uses HTTP Basic Auth from config (not DB).

## Config
All environment-specific values (serial port, rates, pins, credentials) live in `central/config.py`. Never hardcode them.

## Stub mode
`lora_receiver.py` and `lora_sender.py` must support stub mode (no serial hardware) for dev. Stub prints messages instead of writing to serial.

## Build order
1. schema.sql + database.py + seed.py
2. Auth (token creation, validation, role checks)
3. pricing.py + rental_service.py
4. lora_receiver.py + lora_sender.py
5. Admin dashboard + CSV exports (rentals.csv, gps_track.csv)
