import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict


DB_PATH = os.path.join("storage", "demo.db")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def conn():
    os.makedirs("storage", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def ensure_db():
    c = conn()
    cur = c.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor_name TEXT NOT NULL,
            details_json TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS review_state (
            email_id TEXT PRIMARY KEY,
            review_status TEXT NOT NULL,
            last_saved_at TEXT NOT NULL,
            finalized_json TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            email_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            request_type TEXT NOT NULL,
            queue TEXT NOT NULL,
            assignee TEXT NOT NULL,
            priority TEXT NOT NULL,
            title TEXT NOT NULL,
            from_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )

    cur.execute("""CREATE INDEX IF NOT EXISTS idx_tickets_email_id ON tickets(email_id)""")

    c.commit()
    c.close()


def get_review_state(email_id: str) -> Optional[Dict]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT review_status, last_saved_at, finalized_json FROM review_state WHERE email_id=?", (email_id,))
    row = cur.fetchone()
    c.close()
    if not row:
        return None
    return {"review_status": row[0], "last_saved_at": row[1], "finalized": json.loads(row[2])}

def upsert_review_state(email_id: str, review_status: str, finalized: dict):
    c = conn()
    cur = c.cursor()
    cur.execute(
        """
        INSERT INTO review_state(email_id, review_status, last_saved_at, finalized_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email_id) DO UPDATE SET
            review_status=excluded.review_status,
            last_saved_at=excluded.last_saved_at,
            finalized_json=excluded.finalized_json
        """,
        (email_id, review_status, now_iso(), json.dumps(finalized, ensure_ascii=False)),
    )
    c.commit()
    c.close()


def write_audit(entity_type: str, entity_id: str, action: str, actor_name: str, details: dict):
    c = conn()
    cur = c.cursor()
    event_id = f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur.execute(
        """
        INSERT INTO audit_log(event_id, timestamp, entity_type, entity_id, action, actor_name, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, now_iso(), entity_type, entity_id, action, actor_name, json.dumps(details, ensure_ascii=False)),
    )
    c.commit()
    c.close()
