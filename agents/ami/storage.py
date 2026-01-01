import sqlite3
from pathlib import Path
import uuid
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "ami.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Core observations table (sync-ready)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        date TEXT NOT NULL,
        domain TEXT NOT NULL,
        text TEXT NOT NULL,
        deleted INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS context_daily (
        date TEXT PRIMARY KEY,
        sleep TEXT,
        illness TEXT,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cur.execute("""
    INSERT OR IGNORE INTO meta (key, value)
    VALUES ('schema_version', '2')
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------
# Observation helpers
# -------------------------------------------------

def add_observation(text, domain="General"):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()
    obs_uuid = str(uuid.uuid4())
    date = now.split("T")[0]

    cur.execute("""
        INSERT INTO observations
        (uuid, created_at, updated_at, date, domain, text, deleted)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (obs_uuid, now, now, date, domain, text))

    conn.commit()
    conn.close()


def get_recent_observations(limit=5):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, uuid, date, domain, text, updated_at
        FROM observations
        WHERE deleted = 0
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "uuid": r[1],
            "date": r[2],
            "domain": r[3],
            "text": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]


def get_all_observations():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, uuid, date, domain, text, updated_at, deleted
        FROM observations
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "uuid": r[1],
            "date": r[2],
            "domain": r[3],
            "text": r[4],
            "updated_at": r[5],
            "deleted": r[6],
        }
        for r in rows
    ]


def update_observation(obs_id, new_text):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute("""
        UPDATE observations
        SET text = ?, updated_at = ?
        WHERE id = ?
    """, (new_text, now, obs_id))

    conn.commit()
    conn.close()


def set_meta_value(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()
