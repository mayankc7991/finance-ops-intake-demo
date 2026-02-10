import json
import streamlit as st

from core.tickets_full import list_tickets, ticket_metrics


def pill(text: str, bg: str, fg: str = "white") -> str:
    return f"""
    <span style="
      display:inline-block;
      padding:4px 10px;
      border-radius:999px;
      background:{bg};
      color:{fg};
      font-size:12px;
      font-weight:600;
      margin-right:8px;
      border: 1px solid rgba(255,255,255,0.12);
    ">{text}</span>
    """


def render_ticket_queue(demo_users: dict):
    st.markdown("## 🧾 Finance Ops Intake — Ticket Queue")
    st.markdown(
        "<div class='muted' style='margin-top:-6px; margin-bottom:12px;'>"
        "Inbox → Approval → <b>Ticket Queue</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    m = ticket_metrics()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open", m["Open"])
    k2.metric("Waiting on Requester", m["Waiting on Requester"])
    k3.metric("In Progress", m["In Progress"])
    k4.metric("Resolved", m["Resolved"])

    st.divider()

    queues = ["All"] + sorted({q["display_name"] for q in demo_users["queues"]})
    assignees = ["All"] + sorted({a["name"] for a in demo_users["assignees"]})
    statuses = ["All", "Open", "Waiting on Requester", "In Progress", "Resolved"]

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1.0])
    with f1:
        status_f = st.selectbox("Status", statuses, index=0)
    with f2:
        queue_f = st.selectbox("Queue", queues, index=0)
    with f3:
        assignee_f = st.selectbox("Assignee", assignees, index=0)
    with f4:
        st.button("🔄 Refresh", use_container_width=True)

    filters = {"status": status_f, "queue": queue_f, "assignee": assignee_f}
    tickets = list_tickets(filters)

    if not tickets:
        st.info("No tickets yet. Create one from the Approval screen.")
        return

    left, right = st.columns([3.2, 2.3], gap="large")
    with left:
        st.markdown("### Queue")
        table_rows = []
        for t in tickets:
            table_rows.append(
                {
                    "Ticket": t["ticket_id"],
                    "Status": t["status"],
                    "Priority": t["priority"],
                    "Queue": t["queue"],
                    "Assignee": t["assignee"],
                    "Title": t["title"],
                    "Updated": t["updated_at"][:19].replace("T", " "),
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        ticket_ids = [t["ticket_id"] for t in tickets]
        selected = st.selectbox("Open ticket", ticket_ids, index=0)

    with right:
        st.markdown("### Ticket Detail")
        t = next(x for x in tickets if x["ticket_id"] == selected)
        payload = json.loads(t["payload_json"])

        st.markdown(
            pill(f"{t['status']}", "#0f172a") + pill(f"Priority: {t['priority']}", "#334155"),
            unsafe_allow_html=True,
        )
        st.write(f"**Ticket:** {t['ticket_id']}")
        st.write(f"**Queue:** {t['queue']}")
        st.write(f"**Assignee:** {t['assignee']}")
        st.write(f"**Request type:** {t['request_type']}")
        st.write(f"**Created:** {t['created_at'][:19].replace('T',' ')}")
        st.write(f"**Updated:** {t['updated_at'][:19].replace('T',' ')}")

        st.divider()
        st.markdown("**Email reference**")
        st.write(f"From: {t['from_email']}")
        st.write(f"Subject: {t['subject']}")
        st.write(f"Email ID: {t['email_id']}")

        with st.expander("Extracted fields (snapshot)", expanded=False):
            st.code(json.dumps(payload["extraction"], indent=2), language="json")

        with st.expander("Draft response (snapshot)", expanded=False):
            st.write(f"**Subject:** {payload['draft_response']['subject']}")
            st.text_area("Body", payload["draft_response"]["body"], height=220, disabled=True)
