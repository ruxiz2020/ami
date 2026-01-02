# agents/steward/storage.py

import sqlite3
from pathlib import Path
from datetime import datetime
from agents.common.storage import add_entry, get_entries
import uuid
import json


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "steward.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # -------------------------------------------------
    # Project events table (append-only)
    # -------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS project_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT,
        created_at TEXT NOT NULL,
        project TEXT NOT NULL,
        event_type TEXT NOT NULL,
        content TEXT NOT NULL,
        confidence TEXT,
        deleted INTEGER DEFAULT 0
    )
    """)

    # -------------------------------------------------
    # Meta table (schema tracking, etc.)
    # -------------------------------------------------
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
# Project event helpers
# -------------------------------------------------

def add_project_event(record_json: str):
    """
    Record a steward project event from a JSON record.

    The record MUST include a project.
    """

    record = json.loads(record_json)

    project = record.get("project")
    if not project:
        raise ValueError("Steward entry missing project")

    content = record_json

    # ---- Shared entry store (timeline / sync / reflections)
    add_entry(
        agent="steward",
        type="project_event",
        subject=project,      # 👈 project identity
        content=content,
    )

    # ---- Local DB (project-centric queries later)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO project_events (
            uuid, created_at, project, event_type, content, confidence
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        datetime.utcnow().isoformat(),
        project,
        None,        # event_type (v1: unknown / freeform)
        content,
        None,        # confidence
    ))

    conn.commit()
    conn.close()


def get_recent_project_events(project_name: str | None = None, limit: int = 5):
    return get_entries(
        agent="steward",
        type="project_event",
        limit=limit,
    )


def get_all_project_events(project_name: str | None = None):
    """
    Return all steward project events.

    NOTE:
    - Shared storage does NOT support subject filtering.
    - Project-specific filtering must be done in agent-local DB if needed.
    """
    return get_entries(
        agent="steward",
        type="project_event",
    )



def get_events_updated_since(ts: str | None):
    """
    Used for sync / export purposes.
    Mirrors Ami's updated_since pattern.
    """
    conn = get_conn()
    cur = conn.cursor()

    if ts:
        cur.execute("""
            SELECT id, uuid, created_at, project, event_type, content, confidence, deleted
            FROM project_events
            WHERE created_at > ?
        """, (ts,))
    else:
        cur.execute("""
            SELECT id, uuid, created_at, project, event_type, content, confidence, deleted
            FROM project_events
        """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "uuid": r[1],
            "created_at": r[2],
            "project": r[3],
            "event_type": r[4],
            "content": r[5],
            "confidence": r[6],
            "deleted": r[7],
        }
        for r in rows
    ]


# -------------------------------------------------
# Meta helpers (same pattern as Ami)
# -------------------------------------------------

def set_meta_value(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_meta_value(key):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
