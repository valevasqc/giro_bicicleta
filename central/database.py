import sqlite3
import json

try:
    from .config import DB_PATH, SCHEMA_PATH
except ImportError:
    from config import DB_PATH, SCHEMA_PATH


def get_connection():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create all tables from schema.sql and apply lightweight migrations."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)
        _migrate(conn)
        conn.commit()


def _migrate(conn):
    """Add columns introduced after the initial schema, on existing DBs."""
    user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "balance" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0")


def fetch_one(query, params=()):
    """Run a SELECT query and return one row as a dict."""
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        row = cursor.fetchone()

    return dict(row) if row else None


def fetch_all(query, params=()):
    """Run a SELECT query and return all rows as a list of dicts."""
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def execute(query, params=()):
    """Run INSERT/UPDATE/DELETE."""
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def log_event(source: str, event_type: str, payload=None):
    """Insert an event row in the events table."""
    payload_json = json.dumps(payload) if payload is not None else None

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (source, event_type, payload)
            VALUES (?, ?, ?)
            """,
            (source, event_type, payload_json),
        )
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database created at: {DB_PATH}")