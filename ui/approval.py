import json
import streamlit as st

from core.db import get_review_state, upsert_review_state, write_audit
from core.tickets_full import create_or_update_ticket  # we’ll create this file next


REQUEST_TYPES = [
    "AP_INVOICE_PROCESSING",
    "AP_VENDOR_PAYMENT_INQUIRY",
    "AP_VENDOR_MASTERDATA_CHANGE",
    "EXPENSE_REIMBURSEMENT_ISSUE",
    "AR_CUSTOMER_INVOICE_REQUEST",
    "AR_CASH_APPLICATION",
    "AR_CREDIT_MEMO_REQUEST",
    "GL_JOURNAL_ENTRY_REQUEST",
    "AP_3WAY_MATCH_EXCEPTION",
    "CLOSE_SUPPORT_REQUEST",
]


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


def status_color(status: str) -> str:
    return {
        "NEW": "#334155",
        "PENDING_APPROVAL": "#0f766e",
        "NEEDS_INFO": "#b45309",
        "TICKETED": "#1d4ed8",
    }.get(status, "#334155")


def render_approval(email: dict, cached: dict, demo_users: dict, reviewer_name: str = "Demo Reviewer"):
    email_id = email["email_id"]

    # Load from DB if present
    db_state = get_review_state(email_id)
    if "finalized" not in st.session_state or st.session_state.get("active_email_id") != email_id:
        st.session_state.active_email_id = email_id
        if db_state:
            st.session_state.finalized = db_state["finalized"]
            st.session_state.review_status = db_state["review_status"]
        else:
            st.session_state.finalized = {
                "classification": cached["classification"],
                "extraction": cached["extraction"],
                "routing": cached["routing_suggestion"],
                "draft_response": cached["draft_response"],
                "overrides": {"routing_overridden": False, "override_reason": ""},
            }
            st.session_state.review_status = "NEW"
            write_audit("email", email_id, "AGENT_LOADED", reviewer_name, {"source": "agent_cache"})

    finalized = st.session_state.finalized
    extraction = finalized["extraction"]
    fields = extraction["fields"]

    # Required missing for this demo (keep minimal)
    REQUIRED_BY_TYPE = {
    "AP_INVOICE_PROCESSING": ["entity_code", "invoice_date", "invoice_number", "vendor_name", "po_number"],
    "AP_VENDOR_PAYMENT_INQUIRY": ["entity_code", "invoice_number", "vendor_name"],
    "AP_VENDOR_MASTERDATA_CHANGE": ["entity_code", "vendor_name", "vendor_id", "change_type"],
    "AP_3WAY_MATCH_EXCEPTION": ["entity_code", "po_number", "invoice_number"],
    "EXPENSE_REIMBURSEMENT_ISSUE": ["entity_code", "employee_id", "expense_report_id"],
    "AR_CUSTOMER_INVOICE_REQUEST": ["entity_code", "customer_name", "po_number", "invoice_amount"],
    "AR_CASH_APPLICATION": ["entity_code", "payment_amount", "bank_reference"],
    "AR_CREDIT_MEMO_REQUEST": ["entity_code", "customer_name", "invoice_number", "requested_credit_amount", "reason"],
    "GL_JOURNAL_ENTRY_REQUEST": ["entity_code", "effective_date", "amount", "debit_account", "credit_account"],
    "CLOSE_SUPPORT_REQUEST": ["entity_code", "account", "variance_amount"]
    }
    req_type = finalized["classification"]["request_type"]
    required = REQUIRED_BY_TYPE.get(req_type, ["entity_code"])

    required_missing = []
    for k in required:
        if k == "entity_code":
            if not extraction.get("entity_code"):
                required_missing.append("entity_code")
        else:
            if not fields.get(k):
                required_missing.append(k)

    total_required = 2
    complete = total_required - len(required_missing)
    completeness = complete / total_required if total_required else 1.0

    st.markdown("## 🧾 Finance Ops Intake — Approval")
    st.markdown(
        "<div class='muted' style='margin-top:-6px; margin-bottom:8px;'>"
        "Inbox → <b>Approval</b> → Ticket Queue"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="muted">
  <b>Subject:</b> {email["subject"]} <span style="margin:0 8px;">•</span>
  <b>Email ID:</b> {email_id} <span style="margin:0 8px;">•</span>
  <b>Received:</b> {email["received_at"]}
</div>
""",
        unsafe_allow_html=True,
    )

    h1, h2, h3, h4, h5 = st.columns([3.2, 1.2, 1.2, 2.2, 2.2])
    with h1:
        st.markdown(
            pill(f"STATUS: {st.session_state.review_status}", status_color(st.session_state.review_status)),
            unsafe_allow_html=True,
        )
        if required_missing:
            st.markdown(pill("BLOCKED: MISSING INFO", "#991b1b"), unsafe_allow_html=True)
        else:
            st.markdown(pill("READY TO APPROVE", "#15803d"), unsafe_allow_html=True)
    with h2:
        st.metric("Confidence", f"{finalized['classification']['confidence']:.2f}")
    with h3:
        st.metric("Type", finalized["classification"]["request_type"])
    with h4:
        st.write("Review completeness")
        st.progress(completeness)
        st.caption(f"{int(completeness*100)}% complete")
    with h5:
        top_save = st.button("💾 Save Draft", use_container_width=True)
        top_reset = st.button("↩️ Reset to Suggested", use_container_width=True)

    if top_reset:
        st.session_state.finalized = {
            "classification": cached["classification"],
            "extraction": cached["extraction"],
            "routing": cached["routing_suggestion"],
            "draft_response": cached["draft_response"],
            "overrides": {"routing_overridden": False, "override_reason": ""},
        }
        st.session_state.review_status = "NEW"
        write_audit("email", email_id, "RESET_TO_SUGGESTED", reviewer_name, {})
        st.rerun()

    if top_save:
        upsert_review_state(email_id, "PENDING_APPROVAL", st.session_state.finalized)
        st.session_state.review_status = "PENDING_APPROVAL"
        write_audit("email", email_id, "DRAFT_SAVED", reviewer_name, {})
        st.success("Draft saved (not ticketed).")

    st.divider()

    left, middle, right = st.columns([4.1, 4.3, 4.1], gap="large")

    # Source
    with left:
        st.markdown('<div class="zone tight">', unsafe_allow_html=True)
        st.markdown("### 🟦 Source")
        st.caption("Raw email is read-only. Reviewer decisions are based on this evidence.")
        meta = st.expander("Email metadata", expanded=False)
        with meta:
            st.write(f"**From:** {email['from']['name']} <{email['from']['email']}>")
            st.write(f"**To:** {', '.join(email['to'])}")
            if email.get("cc"):
                st.write(f"**CC:** {', '.join(email['cc'])}")
            if email.get("attachments"):
                st.write("**Attachments:**")
                for a in email["attachments"]:
                    st.write(f"- {a['filename']} ({a['filetype']})")

        st.text_area("Email body", value=email["body"], height=430, disabled=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Review
    with middle:
        st.markdown('<div class="zone tight">', unsafe_allow_html=True)
        st.markdown("### 🟨 Review")
        st.caption("Validate request type and extracted fields. Missing data is flagged explicitly.")

        tab1, tab2, tab3 = st.tabs(["Classification", "Fields", "Missing & Risk"])

        with tab1:
            req_type = finalized["classification"]["request_type"]
            new_req_type = st.selectbox("Request type", REQUEST_TYPES, index=REQUEST_TYPES.index(req_type))
            if new_req_type != req_type:
                before = req_type
                finalized["classification"]["request_type"] = new_req_type
                write_audit("email", email_id, "CLASSIFICATION_CHANGED", reviewer_name, {"before": before, "after": new_req_type})

            st.markdown("**Rationale**")
            st.info(finalized["classification"]["rationale"])

        with tab2:
            st.markdown("**Common fields**")
            requester_name = st.text_input("Requester name", value=extraction["requester"]["name"])
            requester_email = st.text_input("Requester email", value=extraction["requester"]["email"])
            entity_code = st.text_input("Entity code (required)", value=extraction.get("entity_code") or "")
            due_date = st.text_input("Due date (optional)", value=extraction.get("due_date") or "")

            def set_field(path: str, before, after):
                if before != after:
                    write_audit("email", email_id, "FIELD_EDITED", reviewer_name, {"field_path": path, "before": before, "after": after})

            set_field("extraction.requester.name", extraction["requester"]["name"], requester_name)
            set_field("extraction.requester.email", extraction["requester"]["email"], requester_email)
            set_field("extraction.entity_code", extraction.get("entity_code"), entity_code or None)
            set_field("extraction.due_date", extraction.get("due_date"), due_date or None)

            extraction["requester"]["name"] = requester_name
            extraction["requester"]["email"] = requester_email
            extraction["entity_code"] = entity_code or None
            extraction["due_date"] = due_date or None

            st.divider()
            st.markdown("**AP Invoice fields**")

            vendor_name = st.text_input("Vendor name", value=fields.get("vendor_name") or "")
            invoice_number = st.text_input("Invoice #", value=fields.get("invoice_number") or "")
            cA, cB = st.columns(2)
            with cA:
                invoice_amount = st.number_input("Invoice amount", value=float(fields.get("invoice_amount") or 0.0), step=1.0)
            with cB:
                currency = st.text_input("Currency", value=fields.get("currency") or "")
            po_number = st.text_input("PO #", value=fields.get("po_number") or "")
            service_period = st.text_input("Service period", value=fields.get("service_period") or "")
            invoice_date = st.text_input("Invoice date (required)", value=fields.get("invoice_date") or "")

            set_field("extraction.fields.vendor_name", fields.get("vendor_name"), vendor_name or None)
            set_field("extraction.fields.invoice_number", fields.get("invoice_number"), invoice_number or None)
            set_field("extraction.fields.invoice_amount", fields.get("invoice_amount"), float(invoice_amount))
            set_field("extraction.fields.currency", fields.get("currency"), currency or None)
            set_field("extraction.fields.po_number", fields.get("po_number"), po_number or None)
            set_field("extraction.fields.service_period", fields.get("service_period"), service_period or None)
            set_field("extraction.fields.invoice_date", fields.get("invoice_date"), invoice_date or None)

            fields["vendor_name"] = vendor_name or None
            fields["invoice_number"] = invoice_number or None
            fields["invoice_amount"] = float(invoice_amount)
            fields["currency"] = currency or None
            fields["po_number"] = po_number or None
            fields["service_period"] = service_period or None
            fields["invoice_date"] = invoice_date or None

        with tab3:
            missing = []
            if not extraction.get("entity_code"):
                missing.append("entity_code")
            if not fields.get("invoice_date"):
                missing.append("invoice_date")

            st.markdown("**Required missing**")
            if missing:
                st.error("Missing: " + ", ".join(missing))
            else:
                st.success("All required fields present.")

            st.markdown("**Risk flags**")
            flags = extraction.get("risk_flags") or []
            if flags:
                st.warning(", ".join(flags))
            else:
                st.caption("None")

        st.markdown("</div>", unsafe_allow_html=True)

    # Decide
    with right:
        st.markdown('<div class="zone tight">', unsafe_allow_html=True)
        st.markdown("### 🟩 Decide")
        st.caption("Route work, finalize draft response, then approve or request info.")

        routing = finalized["routing"]
        draft = finalized["draft_response"]

        tabR, tabD, tabT = st.tabs(["Routing", "Draft Reply", "Ticket Preview"])

        with tabR:
            queue_names = [q["display_name"] for q in demo_users["queues"]]
            current_queue = routing["queue"]
            queue_idx = queue_names.index(current_queue) if current_queue in queue_names else 0
            new_queue = st.selectbox("Queue", queue_names, index=queue_idx)

            queue_id = next((q["queue_id"] for q in demo_users["queues"] if q["display_name"] == new_queue), None)
            allowed_assignees = [a["name"] for a in demo_users["assignees"] if queue_id in a["queues"]] or [routing["assignee"]]
            assignee_idx = allowed_assignees.index(routing["assignee"]) if routing["assignee"] in allowed_assignees else 0
            new_assignee = st.selectbox("Assignee", allowed_assignees, index=assignee_idx)

            priorities = demo_users["priorities"]
            pr_idx = priorities.index(routing["priority"]) if routing["priority"] in priorities else 1
            new_priority = st.selectbox("Priority", priorities, index=pr_idx)

            routing_changed = (new_queue != routing["queue"]) or (new_assignee != routing["assignee"]) or (new_priority != routing["priority"])
            if routing_changed:
                finalized["overrides"]["routing_overridden"] = True
                override_reason = st.selectbox("Override reason (required)", demo_users["override_reasons"], index=0)
                finalized["overrides"]["override_reason"] = override_reason
                st.warning("Routing overridden — reason will be logged.")
            else:
                finalized["overrides"]["routing_overridden"] = False
                finalized["overrides"]["override_reason"] = ""

            def audit_routing(field: str, before, after):
                if before != after:
                    write_audit("email", email_id, "ROUTING_CHANGED", reviewer_name, {"field": field, "before": before, "after": after})

            audit_routing("queue", routing["queue"], new_queue)
            audit_routing("assignee", routing["assignee"], new_assignee)
            audit_routing("priority", routing["priority"], new_priority)

            routing["queue"] = new_queue
            routing["assignee"] = new_assignee
            routing["priority"] = new_priority

        with tabD:
            st.markdown(pill("DRAFT — NOT SENT", "#0f172a"), unsafe_allow_html=True)
            new_subj = st.text_input("Subject", value=draft["subject"])
            new_body = st.text_area("Body", value=draft["body"], height=260)

            if new_subj != draft["subject"]:
                write_audit("email", email_id, "DRAFT_EDITED", reviewer_name, {"field": "subject", "before": draft["subject"], "after": new_subj})
                draft["subject"] = new_subj
            if new_body != draft["body"]:
                write_audit("email", email_id, "DRAFT_EDITED", reviewer_name, {"field": "body", "before": "(previous)", "after": "(updated)"})
                draft["body"] = new_body

            if required_missing:
                st.markdown("**Questions (auto-generated)**")
                for q in draft.get("questions_for_requester", []):
                    st.write(f"- {q}")

        with tabT:
            title_default = f"{finalized['classification']['request_type']}: {fields.get('vendor_name') or 'Vendor'} invoice {fields.get('invoice_number') or ''}".strip()
            st.text_input("Title", value=title_default)
            with st.expander("Ticket description (preview)", expanded=False):
                st.code(
                    json.dumps(
                        {
                            "agent_summary": extraction.get("free_text_summary"),
                            "extracted_fields": extraction,
                            "email_ref": {"email_id": email_id, "subject": email["subject"], "from": email["from"]["email"]},
                            "attachments": [a["filename"] for a in email.get("attachments", [])],
                        },
                        indent=2,
                    ),
                    language="json",
                )

        st.divider()
        st.markdown("#### Actions")

        if required_missing:
            st.markdown(
                "<div style='border:1px solid rgba(220,38,38,0.35); "
                "background: rgba(220,38,38,0.06); "
                "padding:10px 12px; border-radius:12px; margin: 6px 0 10px 0;'>"
                "<b>⚠️ Approval blocked</b><br/>"
                "<span style='color: rgba(30,41,59,0.85); font-size: 13px;'>"
                "Required information is missing. Use <b>Request More Info</b> to proceed."
                "</span>"
                "</div>",
                unsafe_allow_html=True,
            )

        a1, a2 = st.columns(2)
        with a1:
            request_info = st.button("❓ Request More Info", use_container_width=True)
            st.caption("Creates ticket: **Waiting on Requester**")
        with a2:
            approve = st.button("✅ Approve & Create Ticket", use_container_width=True)
            st.caption("Creates ticket: **Open** and assigns work")

        if request_info:
            st.session_state.review_status = "NEEDS_INFO"
            upsert_review_state(email_id, "NEEDS_INFO", st.session_state.finalized)
            write_audit("email", email_id, "REQUEST_MORE_INFO", reviewer_name, {"missing_required_fields": required_missing})

            title_default = f"{finalized['classification']['request_type']}: {fields.get('vendor_name') or 'Vendor'} invoice {fields.get('invoice_number') or ''}".strip()
            t_id = create_or_update_ticket(
                email_id=email_id,
                status="Waiting on Requester",
                title=title_default,
                request_type=finalized["classification"]["request_type"],
                queue=routing["queue"],
                assignee=routing["assignee"],
                priority=routing["priority"],
                from_email=email["from"]["email"],
                subject=email["subject"],
                payload=st.session_state.finalized,
            )
            write_audit("ticket", t_id, "TICKET_CREATED_OR_UPDATED", reviewer_name, {"status": "Waiting on Requester"})
            st.success(f"Ticket created: {t_id} (Waiting on Requester). Go to Ticket Queue.")

        if approve:
            if required_missing:
                st.error("Cannot approve: missing required fields. Use 'Request More Info' instead.")
            else:
                st.session_state.review_status = "TICKETED"
                upsert_review_state(email_id, "TICKETED", st.session_state.finalized)
                write_audit("email", email_id, "APPROVED", reviewer_name, {})

                title_default = f"{finalized['classification']['request_type']}: {fields.get('vendor_name') or 'Vendor'} invoice {fields.get('invoice_number') or ''}".strip()
                t_id = create_or_update_ticket(
                    email_id=email_id,
                    status="Open",
                    title=title_default,
                    request_type=finalized["classification"]["request_type"],
                    queue=routing["queue"],
                    assignee=routing["assignee"],
                    priority=routing["priority"],
                    from_email=email["from"]["email"],
                    subject=email["subject"],
                    payload=st.session_state.finalized,
                )
                write_audit("ticket", t_id, "TICKET_CREATED_OR_UPDATED", reviewer_name, {"status": "Open"})
                st.success(f"Approved. Ticket created: {t_id}. Go to Ticket Queue.")

        st.markdown("</div>", unsafe_allow_html=True)
