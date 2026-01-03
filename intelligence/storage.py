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

    content = report["content"]
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)

    cur.execute("""
        INSERT INTO reports (agent, type, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        report["agent"],
        report["type"],
        content,
        report["created_at"],
    ))

    conn.commit()
    conn.close()


import json

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

    results = []
    for r in rows:
        raw_content = r[3]

        # -----------------------------------------
        # Attempt to deserialize JSON content
        # -----------------------------------------
        content = raw_content
        if isinstance(raw_content, str):
            try:
                content = json.loads(raw_content)
            except Exception:
                # Not JSON → keep as plain string (LLM output)
                content = raw_content

        results.append({
            "id": r[0],
            "agent": r[1],
            "type": r[2],
            "content": content,
            "created_at": r[4],
        })

    return results



def delete_reports_by_type(agent: str, report_type: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM reports WHERE agent = ? AND type = ?",
        (agent, report_type),
    )
    conn.commit()
    conn.close()

