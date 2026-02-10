import json
from typing import Optional, Dict, List

from core.db import conn, now_iso


def ticket_exists_for_email(email_id: str) -> Optional[str]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT ticket_id FROM tickets WHERE email_id=? LIMIT 1", (email_id,))
    row = cur.fetchone()
    c.close()
    return row[0] if row else None


def get_ticket_status_for_email(email_id: str) -> Optional[str]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT status FROM tickets WHERE email_id=? LIMIT 1", (email_id,))
    row = cur.fetchone()
    c.close()
    return row[0] if row else None
