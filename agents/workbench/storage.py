import sqlite3
from pathlib import Path
import uuid
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "workbench.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT,
        created_at TEXT,
        updated_at TEXT,
        topic TEXT,
        content TEXT,
        deleted INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


def add_note(content, topic="General"):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()
    note_uuid = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO notes
        (uuid, created_at, updated_at, topic, content, deleted)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (note_uuid, now, now, topic, content))

    conn.commit()
    conn.close()


def update_note(note_id, new_content):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute("""
        UPDATE notes
        SET content = ?, updated_at = ?
        WHERE id = ?
    """, (new_content, now, note_id))

    conn.commit()
    conn.close()


def get_all_notes():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, uuid, topic, content, updated_at
        FROM notes
        WHERE deleted = 0
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "uuid": r[1],
            "topic": r[2],
            "text": r[3],          # NOTE: reuse "text" key for UI compatibility
            "updated_at": r[4],
        }
        for r in rows
    ]
