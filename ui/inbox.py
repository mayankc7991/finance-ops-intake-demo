import streamlit as st

from core.db import get_review_state
from core.tickets_full import ticket_exists_for_email


def _safe_get_status(email_id: str) -> str:
    rs = get_review_state(email_id)
    if not rs:
        return "NEW"
    return rs.get("review_status") or "NEW"


def _has_ticket(email_id: str) -> bool:
    return ticket_exists_for_email(email_id) is not None


def render_inbox(emails: list, agent_cache: dict, active_email_id: str):
    st.markdown("# 📩 Shared Finance Inbox")
    st.caption("Synthetic inbox for demo. Filter and select an email to review in Approval.")

    # ---- Build inbox rows with derived fields ----
    rows = []
    for e in emails:
        eid = e["email_id"]
        cache = agent_cache.get(eid, {})
        c = cache.get("classification", {})
        r = cache.get("routing_suggestion", {})

        status = _safe_get_status(eid)
        has_ticket = _has_ticket(eid)

        rows.append(
            {
                "Email ID": eid,
                "Received": e["received_at"][:19].replace("T", " "),
                "From": e["from"]["email"],
                "Subject": e["subject"],
                "Status": status,
                "Type": c.get("request_type", "UNKNOWN"),
                "Confidence": float(c.get("confidence", 0.0)),
                "Queue": r.get("queue", ""),
                "Assignee": r.get("assignee", ""),
                "Has Ticket": "Yes" if has_ticket else "No",
            }
        )

    # ---- Filters ----
    st.markdown("### Filters")
    f1, f2, f3, f4 = st.columns([1.2, 1.6, 1.1, 2.1])

    statuses = ["All", "NEW", "PENDING_APPROVAL", "NEEDS_INFO", "TICKETED"]
    types = ["All"] + sorted({x["Type"] for x in rows if x["Type"] != "UNKNOWN"})
    ticket_opts = ["All", "Yes", "No"]

    with f1:
        status_f = st.selectbox("Status", statuses, index=0)
    with f2:
        type_f = st.selectbox("Request type", types, index=0)
    with f3:
        ticket_f = st.selectbox("Has ticket", ticket_opts, index=0)
    with f4:
        q = st.text_input("Search (subject / from / id)", value="").strip().lower()

    def match(row):
        if status_f != "All" and row["Status"] != status_f:
            return False
        if type_f != "All" and row["Type"] != type_f:
            return False
        if ticket_f != "All" and row["Has Ticket"] != ticket_f:
            return False
        if q:
            hay = f"{row['Email ID']} {row['From']} {row['Subject']}".lower()
            return q in hay
        return True

    filtered = [r for r in rows if match(r)]

    st.divider()

    # ---- Inbox table ----
    st.markdown("### Inbox")
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Confidence": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    if not filtered:
        st.info("No emails match the current filters.")
        return

    # ---- Selection + navigation ----
    ids = [r["Email ID"] for r in filtered]

    # keep selection stable if current selection filtered out
    if active_email_id not in ids:
        active_email_id = ids[0]
        st.session_state.active_email_id = active_email_id

    selected = st.selectbox("Select email", ids, index=ids.index(active_email_id))

    # Persist selection
    if selected != st.session_state.get("active_email_id"):
        st.session_state.active_email_id = selected

    c1, c2 = st.columns([1.5, 2.5])
    with c1:
        if st.button("Open in Approval →", use_container_width=True):
            st.session_state.page = "Approval"
            st.rerun()
    with c2:
        st.caption("Opens the Approval screen for the selected email.")
