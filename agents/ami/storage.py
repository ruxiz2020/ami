import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "ami.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        date TEXT NOT NULL,
        domain TEXT NOT NULL,
        text TEXT NOT NULL
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
    VALUES ('schema_version', '1')
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
    date = now.split("T")[0]

    cur.execute("""
    INSERT INTO observations (created_at, date, domain, text)
    VALUES (?, ?, ?, ?)
    """, (now, date, domain, text))

    conn.commit()
    conn.close()


def get_recent_observations(limit=5):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT date, domain, text
    FROM observations
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {"date": r[0], "domain": r[1], "text": r[2]}
        for r in rows
    ]


def get_all_observations():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT date, domain, text
    FROM observations
    ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {"date": r[0], "domain": r[1], "text": r[2]}
        for r in rows
    ]
