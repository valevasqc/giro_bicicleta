# GitHub Copilot instructions — Rentable Bikes MVP

You are assisting on a Python MVP for a smart rentable e-bike system built for a university/business-engineering demo. The deliverable is a working end-to-end prototype: a user authenticates at Station 1, unlocks bike B1, rides it, returns it at Station 2, and the backend records rental state, mock payment state, and ride summary. LoRa-based bike GPS is a later integration.

## Project shape
- `central/`: Flask backend API and admin/debug views, runs on the laptop or base computer.
- `station/`: Flask kiosk app, runs on each Raspberry Pi with touchscreen.
- `common/`: shared constants and protocol helpers.
- `tracker/`: Heltec tracker firmware, separate from the Python apps.
- Database: SQLite using raw `sqlite3`, not an ORM.
- Primary station-to-central communication: WiFi/HTTP.
- LoRa usage: bike GPS packets first; station heartbeat/status over LoRa is optional.

## Current implementation status
The central backend already exists. Current routes include auth, rental lifecycle, admin state, and station status endpoints. Keep new work aligned with the current backend instead of redesigning from scratch.
Current UI flows (kiosk, mobile, admin) are served from `central/app.py` with Jinja templates under `central/templates/`.

## What we are actually coding now
1. Harden the central backend, schema, seed data, and pricing/payment placeholders.
2. Build station kiosk screens with Flask templates for idle, login, availability, payment authorization, unlock, ride active, return, summary, and errors.
3. Add a simple mobile web flow if time allows. It is desirable, not required.
4. Stub GPIO and stub LoRa so the full flow works on a laptop before Raspberry Pi hardware integration.
5. Add lightweight admin/debug screens.
6. Integrate real GPIO lock and dock sensor behavior on the Pi.
7. Integrate LoRa GPS receiver logic for the bike tracker.

## Core MVP rules
- Keep scope tight: no real payment gateway, no QR login, no cloud deployment, no over-engineered abstractions.
- Mobile web is allowed and desirable, but the touchscreen station flow comes first.
- Optimize for the one-bike, two-station demo (`B1`, `S1`, `S2`). Do not over-generalize early.
- The central backend is the source of truth for rentals and bike state.
- A bike can start at Station 1 and be returned at Station 2. Do not make return logic depend on local station memory from the station that started the rental.
- Mock payment should feel realistic: authorize before unlock, capture on successful return.
- `payment_method` currently supports `station_card` and `mobile_web`.
- Pricing is not finalized yet. Keep pricing logic isolated and easy to change. It is acceptable for `simulated_cost` to remain `null` until the pricing rule is chosen.
- Treat `RENTAL_APPROVED` and `BIKE_RELEASED` as different events.
- Use explicit account roles such as `customer`, `station_service`, and `admin`.
- Use UTC timestamps consistently in ISO 8601 format.
- Never let the kiosk crash with a traceback. Catch exceptions and show clean user-facing errors.
- When changing the data model or an API, update schema, seed data, constants, and any station/mobile API client together.

## Coding preferences
- Python 3.11+
- Flask + Jinja templates
- Simple HTML/CSS/JS; do not introduce React unless explicitly asked
- Minimal JavaScript
- Type hints where practical
- Clear function boundaries
- Shared constants for status strings and event types
- Human-readable IDs like `S1`, `S2`, `B1`, `U1`
- Stub-friendly drivers for GPIO and LoRa
- Password hashing should stay compatible with the current Flask/Werkzeug setup; avoid raw SHA-256

## UI branding
- Primary brand red: `#A22522`
- Use off-white `#F8F6EC` instead of pure white most of the time
- Use black `#070707` for text and strong contrast
- Prefer clean, kiosk-friendly layouts: off-white backgrounds, red primary actions/highlights, black text
- Supporting brand colors: green `#3F6634`, orange `#FA7921`

## What to optimize for
- Reliability during a live demo
- Fast manual testing with browser and curl
- Easy debugging
- Small, understandable files
- End-to-end completeness over extra features

## Repo hygiene
- Keep local artifacts out of git: `.DS_Store`, `.vscode/`, `*.db`, `*.sqlite3`, logs, and virtualenv folders.
- Keep this file at `.github/copilot-instructions.md`.
- Keep `README.md` updated when startup commands or demo credentials change.
