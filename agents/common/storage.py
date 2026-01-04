import sqlite3
import json
from pathlib import Path
import uuid
from datetime import datetime

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "entries.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    print(">>> init_db using DB_PATH =", DB_PATH.resolve())
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    print(">>> init_db using DB_PATH =", DB_PATH.resolve())
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            agent TEXT,
            type TEXT,
            subject TEXT,
            tags TEXT,
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

def add_entry(agent, content, type="note", subject=None, tags=None):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()
    tags_json = json.dumps(tags) if tags else None

    serialized = _serialize_content(content)
    cur.execute("""
        INSERT INTO entries
        (uuid, agent, type, subject, tags, content, created_at, updated_at, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        str(uuid.uuid4()),
        agent,
        type,
        subject,
        tags_json,
        serialized,
        now,
        now,
    ))

    conn.commit()
    conn.close()



def update_entry(entry_id, new_content):
    conn = get_conn()
    cur = conn.cursor()

    serialized = _serialize_content(new_content)
    cur.execute("""
        UPDATE entries
        SET content = ?, updated_at = ?
        WHERE id = ? AND deleted = 0
    """, (serialized, datetime.utcnow().isoformat(), entry_id))

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

    results = []

    for r in rows:
        try:
            payload = json.loads(r["content"]) if r["content"] else {}
        except Exception:
            payload = {}

        results.append({
            "id": r["id"],
            "uuid": r["uuid"],
            "agent": r["agent"],
            "type": r["type"],
            "subject": r["subject"],
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "content": payload.get("content", []),          # ✅ list[str]
            "schema_version": payload.get("schema_version", 1),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    return results



def _serialize_content(content):
    """
    Storage invariant:
    - DB always stores ONE JSON string
    - JSON must contain ONLY user text in `content`
    """
    if isinstance(content, dict):
        _validate_payload(content)
        return json.dumps(content, ensure_ascii=False)

    if isinstance(content, str):
        # prevent accidental double-embedding
        if content.strip().startswith("{"):
            raise ValueError("Refusing to store raw JSON string as content")
        return json.dumps({"content": [content], "schema_version": 1}, ensure_ascii=False)

    raise ValueError("content must be dict or str")


def _validate_payload(payload):
    if "content" not in payload or not isinstance(payload["content"], list):
        raise ValueError("payload.content must be a list")

    for c in payload["content"]:
        if not isinstance(c, str):
            raise ValueError("content items must be strings")
        if c.strip().startswith("{"):
            raise ValueError("content must not contain JSON strings")
