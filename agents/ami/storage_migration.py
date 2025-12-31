import sqlite3
from pathlib import Path
from datetime import datetime
import uuid

DB_PATH = Path(__file__).parent / "data" / "ami.db"


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate_observations_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---- Add missing columns safely ----

    if not column_exists(cur, "observations", "uuid"):
        cur.execute("ALTER TABLE observations ADD COLUMN uuid TEXT")

    if not column_exists(cur, "observations", "updated_at"):
        cur.execute("ALTER TABLE observations ADD COLUMN updated_at TEXT")

    if not column_exists(cur, "observations", "deleted"):
        cur.execute("ALTER TABLE observations ADD COLUMN deleted INTEGER DEFAULT 0")

    conn.commit()

    # ---- Backfill existing rows ----

    cur.execute("""
        SELECT id, uuid, updated_at
        FROM observations
    """)

    rows = cur.fetchall()
    now = datetime.utcnow().isoformat()

    for obs_id, obs_uuid, updated_at in rows:
        if obs_uuid is None:
            cur.execute(
                "UPDATE observations SET uuid = ? WHERE id = ?",
                (str(uuid.uuid4()), obs_id)
            )

        if updated_at is None:
            cur.execute(
                "UPDATE observations SET updated_at = ? WHERE id = ?",
                (now, obs_id)
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate_observations_table()
    print("✅ Observation table migration complete.")
