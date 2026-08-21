"""
accounts.py
A lightweight "user account" system: Sign Up / Log In, and saving personal
defaults (home city, default ZIP, daily transit routes, health sensitivity
profile) so a logged-in user gets a personalized "Welcome Back" homepage
without re-entering settings.

HONESTY NOTE -- please read before wiring this into a real product:
Exactly like the community accessibility reports and saved locations
elsewhere in this app, accounts here live ONLY in `st.session_state`, in
memory, for the lifetime of one Streamlit session:

  * Signing up and logging back in works perfectly WITHIN one browser tab's
    session (session_state survives reruns/reloads while that session is
    alive), which is enough to demo "log in -> see your saved city
    instantly" end to end.
  * There is no real database, no password hashing, and no cross-session
    or cross-device persistence. Restarting the app, or opening the app in
    a different browser/tab, starts with zero accounts.
  * Passwords are stored in plain text in server-side memory for this
    session only -- completely fine for a demo login, but NEVER reuse a
    real password here, and don't treat this as a security control.

See README's "Extending it" section for the natural upgrade path (a small
SQLite users table + `hashlib`/`bcrypt` password hashing) if you want real
persistence.
"""

import streamlit as st

from cities import CITY_NAMES, get_city

ACCOUNTS_KEY = "accounts_store"
CURRENT_USER_KEY = "current_username"
MAX_SAVED_ROUTES = 8


def init_accounts_state():
    if ACCOUNTS_KEY not in st.session_state:
        st.session_state[ACCOUNTS_KEY] = {}
    if CURRENT_USER_KEY not in st.session_state:
        st.session_state[CURRENT_USER_KEY] = None


def current_user():
    """The logged-in username, or None if nobody's logged in."""
    init_accounts_state()
    return st.session_state[CURRENT_USER_KEY]


def is_logged_in() -> bool:
    return current_user() is not None


def get_account(username: str) -> dict:
    """The account dict for `username`, or None if it doesn't exist."""
    init_accounts_state()
    if not username:
        return None
    return st.session_state[ACCOUNTS_KEY].get(username)


def _default_account() -> dict:
    home_city = CITY_NAMES[0]
    return {
        "password": "",
        "home_city": home_city,
        "default_zip": get_city(home_city)["zips"][0]["zip"],
        "profile": {"asthma": False, "wheelchair": False},
        "saved_routes": [],
    }


def sign_up(username: str, password: str) -> tuple:
    """Create a new account and log in as it. Returns (ok, message)."""
    init_accounts_state()
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return False, "Please enter both a username and a password."
    if len(username) < 2:
        return False, "Username should be at least 2 characters."
    if len(password) < 4:
        return False, "Password should be at least 4 characters (demo login only -- not a secure one)."
    if username in st.session_state[ACCOUNTS_KEY]:
        return False, f"'{username}' is already signed up this session — try logging in instead."

    account = _default_account()
    account["password"] = password
    st.session_state[ACCOUNTS_KEY][username] = account
    st.session_state[CURRENT_USER_KEY] = username
    return True, f"Welcome, {username}! Your account is ready for this session."


def log_in(username: str, password: str) -> tuple:
    """Returns (ok, message)."""
    init_accounts_state()
    username = (username or "").strip()
    account = st.session_state[ACCOUNTS_KEY].get(username)
    if not account or account.get("password") != (password or ""):
        return False, "That username/password combination isn't recognized this session."
    st.session_state[CURRENT_USER_KEY] = username
    return True, f"Welcome back, {username}!"


def log_out():
    st.session_state[CURRENT_USER_KEY] = None


def save_preferences(username: str, city: str, zip_code: str, profile: dict) -> bool:
    """Persist (for this session) the user's preferred home city, default
    ZIP, and sensitivity profile onto their account."""
    account = get_account(username)
    if not account:
        return False
    account["home_city"] = city
    account["default_zip"] = zip_code
    account["profile"] = dict(profile)
    return True


def add_saved_route(username: str, city: str, origin: str, destination: str, label: str = "") -> bool:
    """Save a daily transit route (origin -> destination for a given city)
    to the user's account, keeping the most recent MAX_SAVED_ROUTES."""
    account = get_account(username)
    if not account:
        return False
    label = (label or "").strip() or f"{origin} → {destination}"
    account["saved_routes"] = [r for r in account["saved_routes"] if r["label"] != label]
    account["saved_routes"].insert(0, {
        "label": label, "city": city, "origin": origin, "destination": destination,
    })
    account["saved_routes"] = account["saved_routes"][:MAX_SAVED_ROUTES]
    return True


def remove_saved_route(username: str, label: str):
    account = get_account(username)
    if account:
        account["saved_routes"] = [r for r in account["saved_routes"] if r["label"] != label]


def apply_account_to_session(username: str, city_key: str, zip_key: str, profile_key_prefix: str):
    """Push a just-logged-in (or just-signed-up) user's saved preferences
    into the sidebar's own widget state (by key), the same pattern
    user_profile.apply_location() uses for saved locations -- so the city
    picker, ZIP field, and sensitivity toggles all pick the account's
    defaults up automatically on the next rerun."""
    account = get_account(username)
    if not account:
        return
    st.session_state[city_key] = account["home_city"]
    st.session_state[zip_key] = account["default_zip"]
    st.session_state[profile_key_prefix + "asthma"] = bool(account["profile"].get("asthma", False))
    st.session_state[profile_key_prefix + "wheelchair"] = bool(account["profile"].get("wheelchair", False))
