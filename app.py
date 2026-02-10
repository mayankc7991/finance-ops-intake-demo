import streamlit as st

# --- Demo password gate (free Streamlit Cloud) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Private Demo")
    st.caption("Authorized users only.")
    pwd = st.text_input("Enter demo password", type="password")
    if pwd and pwd == st.secrets.get("DEMO_PASSWORD", ""):
        st.session_state.auth = True
        st.rerun()
    st.stop()


import os
import streamlit as st
from dotenv import load_dotenv

from core.data import load_json, index_emails
from core.db import ensure_db
from ui.inbox import render_inbox
from ui.approval import render_approval
from ui.ticket_queue import render_ticket_queue

APP_TITLE = "Demo 1 — Finance Ops Intake"


st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")

st.markdown(
    """
<style>
  .block-container { padding-top: 2.25rem; padding-bottom: 1.5rem; }
  header[data-testid="stHeader"] { height: 0px; }
  .muted { color: rgba(30,41,59,0.75); font-size: 13px; }
  .zone {
    border: 1px solid rgba(148,163,184,0.35);
    border-radius: 14px;
    padding: 14px 14px 10px 14px;
    background: rgba(2,6,23,0.02);
  }
  .zone h3 { margin-top: 0px; }
  .tight hr { margin: 0.6rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

load_dotenv()
ensure_db()

emails = load_json(os.path.join("data", "inbox_emails.json"))
emails_by_id = index_emails(emails)
agent_cache = load_json(os.path.join("data", "agent_cache.json"))
demo_users = load_json(os.path.join("data", "demo_users.json"))

# session defaults
if "page" not in st.session_state:
    st.session_state.page = "Inbox"
if "active_email_id" not in st.session_state:
    st.session_state.active_email_id = emails[0]["email_id"]

st.sidebar.title("Demo 1")
page = st.sidebar.radio("Navigate", ["Inbox", "Approval", "Ticket Queue"], index=["Inbox","Approval","Ticket Queue"].index(st.session_state.page))
st.session_state.page = page

active_email = emails_by_id[st.session_state.active_email_id]
cached = agent_cache[st.session_state.active_email_id]

if page == "Inbox":
    render_inbox(emails, agent_cache, st.session_state.active_email_id)
elif page == "Approval":
    render_approval(active_email, cached, demo_users)
else:
    render_ticket_queue(demo_users)
