"""
export_csv.py — Generate rentals.csv and gps_track.csv for the professor.

Usage (from the central/ directory):
    python export_csv.py

Output files are written next to this script (central/).
"""

import csv
from pathlib import Path

from config import DB_PATH
from database import get_connection

OUT_DIR = Path(__file__).resolve().parent


def export_rentals(out_path: Path) -> int:
    """Write rentals.csv. Returns number of rows written."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                r.rental_id,
                u.username          AS user,
                r.start_station_id  AS start_station,
                r.end_station_id    AS end_station,
                r.start_time,
                r.end_time,
                r.duration_minutes  AS duration_min,
                r.simulated_cost    AS cost_gtq
            FROM rentals r
            JOIN users u ON u.user_id = r.user_id
            ORDER BY r.start_time
            """
        ).fetchall()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rental_id", "user", "start_station", "end_station",
            "start_time", "end_time", "duration_min", "cost_gtq",
        ])
        for row in rows:
            writer.writerow([
                row["rental_id"],
                row["user"],
                row["start_station"] or "",
                row["end_station"] or "",
                row["start_time"] or "",
                row["end_time"] or "",
                row["duration_min"] if row["duration_min"] is not None else "",
                row["cost_gtq"] if row["cost_gtq"] is not None else "",
            ])

    return len(rows)


def export_gps_track(out_path: Path) -> int:
    """Write gps_track.csv. Returns number of rows written."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                rental_id,
                timestamp,
                lat,
                lon
            FROM gps_pings
            ORDER BY timestamp
            """
        ).fetchall()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rental_id", "timestamp", "lat", "lon"])
        for row in rows:
            writer.writerow([
                row["rental_id"] or "",
                row["timestamp"],
                row["lat"],
                row["lon"],
            ])

    return len(rows)


if __name__ == "__main__":
    rentals_path = OUT_DIR / "rentals.csv"
    gps_path = OUT_DIR / "gps_track.csv"

    n_rentals = export_rentals(rentals_path)
    print(f"rentals.csv   → {rentals_path}  ({n_rentals} rows)")

    n_pings = export_gps_track(gps_path)
    print(f"gps_track.csv → {gps_path}  ({n_pings} rows)")
