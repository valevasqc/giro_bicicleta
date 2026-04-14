PRAGMA foreign_keys = ON;

-- Physical stations
CREATE TABLE IF NOT EXISTS stations (
    station_id      TEXT PRIMARY KEY,                   -- 'S1', 'S2'
    name            TEXT NOT NULL,
    is_online       INTEGER NOT NULL DEFAULT 0,
    dock_occupied   INTEGER NOT NULL DEFAULT 0,         -- kept for reference; non-authoritative for return logic
    power_connected INTEGER NOT NULL DEFAULT 0,         -- reed-switch: bike charging cable connected
    lock_confirmed  INTEGER NOT NULL DEFAULT 0,         -- reed-switch: physical lock engaged
    last_heartbeat  TEXT
);

-- Users who can log in
CREATE TABLE IF NOT EXISTS users (
    user_id           TEXT PRIMARY KEY,                 -- e.g. 'U1', 'U2'
    username          TEXT UNIQUE NOT NULL,
    name              TEXT NOT NULL,
    password_hash     TEXT NOT NULL,
    role              TEXT NOT NULL DEFAULT 'customer'
                          CHECK (role IN ('customer', 'station_service', 'admin')),
    bound_station_id  TEXT REFERENCES stations(station_id),
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Rentable bikes
CREATE TABLE IF NOT EXISTS bikes (
    bike_id             TEXT PRIMARY KEY,               -- 'B1'
    status              TEXT NOT NULL DEFAULT 'docked'
                            CHECK (status IN ('docked', 'rented', 'unavailable')),
    current_station_id  TEXT REFERENCES stations(station_id),
    last_lat            REAL,
    last_lon            REAL,
    last_gps_time       TEXT
);

-- Active and expired session tokens
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(user_id),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at  TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1
);

-- Rental records
CREATE TABLE IF NOT EXISTS rentals (
    rental_id             TEXT PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES users(user_id),
    bike_id               TEXT NOT NULL REFERENCES bikes(bike_id),
    start_station_id      TEXT NOT NULL REFERENCES stations(station_id),
    end_station_id        TEXT REFERENCES stations(station_id),
    start_time            TEXT NOT NULL,
    end_time              TEXT,
    duration_minutes      REAL,
    simulated_cost        REAL,
    payment_method        TEXT
                              CHECK (payment_method IN ('station_card', 'mobile_web')),
    payment_status        TEXT NOT NULL DEFAULT 'pending'
                              CHECK (payment_status IN ('pending', 'authorized', 'captured', 'failed', 'voided')),
    payment_authorized_at TEXT,
    payment_captured_at   TEXT,
    status                TEXT NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'completed', 'cancelled'))
);

-- System event log
CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    source      TEXT NOT NULL,                          -- 'S1', 'S2', 'B1', 'SYSTEM'
    event_type  TEXT NOT NULL,
    payload     TEXT
);

-- GPS ping history — every LoRa position update stored for export
CREATE TABLE IF NOT EXISTS gps_pings (
    ping_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    bike_id    TEXT NOT NULL REFERENCES bikes(bike_id),
    rental_id  TEXT REFERENCES rentals(rental_id),  -- null if bike was not rented at ping time
    timestamp  TEXT NOT NULL,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gps_pings_rental_id ON gps_pings(rental_id);
CREATE INDEX IF NOT EXISTS idx_gps_pings_bike_id   ON gps_pings(bike_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_rentals_status ON rentals(status);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_rental_per_user
    ON rentals(user_id)
    WHERE status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_rental_per_bike
    ON rentals(bike_id)
    WHERE status = 'active';