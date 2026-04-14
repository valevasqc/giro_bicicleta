from werkzeug.security import generate_password_hash
from database import get_connection, init_db


def hash_password(password: str) -> str:
    # Use PBKDF2 explicitly for compatibility on Python builds without hashlib.scrypt.
    return generate_password_hash(password, method="pbkdf2:sha256")


def seed():
    init_db()

    with get_connection() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM rentals")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM bikes")
        conn.execute("DELETE FROM stations")

        conn.executemany(
            """
            INSERT INTO stations (station_id, name, is_online, dock_occupied, power_connected, lock_confirmed, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("S1", "Station 1", 0, 1, 0, 0, None),
                ("S2", "Station 2", 0, 0, 0, 0, None),
            ],
        )

        conn.executemany(
            """
            INSERT INTO users (
                user_id, username, name, password_hash, role, bound_station_id, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("U1", "valeria", "Valeria Demo", hash_password("demo123"), "customer", None, 1),
                ("A1", "admin", "System Admin", hash_password("admin123"), "admin", None, 1),
                ("SS1", "station_s1", "Station S1 Service", hash_password("station123"), "station_service", "S1", 1),
                ("SS2", "station_s2", "Station S2 Service", hash_password("station123"), "station_service", "S2", 1),
            ],
        )

        conn.execute(
            """
            INSERT INTO bikes (
                bike_id, status, current_station_id, last_lat, last_lon, last_gps_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("B1", "docked", "S1", None, None, None),
        )

        conn.commit()


if __name__ == "__main__":
    seed()
    print("Seed data inserted.")
    print("Test customer login: valeria / demo123")
    print("Test admin login: admin / admin123")
    print("Test station login: station_s1 / station123")