import sqlite3
from pathlib import Path
import uuid
from datetime import datetime, timedelta

# -------------------------------------------------
# Database setup
# -------------------------------------------------

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "workbench.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------
# Initialization
# -------------------------------------------------

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


# -------------------------------------------------
# Write operations
# -------------------------------------------------

from agents.common.storage import add_entry, get_entries

def add_note(text, topic="General"):
    add_entry(
        agent="workbench",
        type="note",
        content=text,
        topic=topic,
    )


def update_note(note_id, new_content):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute("""
        UPDATE notes
        SET content = ?, updated_at = ?
        WHERE id = ? AND deleted = 0
    """, (new_content, now, note_id))

    conn.commit()
    conn.close()


# -------------------------------------------------
# Read helpers
# -------------------------------------------------

def _row_to_note(row):
    """
    Normalize DB row to UI / intelligence format.
    """
    return {
        "id": row["id"],
        "uuid": row["uuid"],
        "topic": row["topic"],
        "text": row["content"],      # normalized key
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# -------------------------------------------------
# Public read APIs
# -------------------------------------------------

def get_all_notes():
    return get_entries(agent="workbench", type="note")


def get_notes_last_n_days(days=7):
    """
    Generic helper for reflection windows.
    """
    conn = get_conn()
    cur = conn.cursor()

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    cur.execute("""
        SELECT *
        FROM notes
        WHERE deleted = 0
          AND updated_at >= ?
        ORDER BY updated_at DESC
    """, (cutoff,))

    rows = cur.fetchall()
    conn.close()

    return [_row_to_note(r) for r in rows]


def get_workbench_notes_last_7_days():
    return get_entries(agent="workbench", type="note")
