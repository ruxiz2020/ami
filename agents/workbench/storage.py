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
