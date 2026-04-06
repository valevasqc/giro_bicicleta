# Giro Bicicleta (MVP)

Minimal MVP for a rentable e-bike flow used in a university demo.

## What this project does

This project simulates a smart bike rental system with one backend and web interfaces for:

- Station kiosk flow (touchscreen style)
- Mobile web flow (basic)
- Admin/debug dashboard

The core demo scenario is:

1. User logs in at Station 1
2. User requests and unlocks bike B1
3. User rides
4. User returns the bike at Station 2
5. Backend records rental state, payment state (mock), and ride summary

The backend is the source of truth for bikes, rentals, users, sessions, and events.

## Project aim

Deliver a reliable, end-to-end prototype that is easy to run locally and easy to demo.

Current priorities:

- Stable rental lifecycle
- Clear station/mobile/admin flows
- SQLite persistence with simple schema and seed data
- Mock payment authorization and capture

## Tech stack

- Python 3.11+
- Flask
- SQLite (sqlite3)
- Jinja templates

## Repository structure

- central/: Flask app, API routes, templates, static files, database schema and seed
- .github/copilot-instructions.md: project coding instructions

## Quick start

### 1. Create and activate virtual environment

macOS/Linux:

python3 -m venv .venv
source .venv/bin/activate

### 2. Install dependencies

pip install Flask Werkzeug

### 3. Initialize seed data

From the repository root:

python central/seed.py

This creates and seeds central/giro_bicicleta.db with demo records.

### 4. Run the app

python central/app.py

Server starts on:

http://127.0.0.1:8000

## Main routes

- Kiosk home: / 
- Station login flow: /station/login
- Mobile home: /mobile
- Admin login: /admin/login
- Health check: /health

## Demo credentials

From the seed script:

- Customer: valeria / demo123
- Admin: admin / admin123
- Station service S1: station_s1 / station123
- Station service S2: station_s2 / station123

## Notes

- Payments are simulated (authorize before ride, capture on return).
- Default station context is S1 (configurable via environment variable STATION_ID).
- Tracker GPS endpoint exists but is still a stub-level integration for MVP.
