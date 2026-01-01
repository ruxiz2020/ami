import sqlite3
from pathlib import Path
import uuid
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "entries.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            agent TEXT,
            type TEXT,
            topic TEXT,
            content TEXT,
            created_at TEXT,
            updated_at TEXT,
            deleted INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------
# Write
# -------------------------------------------------

def add_entry(agent, content, type="note", topic=None):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute("""
        INSERT INTO entries
        (uuid, agent, type, topic, content, created_at, updated_at, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        str(uuid.uuid4()),
        agent,
        type,
        topic,
        content,
        now,
        now,
    ))

    conn.commit()
    conn.close()


def update_entry(entry_id, new_content):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE entries
        SET content = ?, updated_at = ?
        WHERE id = ? AND deleted = 0
    """, (new_content, datetime.utcnow().isoformat(), entry_id))

    conn.commit()
    conn.close()


# -------------------------------------------------
# Read
# -------------------------------------------------

def get_entries(agent=None, type=None, limit=None):
    conn = get_conn()
    cur = conn.cursor()

    query = "SELECT * FROM entries WHERE deleted = 0"
    params = []

    if agent:
        query += " AND agent = ?"
        params.append(agent)

    if type:
        query += " AND type = ?"
        params.append(type)

    query += " ORDER BY created_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "uuid": r["uuid"],
            "agent": r["agent"],
            "type": r["type"],
            "topic": r["topic"],
            "text": r["content"],              # UI-compatible
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
