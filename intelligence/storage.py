# intelligence/storage.py

import sqlite3
from pathlib import Path

DB_PATH = Path("data/intelligence.db")
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent TEXT,
        type TEXT,
        content TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_report(report: dict):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO reports (agent, type, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        report["agent"],
        report["type"],
        report["content"],
        report["created_at"],
    ))

    conn.commit()
    conn.close()


def get_reports(agent: str, report_type: str):
    conn = get_conn()
    cur = conn.cursor()

    if report_type:
        cur.execute("""
            SELECT id, agent, type, content, created_at
            FROM reports
            WHERE agent = ? AND type = ?
            ORDER BY created_at DESC
        """, (agent, report_type))
    else:
        cur.execute("""
            SELECT id, agent, type, content, created_at
            FROM reports
            WHERE agent = ?
            ORDER BY created_at DESC
        """, (agent,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "agent": r[1],
            "type": r[2],
            "content": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]



