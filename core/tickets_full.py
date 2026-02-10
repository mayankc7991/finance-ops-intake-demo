import json
import sqlite3
from typing import Dict, List, Optional

from core.db import conn, now_iso


def ticket_exists_for_email(email_id: str) -> Optional[str]:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT ticket_id FROM tickets WHERE email_id=? LIMIT 1", (email_id,))
    row = cur.fetchone()
    c.close()
    return row[0] if row else None


def next_ticket_id() -> str:
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT ticket_id FROM tickets ORDER BY ticket_id DESC LIMIT 1")
    row = cur.fetchone()
    c.close()
    if not row:
        return "FIN-1001"
    last = row[0]
    try:
        n = int(last.split("-")[1])
    except Exception:
        n = 1000
    return f"FIN-{n+1}"


def create_or_update_ticket(
    *,
    email_id: str,
    status: str,
    title: str,
    request_type: str,
    queue: str,
    assignee: str,
    priority: str,
    from_email: str,
    subject: str,
    payload: dict,
) -> str:
    existing = ticket_exists_for_email(email_id)
    c = conn()
    cur = c.cursor()

    if existing:
        cur.execute(
            """
            UPDATE tickets
            SET updated_at=?,
                status=?,
                request_type=?,
                queue=?,
                assignee=?,
                priority=?,
                title=?,
                from_email=?,
                subject=?,
                payload_json=?
            WHERE ticket_id=?
            """,
            (
                now_iso(),
                status,
                request_type,
                queue,
                assignee,
                priority,
                title,
                from_email,
                subject,
                json.dumps(payload, ensure_ascii=False),
                existing,
            ),
        )
        c.commit()
        c.close()
        return existing

    ticket_id = next_ticket_id()
    ts = now_iso()
    cur.execute(
        """
        INSERT INTO tickets(ticket_id, email_id, created_at, updated_at, status, request_type, queue, assignee, priority, title, from_email, subject, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticket_id,
            email_id,
            ts,
            ts,
            status,
            request_type,
            queue,
            assignee,
            priority,
            title,
            from_email,
            subject,
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    c.commit()
    c.close()
    return ticket_id


def list_tickets(filters: dict) -> List[dict]:
    c = conn()
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    where = []
    params = []

    if filters.get("status") and filters["status"] != "All":
        where.append("status=?")
        params.append(filters["status"])
    if filters.get("queue") and filters["queue"] != "All":
        where.append("queue=?")
        params.append(filters["queue"])
    if filters.get("assignee") and filters["assignee"] != "All":
        where.append("assignee=?")
        params.append(filters["assignee"])

    sql = "SELECT * FROM tickets"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    c.close()
    return [dict(r) for r in rows]


def ticket_metrics() -> Dict[str, int]:
    c = conn()
    cur = c.cursor()
    metrics = {}
    for s in ["Open", "Waiting on Requester", "In Progress", "Resolved"]:
        cur.execute("SELECT COUNT(*) FROM tickets WHERE status=?", (s,))
        metrics[s] = int(cur.fetchone()[0])
    c.close()
    return metrics
