"""
feedback.py
A small "Send Feedback / Report a Bug" widget for the bottom of the
sidebar -- meant for exactly this kind of pilot/Week-1 stage, where the
fastest path to a better app is making it trivially easy for testers to
flag something broken or confusing the moment they notice it.

Two ways to send feedback, since different testers prefer different
things:
  1. A quick inline form that logs the note into `st.session_state` for
     this session (visible to nobody outside your own browser tab -- see
     the honesty note below) -- good for a fast "this button doesn't
     work" note without leaving the page.
  2. A link to an external form (e.g. a Google Form) for testers who'd
     rather fill out a fuller report, or when you want feedback collected
     somewhere durable that this session-only app can't provide itself.

HONESTY NOTE: like every other piece of user-generated content in this
app (saved locations, community posts, accessibility reports), feedback
logged here lives ONLY in `st.session_state` for this browser session --
it is NOT emailed, saved to a file, or sent anywhere. For a real pilot,
either wire `submit_feedback()` to write a row into the same SQLite
database `accounts.py` already sets up (see the README's "Extending it"
section), or point GOOGLE_FORM_URL at a real form and treat that as the
actual collection mechanism.
"""

import uuid
from datetime import datetime

import streamlit as st

FEEDBACK_KEY = "feedback_log"

# Replace with your pilot's real feedback form URL before a real test —
# this default is an intentional placeholder, not a working link.
GOOGLE_FORM_URL = "https://forms.gle/REPLACE-WITH-YOUR-PILOT-FEEDBACK-FORM"

CATEGORIES = ["🐛 Something's broken", "😕 Confusing", "💡 Idea", "✅ Compliment", "Other"]


def init_feedback_state():
    if FEEDBACK_KEY not in st.session_state:
        st.session_state[FEEDBACK_KEY] = []


def submit_feedback(identity: str, category: str, message: str, now: datetime = None) -> bool:
    message = (message or "").strip()
    if not message:
        return False
    init_feedback_state()
    now = now or datetime.now()
    st.session_state[FEEDBACK_KEY].insert(0, {
        "id": uuid.uuid4().hex,
        "identity": identity or "Guest",
        "category": category or "Other",
        "message": message,
        "timestamp": now,
    })
    return True


def get_feedback() -> list:
    init_feedback_state()
    return list(st.session_state[FEEDBACK_KEY])


def render_feedback_widget(identity: str = "Guest"):
    """Renders the feedback expander. Call this from inside `with
    st.sidebar:`, at the very bottom, after everything else."""
    init_feedback_state()
    with st.expander("💬 Send Feedback / Report a Bug"):
        st.caption("Pilot testing this app? A quick note here helps catch things before launch.")

        with st.form("feedback_form", clear_on_submit=True):
            category = st.selectbox("Type", options=CATEGORIES)
            message = st.text_area(
                "What's going on?", placeholder="e.g. The ZIP field didn't accept my ZIP code...",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send", use_container_width=True, type="primary")
            if submitted:
                if submit_feedback(identity, category, message):
                    st.success("Thanks — logged for this session.")
                else:
                    st.warning("Add a few words before sending.")

        count = len(get_feedback())
        if count:
            st.caption(f"💭 {count} note{'s' if count != 1 else ''} logged this session.")

        st.divider()
        st.caption(
            "Prefer a form? Use the pilot bug-report form below "
            "(the maintainer should replace this with a real link before testing begins):"
        )
        st.markdown(f"[🔗 Open bug report form]({GOOGLE_FORM_URL})")
